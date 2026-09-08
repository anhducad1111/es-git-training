import sys
from PyQt6.QtWidgets import QApplication
from app import RoverTeleopApp


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Rover Teleop Cockpit")
    window = RoverTeleopApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
