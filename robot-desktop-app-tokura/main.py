import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import RoverTeleopApp
except Exception as e:
    print(f"Import error: {e}")
    raise

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Rover Teleop Cockpit")
    window = RoverTeleopApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
