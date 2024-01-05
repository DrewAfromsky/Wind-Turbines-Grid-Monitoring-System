## Smart Grid Monitoring System

![Architecture](https://github.com/DrewAfromsky/Wind-Turbines-Grid-Monitoring-System/blob/main/Architecture.pdf)

##### Problem Overview
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
		- When repairs are needed, wind turbine metrics for a particular wind turbine are put in a queue, retrieved and removed from the queue, repaired for some time by a dispatch engineer, and its operational status is reverted back to `"ok"`
			- A repair is simulated by sleeping for `time_to_repair_in_seconds`, updating the operational status to `"ok"` and resetting `time_passed_in_seconds` to `0.0` ; `time_passed_in_seconds` represents the time since the turbine has started or the turbine has been repaired and is used to help simulate broken turbines
##### Solution
###### How to Use
* The solution is deployed/packaged as Linux containers (i.e. via Docker), with all the dependencies and necessary files to keep the application isolated. 
* The containers have their own isolated running process, file system, and network. Additionally, there is a shared Volume because the `GridMonitor` creates the `metrics_data` directory for the wind turbine class to write to; the Streamlit app needs to read from it to display the data in the browser web app
	* The shared Volume allows us to persist the generated container data when the turbines emit and store metrics
* The containers are started/ran from the container images, which are based on an official Python image (i.e. static version of all the files, environment variables, and the default command/program present in the container). 
* Docker compose is used to create the stack of containers for the application, which references the necessary Docker images, coordinates dependency between the grid monitor app and the Streamlit app, and defines the shared volume. 
	* Docker compose defines multi-container applications and allows all services, defined in the compose `YAML` file, to be spun up or teared down. By default a shared network is also created between the containers.
	###### How to Use
	* Requires an installation of Docker, the the following commands can be ran to interface with the application:
		###### Build the Docker images
		- `docker build -t smartgridmonitor-gm --target grid-monitor-app . && docker build -t smartgridmonitor-wt --target wind-turbine-app . && docker build -t smartgridmonitor-test --target test .`
		###### Run the Docker images
		* `docker compose up -d`
		###### View the Logs
		- `docker compose logs -f`
			- Access the Streamlit app @ http://0.0.0.0:8501/
		###### Teardown Everything
		- `docker compose down --volumes && docker image rm smartgridmonitor-wt smartgridmonitor-gm smartgridmonitor-test`
			- Stop and remove containers, networks, as well as images
##### Considerations
- https://docs.streamlit.io/knowledge-base/tutorials/deploy/kubernetes
- https://docs.docker.com/language/python/deploy/
- **Container Memory**
	* Running a single process per container will have a more or less stable, and limited amount of memory consumed by the container
	* If we wanted to deploy this solution to a cluster, we'd be able to set those same memory limits and requirements in a configuration for the container management system like Kubernetes. That way, it will be able to replicate the container in the available machines taking into account the amount of memory needed by them, and the amount available in the machines in the cluster. The app is simple, so this wouldn't necessarily be a problem, but something to consider for more resource-intensive applications, where we would want to adjust the number of container in each machine or add more machines to the cluster
* **Data Store**
	* Currently, wind turbine data is emitted and stored/persisted to a shared Docker volume. Ideally, this would be substituted with storing the data to a NoSQL database like DynamoDB as a key-value store, which is good for high-speed reads and writes (i.e. storing turbine metrics in real-time) as well as horizontal scalability
##### Test Cases
- **TODO**
- 
* The testing conducted performs unit testing async `POST` requests to the grid monitor app (i.e. testing the ability to produce metrics)
* Other forms of validations including validating Streamlit app button clicks; the button for running the wind turbines that emit metrics needs to be clicked prior to displaying metrics and retrieving persisted data

***Things NOT tested:***
* (1.) Test code that makes an external HTTP request to a third-party API and database queries -- ideally would be able to mock the request.  
* (2.) If working with cloud-based storage or databases like DynamoDB, we can create temporary objects like a table via a `setupclass`, run a test on it, then tear it down via a `teardown class`, using SDK specific API calls to a cloud service.
* (3.) There are other forms of testing (integration testing, system testing, mutation testing, hypotheses testing, regression testing, etc) that are not in-scope for this problem.
##### Appendix
###### Wind Turbine Metrics Output Example
```json
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"ok","timestamp":1704427057.340093}
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"ok","timestamp":1704427058.441073}
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"broken","timestamp":1704427059.46271}
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"broken","timestamp":1704427060.5790033}
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"ok","timestamp":1704427061.654295}
{"turbine_number":1,"wind_speed":74.13200003176283,"power_output_in_kwh":2229.3846024355926,"operational_status":"ok","timestamp":1704427062.8082988}

{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427059.529272}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427060.6291208}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427061.703328}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427062.7679012}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427063.829862}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"broken","timestamp":1704427064.938169}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"broken","timestamp":1704427066.0461793}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"broken","timestamp":1704427067.0832596}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"broken","timestamp":1704427068.1439586}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427069.2387676}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427070.3042338}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427071.4122436}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427072.5106378}
{"turbine_number":2,"wind_speed":53.1781167355966,"power_output_in_kwh":2439.817544613848,"operational_status":"ok","timestamp":1704427073.5634034}
```

- Alternatively, we can simulate non-healthy wind turbines to have varying speeds and power outputs; Healthy wind turbines have consistent wind speed and power output
