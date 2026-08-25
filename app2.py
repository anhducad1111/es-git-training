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
    QStackedWidget,
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
    self.setStyleSheet("background-color: #000000;")

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
    left_layout.addWidget(self.create_input_group())
    left_layout.addStretch()  # 下部の余白を詰める

    # --- 右側のレイアウト (右側全体) ---
    log_group = self.create_log_group()
    
    main_layout.addLayout(left_layout, stretch=1)
    main_layout.addWidget(log_group, stretch=2)

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

    # QStackedWidgetを使ってスライダー入力画面とテキスト入力画面を切り替える
    self.input_stack = QStackedWidget()

    # --- ページ0: スライダー入力画面 ---
    slider_page = QWidget()
    slider_layout = QVBoxLayout(slider_page)
    slider_layout.setContentsMargins(0, 0, 0, 0)

    # 温度スライダー
    temp_box = QWidget()
    temp_layout = QHBoxLayout(temp_box)
    temp_layout.setContentsMargins(0, 0, 0, 0)
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

    slider_layout.addWidget(temp_box)
    slider_layout.addWidget(humi_box)

    # --- ページ1: テキストボックス入力画面 ---
    input_page = QWidget()
    input_layout = QVBoxLayout(input_page)
    input_layout.setContentsMargins(0, 0, 0, 0)

    temp_input_box = QWidget()
    temp_in_layout = QHBoxLayout(temp_input_box)
    temp_in_layout.setContentsMargins(0, 0, 0, 0)
    temp_in_layout.addWidget(QLabel("Temp (°C):"))
    self.temp_edit = QLineEdit("25.0")
    temp_in_layout.addWidget(self.temp_edit)

    humi_input_box = QWidget()
    humi_in_layout = QHBoxLayout(humi_input_box)
    humi_in_layout.setContentsMargins(0, 0, 0, 0)
    humi_in_layout.addWidget(QLabel("Humidity (%):"))
    self.humi_edit = QLineEdit("60")
    humi_in_layout.addWidget(self.humi_edit)

    input_layout.addWidget(temp_input_box)
    input_layout.addWidget(humi_input_box)

    # スタックウィジェットに両方のページを追加
    self.input_stack.addWidget(slider_page)  # インデックス 0
    self.input_stack.addWidget(input_page)   # インデックス 1

    # --- 切り替え用ボタン (小さめ) ---
    self.toggle_mode_btn = QPushButton("Switch to Direct Input (Fields)")
    self.toggle_mode_btn.setStyleSheet("font-size: 11px; padding: 4px;")
    self.toggle_mode_btn.clicked.connect(self.toggle_input_mode)

    # 送信ボタン
    self.send_btn = QPushButton("Send Data (POST)")
    self.send_btn.setStyleSheet(
        "background-color: #4CAF50; color: white; font-weight: bold; padding: 6px;"
    )
    self.send_btn.clicked.connect(self.send_data)

    layout.addWidget(self.input_stack)
    layout.addWidget(self.toggle_mode_btn)
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

  def toggle_input_mode(self):
    """スライダー入力とテキスト入力を切り替える"""
    current_index = self.input_stack.currentIndex()
    if current_index == 0:
      # 現在スライダー -> テキスト入力へ切り替え
      # スライダーの現在の値をテキストボックスに同期させる
      self.temp_edit.setText(str(self.temp_slider.value() / 10.0))
      self.humi_edit.setText(str(self.humi_slider.value()))
      
      self.input_stack.setCurrentIndex(1)
      self.toggle_mode_btn.setText("Switch to Slider Input")
    else:
      # 現在テキスト入力 -> スライダーへ切り替え
      try:
        temp_val = float(self.temp_edit.text())
        humi_val = int(float(self.humi_edit.text()))
        # スライダーの範囲内に収める
        self.temp_slider.setValue(int(max(-10.0, min(50.0, temp_val)) * 10))
        self.humi_slider.setValue(max(0, min(100, humi_val)))
      except ValueError:
        pass # 数値変換エラー時はそのまま切り替え

      self.input_stack.setCurrentIndex(0)
      self.toggle_mode_btn.setText("Switch to Direct Input (Fields)")

  def update_temp_label(self, value):
    actual_value = value / 10.0
    self.temp_val_label.setText(f"{actual_value:.1f}°C")

  def update_humi_label(self, value):
    self.humi_val_label.setText(f"{value}%")

  def send_data(self):
    url = self.url_entry.text().strip()
    device = self.device_entry.text().strip()

    # 現在の表示モードに応じて値を取得元を変更
    if self.input_stack.currentIndex() == 0:
      # スライダーモード
      temp = self.temp_slider.value() / 10.0
      humidity = self.humi_slider.value()
    else:
      # テキスト入力モード
      try:
        temp = float(self.temp_edit.text())
        humidity = float(self.humi_edit.text())
      except ValueError:
        QMessageBox.warning(self, "Input Error", "Please enter valid numbers for Temperature and Humidity.")
        return

    payload = {"device": device, "temp": temp, "humidity": humidity}

    try:
      response = requests.post(url, json=payload, timeout=3)
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