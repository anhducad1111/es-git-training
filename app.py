import sys
import requests
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)


class SensorClientApp(QWidget):

  def __init__(self):
    super().__init__()
    self.init_ui()

  def init_ui(self):
    self.setWindowTitle("Haru - Sensor Logger Client")
    self.resize(1000, 500)  

    # --- メインレイアウト (水平) ---
    main_layout = QHBoxLayout(self)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(10)

    # --- 左側のレイアウト (垂直) ---
    left_layout = QVBoxLayout()
    left_layout.setSpacing(10)

    # 1. 接続設定エリア (左上)
    left_layout.addWidget(self.create_config_group())

    # 2. センサーデータ入力エリア (左下)
    # こちらは縦に伸びてほしくないので、スペーサーを追加して調整
    left_layout.addWidget(self.create_input_group())
    left_layout.addStretch()  # 下部の余白を詰める

    # --- 右側のレイアウト (右側全体) ---
    # こちらは縦横に伸びてほしい
    log_group = self.create_log_group()
    # 右側のグループボックスが左側の2倍くらいの幅になるように比率を設定
    # (左:1, 右:2 の比率)
    main_layout.addLayout(left_layout, stretch=1)
    main_layout.addWidget(log_group, stretch=2)

  # 各エリアを作成するメソッドを整理しました

  def create_config_group(self):
    group = QGroupBox("Server Configuration") 
    layout = QFormLayout()
    layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    self.url_entry = QLineEdit("http://192.168.1.100/api/log.php")
    self.device_entry = QLineEdit("Haru-Client")

    layout.addRow(QLabel("API URL:"), self.url_entry)
    layout.addRow(QLabel("Device Name:"), self.device_entry)
    group.setLayout(layout)
    return group

  def create_input_group(self):
    group = QGroupBox("Sensor Data input")
    layout = QVBoxLayout()

    # 温度スライダー
    temp_box = QWidget()
    temp_layout = QHBoxLayout(temp_box)
    temp_layout.setContentsMargins(0,0,0,0)
    temp_layout.addWidget(QLabel("Temp (°C):"))
    self.temp_slider = QSlider(Qt.Orientation.Horizontal)
    self.temp_slider.setRange(-100, 500)
    self.temp_slider.setValue(250)
    self.temp_slider.valueChanged.connect(self.update_temp_label)
    temp_layout.addWidget(self.temp_slider)
    self.temp_val_label = QLabel("25.0°C")
    self.temp_val_label.setFixedWidth(50)
    temp_layout.addWidget(self.temp_val_label)

    # 湿度スライダー
    humi_box = QWidget()
    humi_layout = QHBoxLayout(humi_box)
    humi_layout.setContentsMargins(0,0,0,0)
    humi_layout.addWidget(QLabel("Humidity (%):"))
    self.humi_slider = QSlider(Qt.Orientation.Horizontal)
    self.humi_slider.setRange(0, 100)
    self.humi_slider.setValue(60)
    self.humi_slider.valueChanged.connect(self.update_humi_label)
    humi_layout.addWidget(self.humi_slider)
    self.humi_val_label = QLabel("60%")
    self.humi_val_label.setFixedWidth(50)
    humi_layout.addWidget(self.humi_val_label)

    # 送信ボタン
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

  def create_log_group(self):
    group = QGroupBox("Server logs(Latest 10)")
    layout = QVBoxLayout()

    self.refresh_btn = QPushButton("Refresh List (GET)")
    self.refresh_btn.setStyleSheet(
        "background-color: #2196F3; color: white; padding: 5px;"
    )
    self.refresh_btn.clicked.connect(self.fetch_logs)

    self.log_text = QTextEdit()
    self.log_text.setReadOnly(True)
    self.log_text.setStyleSheet("font-family: Consolas; font-size: 9pt;")

    self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout.addWidget(self.refresh_btn)
    layout.addWidget(self.log_text)
    group.setLayout(layout)
    return group


  def update_temp_label(self, value):
    actual_value = value / 10.0
    self.temp_val_label.setText(f"{actual_value:.1f}°C")

  def update_humi_label(self, value):
    self.humi_val_label.setText(f"{value}%")

  def send_data(self):
    url = self.url_entry.text().strip()
    device = self.device_entry.text().strip()
    try:
        temp = self.temp_slider.value() / 10.0
        humidity = self.humi_slider.value()
    except AttributeError: # 初期化エラー防止
        temp = 25.0
        humidity = 60

    payload = {"device": device, "temp": temp, "humidity": humidity}

    try:
      response = requests.post(url, json=payload, timeout=3) # タイムアウト短縮
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
      response = requests.get(url, timeout=3)
      if response.status_code == 200:
        try:
          data = response.json()
          self.log_text.clear()

          if isinstance(data, list):
            for row in data:
              log_str = (
                  f"[{row.get('created_at', 'N/A')}] "
                  f"Device: {row.get('device_name', 'Unknown')} | "
                  f"Temp: {row.get('temp', row.get('temperature', 'N/A'))}°C | "
                  f"Hum: {row.get('humidity', 'N/A')}%\n"
              )
              self.log_text.append(log_str)
          else:
            self.log_text.setPlainText(str(data))
        except ValueError:
          self.log_text.setPlainText(response.text)
      else:
         self.log_text.setPlainText(f"Error: {response.status_code}")
    except requests.exceptions.RequestException as e:
      self.log_text.setPlainText(f"Connection Failed: {e}")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  client = SensorClientApp()
  client.show()
  sys.exit(app.exec())