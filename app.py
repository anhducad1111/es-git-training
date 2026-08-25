import sys
import requests
from datetime import datetime
from PyQt6.QtCore import Qt
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
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class SensorClientApp(QWidget):

  def __init__(self):
    super().__init__()
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

    layout.addWidget(temp_box)
    layout.addWidget(humi_box)
    layout.addWidget(self.send_btn)
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

  def send_data(self):
    url = self.url_entry.text().strip()
    device = self.device_entry.text().strip()
    try:
        temp = self.temp_slider.value() / 10.0
        humidity = self.humi_slider.value()
    except AttributeError:
        temp = 25.0
        humidity = 60

    payload = {"device": device, "temp": temp, "humidity": humidity}

    try:
      response = requests.post(url, json=payload, timeout=10)
      if response.status_code == 200:
        QMessageBox.information(
            self, "Success", f"Data sent successfully!\nResponse: {response.text}"
        )
        self.fetch_logs()
      else:
        QMessageBox.critical(
            self,
            "Server Error",
            f"Status Code: {response.status_code}\n{response.text}",
        )
    except requests.exceptions.RequestException as e:
      QMessageBox.critical(
          self, "Connection Error", f"Failed to connect to server:\n{e}"
      )

  def fetch_logs(self):
    url = self.url_entry.text().strip()
    try:
      response = requests.get(url, timeout=10)
      if response.status_code == 200:
        try:
          result = response.json()
          data = result.get("data", result) if isinstance(result, dict) else result
          self.draw_line_chart(data)
        except ValueError:
          pass
    except requests.exceptions.RequestException as e:
      QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{e}")

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
        short_labels.append(dt.strftime("%m/%d %H:%M"))
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
  sys.exit(app.exec())
