import random

def produce_random_wind_speed():
    """Produces a random wind speed between 0 and 100

    Returns:
        float: Float in the range [0, 100]
    """
    return random.random() * 100.0

def produce_random_power_output_in_kwh():
    """Produces a random power output in kWh between 0 and 3000

    Returns:
        float: Float in the range [0, 3000]
    """
    return random.random() * 3000.0

def produce_random_time_to_fail_in_seconds():
    """Produces a random time to fail in seconds between 0 and 30
    and chooses the max value between 1 and the random value

    Returns:
        float: Float in the range [1, 30]
    """
    return max(random.random() * 30.0, 1.0)
        
def produce_random_time_to_repair_in_seconds():
    """Produces a random time to repair in seconds between 0 and 5
    and chooses the max value between 1 and the random value

    Returns:
        float: Float in the range [1, 5]
    """    
    return max(random.random() * 5.0, 1.0)

