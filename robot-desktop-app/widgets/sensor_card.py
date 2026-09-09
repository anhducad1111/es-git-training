from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QProgressBar, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)


class SensorCard(QWidget):
    def __init__(self, name, unit, icon="", min_val=0, max_val=100):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.icon_label = QLabel(icon)
        self.icon_label.setFixedWidth(20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.icon_label)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: 600; font-family: 'JetBrains Mono', monospace;")
        top_row.addWidget(self.value_label)

        layout.addLayout(top_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.setStyleSheet(
            "background-color: #171f33; border: 1px solid #243147; border-radius: 6px; padding: 4px;"
        )

    def update_value(self, value, progress=None):
        self.value_label.setText(str(value))
        if progress is not None:
            self.progress.setValue(int(min(100, max(0, progress))))
