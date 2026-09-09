from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QLabel, QSizePolicy


class VideoCanvas(QLabel):
    gimbal_changed = pyqtSignal(float, float)

    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background-color: #0a0e1a;
            border: 1px solid #1e293b;
        """)
        self.setText("NO SIGNAL")
        self.setFont(QFont("JetBrains Mono", 12))
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.setMouseTracking(True)
        self._dragging = False
        self._last_x = 0
        self._last_y = 0
        self._pan = 90.0
        self._tilt = 90.0
        self._sensitivity = 0.3
        self._mouse_gimbal_enabled = True

    def set_gimbal(self, pan, tilt):
        self._pan = pan
        self._tilt = tilt

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._mouse_gimbal_enabled:
            self._dragging = True
            self._last_x = event.position().x()
            self._last_y = event.position().y()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        dx = event.position().x() - self._last_x
        dy = event.position().y() - self._last_y
        self._last_x = event.position().x()
        self._last_y = event.position().y()

        self._pan = max(0, min(180, self._pan - dx * self._sensitivity))
        self._tilt = max(0, min(180, self._tilt + dy * self._sensitivity))
        self.gimbal_changed.emit(self._pan, self._tilt)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._dragging = False
            self._mouse_gimbal_enabled = False
            if hasattr(self, '_app') and hasattr(self._app, '_mouse_gimbal_btn'):
                self._app._mouse_gimbal_btn.setChecked(False)
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap() is None or self.pixmap().isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        color = QColor(255, 255, 255, 200)
        dim_color = QColor(255, 255, 255, 100)

        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawEllipse(QPointF(cx, cy), 6, 6)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(cx, cy), 1, 1)

        painter.setPen(QPen(color, 2))
        painter.drawLine(int(cx), int(cy - 22), int(cx), int(cy - 6))
        painter.drawLine(int(cx), int(cy + 6), int(cx), int(cy + 22))
        painter.drawLine(int(cx - 22), int(cy), int(cx - 6), int(cy))
        painter.drawLine(int(cx + 6), int(cy), int(cx + 22), int(cy))

        painter.setPen(QPen(dim_color, 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 16, 16)

        if hasattr(self, '_app') and hasattr(self._app, '_hog_detections'):
            for det in self._app._hog_detections:
                x, y, w, h = det["x"], det["y"], det["w"], det["h"]
                conf = det["confidence"]
                label = det.get("label", "Person")
                painter.setPen(QPen(QColor(16, 185, 129), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(x, y, w, h)
                painter.setFont(QFont("JetBrains Mono", 8))
                painter.drawText(x, y - 5, f"{label} {conf:.1f}")

        painter.end()

    def update_frame(self, jpeg_data):
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_data)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)

    def update_frame_jpeg(self, image):
        if isinstance(image, QPixmap):
            pixmap = image
        elif isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(image, "JPEG")
        
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_app') and hasattr(self._app, '_gimbal_hud'):
            self._app._gimbal_hud.move(10, self.height() - 190)
