from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget


class FPSDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self._fps = 0.0
        self._frame_count = 0
        self._last_time = QTimer()
        self.setFixedSize(80, 24)
        self.setStyleSheet("background: transparent;")

    def update_fps(self, fps):
        self._fps = fps
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

        # FPS value
        if self._fps >= 25:
            fps_color = QColor(16, 185, 129)  # green
        elif self._fps >= 15:
            fps_color = QColor(245, 158, 11)  # yellow
        else:
            fps_color = QColor(239, 68, 68)  # red

        painter.setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        painter.setPen(QPen(fps_color, 1))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, f"{self._fps:.0f} FPS")

        painter.end()
