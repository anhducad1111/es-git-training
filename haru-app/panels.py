import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


GROUP_BOX_STYLE = "QGroupBox { font-weight: bold; }"


def create_config_group(app):
  group = QGroupBox("Server Configuration")
  group.setStyleSheet(GROUP_BOX_STYLE)
  layout = QFormLayout()
  layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

  app.url_entry = QLineEdit("http://192.168.1.116/es-git-training/esp32-ota/api/api.php")
  app.device_entry = QLineEdit("Haru_Client")

  version_layout = QHBoxLayout()
  app.latest_version_label = QLabel("Loading...")
  app.latest_version_label.setStyleSheet("font-weight: bold; color: #1E88E5;")
  app.version_toggle_btn = QPushButton("Auto: OFF")
  app.version_toggle_btn.setFixedWidth(80)
  app.version_toggle_btn.setStyleSheet(
      "background-color: #757575; color: white; font-weight: bold; padding: 3px; border-radius: 4px;"
  )
  app.version_toggle_btn.clicked.connect(app.toggle_version_fetch)
  app.unpin_btn = QPushButton("Unpin")
  app.unpin_btn.setFixedWidth(60)
  app.unpin_btn.setStyleSheet(
      "background-color: #FF9800; color: white; font-weight: bold; padding: 3px; border-radius: 4px;"
  )
  app.unpin_btn.clicked.connect(app.unpin_version)
  version_layout.addWidget(app.latest_version_label)
  version_layout.addWidget(app.version_toggle_btn)
  version_layout.addWidget(app.unpin_btn)

  layout.addRow(QLabel("API URL:"), app.url_entry)
  layout.addRow(QLabel("Device Name:"), app.device_entry)
  layout.addRow(QLabel("Latest Version:"), version_layout)
  group.setLayout(layout)
  return group


def create_input_group(app):
  group = QGroupBox("Sensor Data input")
  group.setStyleSheet(GROUP_BOX_STYLE)
  layout = QVBoxLayout()

  temp_box = QWidget()
  temp_layout = QHBoxLayout(temp_box)
  temp_layout.setContentsMargins(0, 0, 0, 0)
  temp_layout.addWidget(QLabel("Temp (C):"))
  app.temp_slider = QSlider(Qt.Orientation.Horizontal)
  app.temp_slider.setRange(-100, 500)
  app.temp_slider.setValue(250)
  app.temp_slider.valueChanged.connect(app.update_temp_label)
  temp_layout.addWidget(app.temp_slider)
  app.temp_val_label = QLabel("25.0C")
  app.temp_val_label.setFixedWidth(50)
  temp_layout.addWidget(app.temp_val_label)

  humi_box = QWidget()
  humi_layout = QHBoxLayout(humi_box)
  humi_layout.setContentsMargins(0, 0, 0, 0)
  humi_layout.addWidget(QLabel("Humidity (%):"))
  app.humi_slider = QSlider(Qt.Orientation.Horizontal)
  app.humi_slider.setRange(0, 100)
  app.humi_slider.setValue(60)
  app.humi_slider.valueChanged.connect(app.update_humi_label)
  humi_layout.addWidget(app.humi_slider)
  app.humi_val_label = QLabel("60%")
  app.humi_val_label.setFixedWidth(50)
  humi_layout.addWidget(app.humi_val_label)

  app.send_btn = QPushButton("Send Data (POST)")
  app.send_btn.setStyleSheet(
      "background-color: #2196F3; color: white; font-weight: bold; padding: 5px; border-radius: 4px;"
  )
  app.send_btn.clicked.connect(app.send_data)

  app.auto_btn = QPushButton("Auto: OFF (5s)")
  app.auto_btn.setStyleSheet(
      "background-color: #90CAF9; color: white; font-weight: bold; padding: 5px; border-radius: 4px;"
  )
  app.auto_btn.clicked.connect(app.toggle_auto)

  app.send_timer = QTimer()
  app.send_timer.setInterval(5000)
  app.send_timer.timeout.connect(app.auto_send)

  app.fetch_timer = QTimer()
  app.fetch_timer.setInterval(5000)
  app.fetch_timer.timeout.connect(app.auto_fetch)

  app.drift_timer = QTimer()
  app.drift_timer.setInterval(1000)
  app.drift_timer.timeout.connect(app.drift_values)

  app.auto_running = False

  layout.addWidget(temp_box)
  layout.addWidget(humi_box)
  layout.addWidget(app.send_btn)
  layout.addWidget(app.auto_btn)

  group.setLayout(layout)
  return group


def create_upload_group(app):
  group = QGroupBox("File Upload")
  group.setStyleSheet(GROUP_BOX_STYLE)
  layout = QVBoxLayout()

  ver_layout = QHBoxLayout()
  ver_layout.addWidget(QLabel("Version:"))
  app.ver_entry = QLineEdit("1.0.0")
  ver_layout.addWidget(app.ver_entry)
  layout.addLayout(ver_layout)

  info_layout = QHBoxLayout()
  info_layout.addWidget(QLabel("Info:"))
  app.version_info_entry = QLineEdit("Initial Release")
  info_layout.addWidget(app.version_info_entry)
  layout.addLayout(info_layout)

  app.file_path_label = QLineEdit("No file selected")
  app.file_path_label.setReadOnly(True)
  app.file_path_label.setStyleSheet("color: gray; background-color: #f0f0f0;")
  layout.addWidget(app.file_path_label)

  btn_layout = QHBoxLayout()
  app.select_btn = QPushButton("Select File")
  app.select_btn.setStyleSheet(
      "background-color: #42A5F5; color: white; font-weight: bold; padding: 5px; border-radius: 4px;"
  )
  app.select_btn.clicked.connect(app.select_file)

  app.upload_btn = QPushButton("Upload")
  app.upload_btn.setStyleSheet(
      "background-color: #1E88E5; color: white; font-weight: bold; padding: 5px; border-radius: 4px;"
  )
  app.upload_btn.clicked.connect(app.upload_file)
  app.upload_btn.setVisible(False)

  btn_layout.addWidget(app.select_btn)
  btn_layout.addWidget(app.upload_btn)
  layout.addLayout(btn_layout)

  app.upload_progress = QProgressBar()
  app.upload_progress.setValue(0)
  app.upload_progress.setTextVisible(True)
  app.upload_progress.setFormat("%p%")
  layout.addWidget(app.upload_progress)

  group.setLayout(layout)
  return group
