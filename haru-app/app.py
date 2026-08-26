import sys
import math
import random
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from worker import Worker
from chart import ChartWidget
from panels import create_config_group, create_input_group, create_upload_group, GROUP_BOX_STYLE
import upload as upload_mod


class DisconnectDialog(QDialog):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setModal(True)
    self.setWindowTitle("Connection Error")
    self.setFixedSize(400, 160)
    self.setStyleSheet("""
      QDialog { background-color: #FFEBEE; }
      QLabel { color: #B71C1C; font-size: 14px; font-weight: bold; }
    """)
    layout = QVBoxLayout()
    layout.setSpacing(15)

    msg = QLabel("Error: Disconnected to server!\nPlease wait...")
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(msg)

    hint = QLabel("Click OK to exit the application")
    hint.setStyleSheet("color: #555555; font-size: 11px; font-weight: normal;")
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(hint)

    btn_layout = QHBoxLayout()
    ok_btn = QPushButton("OK - Exit")
    ok_btn.setStyleSheet(
        "background-color: #E53935; color: white; font-weight: bold; padding: 8px 25px; border-radius: 4px;"
    )
    ok_btn.clicked.connect(self.accept)

    cancel_btn = QPushButton("Cancel - Continue")
    cancel_btn.setStyleSheet(
        "background-color: #42A5F5; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;"
    )
    cancel_btn.clicked.connect(self.reject)

    btn_layout.addWidget(ok_btn)
    btn_layout.addWidget(cancel_btn)
    layout.addLayout(btn_layout)

    self.setLayout(layout)

  def mousePressEvent(self, event):
    if not self.rect().contains(event.pos()):
      self.reject()


