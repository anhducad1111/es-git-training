# ESP32 API Client

## Overview
REST API client for ESP32-Car sensor data and control.

## Base URL
```
http://192.168.1.113
```

## Endpoints

### GET /api/telemetry
Get all sensor data.
```json
{
    "temperature": 28.5,
    "humidity": 47.0,
    "gas": 150,
    "distance": 100
}
```

### GET /api/distance
Get distance sensor value.
```json
{"distance": 100}
```

### GET /api/distance?brake=1
Get distance and enable auto-brake.

### GET /api/distance?brake=0
Get distance and disable auto-brake.

### GET /api/pid
Get PID controller status.
```json
{
    "enabled": false,
    "kp": 0.2,
    "ki": 0.05,
    "kd": 0.1
}
```

### GET /servo/status
Get servo status.

### GET /servo/angle?pan=90&tilt=90
Set servo angles.

### GET /servo/center
Center servos.

### GET /speed?val=220
Set motor speed.

## Implementation
Location: `esp32_api.py`

```python
class ESP32API:
    def __init__(self, base_url):
        self._base_url = base_url
        self._timeout = 5
    
    def get_telemetry(self):
        resp = requests.get(f"{self._base_url}/api/telemetry", timeout=self._timeout)
        return resp.json()
    
    def set_brake(self, enabled):
        val = 1 if enabled else 0
        resp = requests.get(f"{self._base_url}/api/distance?brake={val}", timeout=self._timeout)
        return resp.json()
    
    def set_pid(self, enabled, kp, ki, kd):
        # Set PID parameters
        pass
```

## WebSocket Commands
Separate from REST API, sent via WebSocket:
```
forward         # Move forward
backward        # Move backward
left            # Turn left
right           # Turn right
stop            # Stop motors
drive:v,w       # Direct velocity control
servo:pan,tilt  # Set gimbal angles
speed:N         # Set motor speed
```

## Error Handling
- Timeout: 5 seconds
- Connection errors logged to UI
- Retry on failure
