import requests
from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
  finished = pyqtSignal(str, object)
  error = pyqtSignal(str)

  def __init__(self, task, url, payload=None, file_path=None):
    super().__init__()
    self.task = task
    self.url = url
    self.payload = payload
    self.file_path = file_path

  def run(self):
    try:
      if self.task == "post":
        response = requests.post(self.url, json=self.payload, timeout=10)
        self.finished.emit("post", response)
      elif self.task == "get":
        response = requests.get(self.url, timeout=10)
        self.finished.emit("get", response)
      elif self.task == "upload":
        with open(self.file_path, "rb") as f:
          files = {"file": (self.file_path.split("/")[-1].split("\\")[-1], f)}
          response = requests.post(self.url, files=files, timeout=30)
          self.finished.emit("upload", response)
    except requests.exceptions.RequestException as e:
      self.error.emit(str(e))
