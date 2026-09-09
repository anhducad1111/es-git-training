import requests
from PyQt6.QtCore import QThread, pyqtSignal


class CloudWorker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, method, url, payload=None, timeout=10):
        super().__init__()
        self.method = method
        self.url = url
        self.payload = payload
        self.timeout = timeout

    def run(self):
        try:
            if self.method == "GET":
                resp = requests.get(self.url, timeout=self.timeout)
            elif self.method == "POST":
                resp = requests.post(self.url, json=self.payload, timeout=self.timeout)
            else:
                self.error.emit("Invalid method")
                return
            
            resp.raise_for_status()
            self.result.emit(resp.json())
        except requests.RequestException as e:
            self.error.emit(str(e))
