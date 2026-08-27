from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from worker import Worker
from chart import ChartWidget, DropZone, CHART_GROUPS, ALL_LABELS
from gemini_worker import GeminiWorker
from config import load_config, save_config


GROUP_BOX_STYLE = "QGroupBox { font-weight: bold; }"


class DropGroupBox(QGroupBox):
  """QGroupBox that accepts drops anywhere on its frame and forwards to a target widget."""

  def __init__(self, title, drop_target, parent=None):
    super().__init__(title, parent)
    self._drop_target = drop_target
    self.setAcceptDrops(True)

  def dragEnterEvent(self, event):
    if event.mimeData().hasFormat("application/x-chart-group"):
      event.acceptProposedAction()
      self.setStyleSheet(GROUP_BOX_STYLE + """
          QGroupBox { border: 2px dashed #2196F3; background-color: rgba(33, 150, 243, 0.05); }
      """)

  def dragMoveEvent(self, event):
    if event.mimeData().hasFormat("application/x-chart-group"):
      event.acceptProposedAction()

  def dragLeaveEvent(self, event):
    self.setStyleSheet(GROUP_BOX_STYLE)

  def dropEvent(self, event):
    self.setStyleSheet(GROUP_BOX_STYLE)
    if event.mimeData().hasFormat("application/x-chart-group"):
      event.acceptProposedAction()
      self._drop_target.dropEvent(event)


class ChatInput(QTextEdit):
  submit = pyqtSignal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self._suggestions = ALL_LABELS + ["-n", "-d"]

  def _get_word_before_cursor(self):
    cursor = self.textCursor()
    block = cursor.block().text()
    pos = cursor.position() - cursor.block().position()
    word = ""
    for i in range(pos - 1, -1, -1):
      if block[i] == " ":
        break
      word = block[i] + word
    return word

  def _find_suggestion(self, prefix):
    if not prefix:
      return None
    prefix_lower = prefix.lower()
    for s in self._suggestions:
      if s.lower().startswith(prefix_lower) and s.lower() != prefix_lower:
        return s
    return None

  def keyPressEvent(self, event: QKeyEvent):
    if event.key() == Qt.Key.Key_Tab:
      word = self._get_word_before_cursor()
      if word:
        suggestion = self._find_suggestion(word)
        if suggestion:
          cursor = self.textCursor()
          cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.KeepAnchor, len(word))
          cursor.insertText(suggestion + " ")
          self.setTextCursor(cursor)
          return

    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
      if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
        self.submit.emit()
        return

    super().keyPressEvent(event)

SENSOR_GROUPS = {
    "Air Quality": ["co2", "pm1.0", "pm2.5", "pm10"],
    "Environment": ["temperature", "humidity", "pressure"],
    "Other": ["gas", "battery"],
}

UNITS = {
    "co2": "ppm",
    "pm1.0": "ug/m3",
    "pm2.5": "ug/m3",
    "pm10": "ug/m3",
    "temperature": "C",
    "humidity": "%",
    "pressure": "hPa",
    "gas": "",
    "battery": "%",
}


