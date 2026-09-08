from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image


class SuperResolutionWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, image_path, output_path):
        super().__init__()
        self.image_path = image_path
        self.output_path = output_path
    
    def run(self):
        try:
            img = Image.open(self.image_path)
            width, height = img.size
            new_width = width * 4
            new_height = height * 4
            upscaled = img.resize((new_width, new_height), Image.BICUBIC)
            upscaled.save(self.output_path, "PNG")
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))
