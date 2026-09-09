import sys
from PyQt6.QtWidgets import QApplication
from app import CameraApp


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Camera Screen Demo")
    window = CameraApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
