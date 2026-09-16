import os
import json
import socket

from secrets import GEMINI_API_KEY, HF_TOKEN

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "car_ip": "192.168.1.113",
    "cam_ip": "192.168.1.117",
    "cloud_api_url": "http://192.168.1.77/es-git-training/rover-telemetry-backend/public/api/v1",
    "device_uid": "rover-001",
    "gemini_api_key": GEMINI_API_KEY,
    "follow_mode_url": "http://rpi5.local/follow/start",
    "motor_speed": 220,
    "auto_brake": True,
    "brake_threshold": 30,
    "hf_token": HF_TOKEN,
    "remote_control_port": 8765,
    "cam_quality": 14,
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


def get_local_ip():
    """Best-effort LAN IP of this machine, for the web remote-control address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