class SensorDashboardApp(QWidget):

  def __init__(self):
    super().__init__()
    self._config = load_config()
    self._last_data = None
    self._poll_running = False
    self._chat_history = []
    self._gemini_worker = None
    self._is_analyzing = False
    self.init_ui()
    self.load_saved_config()
    self._start_polling_on_launch()

  def init_ui(self):
    self.setWindowTitle("Haru App 2 - Sensor Dashboard")
    self.setMinimumSize(1400, 750)

    main_layout = QVBoxLayout(self)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(10)

    config_group = QGroupBox("Server Configuration")
    config_group.setStyleSheet(GROUP_BOX_STYLE)
    config_layout = QVBoxLayout()

    self.url_entry = QLineEdit()
    self.api_key_entry = QLineEdit()
    self.api_key_entry.setEchoMode(QLineEdit.EchoMode.Password)
    self.api_key_entry.setPlaceholderText("Gemini API Key")
    self.api_key_entry.setFixedWidth(200)
    self.api_key_entry.setVisible(False)

    gemini_label = QLabel("Gemini Key:")
    gemini_label.setVisible(False)

    self.poll_btn = QPushButton("Stop Polling")
    self.poll_btn.setStyleSheet(
        "background-color: #F44336; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
    )
    self.poll_btn.clicked.connect(self.toggle_polling)

    self.status_label = QLabel("Connected")
    self.status_label.setStyleSheet("color: #69F0AE; font-weight: bold;")

    config_layout.addWidget(QLabel("API URL:"))
    config_layout.addWidget(self.url_entry)
    config_layout.addWidget(gemini_label)
    config_layout.addWidget(self.api_key_entry)

    poll_row = QHBoxLayout()
    poll_row.addWidget(self.poll_btn)
    poll_row.addWidget(self.status_label)
    config_layout.addLayout(poll_row)

    config_group.setLayout(config_layout)

    self.top_layout = QHBoxLayout()

    left_layout = QVBoxLayout()
    left_layout.addWidget(config_group)

    cards_group = QGroupBox("Sensor Cards")
    cards_group.setStyleSheet(GROUP_BOX_STYLE)
    cards_group.setMinimumWidth(260)
    self.cards_layout = QVBoxLayout()
    self.cards_layout.setSpacing(8)
    self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    self.card_labels = {}
    self._hidden_charts = set()
    self._create_cards()
    cards_group.setLayout(self.cards_layout)

    self.analyze_btn = QPushButton("Analyze Data (Gemini)")
    self.analyze_btn.setStyleSheet(
        "background-color: #9C27B0; color: white; font-weight: bold; padding: 8px; border-radius: 4px;"
    )
    self.analyze_btn.clicked.connect(self.analyze_data)

    left_layout.addWidget(cards_group)
    left_layout.addWidget(self.analyze_btn)

    self.center_layout = QVBoxLayout()
    self.chart_widget = ChartWidget(num_columns=2)
    self.chart_widget.chart_added.connect(self._on_chart_moved_to_center)
    self.chart_widget.chart_toggled.connect(self.save_current_config)
    self.chart_drop_zone = DropZone(self.chart_widget)
    self.charts_group = DropGroupBox("Charts", self.chart_drop_zone)
    charts_layout = QVBoxLayout()

    reset_charts_btn = QPushButton("Reset Layout")
    reset_charts_btn.setStyleSheet(
        "background-color: #03A9F4; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 9pt;"
    )
    reset_charts_btn.clicked.connect(self._reset_center_charts)
    charts_layout.addWidget(reset_charts_btn)

    center_chart_scroll = QScrollArea()
    center_chart_scroll.setWidgetResizable(True)
    center_chart_scroll.setWidget(self.chart_drop_zone)
    center_chart_scroll.setStyleSheet("""
        QScrollArea {
            background-color: #191A1E;
            border: 1px solid #333;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background: #191A1E;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #444;
            border-radius: 4px;
            min-height: 20px;
        }
    """)
    charts_layout.addWidget(center_chart_scroll)
    self.charts_group.setLayout(charts_layout)
    self.center_layout.addWidget(self.charts_group)

    right_layout = QVBoxLayout()
    chat_group = QGroupBox("Gemini Chat")
    chat_group.setStyleSheet(GROUP_BOX_STYLE)
    chat_layout = QVBoxLayout()

    self.chat_scroll = QScrollArea()
    self.chat_scroll.setWidgetResizable(True)
    self.chat_scroll.setMinimumHeight(400)
    self.chat_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    self.chat_scroll.setStyleSheet("""
        QScrollArea {
            background-color: #191A1E;
            border: 1px solid #333;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background: #191A1E;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #444;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """)
    self.chat_content_widget = QWidget()
    self.chat_content_widget.setStyleSheet("background-color: #191A1E;")
    self.chat_content_layout = QVBoxLayout()
    self.chat_content_layout.setContentsMargins(0, 0, 0, 0)
    self.chat_content_layout.setSpacing(0)
    self.chat_content_layout.addStretch()
    self.chat_content_widget.setLayout(self.chat_content_layout)
    self.chat_scroll.setWidget(self.chat_content_widget)

    chat_input_layout = QHBoxLayout()
    self.chat_input = ChatInput()
    self.chat_input.setPlaceholderText("Type a message to Gemini...")
    self.chat_input.setMaximumHeight(60)
    self.chat_input.setAcceptRichText(False)
    self.chat_input.submit.connect(self.send_chat)
    self.chat_input.setStyleSheet("""
        QTextEdit {
            background-color: #2F3035;
            color: #F0F0F0;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 9pt;
        }
    """)
    self.chat_send_btn = QPushButton("Send")
    self.chat_send_btn.setStyleSheet(
        "background-color: #06C755; color: white; font-weight: bold; padding: 8px 15px; border-radius: 8px;"
    )
    self.chat_send_btn.clicked.connect(self.send_chat)

    chat_input_layout.addWidget(self.chat_input)
    chat_input_layout.addWidget(self.chat_send_btn)

    chat_layout.addWidget(self.chat_scroll)
    chat_layout.addLayout(chat_input_layout)
    chat_group.setLayout(chat_layout)
    chat_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    right_layout.addWidget(chat_group, stretch=1)

    far_right_layout = QVBoxLayout()
    self.custom_chart_widget = ChartWidget(is_custom=True)
    self.custom_chart_widget.chart_added.connect(self._on_custom_chart_added)
    self.custom_drop_zone = DropZone(self.custom_chart_widget)
    custom_charts_group = DropGroupBox("AI Custom Charts", self.custom_drop_zone)
    custom_charts_layout = QVBoxLayout()

    move_btn = QPushButton("Move to Charts")
    move_btn.setStyleSheet(
        "background-color: #2196F3; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 9pt;"
    )
    move_btn.clicked.connect(self._move_custom_to_center)
    custom_charts_layout.addWidget(move_btn)

    self.custom_chart_scroll = QScrollArea()
    self.custom_chart_scroll.setWidgetResizable(True)
    self.custom_chart_scroll.setMinimumHeight(400)
    self.custom_chart_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    self.custom_chart_scroll.setWidget(self.custom_drop_zone)
    self.custom_chart_scroll.setStyleSheet("""
        QScrollArea {
            background-color: #191A1E;
            border: 1px solid #333;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background: #191A1E;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #444;
            border-radius: 4px;
            min-height: 20px;
        }
    """)
    custom_charts_layout.addWidget(self.custom_chart_scroll)
    custom_charts_group.setLayout(custom_charts_layout)
    custom_charts_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    far_right_layout.addWidget(custom_charts_group, stretch=2)

    self.ai_side_panel = QWidget()
    self.ai_side_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    ai_panel_layout = QHBoxLayout()
    ai_panel_layout.setContentsMargins(0, 0, 0, 0)
    ai_panel_layout.setSpacing(10)
    ai_panel_layout.addLayout(right_layout, stretch=2)
    ai_panel_layout.addLayout(far_right_layout, stretch=1)
    self.ai_side_panel.setLayout(ai_panel_layout)
    self.ai_side_panel.setVisible(False)

    right_container = QVBoxLayout()
    right_container.setContentsMargins(0, 0, 0, 0)
    right_container.addWidget(self.ai_side_panel, stretch=1)

    self.chatbot_toggle_btn = QPushButton("\U0001F4AC")
    self.chatbot_toggle_btn.setFixedSize(50, 50)
    self.chatbot_toggle_btn.setStyleSheet("""
        QPushButton {
            background-color: #9C27B0;
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 20px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #7B1FA2;
        }
    """)
    self.chatbot_toggle_btn.clicked.connect(self.toggle_ai_panel)

    self.top_layout.addLayout(left_layout, stretch=1)
    self.top_layout.addLayout(self.center_layout, stretch=10)
    self.top_layout.addLayout(right_container, stretch=0)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    btn_row.addWidget(self.chatbot_toggle_btn)

    self.log_tab = QPushButton("[Log] Click to expand")
    self.log_tab.setStyleSheet(
        "background-color: #424242; color: white; font-weight: bold; padding: 5px; border-radius: 4px;"
    )
    self.log_tab.clicked.connect(self.toggle_log)

    self.log_group = QGroupBox("Log Screen")
    self.log_group.setStyleSheet(GROUP_BOX_STYLE)
    log_layout = QVBoxLayout()
    self.log_display = QTextEdit()
    self.log_display.setReadOnly(True)
    self.log_display.setMinimumHeight(100)
    self.log_display.setMaximumHeight(250)
    self.log_display.setStyleSheet(
        "font-family: Consolas; font-size: 9pt; background-color: #212121; color: #FFFFFF;"
    )
    log_layout.addWidget(self.log_display)
    self.log_group.setLayout(log_layout)
    self.log_group.setVisible(False)

    main_layout.addLayout(self.top_layout, stretch=1)
    main_layout.addLayout(btn_row)
    main_layout.addWidget(self.log_tab)
    main_layout.addWidget(self.log_group)

    self.poll_timer = QTimer()
    self.poll_timer.setInterval(5000)
    self.poll_timer.timeout.connect(self.fetch_data)

  def load_saved_config(self):
    self.url_entry.setText(self._config.get("api_url", ""))
    self.api_key_entry.setText(self._config.get("gemini_api_key", ""))
    saved_charts = self._config.get("center_charts", {})
    saved_hidden = self._config.get("center_charts_hidden", [])
    self._hidden_charts = set(saved_hidden)
    if saved_charts:
      self.chart_widget.current_groups = saved_charts
      self.chart_widget._clear_charts()
      self.chart_widget._build_charts()
      for name in saved_hidden:
        if name in self.chart_widget.charts:
          info = self.chart_widget.charts[name]
          info["container"].setVisible(False)
          if "close_btn" in info:
            info["close_btn"].setText("O")
            info["close_btn"].setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
            """)
      self.append_log(f"Restored {len(saved_charts)} center chart(s)")
    saved_custom = self._config.get("custom_charts", {})
    saved_custom_norm = self._config.get("custom_charts_normalize", {})
    if saved_custom:
      self.custom_chart_widget.current_groups = saved_custom
      self.custom_chart_widget.normalize_flags = saved_custom_norm
      self.custom_chart_widget._clear_charts()
      self.custom_chart_widget._build_charts()
      if self._last_data:
        history = self._last_data.get("history", {})
        self.custom_chart_widget.update_charts(history)
      self.append_log(f"Restored {len(saved_custom)} custom chart(s)")

  def save_current_config(self):
    self._config["api_url"] = self.url_entry.text().strip()
    self._config["gemini_api_key"] = self.api_key_entry.text().strip()
    self._config["center_charts"] = {k: list(v) for k, v in self.chart_widget.current_groups.items()}
    self._hidden_charts = {
        name for name, info in self.chart_widget.charts.items()
        if not info["container"].isVisible()
    }
    self._config["center_charts_hidden"] = list(self._hidden_charts)
    self._config["custom_charts"] = {k: list(v) for k, v in self.custom_chart_widget.current_groups.items()}
    self._config["custom_charts_normalize"] = dict(self.custom_chart_widget.normalize_flags)
    save_config(self._config)

  def _start_polling_on_launch(self):
    if self.url_entry.text().strip():
      self._poll_running = True
      self.poll_timer.start()
      self.fetch_data()
      self.append_log("Polling started automatically")

  def _create_cards(self):
    for group_name, labels in SENSOR_GROUPS.items():
      card = QGroupBox(group_name)
      card.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #555; border-radius: 4px; padding: 5px; }")
      card_layout = QVBoxLayout()
      for label in labels:
        row = QHBoxLayout()
        name_label = QLabel(f"{label}:")
        name_label.setFixedWidth(120)
        name_label.setMinimumHeight(24)
        name_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        value_label = QLabel("N/A")
        value_label.setFixedWidth(100)
        value_label.setMinimumHeight(24)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        arrow_label = QLabel("")
        arrow_label.setFixedWidth(40)
        arrow_label.setMinimumHeight(24)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(name_label)
        row.addWidget(value_label)
        row.addWidget(arrow_label)
        card_layout.addLayout(row)
        self.card_labels[label] = {"value": value_label, "arrow": arrow_label}
      card_layout.addStretch()
      card.setLayout(card_layout)
      self.cards_layout.addWidget(card)
    self.cards_layout.addStretch()

  def toggle_ai_panel(self):
    if self.ai_side_panel.isVisible():
      self.ai_side_panel.setVisible(False)
      self.chatbot_toggle_btn.setText("\U0001F4AC")
      self.charts_group.setVisible(True)
      self.top_layout.setStretch(1, 10)
      self.top_layout.setStretch(2, 0)
    else:
      self.ai_side_panel.setVisible(True)
      self.chatbot_toggle_btn.setText("\u2716")
      self.charts_group.setVisible(False)
      self.top_layout.setStretch(1, 0)
      self.top_layout.setStretch(2, 10)

  def toggle_log(self):
    if self.log_group.isVisible():
      self.log_group.setVisible(False)
      self.log_tab.setText("[Log] Click to expand")
    else:
      self.log_group.setVisible(True)
      self.log_tab.setText("[Log] Click to collapse")

  def toggle_polling(self):
    if self._poll_running:
      self._poll_running = False
      self.poll_timer.stop()
      self.poll_btn.setText("Start Polling")
      self.poll_btn.setStyleSheet(
          "background-color: #757575; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
      )
      self.status_label.setText("Disconnected")
      self.status_label.setStyleSheet("color: #FF5252; font-weight: bold;")
      self.append_log("Polling stopped")
    else:
      self._poll_running = True
      self.poll_timer.start()
      self.poll_btn.setText("Stop Polling")
      self.poll_btn.setStyleSheet(
          "background-color: #F44336; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;"
      )
      self.status_label.setText("Connected")
      self.status_label.setStyleSheet("color: #69F0AE; font-weight: bold;")
      self.append_log("Polling started (every 5s)")
      self.fetch_data()

  def fetch_data(self):
    url = self.url_entry.text().strip()
    self._worker = Worker("get", url)
    self._worker.finished.connect(self.on_fetch_result)
    self._worker.error.connect(self.on_fetch_error)
    self._worker.start()

  def _reset_custom_charts(self):
    self.custom_chart_widget._clear_charts()
    self.custom_chart_widget.current_groups = {}
    self.custom_chart_widget.normalize_flags = {}
    self.add_chat_bubble("System: Custom charts cleared.", is_system=True)
    self.append_log("RESET | Custom charts cleared")

  def _move_custom_to_center(self):
    custom_groups = dict(self.custom_chart_widget.current_groups)
    if not custom_groups:
      self.add_chat_bubble("System: No custom charts to move.", is_system=True)
      return
    moved = []
    for group_name, labels in custom_groups.items():
      name = group_name
      if name in self.chart_widget.current_groups:
        i = 2
        while f"{name} ({i})" in self.chart_widget.current_groups:
          i += 1
        name = f"{name} ({i})"
      self.chart_widget.current_groups[name] = labels
      self.chart_widget._build_draggable_chart(name, labels)
      if name in self.chart_widget.charts:
        self.chart_widget.charts[name]["container"].setVisible(True)
      moved.append(name)
    self.custom_chart_widget._clear_charts()
    self.custom_chart_widget.current_groups = {}
    self.custom_chart_widget.normalize_flags = {}
    if self._last_data:
      history = self._last_data.get("history", {})
      self.chart_widget.update_charts(history)
    self.save_current_config()
    self.add_chat_bubble(f"System: Moved {len(moved)} chart(s) to Charts.", is_system=True)
    self.append_log(f"MOVE | {moved} moved to center charts")

  def _reset_center_charts(self):
    from chart import CHART_GROUPS
    self.chart_widget.current_groups = CHART_GROUPS.copy()
    self.chart_widget._clear_charts()
    self.chart_widget._build_charts()
    self._config["center_charts"] = {}
    self._config["center_charts_hidden"] = []
    save_config(self._config)
    self.add_chat_bubble("System: Charts layout reset to default.", is_system=True)
    self.append_log("RESET | Center charts restored to default")
    if self._last_data:
      history = self._last_data.get("history", {})
      self.chart_widget.update_charts(history)

  def _on_custom_chart_added(self, group_name):
    if group_name in self.chart_widget.charts:
      self.chart_widget.remove_chart(group_name)
    if self._last_data:
      history = self._last_data.get("history", {})
      self.custom_chart_widget.update_charts(history)
    self.save_current_config()

  def _on_chart_moved_to_center(self, group_name):
    if group_name in self.custom_chart_widget.charts:
      self.custom_chart_widget.remove_chart(group_name)
    if group_name in self.chart_widget.charts:
      self.chart_widget.charts[group_name]["container"].setVisible(True)
    if self._last_data:
      history = self._last_data.get("history", {})
      self.chart_widget.update_charts(history)
    self.save_current_config()

  def on_fetch_result(self, task, response):
    if response.status_code in (200, 201):
      try:
        data = response.json()
        if data.get("success"):
          self._last_data = data
          self.update_cards(data.get("latest", {}))
          history = data.get("history", {})
          self.chart_widget.update_charts(history)
          self.custom_chart_widget.update_charts(history)
          self.check_staleness(data)
          self.append_log("FETCH OK")
        else:
          self.append_log(f"FETCH FAIL | {data.get('message', 'Unknown error')}")
      except ValueError:
        self.append_log("FETCH FAIL | Invalid JSON")
    else:
      self.append_log(f"FETCH FAIL | Status {response.status_code}")

  def on_fetch_error(self, msg):
    self.append_log(f"FETCH ERROR | {msg}")

  def update_cards(self, latest):
    history = self._last_data.get("history", {}) if self._last_data else {}
    for label, card in self.card_labels.items():
      value_label = card["value"]
      arrow_label = card["arrow"]
      if label in latest:
        info = latest[label]
        value = info.get("data", "N/A")
        unit = UNITS.get(label, "")
        arrow_text = ""
        color = "#1E88E5"
        if value != "N/A":
          try:
            cur = float(value)
            prev_list = history.get(label, [])
            if len(prev_list) >= 2:
              prv = float(prev_list[-2].get("data", cur))
            else:
              prv = cur
            if cur > prv:
              arrow_text = "↑"
              color = "#2196F3"
            elif cur < prv:
              arrow_text = "↓"
              color = "#FF5252"
            else:
              arrow_text = "→"
              color = "#4CAF50"
          except (ValueError, TypeError):
            pass
        value_label.setText(f"{value} {unit}")
        value_label.setStyleSheet(f"font-weight: bold; font-size: 14pt; color: {color};")
        arrow_label.setText(arrow_text)
        arrow_label.setStyleSheet(f"font-weight: bold; font-size: 14pt; color: {color};")
      else:
        value_label.setText("N/A")
        value_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #1E88E5;")
        arrow_label.setText("")

  def check_staleness(self, data):
    server_time = data.get("server_time")
    latest = data.get("latest", {})
    if not server_time or not latest:
      return
    try:
      server_dt = datetime.strptime(server_time, "%Y-%m-%d %H:%M:%S")
      newest = None
      for label, info in latest.items():
        rt = info.get("reading_time")
        if rt:
          dt = datetime.strptime(rt, "%Y-%m-%d %H:%M:%S")
          if newest is None or dt > newest:
            newest = dt
      if newest:
        diff = (server_dt - newest).total_seconds()
        if diff >= 180:
          self.append_log(f"WARNING | Stale data ({int(diff)}s old)")
    except ValueError:
      pass

  def analyze_data(self):
    api_key = self.api_key_entry.text().strip()
    if not api_key:
      self.append_log("ERROR | Gemini API key not set")
      return
    if not self._last_data:
      self.append_log("ERROR | No sensor data to analyze")
      return

    if not self.ai_side_panel.isVisible():
      self.toggle_ai_panel()

    latest = self._last_data.get("latest", {})
    data_text = "\n".join([
        f"- {label}: {info.get('data', 'N/A')} {UNITS.get(label, '')}"
        for label, info in latest.items()
    ])

    prompt = f"""Analyze this sensor data and provide insights:

