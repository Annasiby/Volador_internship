
from dataclasses import dataclass, asdict

from math import isfinite
from typing import Any


@dataclass
class SensorReading:
    """Stores one measurement collected by a drone sensor."""

    sensor_name: str
    value: float
    unit: str
    
    

    def __post_init__(self) -> None:
        if not self.sensor_name.strip():
            raise ValueError("Sensor name cannot be empty.")

        if not self.unit.strip():
            raise ValueError("Unit cannot be empty.")

        if isinstance(self.value, bool) or not isinstance(
            self.value, (int, float)
        ):
            raise TypeError("Sensor value must be a number.")

        if not isfinite(self.value):
            raise ValueError("Sensor value must be finite.")

       

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
       
        return data
