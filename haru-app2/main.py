import sys
from PyQt6.QtWidgets import QApplication
from app import SensorDashboardApp


if __name__ == "__main__":
  app = QApplication(sys.argv)
  dashboard = SensorDashboardApp()
  dashboard.show()
  sys.exit(app.exec())
