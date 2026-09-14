from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QStackedWidget
)
from ollama_chat import OllamaChat
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

    app._chat_display = QTextEdit()
    app._chat_display.setReadOnly(True)
    app._chat_display.setStyleSheet("""
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
        color: #94a3b8;
        font-size: 11px;
    """)
    right_layout.addWidget(app._chat_display, 1)

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
        background-color: #06b6d4;
        color: #0a0e1a;
        font-weight: 700;
        font-size: 10px;
        border: none;
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


def _send_chat(app):
    text = app._chat_input.text().strip()
    if not text:
        return

    app._chat_display.append(f'<span style="color: #06b6d4;">You:</span> {text}')
    app._chat_input.clear()

    sensor_data = {}
    if hasattr(app, '_temp_card'):
        sensor_data["temperature"] = app._temp_card.value_label.text()
    if hasattr(app, '_humidity_card'):
        sensor_data["humidity"] = app._humidity_card.value_label.text()
    if hasattr(app, '_gas_card'):
        sensor_data["gas"] = app._gas_card.value_label.text()
    if hasattr(app, '_distance_card'):
        sensor_data["distance"] = app._distance_card.value_label.text()

    ollama_url = app._config.get("ollama_url", "http://rpi5.local:11434/api/generate")
    app._chat_worker = OllamaChat(ollama_url, text, sensor_data)
    app._chat_worker.response.connect(lambda r: _on_chat_response(app, r))
    app._chat_worker.error.connect(lambda e: _on_chat_error(app, e))
    app._chat_worker.start()

    app._chat_display.append('<span style="color: #475569;">AI: Thinking...</span>')


def _on_chat_response(app, response):
    cursor = app._chat_display.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.select(cursor.SelectionType.BlockUnderCursor)
    cursor.removeSelectedText()
    app._chat_display.append(f'<span style="color: #10b981;">AI:</span> {response}')


def _on_chat_error(app, error):
    cursor = app._chat_display.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.select(cursor.SelectionType.BlockUnderCursor)
    cursor.removeSelectedText()
    app._chat_display.append(f'<span style="color: #ef4444;">Error:</span> {error}')


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
            app._sensor_chart.update_chart(readings)

    from cloud_worker import CloudWorker
    url = f"{app._cloud_api._base_url}/rovers/{app._cloud_api._device_uid}/readings?limit={limit}"
    worker = CloudWorker("GET", url)
    worker.result.connect(on_result)
    app._cloud_workers.append(worker)
    worker.finished.connect(lambda: app._cloud_workers.remove(worker) if worker in app._cloud_workers else None)
    worker.start()
