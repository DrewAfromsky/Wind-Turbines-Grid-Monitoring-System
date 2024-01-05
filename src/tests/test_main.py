import pytest
from httpx import AsyncClient
import time

from main import grid_monitor_app as app
from main import OperationalStatus, TurbineMetrics, WindTurbine
import logging


# Testing the wind speed out of bounds
wt_turbine_metrics_wind_speed = WindTurbine(
    turbine_number=1,
    wind_speed=100.1,
    power_output_in_kwh=1.0,
)

turbine_metrics_wind_speed = TurbineMetrics(
    turbine_number=wt_turbine_metrics_wind_speed.turbine_number,
    wind_speed=wt_turbine_metrics_wind_speed.wind_speed,
    power_output_in_kwh=wt_turbine_metrics_wind_speed.power_output_in_kwh,
    operational_status=OperationalStatus.ok,
    timestamp=time.time()
)

# Testing the power output in kWh out of bounds
wt_turbine_metrics_power_output_in_kwh = WindTurbine(
    turbine_number=1,
    wind_speed=1.0,
    power_output_in_kwh=3000.1,
)

turbine_metrics_power_output_in_kwh = TurbineMetrics(
    turbine_number=wt_turbine_metrics_power_output_in_kwh.turbine_number,
    wind_speed=wt_turbine_metrics_power_output_in_kwh.wind_speed,
    power_output_in_kwh=wt_turbine_metrics_power_output_in_kwh.power_output_in_kwh,
    operational_status=OperationalStatus.broken,
    timestamp=time.time()
)

test_post_request_inputs = [
    (turbine_metrics_wind_speed.model_dump(), wt_turbine_metrics_wind_speed.grid_monitor_url),
    (turbine_metrics_power_output_in_kwh.model_dump(), wt_turbine_metrics_power_output_in_kwh.grid_monitor_url),
]

@pytest.mark.anyio
@pytest.mark.parametrize("metrics_model_dump, base_url", test_post_request_inputs)
async def test_post_request(metrics_model_dump, base_url):
    """Asynchronously test POST requests to the grid monitor app"""
    async with AsyncClient(app=app, base_url=base_url, timeout=30) as ac:
        response = await ac.post("/post_metrics", json=metrics_model_dump, timeout=30)
        response.raise_for_status()  # Raise HTTPStatusError if one occurred.

    assert response.status_code == 200