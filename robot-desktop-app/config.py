import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "car_ip": "192.168.1.113",
    "cam_ip": "192.168.1.114",
    "cloud_api_url": "http://192.168.1.116/es-git-training/rover-telemetry-backend/public/api",
    "device_uid": "rover-001",
    "ollama_url": "http://rpi5.local:11434/api/generate",
    "follow_mode_url": "http://rpi5.local/follow/start",
    "motor_speed": 220,
    "auto_brake": True,
    "brake_threshold": 30,
    "center_charts": {},
    "custom_charts": {},
    "custom_charts_normalize": {},
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Failed to save config: {e}")
