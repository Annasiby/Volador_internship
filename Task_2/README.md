# Task 2: Drone Observation Data Model

This project models a drone observation and exports it as structured JSON data.

## Overview

The application defines two core data models:

- `SensorReading`: stores a single sensor measurement
- `DroneObservation`: stores a drone observation and its associated list of sensor readings

The script creates sample data, attaches sensor values, and writes the result to a JSON file.

## Files

- `sensors.py` — defines the `SensorReading` dataclass and validation rules
- `drone_observation.py` — defines the `DroneObservation` dataclass and validation rules
- `main.py` — creates example data and writes the final JSON output
- `output.json` — generated JSON result from the sample drone observation

## Features

- Validates required fields and numeric values
- Ensures sensor readings are finite and correctly typed
- Stores geolocation coordinates with range checks
- Serializes the object graph into JSON with nested sensor data

## Example Output

```json
{
  "observation_id": "OBS-001",
  "drone_id": "DRONE-01",
  "latitude": 11.2588,
  "longitude": 75.7804,
  "altitude_m": 50.0,
  "description": "Survey of a green field",
  "sensor_readings": [
    {
      "sensor_name": "Temperature",
      "value": 28.5,
      "unit": "°C"
    },
    {
      "sensor_name": "Humidity",
      "value": 65.0,
      "unit": "%"
    }
  ]
}