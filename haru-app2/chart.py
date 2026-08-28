from datetime import datetime
from PyQt6.QtCore import Qt, QMimeData, QByteArray, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QPushButton,
                              QScrollArea, QSizePolicy, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt


CHART_GROUPS = {
    "Air Quality": ["co2", "pm1.0", "pm2.5", "pm10"],
    "Environment": ["temperature", "humidity", "pressure"],
    "Other": ["gas", "battery"],
}

ALL_LABELS = ["co2", "pm1.0", "pm2.5", "pm10", "temperature", "humidity", "pressure", "gas", "battery"]

COLORS = ["#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00ACC1", "#F4511E", "#3949AB", "#C0CA33"]

DRAG_MIME_TYPE = "application/x-chart-group"

DROP_ZONE_STYLE = """
    QFrame#dropZone {
        border: 2px dashed #2196F3;
        border-radius: 4px;
        background-color: rgba(33, 150, 243, 0.08);
    }
"""

DROP_ZONE_IDLE = """
    QFrame#dropZone {
        border: 1px solid transparent;
        background-color: transparent;
    }
"""


class DropZone(QWidget):
  """Wrapper that accepts drops across its entire area and forwards to the inner ChartWidget."""

  def __init__(self, chart_widget, parent=None):
    super().__init__(parent)
    self.chart_widget = chart_widget
    self.setObjectName("dropZone")
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(self.chart_widget)
    self.setLayout(layout)
    self.setAcceptDrops(True)
    self.setStyleSheet(DROP_ZONE_IDLE)

  def dragEnterEvent(self, event):
    if event.mimeData().hasFormat(DRAG_MIME_TYPE):
      event.acceptProposedAction()
      self.setStyleSheet(DROP_ZONE_STYLE)

  def dragMoveEvent(self, event):
    if event.mimeData().hasFormat(DRAG_MIME_TYPE):
      event.acceptProposedAction()

  def dragLeaveEvent(self, event):
    self.setStyleSheet(DROP_ZONE_IDLE)

  def dropEvent(self, event):
    self.setStyleSheet(DROP_ZONE_IDLE)
    if event.mimeData().hasFormat(DRAG_MIME_TYPE):
      event.acceptProposedAction()
      self.chart_widget.dropEvent(event)


class DraggableContainer(QWidget):
  """Container that can be dragged."""

  def __init__(self, group_name, labels, parent=None):
    super().__init__(parent)
    self.group_name = group_name
    self.labels = labels
    self._drag_start = None

  def mousePressEvent(self, event: QMouseEvent):
    if event.button() == Qt.MouseButton.LeftButton:
      self._drag_start = event.position().toPoint()
    super().mousePressEvent(event)

  def mouseMoveEvent(self, event: QMouseEvent):
    if self._drag_start is None:
      return
    if (event.position().toPoint() - self._drag_start).manhattanLength() > 10:
      drag = QDrag(self)
      mime_data = QMimeData()
      payload = f"{self.group_name}|{','.join(self.labels)}"
      mime_data.setData(DRAG_MIME_TYPE, QByteArray(payload.encode()))
      drag.setMimeData(mime_data)
      drag.exec(Qt.DropAction.MoveAction)
      self._drag_start = None
    super().mouseMoveEvent(event)

  def mouseReleaseEvent(self, event: QMouseEvent):
    self._drag_start = None
    super().mouseReleaseEvent(event)