class SensorClientApp(QWidget):

  def __init__(self):
    super().__init__()
    self.tick = 0
    self.base_temp = 25.0
    self.base_humi = 60.0
    self.version_auto_running = False
    self.version_timer = QTimer()
    self.version_timer.setInterval(5000)
    self.version_timer.timeout.connect(self.fetch_latest_version)
    self.init_ui()
    self.fetch_latest_version()
    self.toggle_version_fetch()

  def init_ui(self):
    self.setWindowTitle("Haru - Sensor Logger Client")
    self.resize(1000, 600)

    main_layout = QHBoxLayout(self)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(10)

    left_layout = QVBoxLayout()
    left_layout.setSpacing(10)

    left_layout.addWidget(create_config_group(self))
    left_layout.addWidget(create_input_group(self))

    log_group = QGroupBox("Log Screen")
    log_group.setStyleSheet(GROUP_BOX_STYLE)
    log_layout = QVBoxLayout()
    self.log_display = QTextEdit()
    self.log_display.setReadOnly(True)
    self.log_display.setFixedHeight(250)
    self.log_display.setStyleSheet(
        "font-family: Consolas; font-size: 9pt; background-color: #212121; color: #FFFFFF;"
    )
    log_layout.addWidget(self.log_display)
    log_group.setLayout(log_layout)
    left_layout.addWidget(log_group)

    left_layout.addStretch()

    self.chart_widget = ChartWidget(on_refresh=self.fetch_logs)

    right_layout = QVBoxLayout()
    right_layout.addWidget(self.chart_widget)
    right_layout.addWidget(create_upload_group(self))

    main_layout.addLayout(left_layout, stretch=1)
    main_layout.addLayout(right_layout, stretch=2)

  def unpin_version(self):
    from worker import Worker
    url = "http://192.168.1.116/es-git-training/esp32-ota/api/target.php"
    headers = {"X-OTA-Key": "shodai-haru-2026-8-25"}
    data = {"action": "clear"}
    self.append_log("UNPIN | Sending clear request...")
    self._unpin_worker = Worker("post", url, data=data, headers=headers)
    self._unpin_worker.finished.connect(self.on_unpin_result)
    self._unpin_worker.error.connect(self.on_unpin_error)
    self._unpin_worker.start()

  def on_unpin_result(self, task, response):
    if response.status_code in (200, 201):
      self.append_log("UNPIN OK | Version unpinned")
    else:
      self.append_log(f"UNPIN FAIL | Status {response.status_code}")

  def on_unpin_error(self, msg):
    self.append_log(f"UNPIN ERROR | {msg}")

  def fetch_latest_version(self):
    from worker import Worker
    url = "http://192.168.1.116/es-git-training//esp32-ota/api/latest.php"
    headers = {"X-OTA-Key": "ota-device-2026-8-25"}
    self._version_worker = Worker("get", url, headers=headers)
    self._version_worker.finished.connect(self.on_version_result)
    self._version_worker.error.connect(self.on_version_error)
    self._version_worker.start()

  def on_version_result(self, task, response):
    if response.status_code in (200, 201):
      try:
        result = response.json()
        version = result.get("version", result.get("latest_version", str(result)))
        version_display = str(version).replace("_", ".")
        self.latest_version_label.setText(version_display)
        self.append_log(f"VERSION OK | Latest: {version_display}")
      except ValueError:
        self.latest_version_label.setText(response.text)
    else:
      self.latest_version_label.setText("N/A")
      self.append_log(f"VERSION FAIL | Status {response.status_code}")

  def on_version_error(self, msg):
    self.latest_version_label.setText("N/A")
    self.append_log(f"VERSION ERROR | {msg}")

  def check_version_after_upload(self):
    ver = self.ver_entry.text().strip()
    uploaded_version = ver.replace(".", "_")
    url = "http://192.168.1.116/es-git-training//esp32-ota/api/latest.php"
    headers = {"X-OTA-Key": "ota-device-2026-8-25"}
    self._check_worker = Worker("get", url, headers=headers)
    self._check_worker.finished.connect(lambda t, r: self.on_check_version_result(r, uploaded_version))
    self._check_worker.error.connect(lambda m: self.append_log(f"VERSION CHECK ERROR | {m}"))
    self._check_worker.start()

  def on_check_version_result(self, response, uploaded_version):
    if response.status_code in (200, 201):
      try:
        result = response.json()
        current_version = str(result.get("version", result.get("latest_version", "")))
        current_display = current_version.replace("_", ".")
        uploaded_display = uploaded_version.replace("_", ".")
        self.latest_version_label.setText(current_display)
        self.append_log(f"VERSION CHECK | Uploaded: {uploaded_display} | Current: {current_display}")
        if uploaded_version == current_version:
          self.append_log("VERSION CHECK | Match - using uploaded version")
        else:
          self.show_version_mismatch_popup(uploaded_display, current_display)
      except ValueError:
        self.append_log("VERSION CHECK | Invalid response")
    else:
      self.append_log(f"VERSION CHECK FAIL | Status {response.status_code}")

  def show_version_mismatch_popup(self, uploaded_ver, current_ver):
    dlg = QDialog(self)
    dlg.setWindowTitle("Version Mismatch")
    dlg.setFixedSize(400, 180)
    layout = QVBoxLayout()
    msg = QLabel(f"Uploaded version: {uploaded_ver}\nCurrent version: {current_ver}\n\nPlease unpin to use the uploaded version.")
    msg.setStyleSheet("font-size: 13px;")
    msg.setWordWrap(True)
    layout.addWidget(msg)
    btn_layout = QHBoxLayout()
    unpin_btn = QPushButton("Unpin Now")
    unpin_btn.setStyleSheet(
        "background-color: #FF9800; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px;"
    )
    unpin_btn.clicked.connect(lambda: (self.unpin_version(), dlg.accept()))
    close_btn = QPushButton("Close")
    close_btn.setStyleSheet(
        "background-color: #757575; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px;"
    )
    close_btn.clicked.connect(dlg.reject)
    btn_layout.addWidget(unpin_btn)
    btn_layout.addWidget(close_btn)
    layout.addLayout(btn_layout)
    dlg.setLayout(layout)
    dlg.exec()

  def toggle_version_fetch(self):
    if self.version_auto_running:
      self.version_auto_running = False
      self.version_timer.stop()
      self.version_toggle_btn.setText("Auto: OFF")
      self.version_toggle_btn.setStyleSheet(
          "background-color: #757575; color: white; font-weight: bold; padding: 3px; border-radius: 4px;"
      )
      self.append_log("VERSION AUTO | Stopped")
    else:
      self.version_auto_running = True
      self.version_timer.start()
      self.version_toggle_btn.setText("Auto: ON")
      self.version_toggle_btn.setStyleSheet(
          "background-color: #F44336; color: white; font-weight: bold; padding: 3px; border-radius: 4px;"
      )
      self.append_log("VERSION AUTO | Started (every 5s)")

  def select_file(self):
    upload_mod.select_file(self)

  def upload_file(self):
    upload_mod.upload_file(self)

  def update_temp_label(self, value):
    actual_value = value / 10.0
    self.temp_val_label.setText(f"{actual_value:.1f}C")

  def update_humi_label(self, value):
    self.humi_val_label.setText(f"{value}%")

  def append_log(self, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if "ERROR" in msg or "FAIL" in msg or "BLOCKED" in msg:
      color = "#FF5252"
    elif "OK" in msg:
      color = "#69F0AE"
    else:
      color = "#FFFFFF"
    self.log_display.append(f'<span style="color:{color}">[{ts}] {msg}</span>')
    self.log_display.verticalScrollBar().setValue(
        self.log_display.verticalScrollBar().maximum()
    )

  def toggle_auto(self):
    if self.auto_running:
      self.send_timer.stop()
      self.fetch_timer.stop()
      self.drift_timer.stop()
      self.auto_running = False
      self.auto_btn.setText("Auto: OFF (5s)")
      self.auto_btn.setStyleSheet(
          "background-color: #757575; color: white; font-weight: bold; padding: 5px;"
      )
    else:
      self.auto_running = True
      self.auto_btn.setText("Auto: ON (5s)")
      self.auto_btn.setStyleSheet(
          "background-color: #F44336; color: white; font-weight: bold; padding: 5px;"
      )
      self.drift_timer.start()
      self.send_timer.start()
      self.auto_send()
      self.fetch_timer.singleShot(2500, self.start_fetch_timer)

  def start_fetch_timer(self):
    if self.auto_running:
      self.auto_fetch()
      self.fetch_timer.start()

  def drift_values(self):
    self.tick += 1
    self.generate_natural_values()

  def auto_send(self):
    self.send_data(silent=True)

  def auto_fetch(self):
    self.fetch_logs(silent=True)

  def generate_natural_values(self):
    t = self.tick * 0.3
    temp = self.base_temp + 5 * math.sin(t * 0.7) + 3 * math.sin(t * 1.9) + random.uniform(-0.5, 0.5)
    humi = self.base_humi + 10 * math.sin(t * 0.5 + 1.0) + 5 * math.sin(t * 1.3) + random.uniform(-1, 1)
    temp = round(max(-10.0, min(50.0, temp)), 1)
    humi = round(max(0, min(100, humi)), 0)
    self.temp_slider.blockSignals(True)
    self.temp_slider.setValue(int(temp * 10))
    self.temp_slider.blockSignals(False)
    self.update_temp_label(self.temp_slider.value())
    self.humi_slider.blockSignals(True)
    self.humi_slider.setValue(int(humi))
    self.humi_slider.blockSignals(False)
    self.update_humi_label(self.humi_slider.value())

  def send_data(self, silent=False):
    url = self.url_entry.text().strip() + "?action=log"
    device = self.device_entry.text().strip()
    try:
        temp = self.temp_slider.value() / 10.0
        humidity = self.humi_slider.value()
    except AttributeError:
        temp = 25.0
        humidity = 60

    payload = {"device": device, "temp": temp, "humidity": humidity}
    self._send_silent = silent
    self._send_device = device
    self._send_temp = temp
    self._send_humi = humidity

    self._send_worker = Worker("post", url, payload)
    self._send_worker.finished.connect(self.on_send_done)
    self._send_worker.error.connect(self.on_send_error)
    self._send_worker.start()

  def on_send_done(self, task, response):
    if response.status_code in (200, 201):
      self.append_log(f"POST OK | {self._send_device} T={self._send_temp}C H={self._send_humi}%")
      if not self._send_silent:
        QMessageBox.information(
            self, "Success", f"Data sent successfully!\nResponse: {response.text}"
        )
    else:
      self.append_log(f"POST FAIL | Status {response.status_code}")
      if not self._send_silent:
        QMessageBox.critical(
            self, "Server Error", f"Status Code: {response.status_code}\n{response.text}"
        )

  def show_disconnect_popup(self):
    if hasattr(self, '_disconnect_shown') and self._disconnect_shown:
      return
    self._disconnect_shown = True
    QTimer.singleShot(100, self._show_popup_now)

  def _show_popup_now(self):
    dlg = DisconnectDialog(self)
    dlg.move(
        self.geometry().x() + (self.width() - dlg.width()) // 2,
        self.geometry().y() + (self.height() - dlg.height()) // 2
    )
    result = dlg.exec()
    self._disconnect_shown = False
    if result == QDialog.DialogCode.Accepted:
      QApplication.quit()

  def on_send_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait... if You want to exit, click ok.")
    self.show_disconnect_popup()

  def fetch_logs(self, silent=False):
    url = self.url_entry.text().strip() + "?action=log"
    self._fetch_silent = silent

    self._fetch_worker = Worker("get", url)
    self._fetch_worker.finished.connect(self.on_fetch_done)
    self._fetch_worker.error.connect(self.on_fetch_error)
    self._fetch_worker.start()

  def on_fetch_done(self, task, response):
    if response.status_code in (200, 201):
      try:
        result = response.json()
        data = result.get("data", result) if isinstance(result, dict) else result
        count = len(data) if isinstance(data, list) else 0
        self.append_log(f"GET OK | {count} records fetched")
        self.chart_widget.draw_line_chart(data)
      except ValueError:
        self.append_log("GET OK | Response not JSON")

  def on_fetch_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait... if You want to exit, click ok.")
    self.show_disconnect_popup()
