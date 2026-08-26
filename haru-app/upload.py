import os
import shutil
import tempfile
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


def build_ota_filename(original_path, ver, info, client):
  basename = os.path.splitext(os.path.basename(original_path))[0]
  ext = os.path.splitext(original_path)[1]
  filename_clean = ''.join(c for c in basename if c.isalnum())
  ver_formatted = ''.join(c for c in ver.replace(".", "_") if c.isalnum() or c == '_')
  info_clean = ''.join(c for c in info if c.isalnum())
  client_clean = ''.join(c for c in client if c.isalnum())
  return f"{filename_clean}-{ver_formatted}-{info_clean}-{client_clean}{ext}"


def upload_file(app):
  if not hasattr(app, "_upload_file_path"):
    return

  fname = app._upload_file_path.split("/")[-1].split("\\")[-1]
  ext = os.path.splitext(fname)[1].lower()
  if ext != ".bin":
    app.append_log(f"UPLOAD BLOCKED | {fname} is not a .bin file")
    QMessageBox.warning(app, "File Error", f"Only .bin files are allowed.\n{fname}")
    return

  size = os.path.getsize(app._upload_file_path)
  if size > 10 * 1024 * 1024 * 1024:
    app.append_log(f"UPLOAD BLOCKED | {fname} exceeds 10 GB limit")
    QMessageBox.warning(app, "File Error", f"File exceeds 10 GB limit.\n{fname}")
    return

  ver = app.ver_entry.text().strip()
  info = app.version_info_entry.text().strip()
  client = app.device_entry.text().strip()
  ota_filename = build_ota_filename(app._upload_file_path, ver, info, client)

  tmp_dir = tempfile.mkdtemp()
  tmp_path = os.path.join(tmp_dir, ota_filename)
  shutil.copy2(app._upload_file_path, tmp_path)

  base_url = app.url_entry.text().strip()
  ota_url = base_url + "?action=ota"
  app.append_log(f"UPLOADING | {ota_filename} ({size} bytes)")
  app.append_log(f"RENAME | {fname} -> {ota_filename}")
  app.upload_progress.setValue(0)

  headers = {"X-OTA-Key": OTA_KEY}

  app._upload_worker = Worker("upload", ota_url, file_path=tmp_path, headers=headers)
  app._upload_worker.finished.connect(lambda t, r: on_upload_done(app, t, r, tmp_dir))
  app._upload_worker.error.connect(lambda m: on_upload_error(app, m, tmp_dir))
  app._upload_worker.progress.connect(lambda p: app.upload_progress.setValue(p))
  app._upload_worker.start()


def on_upload_done(app, task, response, tmp_dir):
  app.upload_progress.setValue(0)
  app.append_log(f"UPLOAD RESP | Status {response.status_code}")
  app.append_log(f"UPLOAD BODY | {response.text}")
  if response.status_code in (200, 201):
    app.upload_btn.setVisible(False)
    app.upload_progress.setValue(100)
    app.append_log(f"UPLOAD OK | File uploaded successfully")
    app.file_path_label.setText("No file selected")
    app.file_path_label.setStyleSheet("color: gray; background-color: #f0f0f0;")
    if hasattr(app, "_upload_file_path"):
      del app._upload_file_path
  else:
    app.append_log(f"UPLOAD FAIL | Status {response.status_code}")
    app.show_disconnect_popup()
  shutil.rmtree(tmp_dir, ignore_errors=True)


def on_upload_error(app, msg, tmp_dir):
  app.upload_progress.setValue(0)
  app.append_log(f"ERROR | {msg}")
  app.show_disconnect_popup()
  shutil.rmtree(tmp_dir, ignore_errors=True)


def on_upload_error(app, msg):
  app.upload_progress.setValue(0)
  app.append_log(f"ERROR | {msg}")
  app.show_disconnect_popup()