class ChartWidget(QWidget):
  chart_added = pyqtSignal(str)
  chart_toggled = pyqtSignal()

  def __init__(self, is_custom=False, num_columns=1):
    super().__init__()
    self.charts = {}
    self.is_custom = is_custom
    self.current_groups = {}
    self.normalize_flags = {}
    self.main_layout = QHBoxLayout()
    self.main_layout.setContentsMargins(0, 0, 0, 0)
    self.main_layout.setSpacing(5)
    self.col_layouts = []
    for _ in range(num_columns):
      col = QVBoxLayout()
      col.setAlignment(Qt.AlignmentFlag.AlignTop)
      self.main_layout.addLayout(col)
      self.col_layouts.append(col)
    self.setLayout(self.main_layout)
    self.setAcceptDrops(True)
    if not is_custom:
      self.current_groups = CHART_GROUPS.copy()
      self._build_charts()

  def dragEnterEvent(self, event):
    if event.mimeData().hasFormat(DRAG_MIME_TYPE):
      event.acceptProposedAction()
      self.setStyleSheet("border: 2px dashed #2196F3; border-radius: 4px;")

  def dragLeaveEvent(self, event):
    self.setStyleSheet("")

  def dropEvent(self, event):
    self.setStyleSheet("")
    if event.mimeData().hasFormat(DRAG_MIME_TYPE):
      payload = event.mimeData().data(DRAG_MIME_TYPE).data().decode()
      parts = payload.split("|")
      if len(parts) == 2:
        group_name = parts[0]
        labels = parts[1].split(",")
        if group_name not in self.current_groups:
          self.current_groups[group_name] = labels
          if self.is_custom:
            self._build_single_chart(group_name, labels)
          else:
            self._build_draggable_chart(group_name, labels)
          self.chart_added.emit(group_name)
          event.acceptProposedAction()

  def _build_single_chart(self, group_name, labels):
    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(5, 0, 5, 0)

    title_label = QLabel(group_name)
    title_label.setStyleSheet("font-weight: bold;")
    header_layout.addWidget(title_label)
    header_layout.addStretch()

    close_btn = QPushButton("X")
    close_btn.setFixedSize(20, 20)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #F44336;
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 10px;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
    """)
    close_btn.clicked.connect(lambda checked, name=group_name, btn=close_btn: self._toggle_chart(name, btn))
    header_layout.addWidget(close_btn)

    chart_layout = QVBoxLayout()
    fig = Figure(figsize=(5, 3), dpi=100)
    canvas = FigureCanvas(fig)
    canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    canvas.setMinimumHeight(150)
    chart_layout.addWidget(canvas)

    container = DraggableContainer(group_name, labels)
    container_layout = QVBoxLayout()
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(0)
    container_layout.addLayout(header_layout)
    container_layout.addLayout(chart_layout)
    container.setLayout(container_layout)
    container.setCursor(Qt.CursorShape.OpenHandCursor)

    self.charts[group_name] = {
        "fig": fig,
        "canvas": canvas,
        "labels": labels,
        "container": container,
    }
    target_col = min(self.col_layouts, key=lambda l: l.count())
    target_col.addWidget(container)

  def _build_charts(self):
    for group_name, labels in self.current_groups.items():
      if group_name in self.charts:
        continue
      if self.is_custom:
        self._build_single_chart(group_name, labels)
      else:
        self._build_draggable_chart(group_name, labels)

  def _build_draggable_chart(self, group_name, labels):
    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(5, 0, 5, 0)

    title_label = QLabel(group_name)
    title_label.setStyleSheet("font-weight: bold;")
    header_layout.addWidget(title_label)
    header_layout.addStretch()

    close_btn = QPushButton("X")
    close_btn.setFixedSize(20, 20)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #F44336;
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 10px;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
    """)
    close_btn.clicked.connect(lambda checked, name=group_name, btn=close_btn: self._toggle_chart(name, btn))
    header_layout.addWidget(close_btn)

    chart_layout = QVBoxLayout()
    fig = Figure(figsize=(5, 3), dpi=100)
    canvas = FigureCanvas(fig)
    canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    canvas.setMinimumHeight(150)
    chart_layout.addWidget(canvas)

    container = DraggableContainer(group_name, labels)
    container_layout = QVBoxLayout()
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.setSpacing(0)
    container_layout.addLayout(header_layout)
    container_layout.addLayout(chart_layout)
    container.setLayout(container_layout)
    container.setCursor(Qt.CursorShape.OpenHandCursor)

    self.charts[group_name] = {
        "fig": fig,
        "canvas": canvas,
        "labels": labels,
        "container": container,
        "close_btn": close_btn,
    }
    target_col = min(self.col_layouts, key=lambda l: l.count())
    target_col.addWidget(container)

  def _toggle_chart(self, group_name, btn):
    self.remove_chart(group_name)
    self.chart_toggled.emit()

  def remove_chart(self, group_name):
    if group_name in self.charts:
      info = self.charts[group_name]
      info["container"].setParent(None)
      info["container"].deleteLater()
      info["fig"].clear()
      del self.charts[group_name]
      del self.current_groups[group_name]
      if group_name in self.normalize_flags:
        del self.normalize_flags[group_name]

  def _clear_charts(self):
    for name, info in self.charts.items():
      if "container" in info and info["container"]:
        info["container"].setParent(None)
        info["container"].deleteLater()
      if "fig" in info and info["fig"]:
        info["fig"].clear()
    self.charts.clear()
    self.normalize_flags.clear()
    # STRICT RULE: Do NOT loop through self.main_layout to remove items here.
    # The col_layouts (QVBoxLayouts) MUST remain attached to main_layout.

  def rebuild_charts(self, groups, normalize_flags=None, normalize=False):
    self.current_groups = groups
    self._clear_charts()
    if normalize_flags:
      self.normalize_flags = normalize_flags
    else:
      self.normalize_flags = {name: normalize for name in groups}
    self._build_charts()

  def update_charts(self, history):
    if not self.charts:
      return
    for group_name, chart_info in self.charts.items():
      fig = chart_info["fig"]
      canvas = chart_info["canvas"]
      labels = chart_info["labels"]
      is_normalized = self.normalize_flags.get(group_name, False)

      if "hover_cid" in chart_info:
        canvas.mpl_disconnect(chart_info["hover_cid"])
        chart_info.pop("hover_cid", None)

      fig.clear()
      ax = fig.add_subplot(111)

      has_data = False
      plot_data = []
      for i, label in enumerate(labels):
        if label in history and history[label]:
          has_data = True
          points = history[label]
          points = sorted(points, key=lambda x: x.get("reading_time", ""))
          times = []
          values = []
          for p in points:
            rt = p.get("reading_time", "")
            try:
              dt = datetime.strptime(rt, "%Y-%m-%d %H:%M:%S")
              times.append(dt.strftime("%H:%M:%S"))
            except Exception:
              times.append(rt)
            values.append(p.get("data", 0))

          if is_normalized and len(values) > 0:
            v_min = min(values)
            v_max = max(values)
            if v_max > v_min:
              values = [(v - v_min) / (v_max - v_min) for v in values]
            else:
              values = [0.5 for _ in values]
            legend_label = f"{label} (Normalized)"
          else:
            legend_label = label

          color = COLORS[i % len(COLORS)]
          line, = ax.plot(times, values, "o-", color=color, label=legend_label, markersize=2)
          plot_data.append((line, times, values, label))

      if has_data:
        ax.legend(loc="upper left", fontsize="small")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.tick_params(axis="x", rotation=45)

        annotation = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                                 textcoords="offset points",
                                 bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.9),
                                 fontsize=8)
        annotation.set_visible(False)

        def on_hover(event, ax=ax, plot_data=plot_data, annotation=annotation, canvas=canvas):
          if event.inaxes == ax:
            for line, times, values, label in plot_data:
              contains, ind = line.contains(event)
              if contains:
                idx = ind["ind"][0]
                if idx < len(times) and idx < len(values):
                  x = times[idx]
                  y = values[idx]
                  ymin, ymax = ax.get_ylim()
                  y_mid = (ymin + ymax) / 2
                  if y > y_mid:
                    annotation.set_position((10, -20))
                  else:
                    annotation.set_position((10, 10))
                  annotation.xy = (x, y)
                  annotation.set_text(f"{label}: {y}")
                  annotation.set_visible(True)
                  canvas.draw_idle()
                  return
            annotation.set_visible(False)
            canvas.draw_idle()

        chart_info["hover_cid"] = canvas.mpl_connect("motion_notify_event", on_hover)

      else:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12, transform=ax.transAxes)

      if is_normalized:
        ax.set_ylabel("Normalized (0-1)", fontsize="small")
      ax.set_xlabel("Time", fontsize="small")
      fig.subplots_adjust(left=0.22, right=0.98, top=0.95, bottom=0.38)
      canvas.draw()
