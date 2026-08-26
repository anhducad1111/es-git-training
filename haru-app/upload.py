import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from worker import Worker

OTA_KEY = "shodai-haru-2026-8-25"


def select_file(app):
  file_path, _ = QFileDialog.getOpenFileName(app, "Select File")
  if file_path:
    app._upload_file_path = file_path
    app.file_path_label.setText(file_path)
    app.file_path_label.setStyleSheet("color: black; background-color: #f0f0f0;")
    app.upload_btn.setVisible(True)


def upload_file(app):
  if not hasattr(app, "_upload_file_path"):
    return

  fname = app._upload_file_path.split("/")[-1].split("\\")[-1]
  ext = os.path.splitext(fname)[1].lower()
  if ext in (".md", ".txt"):
    app.append_log(f"UPLOAD BLOCKED | {fname} is a restricted file type")
    QMessageBox.warning(app, "File Error", f"Cannot upload .md or .txt files.\n{fname}")
    return

  size = os.path.getsize(app._upload_file_path)
  if size > 10 * 1024 * 1024 * 1024:
    app.append_log(f"UPLOAD BLOCKED | {fname} exceeds 10 GB limit")
    QMessageBox.warning(app, "File Error", f"File exceeds 10 GB limit.\n{fname}")
    return

  base_url = app.url_entry.text().strip()
  ota_url = base_url + "?action=ota"
  app.append_log(f"UPLOADING | {fname} ({size} bytes)")
  app.upload_progress.setValue(0)

  headers = {"X-OTA-Key": OTA_KEY}
  form_data = {
      "ver": app.ver_entry.text().strip(),
      "version_information": app.version_info_entry.text().strip(),
      "client": app.device_entry.text().strip()
  }

  app._upload_worker = Worker("upload", ota_url, file_path=app._upload_file_path, headers=headers, data=form_data)
  app._upload_worker.finished.connect(lambda t, r: on_upload_done(app, t, r))
  app._upload_worker.error.connect(lambda m: on_upload_error(app, m))
  app._upload_worker.progress.connect(lambda p: app.upload_progress.setValue(p))
  app._upload_worker.start()


def on_upload_done(app, task, response):
  fname = app._upload_file_path.split("/")[-1].split("\\")[-1]
  app.upload_progress.setValue(0)
  app.append_log(f"UPLOAD RESP | Status {response.status_code}")
  app.append_log(f"UPLOAD BODY | {response.text}")
  if response.status_code in (200, 201):
    app.upload_btn.setVisible(False)
    app.upload_progress.setValue(100)
    app.append_log(f"UPLOAD OK | {fname}")
  else:
    app.append_log(f"UPLOAD FAIL | Status {response.status_code}")
    app.show_disconnect_popup()


def on_upload_error(app, msg):
  app.upload_progress.setValue(0)
  app.append_log(f"ERROR | {msg}")
  app.show_disconnect_popup()
