import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class ImageProcessor(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, input_path, output_path, mode):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode

    def run(self):
        try:
            self.status.emit("Processing...")
            img = cv2.imread(self.input_path)
            if img is None:
                self.error.emit("Failed to read image")
                return

            if isinstance(self.mode, list):
                result = img
                for m in self.mode:
                    result = self._apply_mode(result, m)
            else:
                result = self._apply_mode(img, self.mode)

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _apply_mode(self, img, mode):
        if mode == "auto":
            return self._auto_correct(img)
        elif mode == "contrast":
            return self._enhance_contrast(img)
        elif mode == "brightness":
            return self._adjust_brightness(img)
        elif mode == "denoise":
            return self._denoise(img)
        elif mode == "sharpen":
            return self._sharpen(img)
        elif mode == "bicubic":
            return self._bicubic_resize(img)
        return img

    def _auto_correct(self, img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return result

    def _enhance_contrast(self, img):
        gaussian = cv2.GaussianBlur(img, (0, 0), 3)
        sharpened = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
        return sharpened

    def _adjust_brightness(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v = cv2.equalizeHist(v)
        hsv = cv2.merge([h, s, v])
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    def _denoise(self, img):
        return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    def _sharpen(self, img):
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(img, -1, kernel)

    def _bicubic_resize(self, img):
        h, w = img.shape[:2]
        new_w = int(w * 1.5)
        new_h = int(h * 1.5)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def apply_auto_correct(input_path, output_path):
    img = cv2.imread(input_path)
    if img is None:
        return False

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    cv2.imwrite(output_path, result)
    return True
