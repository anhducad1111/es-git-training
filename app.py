import sys
import math
import random
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from worker import Worker
from chart import ChartWidget


class SensorClientApp(QWidget):

  def __init__(self):
    super().__init__()
    self.tick = 0
    self.base_temp = 25.0
    self.base_humi = 60.0
    self.init_ui()

  def init_ui(self):
    self.setWindowTitle("Haru - Sensor Logger Client")
    self.resize(1000, 500)

    main_layout = QHBoxLayout(self)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(10)

    left_layout = QVBoxLayout()
    left_layout.setSpacing(10)

    left_layout.addWidget(self.create_config_group())
    left_layout.addWidget(self.create_input_group())
    left_layout.addStretch()

    self.chart_widget = ChartWidget(on_refresh=self.fetch_logs)

    right_layout = QVBoxLayout()
    right_layout.addWidget(self.chart_widget)
    right_layout.addWidget(self.create_upload_group())

    main_layout.addLayout(left_layout, stretch=1)
    main_layout.addLayout(right_layout, stretch=2)

  def create_config_group(self):
    group = QGroupBox("Server Configuration")
    layout = QFormLayout()
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    self.url_entry = QLineEdit("http://192.168.2.68/shodai-api/api/log.php")
    self.device_entry = QLineEdit("Haru-Client")

    layout.addRow(QLabel("API URL:"), self.url_entry)
    layout.addRow(QLabel("Device Name:"), self.device_entry)
    group.setLayout(layout)
    return group

  def create_input_group(self):
    group = QGroupBox("Sensor Data input")
    layout = QVBoxLayout()

    temp_box = QWidget()
    temp_layout = QHBoxLayout(temp_box)
    temp_layout.setContentsMargins(0, 0, 0, 0)
    temp_layout.addWidget(QLabel("Temp (C):"))
    self.temp_slider = QSlider(Qt.Orientation.Horizontal)
    self.temp_slider.setRange(-100, 500)
    self.temp_slider.setValue(250)
    self.temp_slider.valueChanged.connect(self.update_temp_label)
    temp_layout.addWidget(self.temp_slider)
    self.temp_val_label = QLabel("25.0C")
    self.temp_val_label.setFixedWidth(50)
    temp_layout.addWidget(self.temp_val_label)

    humi_box = QWidget()
    humi_layout = QHBoxLayout(humi_box)
    humi_layout.setContentsMargins(0, 0, 0, 0)
    humi_layout.addWidget(QLabel("Humidity (%):"))
    self.humi_slider = QSlider(Qt.Orientation.Horizontal)
    self.humi_slider.setRange(0, 100)
    self.humi_slider.setValue(60)
    self.humi_slider.valueChanged.connect(self.update_humi_label)
    humi_layout.addWidget(self.humi_slider)
    self.humi_val_label = QLabel("60%")
    self.humi_val_label.setFixedWidth(50)
    humi_layout.addWidget(self.humi_val_label)

    self.send_btn = QPushButton("Send Data (POST)")
    self.send_btn.setStyleSheet(
        "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;"
    )
    self.send_btn.clicked.connect(self.send_data)

    self.auto_btn = QPushButton("Auto: OFF (5s)")
    self.auto_btn.setStyleSheet(
        "background-color: #757575; color: white; font-weight: bold; padding: 5px;"
    )
    self.auto_btn.clicked.connect(self.toggle_auto)

    self.send_timer = QTimer()
    self.send_timer.setInterval(5000)
    self.send_timer.timeout.connect(self.auto_send)

    self.fetch_timer = QTimer()
    self.fetch_timer.setInterval(5000)
    self.fetch_timer.timeout.connect(self.auto_fetch)

    self.drift_timer = QTimer()
    self.drift_timer.setInterval(1000)
    self.drift_timer.timeout.connect(self.drift_values)

    self.auto_running = False

    layout.addWidget(temp_box)
    layout.addWidget(humi_box)
    layout.addWidget(self.send_btn)
    layout.addWidget(self.auto_btn)

    self.log_display = QTextEdit()
    self.log_display.setReadOnly(True)
    self.log_display.setFixedHeight(120)
    self.log_display.setStyleSheet("font-family: Consolas; font-size: 9pt;")
    layout.addWidget(self.log_display)

    group.setLayout(layout)
    return group

  def create_upload_group(self):
    group = QGroupBox("File Upload (WiFi)")
    layout = QVBoxLayout()

    url_layout = QHBoxLayout()
    url_layout.addWidget(QLabel("Upload URL:"))
    self.upload_url_entry = QLineEdit("http://192.168.2.68/shodai-api/api/upload.php")
    url_layout.addWidget(self.upload_url_entry)
    layout.addLayout(url_layout)

    self.file_path_label = QLabel("No file selected")
    self.file_path_label.setStyleSheet("color: gray;")
    layout.addWidget(self.file_path_label)

    btn_layout = QHBoxLayout()
    self.select_btn = QPushButton("Select File")
    self.select_btn.setStyleSheet(
        "background-color: #FF9800; color: white; font-weight: bold; padding: 5px;"
    )
    self.select_btn.clicked.connect(self.select_file)

    self.upload_btn = QPushButton("Upload")
    self.upload_btn.setStyleSheet(
        "background-color: #9C27B0; color: white; font-weight: bold; padding: 5px;"
    )
    self.upload_btn.clicked.connect(self.upload_file)
    self.upload_btn.setEnabled(False)

    btn_layout.addWidget(self.select_btn)
    btn_layout.addWidget(self.upload_btn)
    layout.addLayout(btn_layout)

    group.setLayout(layout)
    return group

  def select_file(self):
    file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
    if file_path:
      self._upload_file_path = file_path
      fname = file_path.split("/")[-1].split("\\")[-1]
      self.file_path_label.setText(fname)
      self.file_path_label.setStyleSheet("color: black;")
      self.upload_btn.setEnabled(True)

  def upload_file(self):
    if not hasattr(self, "_upload_file_path"):
      return
    url = self.upload_url_entry.text().strip()
    self.append_log(f"UPLOADING | {self._upload_file_path.split('/')[-1].split(chr(92))[-1]}")

    self._upload_worker = Worker("upload", url, file_path=self._upload_file_path)
    self._upload_worker.finished.connect(self.on_upload_done)
    self._upload_worker.error.connect(self.on_upload_error)
    self._upload_worker.start()

  def on_upload_done(self, task, response):
    fname = self._upload_file_path.split("/")[-1].split("\\")[-1]
    if response.status_code == 200:
      self.append_log(f"UPLOAD OK | {fname}")
    else:
      self.append_log(f"UPLOAD FAIL | Status {response.status_code}")

  def on_upload_error(self, msg):
    self.append_log("ERROR | Upload failed. Disconnected to server.")
    self.show_disconnect_popup()

  def update_temp_label(self, value):
    actual_value = value / 10.0
    self.temp_val_label.setText(f"{actual_value:.1f}C")

  def update_humi_label(self, value):
    self.humi_val_label.setText(f"{value}%")

  def append_log(self, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    self.log_display.append(f"[{ts}] {msg}")
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
    url = self.url_entry.text().strip()
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
    if response.status_code == 200:
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
    reply = QMessageBox.critical(
        self, "Error", "Error, disconnected to server. Please wait...   if you want to exit, click ok",
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    self._disconnect_shown = False
    if reply == QMessageBox.StandardButton.Ok:
      QApplication.quit()

  def on_send_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait... ")
    self.show_disconnect_popup()

  def fetch_logs(self, silent=False):
    url = self.url_entry.text().strip()
    self._fetch_silent = silent

    self._fetch_worker = Worker("get", url)
    self._fetch_worker.finished.connect(self.on_fetch_done)
    self._fetch_worker.error.connect(self.on_fetch_error)
    self._fetch_worker.start()

  def on_fetch_done(self, task, response):
    if response.status_code == 200:
      try:
        result = response.json()
        data = result.get("data", result) if isinstance(result, dict) else result
        count = len(data) if isinstance(data, list) else 0
        self.append_log(f"GET OK | {count} records fetched")
        self.chart_widget.draw_line_chart(data)
      except ValueError:
        self.append_log("GET OK | Response not JSON")

  def on_fetch_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait...")
    self.show_disconnect_popup()


if __name__ == "__main__":
  app = QApplication(sys.argv)
  client = SensorClientApp()
  client.show()
  client.toggle_auto()
  sys.exit(app.exec())
