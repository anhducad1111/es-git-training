from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QColor, QBrush, QRadialGradient
from PyQt6.QtWidgets import QLabel, QSizePolicy


class CameraDirectionWidget(QLabel):
    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self._pan = 90.0
        self._tilt = 90.0
        self.setFixedSize(120, 160)
        self.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 42, 133, 0.3);
            border-radius: 8px;
        """)

    def set_gimbal(self, pan, tilt):
        self._pan = pan
        self._tilt = tilt
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        cx = w // 2
        pan_cy = 50
        tilt_cy = 130
        r = 35

        pink = QColor(255, 42, 133)
        dim_pink = QColor(255, 42, 133, 80)
        white = QColor(255, 255, 255, 200)
        dim_white = QColor(148, 163, 184, 100)

        painter.setPen(QPen(dim_pink, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, pan_cy), r, r)

        painter.setPen(QPen(QColor(59, 130, 246, 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(cx - 25, pan_cy, cx + 25, pan_cy)

        pan_rad = 3.14159 + (self._pan / 180.0) * 3.14159
        arrow_len = r - 8
        tip_x = cx + arrow_len * __import__('math').cos(pan_rad)
        tip_y = pan_cy + arrow_len * __import__('math').sin(pan_rad)

        painter.setPen(QPen(pink, 2))
        painter.drawLine(cx, pan_cy, int(tip_x), int(tip_y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(pink))
        painter.drawEllipse(QPointF(cx, pan_cy), 3, 3)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(QPointF(cx, pan_cy), 1, 1)

        painter.setPen(QPen(dim_pink, 1))
        painter.drawEllipse(QPointF(cx, tilt_cy), r, r)

        painter.setPen(QPen(QColor(59, 130, 246, 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(cx - 25, tilt_cy, cx + 25, tilt_cy)

        tilt_frac = (self._tilt - 90.0) / 90.0
        max_deflection = 0.95
        needle_angle = -tilt_frac * max_deflection

        import math
        start_x = cx - 12
        start_y = tilt_cy
        needle_len = r - 5
        tip_x = start_x + needle_len * math.cos(needle_angle)
        tip_y = start_y + needle_len * math.sin(needle_angle)

        painter.setPen(QPen(pink, 2))
        painter.drawLine(start_x, start_y, int(tip_x), int(tip_y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(pink))
        painter.drawEllipse(QPointF(start_x, start_y), 3, 3)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(QPointF(start_x, start_y), 1, 1)

        painter.end()
