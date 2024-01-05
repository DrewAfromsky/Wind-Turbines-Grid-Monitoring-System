Take Home Assignment - Smart Grid Monitoring System

You are a software engineer at a company specializing in smart grid technologies.
Your task is to develop a system that can collect real-time metrics from wind turbines,
identify broken ones and dispatch engineers for repairs as needed.

As part of your task you will need to:
1. Simulate a set of wind turbines (at least 5) simultaneously generating real-time data. Each turbine should produce metrics such as wind speed, power output, and operational status.
2. Implement a mechanism to store this data.
3. Implement a mechanism to dispatch engineers to repair broken wind turbines.

You are given the Python code below which contains `WindTurbine` and `GridMonitor` classes.
The goal of this assignment is to implement the following methods, defined with placeholders below:
1. `WindTurbine.receive_repairs`
2. `GridMonitor.dispatch_engineer`
3. `GridMonitor.store_metrics`

You will also need to define an entrypoint to start the `WindTurbine`.
`WindTurbine` core logic is expected to be started by calling `run` method.

```python
import asyncio
import random
from contextlib import asynccontextmanager
from enum import Enum

import httpx
import typer
import uvicorn
from fastapi import FastAPI

# Assume pydantic version 1.*
from pydantic import BaseModel

app = typer.Typer()


class OperationalStatus(str, Enum):
    ok = "ok"
    broken = "broken"


class TurbineMetrics(BaseModel):
    turbine_number: int
    wind_speed: float
    power_output_in_kwh: float
    operational_status: OperationalStatus


class WindTurbine:
    def __init__(
        self,
        turbine_number: int,
        upload_frequency_in_seconds: float = 1.0,
        time_to_fail_in_seconds: float = max(random.random() * 30.0, 1.0),
        time_to_repair_in_seconds: float = max(random.random() * 5.0, 1.0),
        grid_monitor_url: str = "http://localhost:8787",
    ) -> None:
        # This is the unique identifier of the turbine
        self.turbine_number = turbine_number
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
        # Use 30s as default timeout instead of the default 5s
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.grid_monitor_url}/post_metrics",
                json=turbine_metrics.dict(),
                timeout=30,
            )
            r.raise_for_status()

    async def repair(self):
        await asyncio.sleep(self.time_to_repair_in_seconds)
        self.operational_status = OperationalStatus.ok
        self.time_passed_in_seconds = 0.0

    async def receive_repairs(self):
        # This function should call repair when an engineer has been assigned to fix it.
        raise NotImplementedError("Please implement")

    async def produce_metrics_indefinitely(self) -> None:
        while True:
            await self.produce_metrics(
                TurbineMetrics(
                    turbine_number=self.turbine_number,
                    wind_speed=100.0,
                    power_output_in_kwh=3000.0,
                    operational_status=self.operational_status,
                )
            )
            await asyncio.sleep(self.upload_frequency_in_seconds)
            self.time_passed_in_seconds += self.upload_frequency_in_seconds
            # This should be atomic too
            if self.time_passed_in_seconds >= self.time_to_fail_in_seconds:
                self.operational_status = OperationalStatus.broken

    async def receive_repairs_indefinitely(self) -> None:
        while True:
            if self.operational_status == OperationalStatus.broken:
                await self.receive_repairs()
            else:
                await asyncio.sleep(self.upload_frequency_in_seconds)

    async def run(self) -> None:
        producer_task = asyncio.create_task(self.produce_metrics_indefinitely())
        listener_task = asyncio.create_task(self.receive_repairs_indefinitely())
        done, pending = await asyncio.wait(
            [producer_task, listener_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()


class GridMonitor:
    def __init__(self, engineer_count: int, metrics_queue: asyncio.Queue = None):
        self.engineer_count = engineer_count
        self.last_turbines_metrics = {}
        self.metrics_queue = metrics_queue

    async def dispatch_engineer(self, turbine_number: int) -> None:
        raise NotImplementedError("Please implement")

    async def collect_metrics(self) -> TurbineMetrics:
        return await self.metrics_queue.get()

    async def store_metrics(self, turbine_metrics: TurbineMetrics) -> None:
        raise NotImplementedError("Please implement")

    async def run(self) -> None:
        while True:
            turbine_metrics = await self.collect_metrics()
            await self.store_metrics(turbine_metrics)
            # Check if we already have some details for this wind turbine
            last_turbine_metrics = None
            if turbine_metrics.turbine_number in self.last_turbines_metrics:
                last_turbine_metrics = self.last_turbines_metrics[
                    turbine_metrics.turbine_number
                ]
            self.last_turbines_metrics[turbine_metrics.turbine_number] = turbine_metrics
            # Dispatch an engineer only if we have not dispatched one already.
            # Optionally, improve the below logic to capture potential corner cases
            if (
                turbine_metrics.operational_status == OperationalStatus.broken
                and last_turbine_metrics is None
            ) or (
                turbine_metrics.operational_status == OperationalStatus.broken
                and last_turbine_metrics.operational_status == OperationalStatus.ok
            ):
                await self.dispatch_engineer(turbine_metrics.turbine_number)


grid_monitor_task = None
grid_monitor_metrics_queue = asyncio.Queue()
grid_monitor = GridMonitor(3, metrics_queue=grid_monitor_metrics_queue)


@asynccontextmanager
async def grid_monitor_lifespan(app: FastAPI):
    global grid_monitor_task
    grid_monitor_task = asyncio.create_task(grid_monitor.run())
    yield
    if not grid_monitor_task.done():
        grid_monitor_task.cancel()


grid_monitor_app = FastAPI(lifespan=grid_monitor_lifespan)


@grid_monitor_app.post("/post_metrics")
async def on_post_metrics(turbine_metrics: TurbineMetrics) -> None:
    await grid_monitor_metrics_queue.put(turbine_metrics)


@app.command()
def run_grid_monitor(
    host: str = typer.Option(
        default="localhost",
        help="Specify the hostname on which the monitor should listen on",
    ),
    port: int = typer.Option(
        default="8787",
        help="Specify the base port on which the monitor should listen on",
    ),
) -> None:
    uvicorn.run(grid_monitor_app, host=host, port=port)


if __name__ == "__main__":
    app()
```

