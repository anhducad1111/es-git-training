from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget


class LatencyDisplay(QWidget):
    """Shows time from frame decode to on-screen display, not network RTT."""

    def __init__(self):
        super().__init__()
        self._latency_ms = 0.0
        self.setFixedSize(130, 24)
        self.setStyleSheet("background: transparent;")

    def update_latency(self, latency_ms):
        self._latency_ms = latency_ms
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

        # Latency value
        if self._latency_ms < 150:
            color = QColor(16, 185, 129)  # green
        elif self._latency_ms < 500:
            color = QColor(245, 158, 11)  # yellow
        else:
            color = QColor(239, 68, 68)  # red

        painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        painter.setPen(QPen(color, 1))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, f"Lat {self._latency_ms:.0f} ms")

        painter.end()
