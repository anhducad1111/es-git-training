from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget
)


def create_diagnostics_view(app):
    widget = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)

    left_panel = QWidget()
    left_layout = QVBoxLayout()
    left_layout.setContentsMargins(0, 0, 0, 0)

    charts_title = QLabel("Historical Sensor Analytics")
    charts_title.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
    left_layout.addWidget(charts_title)

    charts_placeholder = QLabel("Charts will be displayed here")
    charts_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    charts_placeholder.setStyleSheet(
        "background-color: #1e293b; border-radius: 6px; padding: 40px; color: #64748b;"
    )
    left_layout.addWidget(charts_placeholder)

    left_panel.setLayout(left_layout)
    layout.addWidget(left_panel, 1)

    right_panel = QWidget()
    right_panel.setFixedWidth(384)
    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)

    chat_title = QLabel("Local AI Sensor Analyst (Ollama)")
    chat_title.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
    right_layout.addWidget(chat_title)

    app._chat_display = QTextEdit()
    app._chat_display.setReadOnly(True)
    app._chat_display.setStyleSheet("background-color: #131b2e; border-radius: 6px; padding: 8px;")
    right_layout.addWidget(app._chat_display, 1)

    chat_input_layout = QHBoxLayout()
    app._chat_input = QLineEdit()
    app._chat_input.setPlaceholderText("Ask about sensor data...")
    chat_input_layout.addWidget(app._chat_input)

    send_btn = QPushButton("Send")
    send_btn.setFixedWidth(60)
    send_btn.clicked.connect(app._send_chat)
    chat_input_layout.addWidget(send_btn)

    right_layout.addLayout(chat_input_layout)

    right_panel.setLayout(right_layout)
    layout.addWidget(right_panel)

    widget.setLayout(layout)
    return widget
