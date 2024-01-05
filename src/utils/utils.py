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
