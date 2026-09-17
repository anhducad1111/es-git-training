from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QStackedWidget, QScrollArea
)
from gemini_chat import GeminiChat
from widgets.sensor_chart import SensorChart


def create_diagnostics_view(app):
    widget = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)

    left_panel = QWidget()
    left_layout = QVBoxLayout()
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(8)

    charts_header = QHBoxLayout()
    charts_title = QLabel("DATA VIEW")
    charts_title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    charts_header.addWidget(charts_title)
    charts_header.addStretch()

    app._view_charts_btn = QPushButton("CHARTS")
    app._view_charts_btn.setFixedWidth(60)
    app._view_charts_btn.setStyleSheet("""
        QPushButton {
            background-color: #06b6d4;
            color: #0a0e1a;
            font-weight: 700;
            font-size: 9px;
            border: none;
            letter-spacing: 1px;
        }
    """)
    app._view_charts_btn.clicked.connect(lambda: _switch_view(app, "charts"))
    charts_header.addWidget(app._view_charts_btn)

    app._view_table_btn = QPushButton("TABLE")
    app._view_table_btn.setFixedWidth(60)
    app._view_table_btn.setStyleSheet("""
        QPushButton {
            background-color: #1e293b;
            border: 1px solid #334155;
            color: #64748b;
            font-weight: 600;
            font-size: 9px;
            letter-spacing: 1px;
        }
    """)
    app._view_table_btn.clicked.connect(lambda: _switch_view(app, "table"))
    charts_header.addWidget(app._view_table_btn)

    left_layout.addLayout(charts_header)

    app._data_stack = QStackedWidget()

    charts_page = QWidget()
    charts_layout = QVBoxLayout()
    charts_layout.setContentsMargins(0, 0, 0, 0)

    app._sensor_chart = SensorChart()
    charts_layout.addWidget(app._sensor_chart)

    charts_page.setLayout(charts_layout)
    app._data_stack.addWidget(charts_page)

    table_page = QWidget()
    table_layout = QVBoxLayout()
    table_layout.setContentsMargins(0, 0, 0, 0)

    table_toolbar = QHBoxLayout()
    app._history_limit = QComboBox()
    app._history_limit.addItems(["10", "20", "50", "100"])
    app._history_limit.setCurrentText("20")
    app._history_limit.setFixedWidth(60)
    app._history_limit.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 2px 4px;
        color: #e2e8f0;
        font-size: 10px;
    """)
    app._history_limit.currentTextChanged.connect(lambda: _load_history(app))
    table_toolbar.addWidget(app._history_limit)

    refresh_btn = QPushButton("LOAD")
    refresh_btn.setFixedWidth(50)
    refresh_btn.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #06b6d4;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: 1px;
    """)
    refresh_btn.clicked.connect(lambda: _load_history(app))
    table_toolbar.addWidget(refresh_btn)
    table_toolbar.addStretch()

    table_layout.addLayout(table_toolbar)

    app._history_table = QTableWidget()
    app._history_table.setColumnCount(5)
    app._history_table.setHorizontalHeaderLabels(["Time", "Temp", "Humidity", "Gas", "Distance"])
    app._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    app._history_table.setStyleSheet("""
        QTableWidget {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 6px;
            color: #94a3b8;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #1e293b;
            color: #64748b;
            border: none;
            border-bottom: 1px solid #1e293b;
            padding: 4px;
            font-size: 9px;
            letter-spacing: 1px;
        }
    """)
    app._history_table.verticalHeader().setVisible(False)
    table_layout.addWidget(app._history_table)

    table_page.setLayout(table_layout)
    app._data_stack.addWidget(table_page)

    app._data_stack.setCurrentIndex(0)

    left_layout.addWidget(app._data_stack)

    left_panel.setLayout(left_layout)
    layout.addWidget(left_panel, 1)

    right_panel = QWidget()
    right_panel.setFixedWidth(384)
    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(8)

    chat_title = QLabel("AI SENSOR ANALYST")
    chat_title.setStyleSheet("""
        color: #06b6d4;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
    """)
    right_layout.addWidget(chat_title)

    app._chat_scroll = QScrollArea()
    app._chat_scroll.setWidgetResizable(True)
    app._chat_scroll.setStyleSheet("""
        QScrollArea {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 6px;
        }
        QScrollBar:vertical {
            background: #0f172a;
            width: 6px;
        }
        QScrollBar::handle:vertical {
            background: #334155;
            border-radius: 3px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """)

    app._chat_content = QWidget()
    app._chat_content.setStyleSheet("background-color: #0f172a;")
    app._chat_content_layout = QVBoxLayout()
    app._chat_content_layout.setContentsMargins(8, 8, 8, 8)
    app._chat_content_layout.setSpacing(4)
    app._chat_content_layout.addStretch()
    app._chat_content.setLayout(app._chat_content_layout)
    app._chat_scroll.setWidget(app._chat_content)
    right_layout.addWidget(app._chat_scroll, 1)

    chat_input_layout = QHBoxLayout()
    chat_input_layout.setSpacing(8)

    app._chat_input = QLineEdit()
    app._chat_input.setPlaceholderText("Ask about sensor data...")
    app._chat_input.setStyleSheet("""
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 6px 10px;
        color: #e2e8f0;
        font-size: 11px;
    """)
    app._chat_input.returnPressed.connect(lambda: _send_chat(app))
    chat_input_layout.addWidget(app._chat_input)

    send_btn = QPushButton("SEND")
    send_btn.setFixedWidth(60)
    send_btn.setStyleSheet("""
        background-color: #06C755;
        color: white;
        font-weight: 700;
        font-size: 10px;
        border: none;
        border-radius: 8px;
        letter-spacing: 1px;
    """)
    send_btn.clicked.connect(lambda: _send_chat(app))
    chat_input_layout.addWidget(send_btn)

    right_layout.addLayout(chat_input_layout)

    right_panel.setLayout(right_layout)
    layout.addWidget(right_panel)

    widget.setLayout(layout)
    return widget


