from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QRadialGradient
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout


class SensorCard(QWidget):
    def __init__(self, name, unit, icon, min_val=0, max_val=100):
        super().__init__()
        self._name = name
        self._unit = unit
        self._icon = icon
        self._min = min_val
        self._max = max_val
        self._value = 0
        self._percent = 0
        self._text = "0"
        self._is_distance = (name == "Distance")
        
        self.setFixedHeight(70 if not self._is_distance else 160)
        self.setStyleSheet("""
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
        """)
    
    def update_value(self, text, percent):
        self._text = text
        self._percent = max(0, min(100, percent))
        try:
            self._value = float(text.split()[0])
        except:
            self._value = 0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        if self._is_distance:
            self._paint_distance_gauge(painter, w, h)
        else:
            self._paint_sensor_bar(painter, w, h)
        
        painter.end()
    
    def _paint_distance_gauge(self, painter, w, h):
        pink = QColor(255, 42, 133)
        white = QColor(255, 255, 255, 200)
        dim_white = QColor(148, 163, 184, 150)
        
        painter.setFont(QFont("JetBrains Mono", 9))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(10, 18, "PROXIMITY / COLLISION RISK")
        
        cx = w // 2
        cy = 95
        r = 55
        
        dist = self._value
        if dist <= 20:
            status_color = QColor(239, 68, 68)
            status_text = "DANGER"
        elif dist <= 40:
            status_color = QColor(245, 158, 11)
            status_text = "CAUTION"
        else:
            status_color = QColor(16, 185, 129)
            status_text = "SAFE"
        
        painter.setPen(QPen(QColor(30, 41, 59), 10))
        painter.drawArc(cx - r, cy - r, r * 2, r * 2, 0, 180 * 16)
        
        safe_angle = min(180, max(0, (dist / 100) * 180))
        painter.setPen(QPen(status_color, 10))
        painter.drawArc(cx - r, cy - r, r * 2, r * 2, 0, int(safe_angle * 16))
        
        needle_rad = 3.14159 * (1 - safe_angle / 180)
        tip_x = cx + (r - 8) * __import__('math').cos(needle_rad)
        tip_y = cy - (r - 8) * __import__('math').sin(needle_rad)
        painter.setPen(QPen(white, 2))
        painter.drawLine(cx, cy, int(tip_x), int(tip_y))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(status_color))
        painter.drawEllipse(QPointF(cx, cy), 5, 5)
        
        painter.setFont(QFont("JetBrains Mono", 14))
        painter.setPen(QPen(status_color, 1))
        painter.drawText(cx - 40, cy + 30, f"{int(dist)} cm")
        
        painter.setFont(QFont("JetBrains Mono", 8))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(10, h - 10, "0")
        painter.drawText(w - 20, h - 10, "100+")
        
        painter.setPen(QPen(status_color, 1))
        badge_x = w - 80
        painter.drawText(badge_x, 18, status_text)
    
    def _paint_sensor_bar(self, painter, w, h):
        white = QColor(255, 255, 255, 200)
        dim_white = QColor(148, 163, 184, 150)
        
        painter.setFont(QFont("JetBrains Mono", 8))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(10, 15, self._name.upper())
        
        painter.setFont(QFont("JetBrains Mono", 12))
        painter.setPen(QPen(white, 1))
        painter.drawText(10, 35, self._text)
        
        bar_y = 45
        bar_h = 12
        bar_w = w - 20
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 41, 59)))
        painter.drawRoundedRect(10, bar_y, bar_w, bar_h, 4, 4)
        
        if self._name == "Temp":
            if self._percent < 50:
                fill_color = QColor(16, 185, 129)
            elif self._percent < 75:
                fill_color = QColor(245, 158, 11)
            else:
                fill_color = QColor(239, 68, 68)
        elif self._name == "Humidity":
            fill_color = QColor(59, 130, 246)
        else:
            fill_color = QColor(16, 185, 129)
        
        fill_w = int(bar_w * self._percent / 100)
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(10, bar_y, fill_w, bar_h, 4, 4)
        
        painter.setFont(QFont("JetBrains Mono", 7))
        painter.setPen(QPen(dim_white, 1))
        painter.drawText(10, h - 5, f"0")
        painter.drawText(w - 30, h - 5, f"{self._max}")
