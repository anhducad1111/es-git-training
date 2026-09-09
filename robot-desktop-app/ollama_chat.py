import requests
from PyQt6.QtCore import QThread, pyqtSignal


class OllamaChat(QThread):
    response = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, prompt, sensor_data=None):
        super().__init__()
        self.url = url
        self.prompt = prompt
        self.sensor_data = sensor_data or {}

    def run(self):
        context = f"Current sensor data: {self.sensor_data}\n\nUser question: {self.prompt}"
        payload = {
            "model": "llama3.2",
            "prompt": context,
            "stream": False,
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                self.response.emit(data.get("response", "No response"))
            else:
                self.error.emit(f"HTTP {resp.status_code}")
        except requests.exceptions.Timeout:
            self.error.emit("Timeout - Ollama not responding")
        except requests.exceptions.ConnectionError:
            self.error.emit("Cannot connect to Ollama")
        except Exception as e:
            self.error.emit(str(e))
