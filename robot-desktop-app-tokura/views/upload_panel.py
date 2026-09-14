import os
import tempfile
import shutil
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout
)
from cloud_worker import CloudWorker


OTA_KEY = "shodai-haru-2026-8-25"


def create_upload_panel(app):
    group = QGroupBox("OTA FIRMWARE")
    group.setStyleSheet("""
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 10px 10px 10px;
            margin-top: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #f59e0b;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }
    """)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(6)

    file_row = QHBoxLayout()
    file_row.setSpacing(6)
    app._ota_file_btn = QPushButton("SELECT")
    app._ota_file_btn.setFixedHeight(26)
    app._ota_file_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #f59e0b;
            font-weight: 600;
            font-size: 10px;
            padding: 0 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #334155;
        }
    """)
    app._ota_file_btn.clicked.connect(lambda: _select_file(app))
    file_row.addWidget(app._ota_file_btn)

    app._ota_file_label = QLabel("No file selected")
    app._ota_file_label.setStyleSheet("color: #64748b; font-size: 10px;")
    app._ota_file_label.setWordWrap(True)
    file_row.addWidget(app._ota_file_label, 1)
    layout.addLayout(file_row)

    ver_row = QHBoxLayout()
    ver_row.setSpacing(6)
    ver_label = QLabel("VER")
    ver_label.setFixedWidth(30)
    ver_label.setStyleSheet("color: #64748b; font-size: 10px; letter-spacing: 1px;")
    ver_row.addWidget(ver_label)
    app._ota_ver_input = QLineEdit()
    app._ota_ver_input.setPlaceholderText("1.0.0")
    app._ota_ver_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 4px;
    """)
    ver_row.addWidget(app._ota_ver_input)
    layout.addLayout(ver_row)

    info_row = QHBoxLayout()
    info_row.setSpacing(6)
    info_label = QLabel("INFO")
    info_label.setFixedWidth(30)
    info_label.setStyleSheet("color: #64748b; font-size: 10px; letter-spacing: 1px;")
    info_row.addWidget(info_label)
    app._ota_info_input = QLineEdit()
    app._ota_info_input.setPlaceholderText("Release notes")
    app._ota_info_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 4px;
    """)
    info_row.addWidget(app._ota_info_input)
    layout.addLayout(info_row)

    url_row = QHBoxLayout()
    url_row.setSpacing(6)
    url_label = QLabel("URL")
    url_label.setFixedWidth(30)
    url_label.setStyleSheet("color: #64748b; font-size: 10px; letter-spacing: 1px;")
    url_row.addWidget(url_label)
    app._ota_url_input = QLineEdit()
    app._ota_url_input.setPlaceholderText("http://rpi5.local/ota/api/ota.php")
    app._ota_url_input.setText(app._config.get("ota_server_url", ""))
    app._ota_url_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 4px;
    """)
    url_row.addWidget(app._ota_url_input)
    layout.addLayout(url_row)

    app._ota_upload_btn = QPushButton("UPLOAD")
    app._ota_upload_btn.setFixedHeight(30)
    app._ota_upload_btn.setVisible(False)
    app._ota_upload_btn.setStyleSheet("""
        QPushButton {
            background-color: #f59e0b;
            color: #0a0e1a;
            font-weight: 700;
            font-size: 11px;
            border: none;
            border-radius: 4px;
            letter-spacing: 1px;
        }
        QPushButton:hover {
            background-color: #d97706;
        }
        QPushButton:disabled {
            background-color: #475569;
            color: #94a3b8;
        }
    """)
    app._ota_upload_btn.clicked.connect(lambda: _upload_file(app))
    layout.addWidget(app._ota_upload_btn)

    app._ota_progress = QProgressBar()
    app._ota_progress.setFixedHeight(6)
    app._ota_progress.setTextVisible(False)
    app._ota_progress.setStyleSheet("""
        QProgressBar {
            background-color: #1e293b;
            border: none;
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background-color: #f59e0b;
            border-radius: 3px;
        }
    """)
    app._ota_progress.setValue(0)
    layout.addWidget(app._ota_progress)

    group.setLayout(layout)
    return group


