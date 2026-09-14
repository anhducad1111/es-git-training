import math
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtWidgets import QWidget


class SensorGauges(QWidget):
    def __init__(self):
        super().__init__()
        self._temp = 0.0
        self._humidity = 0.0
        self._gas = 0.0
        self._current_temp = 0.0
        self._current_humidity = 0.0
        self._current_gas = 0.0
        self.setFixedSize(180, 70)
        self.setStyleSheet("background: transparent;")
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_values(self, temp, humidity, gas):
        self._temp = temp
        self._humidity = humidity
        self._gas = gas

    def _animate(self):
        self._current_temp += (self._temp - self._current_temp) * 0.15
        self._current_humidity += (self._humidity - self._current_humidity) * 0.15
        self._current_gas += (self._gas - self._current_gas) * 0.15
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        
        pink = QColor(255, 42, 133)
        amber = QColor(245, 158, 11)
        cyan = QColor(6, 182, 212)
        green = QColor(16, 185, 129)
        dim_white = QColor(148, 163, 184, 150)
        dark_bg = QColor(11, 19, 38)
        border_color = QColor(36, 49, 71)
        
        gauge_r = 24
        gauge_y = 35
        
        self._draw_gauge(painter, 30, gauge_y, gauge_r, self._current_temp, 60, "T", amber, "°C")
        self._draw_gauge(painter, w // 2, gauge_y, gauge_r, self._current_humidity, 100, "H", cyan, "%")
        self._draw_gauge(painter, w - 30, gauge_y, gauge_r, self._current_gas, 1000, "G", green, "")
        
        painter.setFont(QFont("JetBrains Mono", 7))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(18, 12, "TEMP")
        painter.drawText(w // 2 - 15, 12, "HUMID")
        painter.drawText(w - 42, 12, "GAS")
        
        painter.end()
    
    def _draw_gauge(self, painter, cx, cy, r, value, max_val, label, color, unit):
        dark_bg = QColor(11, 19, 38)
        border_color = QColor(36, 49, 71)
        dim_color = QColor(100, 116, 139, 100)
        
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(dark_bg))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        
        painter.setPen(QPen(QColor(30, 41, 59), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r - 3, r - 3)
        
        start_angle = 225
        span_angle = -270
        painter.setPen(QPen(border_color, 2))
        painter.drawArc(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2, start_angle * 16, span_angle * 16)
        
        fill_percent = min(1.0, value / max_val) if max_val > 0 else 0
        fill_angle = int(270 * fill_percent)
        painter.setPen(QPen(color, 2))
        painter.drawArc(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2, start_angle * 16, -fill_angle * 16)
        
        for i in range(0, 7):
            angle = math.radians(225 - i * 45)
            x1 = cx + (r - 6) * math.cos(angle)
            y1 = cy - (r - 6) * math.sin(angle)
            x2 = cx + (r - 2) * math.cos(angle)
            y2 = cy - (r - 2) * math.sin(angle)
            is_major = i % 2 == 0
            painter.setPen(QPen(dim_color if not is_major else color, 1))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        needle_angle = math.radians(225 - fill_angle)
        needle_len = r - 10
        tip_x = cx + needle_len * math.cos(needle_angle)
        tip_y = cy - needle_len * math.sin(needle_angle)
        painter.setPen(QPen(color, 1.5))
        painter.drawLine(cx, cy, int(tip_x), int(tip_y))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(cx, cy), 3, 3)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(QPointF(cx, cy), 1.5, 1.5)
        
        painter.setFont(QFont("JetBrains Mono", 7))
        painter.setPen(QPen(color, 1))
        display_val = f"{int(value)}" if value >= 10 else f"{value:.1f}"
        painter.drawText(cx - 10, cy + r + 12, f"{display_val}{unit}")