Sensor Readings:
{data_text}

Please provide:
1. Overall air quality assessment
2. Any concerning values
3. Recommendations based on the data

Keep the response concise and helpful."""

    self.append_log("Analyzing data with Gemini...")
    if not self.init_gemini():
      self.add_chat_bubble("System: Failed to connect to Gemini", is_user=False, is_system=True)
      return
    self.add_chat_bubble("Analyze my sensor data", is_user=True)
    self._is_analyzing = True
    try:
      self._gemini_worker.finished.disconnect(self.on_chat_result)
    except TypeError:
      pass
    self._gemini_worker.finished.connect(self.on_analysis_result)
    self._gemini_worker.send_message(prompt)

  def on_analysis_result(self, text):
    self.add_chat_bubble(f"Analysis:\n{text}", is_user=False, is_analysis=True)
    self.append_log("GEMINI OK | Analysis complete")
    self._is_analyzing = False
    try:
      self._gemini_worker.finished.disconnect(self.on_analysis_result)
    except TypeError:
      pass
    self._gemini_worker.finished.connect(self.on_chat_result)

    url = self.url_entry.text().strip()
    if not url:
      self.append_log("ERROR | No API URL set")
      return

    api_url = "https://iotdigi.io.vn/es-git-training/sensor-dashboard/api/post-analysis.php"
    payload = {"content": text}

    self.append_log(f"Sending to: {api_url}")
    self._worker = Worker("post", api_url, payload=payload)
    self._worker.finished.connect(self.on_analyze_upload_result)
    self._worker.error.connect(self.on_analyze_upload_error)
    self._worker.start()

  def on_analyze_upload_result(self, task, response):
    if response.status_code in (200, 201):
      self.append_log("UPLOAD OK | Analysis sent to server")
      self.add_chat_bubble("System: Analysis sent to server successfully.", is_system=True)
    else:
      self.append_log(f"UPLOAD FAIL | Status {response.status_code}")
      self.add_chat_bubble(f"System: Failed to send analysis (Status {response.status_code})", is_system=True)

  def on_analyze_upload_error(self, msg):
    self.append_log(f"UPLOAD ERROR | {msg}")
    self.add_chat_bubble(f"System: Upload error: {msg}", is_system=True)

  def init_gemini(self):
    api_key = self.api_key_entry.text().strip()
    if not api_key:
      self.append_log("ERROR | Gemini API key not set")
      return False
    if self._gemini_worker is None:
      self._gemini_worker = GeminiWorker(api_key)
      self._gemini_worker.finished.connect(self.on_chat_result)
      self._gemini_worker.error.connect(self.on_gemini_error)
      self._gemini_worker.tool_called.connect(self.on_tool_called)
    if not self._gemini_worker.chat:
      if not self._gemini_worker.init_chat():
        return False
    return True

  def send_chat(self):
    message = self.chat_input.toPlainText().strip()
    if not message:
      return

    if message.startswith("/chart"):
      self._handle_chart_command(message)
      return

    if not self.init_gemini():
      self.add_chat_bubble("System: Failed to connect to Gemini", is_user=False, is_system=True)
      return

    self.add_chat_bubble(message, is_user=True)
    self.chat_input.setPlainText("")

    self._chat_history.append(message)

    system_prompt = (
        "IMPORTANT: You are a sensor data assistant with chart creation capabilities. "
        "AVAILABLE SENSORS: co2, pm1.0, pm2.5, pm10, temperature, humidity, pressure, gas, battery. "
        "RULE: When a user asks to show, view, display, create, compare, or chart ANY sensor data, "
        "you MUST execute the create_custom_charts tool. Under NO circumstances should you respond "
        "with only text. You MUST call the tool with a dictionary mapping chart titles to sensor lists. "
        "Example: User says 'show temperature' -> call create_custom_charts({\"Temperature\": [\"temperature\"]}). "
        "NORMALIZATION RULE: If the user requests overlaying sensors with vastly different value scales "
        "(e.g., co2 in thousands, temperature in tens, pm2.5 in single digits) on a single chart, "
        "do NOT immediately call the tool. Instead, ask: 'These sensors have significantly different value scales. "
        "Should I normalize them (Min-Max scaling) to 0-1 range for easier comparison, or display as is?' "
        "Wait for user response before executing the tool."
    )
    prompt = f"{system_prompt}\n\nUser: {message}"
    if self._last_data:
      latest = self._last_data.get("latest", {})
      data_text = ", ".join([
          f"{label}: {info.get('data', 'N/A')}{UNITS.get(label, '')}"
          for label, info in latest.items()
      ])
      prompt = f"{system_prompt}\n\nCurrent sensor data: {data_text}\n\nUser: {message}"

    self.append_log("Sending to Gemini...")
    self._gemini_worker.send_message(prompt)

  def _handle_chart_command(self, message):
    tokens = message.split()
    normalize = False
    separate_charts = False
    sensors = []
    chart_name = None
    i = 0
    while i < len(tokens):
      token = tokens[i]
      if token == "/chart":
        i += 1
        continue
      if token == "-n":
        if i + 1 < len(tokens) and tokens[i + 1] not in ALL_LABELS and tokens[i + 1] != "-d":
          chart_name = tokens[i + 1]
          i += 2
          continue
        else:
          normalize = True
          i += 1
          continue
      if token == "-d":
        separate_charts = True
        i += 1
        continue
      if token in ALL_LABELS:
        sensors.append(token)
      i += 1
    self.chat_input.setPlainText("")
    self.add_chat_bubble(message, is_user=True)
    if not sensors:
      self.add_chat_bubble("System: No valid sensors. Use: /chart co2 temperature -n My Chart", is_system=True)
      return
    if separate_charts:
      custom_groups = {sensor.capitalize(): [sensor] for sensor in sensors}
    else:
      name = chart_name if chart_name else "Command Chart"
      custom_groups = {name: sensors}
    self.custom_chart_widget.rebuild_charts(custom_groups, normalize=normalize)
    if self._last_data:
      history = self._last_data.get("history", {})
      self.custom_chart_widget.update_charts(history)
    self.save_current_config()
    norm_text = " (normalized)" if normalize else ""
    name_text = f" as '{chart_name}'" if chart_name else ""
    sep_text = " (separated)" if separate_charts else ""
    self.add_chat_bubble(f"System: Chart created: {', '.join(sensors)}{name_text}{norm_text}{sep_text}", is_system=True)
    self.append_log(f"CHART COMMAND | {', '.join(sensors)} name={chart_name} normalize={normalize} separate={separate_charts}")

  def on_chat_result(self, text):
    self._chat_history.append(text)
    self.add_chat_bubble(text, is_user=False)
    self.append_log("GEMINI OK | Response received")

  def on_tool_called(self, func_name, func_args):
    if func_name == "create_custom_charts":
      custom_groups = func_args.get("custom_groups", {})
      normalize = func_args.get("normalize", False)
      valid_groups = {}
      normalize_flags = {}
      for title, sensors in custom_groups.items():
        if isinstance(sensors, str):
            sensors = [sensors]
        elif not isinstance(sensors, list):
            continue
        valid_sensors = [s for s in sensors if s in ALL_LABELS]
        if valid_sensors:
          valid_groups[title] = valid_sensors
          normalize_flags[title] = normalize
      if not valid_groups:
        self.add_chat_bubble("System: No valid sensor names provided. Available: " + ", ".join(ALL_LABELS), is_system=True)
        return
      self.custom_chart_widget.rebuild_charts(valid_groups, normalize_flags)
      if self._last_data:
        history = self._last_data.get("history", {})
        self.custom_chart_widget.update_charts(history)
      self.save_current_config()
      norm_text = " (normalized)" if normalize else ""
      self.add_chat_bubble(f"System: Custom charts created: {', '.join(valid_groups.keys())}{norm_text}", is_system=True)
      self.append_log(f"GEMINI TOOL | create_custom_charts: {list(valid_groups.keys())} normalize={normalize}")
    else:
      self.add_chat_bubble(f"System: Unknown tool '{func_name}'", is_system=True)

  def add_chat_bubble(self, text, is_user=False, is_system=False, is_analysis=False):
    ts = datetime.now().strftime("%H:%M")

    bubble = QLabel()
    bubble.setWordWrap(True)
    bubble.setTextFormat(Qt.TextFormat.RichText)

    time_label = QLabel(ts)
    time_label.setStyleSheet("font-size: 7pt; color: #888; background: transparent;")

    if is_system:
      bubble.setText(text)
      bubble.setStyleSheet("""
          QLabel {
              background-color: #3D3D3D;
              color: #CCCCCC;
              padding: 10px 14px;
              border-radius: 10px;
              font-size: 9pt;
          }
      """)
      layout = QHBoxLayout()
      layout.setContentsMargins(50, 4, 50, 4)
      layout.addStretch()
      layout.addWidget(bubble)
      layout.addStretch()
      time_layout = QHBoxLayout()
      time_layout.setContentsMargins(50, 0, 50, 4)
      time_layout.addStretch()
      time_layout.addWidget(time_label)
      time_layout.addStretch()
    elif is_analysis:
      html = self.markdown_to_html(text)
      bubble.setText(html)
      bubble.setStyleSheet("""
          QLabel {
              background-color: #2F3035;
              color: #F0F0F0;
              padding: 10px 14px;
              border-radius: 10px;
              font-size: 9pt;
          }
      """)
      layout = QHBoxLayout()
      layout.setContentsMargins(4, 4, 4, 4)
      layout.addWidget(bubble)
      layout.addStretch()
      time_layout = QHBoxLayout()
      time_layout.setContentsMargins(4, 0, 4, 4)
      time_layout.addWidget(time_label)
      time_layout.addStretch()
    elif is_user:
      bubble.setText(text)
      bubble.setStyleSheet("""
          QLabel {
              background-color: #06C755;
              color: white;
              padding: 10px 14px;
              border-radius: 10px;
              font-size: 9pt;
          }
      """)
      layout = QHBoxLayout()
      layout.setContentsMargins(4, 4, 4, 4)
      layout.addStretch()
      layout.addWidget(bubble)
      time_layout = QHBoxLayout()
      time_layout.setContentsMargins(4, 0, 4, 4)
      time_layout.addStretch()
      time_layout.addWidget(time_label)
    else:
      html = self.markdown_to_html(text)
      bubble.setText(html)
      bubble.setStyleSheet("""
          QLabel {
              background-color: #2F3035;
              color: #F0F0F0;
              padding: 10px 14px;
              border-radius: 10px;
              font-size: 9pt;
          }
      """)
      layout = QHBoxLayout()
      layout.setContentsMargins(4, 4, 4, 4)
      layout.addWidget(bubble)
      layout.addStretch()
      time_layout = QHBoxLayout()
      time_layout.setContentsMargins(4, 0, 4, 4)
      time_layout.addWidget(time_label)
      time_layout.addStretch()

    container = QWidget()
    container_layout = QVBoxLayout()
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(0)
    container_layout.addLayout(layout)
    container_layout.addLayout(time_layout)
    container.setLayout(container_layout)
    container.setStyleSheet("background: transparent;")

    self.chat_content_layout.insertWidget(self.chat_content_layout.count() - 1, container)
    self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

  def markdown_to_html(self, text):
    import re
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\$([^$]+)_\{?(\w+)\}?\$', r'\1<sub>\2</sub>', text)
    text = re.sub(r'\$([^$]+)\^\{?(\w+)\}?\$', r'\1<sup>\2</sup>', text)
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)
    lines = text.split('\n')
    html_lines = []
    for line in lines:
      line = line.strip()
      if not line:
        html_lines.append('<br>')
        continue
      if line.startswith('### '):
        html_lines.append(f'<h3 style="color: #64B5F6; margin: 8px 0 4px 0;">{line[4:]}</h3>')
      elif line.startswith('## '):
        html_lines.append(f'<h2 style="color: #64B5F6; margin: 8px 0 4px 0;">{line[3:]}</h2>')
      elif line.startswith('# '):
        html_lines.append(f'<h1 style="color: #64B5F6; margin: 8px 0 4px 0;">{line[2:]}</h1>')
      elif line.startswith('*   ') or line.startswith('- '):
        content = line[3:] if line.startswith('*   ') else line[2:]
        content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
        content = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', content)
        html_lines.append(f'<div style="margin-left: 10px;">• {content}</div>')
      else:
        line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', line)
        line = re.sub(r'`(.*?)`', r'<code style="background-color: #2d2d2d; padding: 2px 4px;">\1</code>', line)
        html_lines.append(f'<p style="margin: 2px 0;">{line}</p>')
    return ''.join(html_lines)

  def on_gemini_error(self, msg):
    self.append_log(f"GEMINI ERROR | {msg}")

  def append_log(self, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if "ERROR" in msg or "FAIL" in msg or "WARNING" in msg:
      color = "#FF5252"
    elif "OK" in msg:
      color = "#69F0AE"
    else:
      color = "#FFFFFF"
    self.log_display.append(f'<span style="color:{color}">[{ts}] {msg}</span>')
    self.log_display.verticalScrollBar().setValue(
        self.log_display.verticalScrollBar().maximum()
    )
