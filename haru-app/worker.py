import os
import requests
from PyQt6.QtCore import QThread, pyqtSignal


class ProgressFileReader:
  def __init__(self, file_path, progress_callback):
    self._file = open(file_path, "rb")
    self._size = os.path.getsize(file_path)
    self._read = 0
    self._callback = progress_callback
    self._finished = False

  def read(self, size=-1):
    chunk_size = 8192
    if size == -1:
      size = chunk_size
    data = self._file.read(min(size, chunk_size))
    if not data:
      self._finished = True
      return data
    self._read += len(data)
    if self._size > 0:
      percent = min(99, int(self._read / self._size * 100))
      self._callback(percent)
    return data

  def close(self):
    self._file.close()


class Worker(QThread):
  finished = pyqtSignal(str, object)
  error = pyqtSignal(str)
  progress = pyqtSignal(int)

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
        reader = ProgressFileReader(self.file_path, self._on_progress)
        try:
          fname = self.file_path.split("/")[-1].split("\\")[-1]
          files = {"file": (fname, reader)}
          response = requests.post(self.url, files=files, timeout=10)
          reader.close()
          self.finished.emit("upload", response)
        except Exception:
          reader.close()
          raise
    except requests.exceptions.RequestException as e:
      self.error.emit(str(e))

  def _on_progress(self, percent):
    self.progress.emit(percent)
