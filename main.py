import asyncio
import random
from contextlib import asynccontextmanager
from enum import Enum
# import logging
from typing import List
import aiofiles
from pathlib import Path
from utils.utils import produce_random_wind_speed, produce_random_power_output_in_kwh, \
    produce_random_time_to_fail_in_seconds, produce_random_time_to_repair_in_seconds

import httpx
import typer
import uvicorn
from fastapi import FastAPI
import time

# Assume pydantic version 1.*
from pydantic import BaseModel

app = typer.Typer() 

# logger = logging.basicConfig(level=logging.INFO)


class OperationalStatus(str, Enum):
    """Class attributes with fixed, string values: ok and broken."""
    ok = "ok"
    broken = "broken"


class TurbineMetrics(BaseModel):
    """
    Data model for turbine metrics, which defines the schema for producing 
    and storing turbine metrics and the request body routed to the 
    grid monitor app.
    """
    turbine_number: int
    wind_speed: float
    power_output_in_kwh: float
    operational_status: OperationalStatus
    timestamp: float


repairs_queue = asyncio.Queue()  # Create a queue of work; non-blocking async queue.

class WindTurbine:
    def __init__(
        self,
        turbine_number: int,
        wind_speed: float,
        power_output_in_kwh: float,
        upload_frequency_in_seconds: float = 1.0,
        time_to_fail_in_seconds: float = max(random.random() * 30.0, 1.0),
        time_to_repair_in_seconds: float = max(random.random() * 5.0, 1.0),
        grid_monitor_url: str = "http://grid-monitor-app:8787",
    ) -> None:
        # This is the unique identifier of the turbine
        self.turbine_number = turbine_number

        # This defines the wind speed in km/h
        self.wind_speed = wind_speed
        
        # This defines the power output in kWh
        self.power_output_in_kwh = power_output_in_kwh

        # This defines how frequently the turbine produces metrics
        self.upload_frequency_in_seconds = upload_frequency_in_seconds
        
        # This defines after how many seconds from the start/repair the turbine should change its status to "broken"
        self.time_to_fail_in_seconds = time_to_fail_in_seconds
        
        # This defines how much time in seconds it takes for the repair to happen
        self.time_to_repair_in_seconds = time_to_repair_in_seconds
        
        # Here we define our current operational status of the turbine
        self.operational_status = OperationalStatus.ok
        
        # Here we can keep time since the turbine has started or the turbine has been repaired
        self.time_passed_in_seconds = 0.0
        
        # Make sure we store the url for the grid monitor to which we will be pushing our metrics
        self.grid_monitor_url = grid_monitor_url

    async def produce_metrics(self, turbine_metrics: TurbineMetrics) -> None:
        """Produce turbine metrics.

        Args:
            turbine_metrics (TurbineMetrics): Metrics to be pushed to the grid monitor app.
        """
        # Use 30s as default timeout instead of the default 5s when sending requests.
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.grid_monitor_url}/post_metrics",
                json=turbine_metrics.model_dump(),
                timeout=30,
            )
            r.raise_for_status()  # Raise HTTPStatusError if one occurred.

    async def repair(self):
        """Repair the wind turbine."""
        try:
            # Pull from the repairs queue
            await self.collect_repairs()
            await asyncio.sleep(self.time_to_repair_in_seconds)
            self.operational_status = OperationalStatus.ok
            self.time_passed_in_seconds = 0.0
        except Exception as e:
            print(f"Could not repair turbine: {self.turbine_number}", e)
            raise e

    async def receive_repairs(self):
        """Receive repairs for the wind turbine
        
        Note: This function should call repair when an engineer has been assigned to fix it.
        """
        try:
            # Put a message in the queue to indicate that the turbine is broken
            random_wind_speed = produce_random_wind_speed()
            random_power_output_in_kwh = produce_random_power_output_in_kwh()

            await repairs_queue.put(
                TurbineMetrics(
                    turbine_number=self.turbine_number, 
                    wind_speed=random_wind_speed,
                    power_output_in_kwh=random_power_output_in_kwh,
                    operational_status=self.operational_status,
                    timestamp=time.time()
                )
            )
            # Call the repair function to pull the message from the queue and repair the turbine
            await self.repair()
        except Exception as e:
            print(f"Could not receive repairs for turbine: {self.turbine_number}\n", e)
            raise e
    
    async def collect_repairs(self) -> TurbineMetrics:
        """Pull broken turbines from the repairs queue"""
        return await repairs_queue.get()

    async def produce_metrics_indefinitely(self) -> None:
        """Produce metrics indefinitely.

        While the turbine is running, it should produce metrics every upload_frequency_in_seconds.
        While the grid monitor app is running, it should collect metrics every upload_frequency_in_seconds.
        If the turbine has been running for time_to_fail_in_seconds or more, its status should be changed to broken,
            and it should start waiting for repairs, but still produce metrics.
        """

        while True:
        # OPTIONAL: Run the grid monitor app for 30 seconds
        # for _ in range(30):  
            await self.produce_metrics(
                TurbineMetrics(
                    turbine_number=self.turbine_number,
                    wind_speed = self.wind_speed,
                    power_output_in_kwh = self.power_output_in_kwh,
                    operational_status=self.operational_status,
                    timestamp=time.time()
                )
            )
            await asyncio.sleep(self.upload_frequency_in_seconds)
            self.time_passed_in_seconds += self.upload_frequency_in_seconds
            
            # Change the status to broken if the turbine has been running for time_to_fail_in_seconds or more
            if self.time_passed_in_seconds >= self.time_to_fail_in_seconds:
                self.operational_status = OperationalStatus.broken
                # OPTIONAL: Simulate new metrics when the turbine becomes broken then repaired
                # self.wind_speed = produce_random_wind_speed()
                # self.power_output_in_kwh = produce_random_power_output_in_kwh()

    async def receive_repairs_indefinitely(self) -> None:
        """Receive repairs indefinitely.

        Note: If the turbine is broken, it should get assigned a repair engineer. 
              Otherwise, it should sleep for upload_frequency_in_seconds.
        """
        while True:
        # OPTIONAL: Run the grid monitor app for 30 seconds
        # for _ in range(30):
            if self.operational_status == OperationalStatus.broken:
                await self.receive_repairs()
            else:
                await asyncio.sleep(self.upload_frequency_in_seconds)

    async def run(self) -> None:
        """Run the wind turbine app.

        Note: Create a task for producing metrics indefinitely and a task for receiving repairs indefinitely.
        """
        producer_task = asyncio.create_task(self.produce_metrics_indefinitely())
        listener_task = asyncio.create_task(self.receive_repairs_indefinitely())
        done, pending = await asyncio.wait(
            [producer_task, listener_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

@app.command()
def run_wind_turbine(
    turbine_number: int = typer.Option(
        default=1,
        help="Specify the unique identifier of the wind turbine",
    ),
    random_wind_speed: float = typer.Option(
        default=produce_random_wind_speed(),
        help="Specify the wind speed in km/h",
    ),
    random_power_output_in_kwh: float = typer.Option(
        default=produce_random_power_output_in_kwh(),
        help="Specify the power output in kWh",
    ),
    upload_frequency_in_seconds: float = typer.Option(
        default=1.0,
        help="Specify the frequency with which the turbine produces metrics",
    ),
    time_to_fail_in_seconds: float = typer.Option(
        default=max(random.random() * 30.0, 1.0),
        help="Specify the time after which the turbine should fail",
    ),
    time_to_repair_in_seconds: float = typer.Option(
        default=max(random.random() * 5.0, 1.0),
        help="Specify the time it takes for the turbine to be repaired",
    ),
    grid_monitor_url: str = typer.Option(
        default="http://grid-monitor-app:8787",
        help="Specify the url of the grid monitor app",
    ),
) -> None:
    """Create multiple wind turbines and run them asynchronously."""
    turbines = []

    for turbine_number in range(1, 6):        
        random_wind_speed = produce_random_wind_speed()
        random_power_output_in_kwh = produce_random_power_output_in_kwh()
        random_time_to_fail_in_seconds = produce_random_time_to_fail_in_seconds()
        random_time_to_repair_in_seconds = produce_random_time_to_repair_in_seconds()

        wind_turbine = WindTurbine(
            turbine_number,
            random_wind_speed,
            random_power_output_in_kwh,
            time_to_fail_in_seconds=random_time_to_fail_in_seconds,
            time_to_repair_in_seconds=random_time_to_repair_in_seconds
        )
        turbines.append(wind_turbine)

    asyncio.run(run_wind_turbines(turbines))

async def run_wind_turbines(turbines: List[WindTurbine]) -> None:
    """Run wind turbines asynchronously

    Args:
        turbines (List[WindTurbine]): List of wind turbines to be run asynchronously.
    """
    tasks = [turbine.run() for turbine in turbines]

    # Schedules the run() coroutine method to be executed concurrently, for each WindTurbine object, as a Task.
    await asyncio.gather(*tasks)


class GridMonitor:
    def __init__(self, engineer_count: int, metrics_queue: asyncio.Queue = None):
        self.engineer_count = engineer_count
        self.last_turbines_metrics = {}
        self.metrics_queue = metrics_queue

    async def dispatch_engineer(self, turbine_number: int, wind_speed: float, power_output_in_kwh: float) -> None:        
        """Dispatch an engineer to fix a broken wind turbine, if a repair engineer is available.

        Args:
            turbine_number (int): Unique identifier of the turbine.
            wind_speed (float): Wind speed in km/h.
            power_output_in_kwh (float): Power output in kWh.
        """
        # If there are no engineers available, log a message saying so. And wait for an engineer to become available.
        if self.engineer_count == 0:
            print("No engineers available. Waiting for one to become available.")
            # logging.info("No engineers available. Waiting for one to become available.")
            # return
        # If there are engineers available, dispatch one to fix the turbine.
        else:
            self.engineer_count -= 1  # Decrement the number of available repair engineers
            print(f"Dispatching an engineer to fix turbine: {turbine_number}")
            # logging.info(f"Dispatching an engineer to fix turbine: {turbine_number}")
            try:
                await WindTurbine(turbine_number, wind_speed, power_output_in_kwh).receive_repairs()
            except Exception as e:
                print(f"Could not dispatch an engineer to fix turbine: {turbine_number}\n", e)
                raise e

            self.engineer_count += 1  # Increment the number of available repair engineers

    async def collect_metrics(self) -> TurbineMetrics:
        """Collect metrics from the metrics queue.

        Returns:
            TurbineMetrics: Turbine metrics.
        """
        # Remove and return an item from the queue. If queue is empty, wait until an item is available.
        return await self.metrics_queue.get()

    async def store_metrics(self, turbine_metrics: TurbineMetrics) -> None:
        """Store turbine metrics in a Docker shared volume.

        Args:
            turbine_metrics (TurbineMetrics): Turbine metrics to be stored.
        """
        # Alternative: Store metrics in a database (e.g. S3, MongoDB, PostgreSQL, DynamoDB, etc.)
        project_dir = Path(__file__).parent.parent.absolute()
        data_dir = project_dir / "data/metrics_data"
        Path.mkdir(data_dir, parents=True, exist_ok=True)
        try:
            async with aiofiles.open(data_dir / f"turbine_{turbine_metrics.turbine_number}.txt", mode="a") as f:
                await f.write(turbine_metrics.model_dump_json())
                await f.write("\n")
        except Exception as e:
            print(f"Could not store metrics for turbine: {turbine_metrics.turbine_number}\n", e)
            raise e

    async def run(self) -> None:
        """Run the grid monitor app."""
        while True:
        # OPTIONAL: Run the grid monitor app for 30 seconds
        # for _ in range(30):
            try:
                turbine_metrics = await self.collect_metrics()
                # Once there are tubine metrics to be stored, store them
                await self.store_metrics(turbine_metrics)
                # Check if we already have some details for this wind turbine
                last_turbine_metrics = None
                if turbine_metrics.turbine_number in self.last_turbines_metrics:
                    last_turbine_metrics = self.last_turbines_metrics[turbine_metrics.turbine_number]  # Get the turbine metrics for the turbine number
                self.last_turbines_metrics[turbine_metrics.turbine_number] = turbine_metrics
                # Dispatch an engineer only if we have not dispatched one already.
                # Optionally, improve the below logic to capture potential corner cases
                # If the turbine is broken, and it has not yet emitted any metrics, dispatch an engineer
                if (
                    turbine_metrics.operational_status == OperationalStatus.broken
                    and last_turbine_metrics is None
                ) or (
                    # If the turbine is broken, and it has emitted metrics previously, 
                    # and the last emitted metrics were ok, dispatch an engineer
                    turbine_metrics.operational_status == OperationalStatus.broken
                    and last_turbine_metrics.operational_status == OperationalStatus.ok
                ):
                    # Generate new/different metrics when the turbine becomes broken
                    await self.dispatch_engineer(
                        turbine_metrics.turbine_number,
                        produce_random_wind_speed(),
                        produce_random_power_output_in_kwh(),
                    )
            except Exception as e:
                print("Could not run the grid monitor app.\n", e)
                raise e


grid_monitor_task = None
grid_monitor_metrics_queue = asyncio.Queue()  # Create a queue of work; non-blocking async queue.
grid_monitor = GridMonitor(5, metrics_queue=grid_monitor_metrics_queue)  # Create a grid monitor instance with 3 engineers.


@asynccontextmanager
async def grid_monitor_lifespan(app: FastAPI):
    """Define the startup and shutdown logic for the grid monitor app.
    
    Note:
        Everything before yield is executed before the app starts accepting requests, during startup.
        Everything after yield is executed after the app finishes handling requests, right before the shutdown.
    Args:
        app (FastAPI): FastAPI instance.
    """
    global grid_monitor_task
    grid_monitor_task = asyncio.create_task(grid_monitor.run())
    yield
    if not grid_monitor_task.done():
        grid_monitor_task.cancel()

# Pass in the async context manager directly into FastAPI
grid_monitor_app = FastAPI(lifespan=grid_monitor_lifespan)


@grid_monitor_app.post("/post_metrics")
async def on_post_metrics(turbine_metrics: TurbineMetrics) -> None:
    """POST request endpoint for pushing turbine metrics.

    Args:
        turbine_metrics (TurbineMetrics): Turbine metrics to be pushed to the grid monitor app.
    """
    # Put an item into the queue. If the queue is full, wait until a free slot is available before adding item.
    await grid_monitor_metrics_queue.put(turbine_metrics)


@app.command()
def run_grid_monitor(
    host: str = typer.Option(
        default="grid-monitor-app",
        help="Specify the hostname on which the monitor should listen on",
    ),
    port: int = typer.Option(
        default="8787",
        help="Specify the base port on which the monitor should listen on",
    ),
) -> None:
    """Run the grid monitor app. This is the main entry point for the program."""
    uvicorn.run(grid_monitor_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()  # Run the Typer app