def _switch_view(app, view):
    if view == "charts":
        app._data_stack.setCurrentIndex(0)
        app._view_charts_btn.setStyleSheet("""
            QPushButton {
                background-color: #06b6d4;
                color: #0a0e1a;
                font-weight: 700;
                font-size: 9px;
                border: none;
                letter-spacing: 1px;
            }
        """)
        app._view_table_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #64748b;
                font-weight: 600;
                font-size: 9px;
                letter-spacing: 1px;
            }
        """)
        _load_history(app)
    else:
        app._data_stack.setCurrentIndex(1)
        app._view_table_btn.setStyleSheet("""
            QPushButton {
                background-color: #06b6d4;
                color: #0a0e1a;
                font-weight: 700;
                font-size: 9px;
                border: none;
                letter-spacing: 1px;
            }
        """)
        app._view_charts_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #64748b;
                font-weight: 600;
                font-size: 9px;
                letter-spacing: 1px;
            }
        """)
        _load_history(app)


CHART_LABELS = ["temperature", "humidity", "gas", "distance"]


def _add_chat_bubble(app, text, is_user=False, is_system=False):
    ts = datetime.now().strftime("%H:%M")

    bubble = QLabel()
    bubble.setWordWrap(True)
    bubble.setTextFormat(Qt.TextFormat.RichText)
    bubble.setMaximumWidth(280)

    time_label = QLabel(ts)
    time_label.setStyleSheet("font-size: 7pt; color: #64748b; background: transparent; border: none;")

    if is_system:
        bubble.setText(text)
        bubble.setStyleSheet("""
            QLabel {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 8px 12px;
                border-radius: 10px;
                font-size: 11px;
            }
        """)
        row = QHBoxLayout()
        row.setContentsMargins(40, 2, 40, 0)
        row.addStretch()
        row.addWidget(bubble)
        row.addStretch()
        time_row = QHBoxLayout()
        time_row.setContentsMargins(40, 0, 40, 4)
        time_row.addStretch()
        time_row.addWidget(time_label)
        time_row.addStretch()
    elif is_user:
        bubble.setText(text)
        bubble.setStyleSheet("""
            QLabel {
                background-color: #06C755;
                color: white;
                padding: 8px 12px;
                border-radius: 10px;
                font-size: 11px;
            }
        """)
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        row.addStretch()
        row.addWidget(bubble)
        time_row = QHBoxLayout()
        time_row.setContentsMargins(4, 0, 4, 4)
        time_row.addStretch()
        time_row.addWidget(time_label)
    else:
        import re
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        formatted = formatted.replace('\n', '<br>')
        bubble.setText(formatted)
        bubble.setStyleSheet("""
            QLabel {
                background-color: #1e293b;
                color: #10b981;
                padding: 8px 12px;
                border-radius: 10px;
                font-size: 11px;
            }
        """)
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 0)
        row.addWidget(bubble)
        row.addStretch()
        time_row = QHBoxLayout()
        time_row.setContentsMargins(4, 0, 4, 4)
        time_row.addWidget(time_label)
        time_row.addStretch()

    container = QWidget()
    container_layout = QVBoxLayout()
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(0)
    container_layout.addLayout(row)
    container_layout.addLayout(time_row)
    container.setLayout(container_layout)
    container.setStyleSheet("background: transparent;")

    app._chat_content_layout.insertWidget(app._chat_content_layout.count() - 1, container)
    app._chat_scroll.verticalScrollBar().setValue(app._chat_scroll.verticalScrollBar().maximum())


