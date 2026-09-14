import math
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtWidgets import QWidget


class SpeedMeter(QWidget):
    def __init__(self):
        super().__init__()
        self._current_speed = 0
        self._target_speed = 0
        self._max_speed = 255
        self.setFixedSize(120, 70)
        self.setStyleSheet("background: transparent;")

        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_speed(self, speed):
        self._target_speed = max(0, min(self._max_speed, speed))

    def _animate(self):
        self._current_speed += (self._target_speed - self._current_speed) * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2

        pink = QColor(255, 42, 133)
        dim_pink = QColor(255, 42, 133, 80)
        white = QColor(255, 255, 255, 200)
        dim_white = QColor(148, 163, 184, 100)
        green = QColor(16, 185, 129)
        yellow = QColor(245, 158, 11)
        red = QColor(239, 68, 68)

        header_y = 5
        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(5, header_y, w - 10, 18, 3, 3)

        painter.setFont(QFont("JetBrains Mono", 6))
        painter.setPen(QPen(pink, 1))
        painter.drawText(10, header_y + 12, "SPD")
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(w - 40, header_y + 12, "MOTOR")

        painter.setPen(QPen(pink, 1))
        painter.drawText(cx - 12, header_y + 12, f"{int(self._current_speed)}")

        gauge_cy = 48
        r = 22

        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, gauge_cy), r, r)

        painter.setPen(QPen(QColor(59, 130, 246, 80), 1, Qt.PenStyle.DashLine))
        painter.drawLine(cx - 18, gauge_cy, cx + 18, gauge_cy)

        for deg in range(0, 181, 30):
            rad = math.pi * (1 - deg / 180)
            x1 = cx + math.cos(rad) * (r - 2)
            y1 = gauge_cy + math.sin(rad) * (r - 2)
            x2 = cx + math.cos(rad) * (r - 5)
            y2 = gauge_cy + math.sin(rad) * (r - 5)
            is_major = deg % 90 == 0
            painter.setPen(QPen(pink if is_major else dim_white, 1))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        speed_frac = self._current_speed / self._max_speed
        needle_angle = math.pi * (1 - speed_frac)
        arrow_len = r - 6
        tip_x = cx + arrow_len * math.cos(needle_angle)
        tip_y = gauge_cy + arrow_len * math.sin(needle_angle)

        speed_pct = (self._current_speed / self._max_speed) * 100
        if speed_pct > 80:
            needle_color = red
        elif speed_pct > 50:
            needle_color = yellow
        else:
            needle_color = green

        painter.setPen(QPen(needle_color, 2))
        painter.drawLine(cx, gauge_cy, int(tip_x), int(tip_y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(needle_color))
        painter.drawEllipse(QPointF(cx, gauge_cy), 3, 3)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(QPointF(cx, gauge_cy), 1, 1)

        painter.setFont(QFont("JetBrains Mono", 5))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(cx - 3, gauge_cy + r + 8, "0")
        painter.drawText(cx - 8, gauge_cy - r - 2, "255")

        painter.end()
