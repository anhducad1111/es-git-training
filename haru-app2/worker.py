import requests
from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
  finished = pyqtSignal(str, object)
  error = pyqtSignal(str)

  def __init__(self, task, url, payload=None, headers=None):
    super().__init__()
    self.task = task
    self.url = url
    self.payload = payload
    self.headers = headers or {}

  def run(self):
    try:
      if self.task == "get":
        response = requests.get(self.url, headers=self.headers, timeout=10)
        self.finished.emit("get", response)
      elif self.task == "post":
        response = requests.post(self.url, json=self.payload, headers=self.headers, timeout=10)
        self.finished.emit("post", response)
    except requests.exceptions.RequestException as e:
      self.error.emit(str(e))