Your primary task is to implement the missing methods mentioned above and create a runnable script for `WindTurbine` and `GridMonitor`.
At minimum, you should be able to run the services locally and show how they interact with one another.
Optionally, you may choose to take any or all of the following steps if you feel it would improve the output of your project:
- Write tests to demonstrate that your implementation works under multiple scenarios
- Dockerize the code to make it easier to run multiple instances and scale up and down with the desired number of wind turbines
- Alter the methods provided in the `WindTurbine` and `GridMonitor` classes (as long as the core logic is kept the same) to improve communication between the services
- Stand up a lightweight GUI using any of the available Python frameworks for this purpose (i.e., Streamlit or similar) rather than interacting with the services using a script

Solution assumptions:
- You can safely assume every turbine breaks after a random amount of time
- You can safely assume every turbine takes a fixed amount of time to repair it
- The turbine should continue to produce metrics even when it is "broken"
- Turbines can come up online at anytime and start sending messages
- For turbines that go offline you can assume the engineer immediately returns to the pool of available engineers
- Only one engineer is needed per turbine to repair it
- We do not care a lot about performance; focus on reliably and cleanly fulfilling the requirements described above.
- We do not care a lot about how the metrics are stored as long as we can easily show what was collected
- Rely on existing Python frameworks to the extent possible e.g. httpx (or similar) for making requests, FastAPI (or similar) for web servers, websockets for streams
- You can assume static wind_speed and power_output_in_kwh for every turbine (though variable values can help you debug)
- You can assume only one instance of `GridMonitor` will run at a time, but be prepared to answer questions related to how you would scale it beyond one instance

Please ask as many clarifying questions as you like before starting your implementation. Have fun!