def _select_file(app):
    file_path, _ = QFileDialog.getOpenFileName(
        app, "Select Firmware", "", "Firmware Files (*.bin);;All Files (*)"
    )
    if file_path:
        app._ota_file_path = file_path
        fname = os.path.basename(file_path)
        size_kb = os.path.getsize(file_path) / 1024
        app._ota_file_label.setText(f"{fname} ({size_kb:.1f} KB)")
        app._ota_file_label.setStyleSheet("color: #e2e8f0; font-size: 10px;")
        app._ota_upload_btn.setVisible(True)


def _upload_file(app):
    if not hasattr(app, '_ota_file_path'):
        return

    file_path = app._ota_file_path
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".bin":
        QMessageBox.warning(app, "File Error", "Only .bin files are allowed.")
        return

    base_url = app._ota_url_input.text().strip()
    if not base_url:
        QMessageBox.warning(app, "URL Error", "Please enter server URL.")
        return

    ver = app._ota_ver_input.text().strip() or "1.0.0"
    info = app._ota_info_input.text().strip() or "firmware"
    device = app._config.get("device_uid", "rover-001")

    fname = _build_ota_filename(file_path, ver, info, device)

    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, fname)
    shutil.copy2(file_path, tmp_path)

    upload_url = base_url + ("&" if "?" in base_url else "?") + "action=ota"
    size = os.path.getsize(file_path)
    app._add_log("OTA", f"Uploading {fname} ({size} bytes)")
    app._add_log("OTA", f"URL: {upload_url}")

    app._ota_upload_btn.setEnabled(False)
    app._ota_progress.setValue(0)

    headers = {"X-OTA-Key": OTA_KEY}
    app._ota_worker = CloudWorker("UPLOAD", upload_url, file_path=tmp_path, headers=headers)
    app._ota_worker.result.connect(lambda r: _on_upload_done(app, r, tmp_dir))
    app._ota_worker.error.connect(lambda e: _on_upload_error(app, e, tmp_dir))
    app._ota_worker.start()


def _build_ota_filename(original_path, ver, info, client):
    basename = os.path.splitext(os.path.basename(original_path))[0]
    ext = os.path.splitext(original_path)[1]
    filename_clean = ''.join(c for c in basename if c.isalnum())
    ver_formatted = ''.join(c for c in ver.replace(".", "_") if c.isalnum() or c == '_')
    info_clean = ''.join(c for c in info if c.isalnum())
    client_clean = ''.join(c for c in client if c.isalnum())
    return f"{filename_clean}-{ver_formatted}-{info_clean}-{client_clean}{ext}"


def _on_upload_done(app, result, tmp_dir):
    app._ota_upload_btn.setEnabled(True)
    app._ota_progress.setValue(100)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if isinstance(result, dict) and result.get("error"):
        app._add_log("OTA", f"Upload failed: {result['error']}")
        QMessageBox.warning(app, "Upload Error", result["error"])
        return

    status = result.get("status", "") if isinstance(result, dict) else str(result)
    if "success" in str(status).lower() or "ok" in str(status).lower():
        app._add_log("OTA", "Upload successful")
        app._ota_file_label.setText("No file selected")
        app._ota_file_label.setStyleSheet("color: #64748b; font-size: 10px;")
        app._ota_upload_btn.setVisible(False)
        if hasattr(app, '_ota_file_path'):
            del app._ota_file_path
    else:
        msg = result.get("message", str(result)) if isinstance(result, dict) else str(result)
        app._add_log("OTA", f"Upload response: {msg}")
        QMessageBox.information(app, "Upload Result", str(msg))


def _on_upload_error(app, error, tmp_dir):
    app._ota_upload_btn.setEnabled(True)
    app._ota_progress.setValue(0)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    app._add_log("OTA", f"Upload error: {error}")
    QMessageBox.warning(app, "Upload Error", error)
