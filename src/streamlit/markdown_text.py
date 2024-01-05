

APP_FUNCTIONALITY = """ #### App Functionality 
Collect wind turbine metric data asynchronously from multiple wind turbines and display the data    """

APP_USAGE = """ 
    #### App Usage
    This app is designed to display the wind turbine metric data collected from multiple wind turbines.

    The data is collected from 5 wind turbines and the metrics have the following schema:\n
        {
            "turbine_number": int,
            "wind_speed": float,
            "power_output_in_kwh": float,
            "operational_status": OperationalStatus
            "timestamp": float
        }        
        
        e.g.

        {
            "turbine_number": 1,
            "wind_speed": 45.60188548192473,
            "power_output_in_kwh": 2830.78964464337,
            "operational_status": "ok"
            "timestamp": 1704307285.2808006
        }
    
    You can click the Display Metrics button to display the metrics from the wind turbines in the browser.
    
    Clicking this button multiple times will update the metrics displayed.
    """