def _handle_chart_command(app, message):
    tokens = message.split()
    normalize = False
    sensors = []
    chart_name = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "/chart":
            i += 1
            continue
        if token == "-n":
            normalize = True
            i += 1
            continue
        if token == "-m":
            if i + 1 < len(tokens) and tokens[i + 1] not in CHART_LABELS and tokens[i + 1] not in ("-n",):
                chart_name = tokens[i + 1]
                i += 2
                continue
            else:
                i += 1
                continue
        if token in CHART_LABELS:
            sensors.append(token)
        i += 1

    app._chat_input.clear()
    _add_chat_bubble(app, message, is_user=True)

    if not sensors:
        _add_chat_bubble(app, "利用可能なセンサー: temperature, humidity, gas, distance<br>使い方: /chart temperature humidity -n -m \"My Chart\"", is_system=True)
        return

    name = chart_name if chart_name else "Command Chart"
    custom_groups = {name: sensors}
    normalize_flags = {name: normalize}
    app._sensor_chart.rebuild_charts(custom_groups, normalize_flags)

    if hasattr(app, '_last_readings') and app._last_readings:
        app._sensor_chart.update_chart(app._last_readings)

    norm_text = " (正規化)" if normalize else ""
    name_text = f" as '{chart_name}'" if chart_name else ""
    _add_chat_bubble(app, f"チャート作成: {', '.join(sensors)}{name_text}{norm_text}", is_system=True)


def _send_chat(app):
    text = app._chat_input.text().strip()
    if not text:
        return

    if text.startswith("/chart"):
        _handle_chart_command(app, text)
        return

    _add_chat_bubble(app, text, is_user=True)
    app._chat_input.clear()

    sensor_data = {}
    if hasattr(app, '_temp_card'):
        sensor_data["temperature"] = app._temp_card._text
    if hasattr(app, '_humidity_card'):
        sensor_data["humidity"] = app._humidity_card._text
    if hasattr(app, '_gas_card'):
        sensor_data["gas"] = app._gas_card._text
    if hasattr(app, '_distance_card'):
        sensor_data["distance"] = app._distance_card._text

    gemini_api_key = app._config.get("gemini_api_key", "")
    if not gemini_api_key:
        app._add_log("CHAT", "Gemini API key not configured")
        return
    app._chat_worker = GeminiChat(gemini_api_key, text, sensor_data)
    app._chat_worker.response.connect(lambda r: _on_chat_response(app, r))
    app._chat_worker.error.connect(lambda e: _on_chat_error(app, e))
    app._chat_worker.tool_called.connect(lambda f, a: _on_tool_called(app, f, a))
    app._chat_worker.start()

    _add_chat_bubble(app, "思考中...", is_system=True)


def _on_chat_response(app, response):
    _add_chat_bubble(app, response, is_user=False)


def _on_chat_error(app, error):
    _add_chat_bubble(app, f"Error: {error}", is_system=True)


def _on_tool_called(app, func_name, func_args):
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
            valid_sensors = [s for s in sensors if s in ("temperature", "humidity", "gas", "distance")]
            if valid_sensors:
                valid_groups[title] = valid_sensors
                normalize_flags[title] = normalize
        if not valid_groups:
            _add_chat_bubble(app, "利用可能なセンサー: temperature, humidity, gas, distance", is_system=True)
            return
        app._sensor_chart.rebuild_charts(valid_groups, normalize_flags)
        if hasattr(app, '_last_readings') and app._last_readings:
            app._sensor_chart.update_chart(app._last_readings)
        norm_text = " (正規化)" if normalize else ""
        _add_chat_bubble(app, f"チャート作成: {', '.join(valid_groups.keys())}{norm_text}", is_system=True)


def _load_history(app):
    if not hasattr(app, '_cloud_api') or not app._cloud_api:
        return

    limit = int(app._history_limit.currentText())
    app._history_table.setRowCount(0)

    def on_result(data):
        readings = data.get("readings", []) if isinstance(data, dict) else data
        if not isinstance(readings, list):
            return

        app._history_table.setRowCount(len(readings))
        for i, row in enumerate(readings):
            time_item = QTableWidgetItem(str(row.get("recorded_at", ""))[:19])
            temp_item = QTableWidgetItem(f"{row.get('temperature_c', 0):.1f}")
            hum_item = QTableWidgetItem(f"{row.get('humidity_pct', 0):.1f}")
            gas_item = QTableWidgetItem(f"{row.get('gas_ppm', 0):.0f}")
            dist_item = QTableWidgetItem(f"{row.get('distance_cm', 0):.1f}")

            for item in [time_item, temp_item, hum_item, gas_item, dist_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            app._history_table.setItem(i, 0, time_item)
            app._history_table.setItem(i, 1, temp_item)
            app._history_table.setItem(i, 2, hum_item)
            app._history_table.setItem(i, 3, gas_item)
            app._history_table.setItem(i, 4, dist_item)

        if hasattr(app, '_sensor_chart'):
            app._last_readings = readings
            app._sensor_chart.update_chart(readings)

    from cloud_worker import CloudWorker
    url = f"{app._cloud_api._base_url}/rovers/{app._cloud_api._device_uid}/readings?limit={limit}"
    worker = CloudWorker("GET", url)
    worker.result.connect(on_result)
    app._cloud_workers.append(worker)
    worker.finished.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
    worker.start()
