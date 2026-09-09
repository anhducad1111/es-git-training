# Configuration System

## Overview
JSON-based configuration with defaults and persistence.

## Config File
Location: `config.json` (project root)

## Default Values
```python
DEFAULT_CONFIG = {
    "car_ip": "192.168.1.113",
    "cam_ip": "192.168.1.87",
    "cloud_api_url": "http://192.168.1.116/es-git-training/rover-telemetry-backend/public/api/v1",
    "device_uid": "rover-001",
    "ollama_url": "http://rpi5.local:11434/api/generate",
    "follow_mode_url": "http://rpi5.local/follow/start",
    "motor_speed": 220,
    "auto_brake": True,
    "brake_threshold": 30,
    "center_charts": {},
    "custom_charts": {},
    "custom_charts_normalize": {}
}
```

## API

### Load Config
```python
from config import load_config
config = load_config()
```

### Save Config
```python
from config import save_config
save_config(config)
```

## Usage

### IP Configuration
```python
# In header.py
app._car_ip_input.setText(config["car_ip"])
app._cam_ip_input.setText(config["cam_ip"])
```

### Connection
```python
# In app.py
self._config = load_config()
self._rover_ws = RoverWS(self._config["car_ip"])
self._video_receiver = MJPEGReceiver(self._config["cam_ip"])
```

## Merging
When loading, defaults are merged with saved config:
```python
def load_config():
    if os.path.exists(CONFIG_FILE):
        config = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    return DEFAULT_CONFIG.copy()
```

## Runtime Changes
- IP changes require app restart
- Speed/brake changes apply immediately
- Chart settings persist automatically
