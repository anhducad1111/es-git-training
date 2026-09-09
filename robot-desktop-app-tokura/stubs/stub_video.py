import time
import random
from PyQt6.QtCore import QThread, pyqtSignal, QBuffer, QByteArray
from PyQt6.QtGui import QImage, QPainter, QColor, QFont


class StubVideoThread(QThread):
    frame_received = pyqtSignal(bytes)

    def __init__(self, width=640, height=480, fps=30):
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self._running = False
        self._frame_count = 0

    def run(self):
        self._running = True
        interval = 1.0 / self.fps

        while self._running:
            start = time.time()
            frame = self._generate_frame()
            self.frame_received.emit(frame)
            self._frame_count += 1
            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)

    def _generate_frame(self):
        img = QImage(self.width, self.height, QImage.Format.Format_RGB888)
        painter = QPainter(img)

        bg_color = QColor(20, 30, 50)
        painter.fillRect(0, 0, self.width, self.height, bg_color)

        painter.setPen(QColor(100, 160, 255))
        for x in range(0, self.width, 80):
            painter.drawLine(x, 0, x, self.height)
        for y in range(0, self.height, 80):
            painter.drawLine(0, y, self.width, y)

        center_x = self.width // 2
        center_y = self.height // 2
        painter.setPen(QColor(0, 255, 100))
        painter.drawLine(center_x - 20, center_y, center_x + 20, center_y)
        painter.drawLine(center_x, center_y - 20, center_x, center_y + 20)

        painter.setPen(QColor(255, 255, 255))
        font = QFont("JetBrains Mono", 12)
        painter.setFont(font)
        painter.drawText(10, 25, f"STUB VIDEO | {self.width}x{self.height} | Frame: {self._frame_count}")

        painter.setPen(QColor(0, 255, 0))
        painter.drawText(10, 50, f"FPS: {self.fps} | Simulated Feed")

        for i in range(3):
            x = random.randint(100, self.width - 100)
            y = random.randint(100, self.height - 100)
            size = random.randint(20, 60)
            color = QColor(
                random.randint(50, 255),
                random.randint(50, 255),
                random.randint(50, 255),
            )
            painter.setBrush(color)
            painter.drawEllipse(x, y, size, size)

        painter.end()

        buffer = QByteArray()
        qbuffer = QBuffer(buffer)
        qbuffer.open(QBuffer.OpenModeFlag.WriteOnly)
        img.save(qbuffer, "JPEG", quality=85)
        qbuffer.close()
        return buffer.data()

    def stop(self):
        self._running = False
        self.wait()
