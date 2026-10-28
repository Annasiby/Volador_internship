from dataclasses import dataclass, field, asdict
from sensors import SensorReading
from typing import Any
from math import isfinite

@dataclass
class DroneObservation:
    """Stores one observation made during a drone flight."""

    observation_id: str
    drone_id: str
    latitude: float
    longitude: float
    altitude_m: float
    description: str
    
    
    sensor_readings: list[SensorReading] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("Observation ID cannot be empty.")

        if not self.drone_id.strip():
            raise ValueError("Drone ID cannot be empty.")

        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        for name, value in (
            ("latitude", self.latitude),
            ("longitude", self.longitude),
            ("altitude_m", self.altitude_m),
        ):
            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                raise TypeError(f"{name} must be a number.")

            if not isfinite(value):
                raise ValueError(f"{name} must be finite.")

       

        if not all(
            isinstance(reading, SensorReading)
            for reading in self.sensor_readings
        ):
            raise TypeError(
                "All readings must be SensorReading objects."
            )

    def add_sensor_reading(self, reading: SensorReading) -> None:
        """Attach a sensor measurement to this observation."""
        if not isinstance(reading, SensorReading):
            raise TypeError("Expected a SensorReading object.")

        self.sensor_readings.append(reading)

    def to_dict(self) -> dict[str, Any]:
        """Convert the observation and its readings into a dictionary."""
        data = asdict(self)
       

      

        return data
