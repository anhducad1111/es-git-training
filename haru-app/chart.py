from datetime import datetime
from PyQt6.QtWidgets import QGroupBox, QPushButton, QVBoxLayout, QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ChartWidget(QGroupBox):

  def __init__(self, on_refresh):
    super().__init__("Temperature & Humidity History")
    self.setStyleSheet("QGroupBox { font-weight: bold; }")
    self.on_refresh = on_refresh
    self._init_ui()

  def _init_ui(self):
    layout = QVBoxLayout()

    self.refresh_btn = QPushButton("Refresh Chart (GET)")
    self.refresh_btn.setStyleSheet(
        "background-color: #64B5F6; color: white; padding: 5px; border-radius: 4px;"
    )
    self.refresh_btn.clicked.connect(self.on_refresh)

    self.figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
    self.canvas = FigureCanvas(self.figure)
    self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout.addWidget(self.refresh_btn)
    layout.addWidget(self.canvas)
    self.setLayout(layout)

  def draw_line_chart(self, data):
    self.figure.clear()
    if not isinstance(data, list) or len(data) == 0:
      ax = self.figure.add_subplot(111)
      ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
      self.canvas.draw()
      return

    data_sorted = sorted(data, key=lambda r: r.get("created_at", ""))
    timestamps = [row.get("created_at", "") for row in data_sorted]
    short_labels = []
    for t in timestamps:
      try:
        dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        short_labels.append(dt.strftime("%H:%M:%S"))
      except Exception:
        short_labels.append(t)

    temps = [row.get("temperature", row.get("temp", 0)) for row in data_sorted]
    hums = [row.get("humidity", 0) for row in data_sorted]

    ax1 = self.figure.add_subplot(111)
    ax2 = ax1.twinx()

    line1, = ax1.plot(short_labels, temps, "o-", color="#E53935", label="Temp (C)")
    line2, = ax2.plot(short_labels, hums, "s--", color="#1E88E5", label="Humidity (%)")

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Temperature (C)", color="#E53935")
    ax2.set_ylabel("Humidity (%)", color="#1E88E5")
    ax1.set_title("Sensor Data History")
    ax1.tick_params(axis="x", rotation=45)

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left")

    self.figure.tight_layout()
    self.canvas.draw()
