## Smart Grid Monitoring System

- Wind turbines emit metrics (`turbine_number, wind_speed, power_output_in_kwh, operational_status`) at some frequency, asynchronously; whether it is in an `"ok"` operational state or not (`"broken"`)
	- To simulate broken turbines, we define a number of seconds from the start or repair times, that the turbine should change its status to a `"broken"` operational status state
- For each turbine, the metrics are pushed (_JSON_ `POST` request) to a FastAPI endpoint, hosted by `uvicorn` worker
	- The endpoint for the app is responsible for pushing turbine metrics to an asynchronous queue that coordinates producer and consumer workflows for coroutines
	- When the app is launched, the app will check if metrics have been added to the queue
		- When metrics are pushed/`POST` requested to the app, they are then added into the queue
	- If there are items (turbine metrics) in the queue, then the turbine metrics are fetched/collected and subsequently persisted/stored/logged
		- An item is removed and returned from the queue
	- If there are no items in the queue, wait until the queue is non-empty
	- Turbine metrics are stored to disk (i.e. `.txt` file for each turbine, with each line containing a JSON data structure with all metrics for that turbine at every instance the metrics are emitted)
- If we've previously collected metrics from a turbine, then we will temporarily store its metrics in memory, and replace them with the latest turbine metric values; the last turbine metrics are used to determine if a repair engineer needs to be dispatched
- Dispatching an engineer to fix a broken wind turbine consists of modifying the operational status to `"ok"` after some random delay to simulate variance in repairs
		- If the turbine is broken (broken operational status) and there is no previous metrics recorded for the turbine, then a repair engineer would be dispatched
		- If the turbine is broken (broken operational status) and the previous metrics recorded for the turbine indicate the operational status was `"ok"`, then a repair engineer would be dispatched
		- A repair is simulated by sleeping for `time_to_repair_in_seconds`, updating the operational status to `"ok"` and resetting `time_passed_in_seconds` to `0.0` ; `time_passed_in_seconds` represents the time since the turbine has started or the turbine has been repaired and is used to help simulate broken turbines
