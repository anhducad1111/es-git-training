import sys
import math
import random
import requests
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
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
    QSizePolicy,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class Worker(QThread):
  finished = pyqtSignal(str, object)
  error = pyqtSignal(str)

  def __init__(self, task, url, payload=None):
    super().__init__()
    self.task = task
    self.url = url
    self.payload = payload

  def run(self):
    try:
      if self.task == "post":
        response = requests.post(self.url, json=self.payload, timeout=10)
        self.finished.emit("post", response)
      elif self.task == "get":
        response = requests.get(self.url, timeout=10)
        self.finished.emit("get", response)
    except requests.exceptions.RequestException as e:
      self.error.emit(str(e))


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

    chart_group = self.create_chart_group()

    main_layout.addLayout(left_layout, stretch=1)
    main_layout.addWidget(chart_group, stretch=2)

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

  def create_chart_group(self):
    group = QGroupBox("Temperature & Humidity History")
    layout = QVBoxLayout()

    self.refresh_btn = QPushButton("Refresh Chart (GET)")
    self.refresh_btn.setStyleSheet(
        "background-color: #2196F3; color: white; padding: 5px;"
    )
    self.refresh_btn.clicked.connect(self.fetch_logs)

    self.figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
    self.canvas = FigureCanvas(self.figure)
    self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout.addWidget(self.refresh_btn)
    layout.addWidget(self.canvas)
    group.setLayout(layout)
    return group

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
        self, "Error", "Error, disconnected to server. Please wait...",
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    self._disconnect_shown = False
    if reply == QMessageBox.StandardButton.Ok:
      QApplication.quit()

  def on_send_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait...")
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
        self.draw_line_chart(data)
      except ValueError:
        self.append_log("GET OK | Response not JSON")

  def on_fetch_error(self, msg):
    self.append_log("ERROR | Disconnected to server. Please wait...")
    self.show_disconnect_popup()

  def draw_line_chart(self, data):
    self.figure.clear()
    if not isinstance(data, list) or len(data) == 0:
      ax = self.figure.add_subplot(111)
      ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
      self.canvas.draw()
      return

    data_sorted = sorted(data, key=lambda r: r.get("created_at", ""))
    timestamps = [row.get("created_at", "") for row in data_sorted]
    short_labels = []
    for t in timestamps:
      try:
        dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        short_labels.append(dt.strftime("%H:%M:%S"))
      except Exception:
        short_labels.append(t)

    temps = [row.get("temperature", row.get("temp", 0)) for row in data_sorted]
    hums = [row.get("humidity", 0) for row in data_sorted]

    ax1 = self.figure.add_subplot(111)
    ax2 = ax1.twinx()

    line1, = ax1.plot(short_labels, temps, "o-", color="#E53935", label="Temp (C)")
    line2, = ax2.plot(short_labels, hums, "s--", color="#1E88E5", label="Humidity (%)")

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Temperature (C)", color="#E53935")
    ax2.set_ylabel("Humidity (%)", color="#1E88E5")
    ax1.set_title("Sensor Data History")
    ax1.tick_params(axis="x", rotation=45)

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left")

    self.figure.tight_layout()
    self.canvas.draw()


if __name__ == "__main__":
  app = QApplication(sys.argv)
  client = SensorClientApp()
  client.show()
  client.toggle_auto()
  sys.exit(app.exec())
