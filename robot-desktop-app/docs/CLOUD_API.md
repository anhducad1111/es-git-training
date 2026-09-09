# Cloud API Integration

## Overview
Telemetry upload and data retrieval from cloud backend.

## Configuration
```python
# config.py
DEFAULT_CONFIG = {
    "cloud_api_url": "http://192.168.1.116/es-git-training/rover-telemetry-backend/public/api/v1",
    "device_uid": "rover-001"
}
```

## API Endpoints

### POST /telemetry
Upload telemetry data every 10 seconds.
```python
{
    "device_uid": "rover-001",
    "recorded_at": "2026-09-08T08:28:42.639Z",
    "temperature_c": 28.5,
    "humidity_pct": 47.0,
    "gas_ppm": 150,
    "distance_cm": 100,
    "auto_brake": true
}
```

### GET /rovers
List all rovers with status.

### GET /rovers/{uid}/latest
Get latest reading for a rover.

### GET /rovers/{uid}/readings
Get historical readings with pagination.

### GET /rovers/{uid}/summary
Get aggregated statistics.

### POST /rovers/{uid}/media
Upload snapshot images (multipart/form-data).

### GET /health
Service health check.

### GET /system
Gateway host metrics.

## Implementation

### CloudAPI Class
Location: `cloud_api.py`

```python
class CloudAPI:
    def __init__(self):
        self._config = load_config()
        self._base_url = self._config.get("cloud_api_url", "")
        self._device_uid = self._config.get("device_uid", "rover-001")
    
    def post_telemetry(self, data):
        # POST /telemetry
        pass
    
    def get_rovers(self):
        # GET /rovers
        pass
    
    def get_latest(self, device_uid=None):
        # GET /rovers/{uid}/latest
        pass
```

### Cloud Timer
```python
# In app.py
self._cloud_timer = QTimer()
self._cloud_timer.timeout.connect(self._send_cloud_update)
self._cloud_timer.start(10000)  # 10 seconds
```

## Error Handling
- Connection timeout: 10 seconds
- Retry on failure
- Log errors to UI

## Data Flow
1. ESP32 sends telemetry via WebSocket
2. App receives and updates UI
3. Every 10 seconds, POST to cloud API
4. Cloud stores in database
5. Historical data retrievable via GET endpoints
