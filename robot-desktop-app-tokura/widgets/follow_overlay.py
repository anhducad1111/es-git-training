from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel


class FollowModeOverlay(QWidget):
    """Overlay widget for follow mode: shows distance and target angle on video canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: rgba(15, 23, 42, 0.85); border-radius: 4px;")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(16)

        dist_title = QLabel("DIST")
        dist_title.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(dist_title)

        self._dist_value = QLabel("-- cm")
        self._dist_value.setFixedWidth(70)
        self._dist_value.setStyleSheet("""
            color: #10b981;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
        """)
        layout.addWidget(self._dist_value)

        target_title = QLabel("TARGET")
        target_title.setStyleSheet("color: #475569; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(target_title)

        self._target_value = QLabel("0°")
        self._target_value.setFixedWidth(60)
        self._target_value.setStyleSheet("""
            color: #a78bfa;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
        """)
        layout.addWidget(self._target_value)

        self.setLayout(layout)
        self.adjustSize()
        self.hide()

    def update_distance(self, dist_cm):
        self._dist_value.setText(f"{dist_cm:.0f} cm")
        if dist_cm < 30:
            self._dist_value.setStyleSheet("color: #ef4444; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        elif dist_cm < 60:
            self._dist_value.setStyleSheet("color: #f59e0b; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        else:
            self._dist_value.setStyleSheet("color: #10b981; font-size: 11px; font-family: 'JetBrains Mono', monospace;")

    def update_target_angle(self, angle):
        sign = "+" if angle >= 0 else ""
        self._target_value.setText(f"{sign}{angle:.1f}°")
        if abs(angle) < 10:
            self._target_value.setStyleSheet("color: #10b981; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        elif abs(angle) < 30:
            self._target_value.setStyleSheet("color: #f59e0b; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        else:
            self._target_value.setStyleSheet("color: #ef4444; font-size: 11px; font-family: 'JetBrains Mono', monospace;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            parent_w = self.parent().width()
            self.move(parent_w - self.width() - 10, 10)
