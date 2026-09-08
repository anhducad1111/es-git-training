import math
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtWidgets import QWidget


class GimbalHUD(QWidget):
    def __init__(self):
        super().__init__()
        self._pan = 90.0
        self._tilt = 90.0
        self._current_pan = 90.0
        self._current_tilt = 90.0
        self.setFixedSize(120, 180)
        self.setStyleSheet("background: transparent;")
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_gimbal(self, pan, tilt):
        self._pan = 180 - pan
        self._tilt = 180 - tilt

    def _animate(self):
        self._current_pan += (self._pan - self._current_pan) * 0.22
        self._current_tilt += (self._tilt - self._current_tilt) * 0.22
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w // 2
        
        painter.translate(cx, h // 2)
        painter.scale(1, -1)
        painter.translate(-cx, -h // 2)
        
        pink = QColor(255, 42, 133)
        dim_pink = QColor(255, 42, 133, 80)
        white = QColor(255, 255, 255, 200)
        dim_white = QColor(148, 163, 184, 100)
        
        header_y = 10
        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(5, header_y - 5, w - 10, 25, 4, 4)
        
        painter.setFont(QFont("JetBrains Mono", 7))
        painter.setPen(QPen(pink, 1))
        painter.drawText(10, header_y + 10, "CAM")
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(w - 35, header_y + 10, "GIMBAL")
        
        painter.setPen(QPen(pink, 1))
        painter.drawText(cx - 15, header_y + 10, f"{int(self._current_pan)}°")
        
        tilt_cy = 70
        r = 30
        
        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, tilt_cy), r, r)
        
        painter.setPen(QPen(QColor(59, 130, 246, 80), 1, Qt.PenStyle.DashLine))
        painter.drawLine(cx - 22, tilt_cy, cx + 22, tilt_cy)
        
        painter.setFont(QFont("JetBrains Mono", 6))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(cx + r + 2, tilt_cy - 15, "UP")
        painter.drawText(cx + r + 2, tilt_cy + 3, "LVL")
        painter.drawText(cx + r + 2, tilt_cy + 18, "DN")
        
        for offset in [-24, -12, 0, 12, 24]:
            is_zero = offset == 0
            width = 20 if is_zero else 12
            painter.setPen(QPen(pink if is_zero else dim_white, 1 if is_zero else 1))
            painter.drawLine(cx - width // 2, tilt_cy + offset, cx + width // 2, tilt_cy + offset)
        
        tilt_frac = (self._current_tilt - 90.0) / 90.0
        max_deflection = 0.95
        needle_angle = tilt_frac * max_deflection
        
        start_x = cx - 14
        start_y = tilt_cy
        needle_len = r + 5
        tip_x = start_x + needle_len * math.cos(needle_angle)
        tip_y = start_y + needle_len * math.sin(needle_angle)
        
        painter.setPen(QPen(pink, 2))
        painter.drawLine(start_x, start_y, int(tip_x), int(tip_y))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(pink))
        painter.drawEllipse(QPointF(start_x, start_y), 4, 4)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(QPointF(start_x, start_y), 2, 2)
        
        tilt_offset = int(self._current_tilt - 90)
        painter.setFont(QFont("JetBrains Mono", 6))
        painter.setPen(QPen(pink, 1))
        painter.drawText(cx - 10, tilt_cy + r + 18, f"{tilt_offset:+d}°")
        
        pan_cy = 135
        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, pan_cy), r, r)
        
        painter.setPen(QPen(QColor(59, 130, 246, 80), 1, Qt.PenStyle.DashLine))
        painter.drawLine(cx - 22, pan_cy, cx + 22, pan_cy)
        
        painter.setFont(QFont("JetBrains Mono", 6))
        painter.setPen(QPen(pink, 1))
        painter.drawText(cx - 3, pan_cy - r - 2, "N")
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(cx - 3, pan_cy + r + 8, "S")
        painter.drawText(cx - r - 8, pan_cy + 3, "W")
        painter.drawText(cx + r + 2, pan_cy + 3, "E")
        
        for deg in range(0, 181, 15):
            rad = math.pi * (1 - deg / 180)
            x1 = cx + math.cos(rad) * (r - 2)
            y1 = pan_cy + math.sin(rad) * (r - 2)
            x2 = cx + math.cos(rad) * (r - 6)
            y2 = pan_cy + math.sin(rad) * (r - 6)
            is_major = deg % 45 == 0
            painter.setPen(QPen(pink if is_major else dim_white, 1))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        pan_rad = math.pi * (1 - self._current_pan / 180)
        arrow_len = r - 8
        tip_x = cx + arrow_len * math.cos(pan_rad)
        tip_y = pan_cy + arrow_len * math.sin(pan_rad)
        
        painter.setPen(QPen(pink, 2))
        painter.drawLine(cx, pan_cy, int(tip_x), int(tip_y))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(pink))
        painter.drawEllipse(QPointF(cx, pan_cy), 4, 4)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(QPointF(cx, pan_cy), 2, 2)
        
        pan_offset = int(self._current_pan - 90)
        painter.setFont(QFont("JetBrains Mono", 6))
        painter.setPen(QPen(pink, 1))
        painter.drawText(cx - 10, pan_cy + r + 18, f"{pan_offset:+d}°")
        
        painter.end()
