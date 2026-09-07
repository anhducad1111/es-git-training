from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy


class VideoCanvas(QLabel):
    gimbal_changed = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0f172a; border: 1px solid #334155;")
        self.setText("No Video Feed")
        self.setFont(QFont("JetBrains Mono", 14))
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

    def set_gimbal(self, pan, tilt):
        self._pan = pan
        self._tilt = tilt

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

        self._pan = max(0, min(180, self._pan + dx * self._sensitivity))
        self._tilt = max(0, min(180, self._tilt - dy * self._sensitivity))
        self.gimbal_changed.emit(self._pan, self._tilt)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

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
