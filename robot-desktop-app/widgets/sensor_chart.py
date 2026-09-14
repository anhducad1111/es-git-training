import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

SENSOR_COLORS = {
    "temperature": "#ef4444",
    "humidity": "#3b82f6",
    "gas": "#10b981",
    "distance": "#f59e0b",
}

SENSOR_LABELS = {
    "temperature": "Temp (°C)",
    "humidity": "Humidity (%)",
    "gas": "Gas (ppm)",
    "distance": "Distance (cm)",
}

SENSOR_KEYS = {
    "temperature": "temperature_c",
    "humidity": "humidity_pct",
    "gas": "gas_ppm",
    "distance": "distance_cm",
}


class SensorChart(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        super().__init__(Figure(figsize=(8, 4), facecolor='#0f172a'))
        self.setParent(parent)
        self.figure.set_facecolor('#0f172a')
        self.ax = self.figure.add_subplot(111)
        self._setup_axes()

        self._readings = []
        self._custom_groups = None
        self._normalize = {}
        self._hover_idx = None

        self.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.mpl_connect('axes_leave_event', self._on_mouse_leave)

    def _setup_axes(self):
        self.ax.set_facecolor('#0f172a')
        self.ax.tick_params(colors='#64748b', labelsize=8)
        self.ax.spines['bottom'].set_color('#1e293b')
        self.ax.spines['top'].set_color('#1e293b')
        self.ax.spines['left'].set_color('#1e293b')
        self.ax.spines['right'].set_color('#1e293b')
        self.ax.grid(True, color='#1e293b', linestyle='--', alpha=0.5)

    def rebuild_charts(self, custom_groups, normalize_flags=None):
        self._custom_groups = custom_groups
        self._normalize = normalize_flags or {}

    def clear_custom_charts(self):
        self._custom_groups = None
        self._normalize = {}

    def update_chart(self, readings):
        self._readings = readings
        self._draw_chart()

    def _draw_chart(self):
        self.ax.clear()
        self._setup_axes()

        if not self._readings:
            self.ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                        color='#475569', fontsize=12, transform=self.ax.transAxes)
            self.draw()
            return

        if self._custom_groups:
            self._draw_custom_charts()
        else:
            self._draw_default_charts()

    def _draw_default_charts(self):
        times = [r.get('recorded_at', '')[:16] for r in self._readings]
        temps = [r.get('temperature_c', 0) for r in self._readings]
        hums = [r.get('humidity_pct', 0) for r in self._readings]

        x = range(len(times))
        self.ax.plot(x, temps, color='#ef4444', linewidth=1.5, label='Temp (°C)', marker='o', markersize=3)
        self.ax.plot(x, hums, color='#3b82f6', linewidth=1.5, label='Humidity (%)', marker='s', markersize=3)

        self._finalize_axes(times, x)

    def _draw_custom_charts(self):
        times = [r.get('recorded_at', '')[:16] for r in self._readings]
        x = range(len(times))

        for title, sensors in self._custom_groups.items():
            for sensor in sensors:
                key = SENSOR_KEYS.get(sensor)
                color = SENSOR_COLORS.get(sensor, '#94a3b8')
                label = SENSOR_LABELS.get(sensor, sensor)
                values = [r.get(key, 0) for r in self._readings]

                if self._normalize.get(title, False):
                    min_val = min(values) if values else 0
                    max_val = max(values) if values else 1
                    rng = max_val - min_val if max_val != min_val else 1
                    values = [(v - min_val) / rng for v in values]

                self.ax.plot(x, values, color=color, linewidth=1.5, label=f"{title}: {label}",
                           marker='o', markersize=3)

        self._finalize_axes(times, x)

    def _finalize_axes(self, times, x):
        self.ax.set_ylabel('Value', color='#94a3b8', fontsize=9)
        self.ax.legend(loc='upper left', fontsize=8, facecolor='#0f172a', edgecolor='#1e293b',
                      labelcolor='#94a3b8')

        if len(times) > 10:
            step = len(times) // 10
            self.ax.set_xticks(x[::step])
            self.ax.set_xticklabels(times[::step], rotation=45, ha='right', fontsize=7)
        else:
            self.ax.set_xticks(x)
            self.ax.set_xticklabels(times, rotation=45, ha='right', fontsize=7)

        self.ax.set_xlim(-0.5, len(times) - 0.5)

        if self._hover_idx is not None and 0 <= self._hover_idx < len(self._readings):
            self._draw_cursor(self._hover_idx)

        self.figure.tight_layout()
        self.draw()

    def _draw_cursor(self, idx):
        r = self._readings[idx]
        temp = r.get('temperature_c', 0)
        hum = r.get('humidity_pct', 0)

        self.ax.axvline(x=idx, color='#475569', linestyle='--', linewidth=1, alpha=0.8)

        self.ax.annotate(
            f'{temp:.1f}°C',
            xy=(idx, temp), xytext=(10, 10),
            textcoords='offset points',
            color='#ef4444', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0f172a', edgecolor='#ef4444', alpha=0.9),
            arrowprops=dict(arrowstyle='->', color='#ef4444', lw=1.5)
        )

        self.ax.annotate(
            f'{hum:.1f}%',
            xy=(idx, hum), xytext=(10, -15),
            textcoords='offset points',
            color='#3b82f6', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0f172a', edgecolor='#3b82f6', alpha=0.9),
            arrowprops=dict(arrowstyle='->', color='#3b82f6', lw=1.5)
        )

    def _on_mouse_move(self, event):
        if not self._readings or not event.inaxes == self.ax:
            return

        idx = int(round(event.xdata))
        if idx < 0 or idx >= len(self._readings):
            idx = None

        if idx != self._hover_idx:
            self._hover_idx = idx
            self._draw_chart()

    def _on_mouse_leave(self, event):
        if self._hover_idx is not None:
            self._hover_idx = None
            self._draw_chart()
