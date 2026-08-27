import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "api_url": "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/get-data.php",
    "gemini_api_key": "",
    "center_charts": {},
    "center_charts_hidden": [],
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
