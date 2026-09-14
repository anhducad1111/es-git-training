from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget


class PingDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self._ping_ms = 0.0
        self.setFixedSize(130, 24)
        self.setStyleSheet("background: transparent;")

    def update_ping(self, ping_ms):
        self._ping_ms = ping_ms
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.setPen(QPen(QColor(30, 41, 59, 180), 1))
        painter.setBrush(QColor(15, 23, 42, 180))
        painter.drawRoundedRect(0, 0, w, h, 4, 4)

        # Ping value
        if self._ping_ms < 50:
            ping_color = QColor(16, 185, 129)  # green
        elif self._ping_ms < 150:
            ping_color = QColor(245, 158, 11)  # yellow
        else:
            ping_color = QColor(239, 68, 68)  # red

        painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        painter.setPen(QPen(ping_color, 1))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, f"Ping {self._ping_ms:.0f} ms")

        painter.end()
