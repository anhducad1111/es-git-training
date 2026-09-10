import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "cam_ip": "192.168.1.114",
    "cam_port": 80,
    "stream_path": "/640x480.mjpeg",
    "led_brightness": 0,
    "jpeg_quality": 14,
    "detection_enabled": False,
    "detection_interval": 3,
    "detection_confidence": 0.5,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
