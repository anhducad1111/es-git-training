from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

KEY_HINTS = [
    ("W/S/A/D", "Forward/Back/Left/Right"),
    ("Space", "Emergency Stop"),
    ("V", "Toggle Follow Mode"),
    ("I/K", "Gimbal Up/Down"),
    ("J/L", "Gimbal Left/Right"),
    ("C", "Center Gimbal"),
    ("Shift", "Speed Up"),
    ("Ctrl", "Slow Down"),
]


def create_key_legend(app):
    widget = QWidget()
    widget.setFixedHeight(24)
    widget.setStyleSheet("""
        background-color: #0f172a;
        border-top: 1px solid #1e293b;
    """)
    layout = QHBoxLayout()
    layout.setContentsMargins(16, 0, 16, 0)
    layout.setSpacing(16)

    for key, desc in KEY_HINTS:
        item = QLabel()
        item.setText(f'<span style="color:#06b6d4;font-weight:700;">{key}</span> <span style="color:#64748b;">{desc}</span>')
        item.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(item)

    layout.addStretch()
    widget.setLayout(layout)
    return widget
