import sys
from PyQt6.QtWidgets import QApplication
from app import SensorClientApp


if __name__ == "__main__":
  app = QApplication(sys.argv)
  client = SensorClientApp()
  client.show()
  client.toggle_auto()
  sys.exit(app.exec())
