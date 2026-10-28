
import json

from sensors import SensorReading
from drone_observation import  DroneObservation


# 1. Create two sensor measurements.
temperature = SensorReading(
    sensor_name="Temperature",
    value=28.5,
    unit="°C",
)

humidity = SensorReading(
    sensor_name="Humidity",
    value=65.0,
    unit="%",
)


# 2. Create drone observation.
observation = DroneObservation(
    observation_id="OBS-001",
    drone_id="DRONE-01",
    latitude=11.2588,
    longitude=75.7804,
    altitude_m=50.0,
    description="Survey of a green field",
)


# 3. Attach the sensor readings.
observation.add_sensor_reading(temperature)
observation.add_sensor_reading(humidity)


# 4. observation into a dictionary.
data = observation.to_dict()

with open("output", "w") as file:
    file.write(json.dumps(data, indent=2,ensure_ascii=False))


