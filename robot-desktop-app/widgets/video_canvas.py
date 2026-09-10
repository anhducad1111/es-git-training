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
        self._follow_detections = []

    def set_gimbal(self, pan, tilt):
        self._pan = pan
        self._tilt = tilt

    def set_follow_detections(self, detections):
        """Set follow mode detections for overlay display."""
        self._follow_detections = detections
        self.update()

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

        # Follow mode detections
        if self._follow_detections:
            for det in self._follow_detections:
                bbox = det.get("bbox")
                if bbox is None:
                    continue
                    
                # bbox format from RcCarPoseDetector: (x, y, w, h)
                bx, by, bw, bh = bbox
                x1, y1 = bx, by
                x2, y2 = bx + bw, by + bh
                
                # Calculate scale to map original coords to display coords
                pixmap = self.pixmap()
                if pixmap and not pixmap.isNull():
                    orig_w, orig_h = 640, 480
                    pw, ph = pixmap.width(), pixmap.height()
                    scale_x = pw / orig_w
                    scale_y = ph / orig_h
                    offset_x = (self.width() - pw) / 2
                    offset_y = (self.height() - ph) / 2
                    
                    dx1 = int(x1 * scale_x + offset_x)
                    dy1 = int(y1 * scale_y + offset_y)
                    dx2 = int(x2 * scale_x + offset_x)
                    dy2 = int(y2 * scale_y + offset_y)
                    w = dx2 - dx1
                    h = dy2 - dy1
                    
                    if not hasattr(self, '_follow_log_count'):
                        self._follow_log_count = 0
                    self._follow_log_count += 1
                    if self._follow_log_count % 30 == 0:
                        print(f"[DEBUG] bbox=({x1},{y1},{x2},{y2}) pixmap=({pw},{ph}) widget=({self.width()},{self.height()}) scale=({scale_x:.2f},{scale_y:.2f}) offset=({offset_x:.0f},{offset_y:.0f}) -> ({dx1},{dy1},{dx2},{dy2})")
                else:
                    dx1, dy1, w, h = x1, y1, x2 - x1, y2 - y1
                
                # Draw bounding box
                painter.setPen(QPen(QColor(255, 165, 0), 2))  # Orange
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(dx1, dy1, w, h)
                
                # Draw label
                yaw = det.get("yaw_deg")
                dist = det.get("dist_m")
                conf = det.get("confidence", 0.0)
                
                label_parts = ["TARGET"]
                if yaw is not None:
                    label_parts.append(f"yaw{yaw:+.0f}°")
                if dist is not None:
                    label_parts.append(f"{dist:.2f}m")
                label_parts.append(f"{conf:.0%}")
                
                label = " ".join(label_parts)
                painter.setFont(QFont("JetBrains Mono", 8))
                painter.setPen(QPen(QColor(255, 165, 0), 1))
                painter.drawText(dx1, dy1 - 5, label)

        painter.end()

    def update_frame(self, jpeg_data):
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_data)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
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
                Qt.TransformationMode.FastTransformation,
            )
            self.setPixmap(scaled)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_app') and hasattr(self._app, '_gimbal_hud'):
            self._app._gimbal_hud.move(10, self.height() - 260)
        if hasattr(self, '_app') and hasattr(self._app, '_speed_meter'):
            self._app._speed_meter.move(10, self.height() - 330)
