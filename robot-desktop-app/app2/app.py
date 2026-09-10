from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import dataclass
from time import monotonic

import cv2
from PyQt6.QtCore import QSettings, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .calibration import (
    CharucoCalibrationSession,
    TIER_LABELS_JA,
    TIER_STATUS_LEVELS,
    append_calibration_history,
    calibration_from_dict,
    error_quality_tier,
    format_history_entry,
    load_calibration_history,
    save_calibration,
    summarize_coverage,
)
from .capture import save_capture
from .detectors import create_detector
from .follow_controller import FollowController
from .latest_frame import LatestFrame
from .marker_tracking import MarkerTracker, MarkerTrackResult
from .workers import CaptureWorker, FramePacket, InferenceWorker


# Fixed-resolution MJPEG endpoints exposed by the ESP32-Cam firmware
# (GET /{width}x{height}.mjpeg), per API_DOCUMENTATION.md section 3.1.
# 640x480 is called out there as the recommended, stable 25-30 FPS setting;
# "auto" leaves resolution up to whatever /stream is currently configured for.
STREAM_RESOLUTIONS = ["auto", "320x240", "640x480", "800x600", "1024x768", "1600x1200"]


def normalize_url(value: str, resolution: str = "auto") -> str:
    value = value.strip()
    if not value:
        value = "192.168.4.1"
    if "://" not in value:
        value = f"http://{value}"
    base = value.rstrip("/")
    if base.endswith(("/stream",)) or base.endswith(".mjpeg"):
        return base
    if resolution and resolution != "auto":
        return f"{base}/{resolution}.mjpeg"
    return base + "/stream"


def format_marker_panel(result: MarkerTrackResult) -> str:
    """High-precision distance/x/y readout for the right-hand info panel.

    Kept separate from the on-frame box labels (drawn with cv2.putText, which
    doesn't render many digits legibly at small sizes) so a single tracked
    marker can be read out to sub-millimeter precision. Takes a
    MarkerTrackResult (see MarkerTracker) rather than a raw Detection so a
    brief detection gap shows the held last-known pose instead of flickering
    to "no marker".
    """
    if result.status == "none":
        return "Marker: 検出なし"
    if result.status == "uncalibrated":
        return "Marker: キャリブレーション未設定のため距離不明"
    if result.status == "multiple":
        return f"Marker: {result.count}個検出（1個のときのみ距離表示）"
    suffix = "（前回検出値を保持中）" if result.stale else ""
    pose = result.pose
    return (
        f"{result.label}{suffix}\n距離: {pose.distance_m:.6f} m\n"
        f"X: {pose.x_m:+.6f} m\nY: {pose.y_m:+.6f} m\nYaw: {pose.yaw_deg:+.1f} deg"
    )


def capture_filename_suffix(result: MarkerTrackResult, manual_distance_m: float) -> str:
    """Distance metadata for the captured-photo filename (ML training label).
    Prefers the marker-measured distance; falls back to a manually entered
    value when there's no single unambiguous marker pose to measure it from."""
    distance_m = result.pose.distance_m if result.status == "single" else manual_distance_m
    return f"_d{distance_m:.3f}"


def yaw_suffix(yaw_deg: float) -> str:
    """Vehicle yaw for the capture filename. Entered manually rather than
    read from marker pose: the marker's apparent yaw isn't necessarily the
    ground-truth vehicle yaw the training label needs."""
    return f"_yaw{yaw_deg:+.1f}"


def camera_pose_suffix(pan: int, tilt: int) -> str:
    """Manually-entered camera pan/tilt servo angles for the capture filename
    (no live servo-status API wired up yet — see the gimbal-controller app)."""
    return f"_pan{pan:03d}_tilt{tilt:03d}"


@dataclass
class AppConfig:
    url: str = "192.168.4.1"
    detector_kind: str = "hog"
    confidence: float = 0.35
    detection_enabled: bool = True


class MainWindow(QMainWindow):
    status_signal = pyqtSignal(str)
    calibration_result_signal = pyqtSignal(object)

    _STATUS_COLORS = {
        "info": "#ddd",
        "ok": "#4caf50",
        "warn": "#ffb300",
        "error": "#f44336",
    }

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or AppConfig()
        self.capture_slot: LatestFrame[FramePacket] | None = None
        self.raw_slot: LatestFrame[FramePacket] | None = None
        self.display_slot: LatestFrame[FramePacket] | None = None
        self.capture: CaptureWorker | None = None
        self.inference: InferenceWorker | None = None
        self.calibration_session: CharucoCalibrationSession | None = None
        self.marker_tracker = MarkerTracker(hold_seconds=1.0)
        self._last_track_result = MarkerTrackResult(status="none")
        self.follow_controller: FollowController | None = None
        self.capture_count = 0
        self._last_raw_image = None
        self.frames = 0
        self.last_fps_time = monotonic()
        self.setWindowTitle("ESP32-CAM Live Object Detection")
        self.resize(960, 720)
        self._build_ui()
        self._load_settings()
        self.status_signal.connect(self._on_worker_status)
        self.calibration_result_signal.connect(self._on_calibration_result)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._display_latest)
        self.timer.start(15)

    def _build_ui(self) -> None:
        self.url_edit = QLineEdit(self.config.url)
        self.url_edit.setPlaceholderText("192.168.4.1")
        self.url_edit.setToolTip("ESP32-CAM host/IP (or a full stream URL)")
        self.url_edit.setMinimumWidth(220)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(STREAM_RESOLUTIONS)
        self.resolution_combo.setCurrentText("640x480")
        self.resolution_combo.setToolTip(
            "MJPEG resolution endpoint (GET /{width}x{height}.mjpeg). "
            "640x480 is the firmware's recommended, stable 25-30 FPS setting; "
            "'auto' uses /stream instead."
        )
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(0, 63)
        self.quality_spin.setValue(14)
        self.quality_spin.setToolTip(
            "JPEG quality (0-63, lower = higher quality/larger frames). Sent to the camera's "
            "/api/quality endpoint on connect. Raising this reduces the frame-size spikes that "
            "can destabilize the stream when the scene has fast motion."
        )
        self.connect_button = QPushButton("Connect")
        self.connect_button.setToolTip("Connect to or disconnect from the stream")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_box = QGroupBox("Connection")
        connection_host_row = QHBoxLayout()
        connection_host_row.addWidget(QLabel("Host:"))
        connection_host_row.addWidget(self.url_edit, 1)
        connection_host_row.addWidget(self.connect_button)
        connection_options_row = QHBoxLayout()
        connection_options_row.addWidget(QLabel("Resolution:"))
        connection_options_row.addWidget(self.resolution_combo)
        connection_options_row.addWidget(QLabel("Quality:"))
        connection_options_row.addWidget(self.quality_spin)
        connection_layout = QVBoxLayout()
        connection_layout.addLayout(connection_host_row)
        connection_layout.addLayout(connection_options_row)
        connection_box.setLayout(connection_layout)

        self.detect_check = QCheckBox("Enabled")
        self.detect_check.setChecked(self.config.detection_enabled)
        self.detect_check.setToolTip("Turn object detection on/off")
        self.detector_combo = QComboBox()
        self.detector_combo.addItems(["aruco", "hog", "none", "rccar", "yolo"])
        self.detector_combo.setCurrentText(self.config.detector_kind)
        self.detector_combo.setToolTip("Detection algorithm to run on each frame")
        self.confidence = QDoubleSpinBox()
        self.confidence.setRange(0.05, 0.99)
        self.confidence.setSingleStep(0.05)
        self.confidence.setValue(self.config.confidence)
        self.confidence.setToolTip("Minimum confidence score to accept a detection")
        self.marker_size = QDoubleSpinBox()
        self.marker_size.setRange(0.0001, 2.0)
        self.marker_size.setSingleStep(0.0001)
        self.marker_size.setDecimals(4)
        self.marker_size.setValue(0.05)
        self.marker_size.setSuffix(" m")
        self.marker_size.setToolTip("Physical side length of the standalone ArUco marker used for pose/distance estimation")
        detection_box = QGroupBox("Object Detection")
        detection_layout = QVBoxLayout()
        detection_layout.addWidget(self.detect_check)
        detection_layout.addLayout(self._labeled_row("Detector:", self.detector_combo))
        detection_layout.addLayout(self._labeled_row("Confidence:", self.confidence))
        detection_layout.addLayout(self._labeled_row("Marker Size:", self.marker_size))
        self.follow_check = QCheckBox("Follow Mode")
        self.follow_check.setToolTip("Stanley制御で前の車を自動追従")
        detection_layout.addWidget(self.follow_check)
        detection_box.setLayout(detection_layout)

        self.target_frames = QSpinBox()
        self.target_frames.setRange(5, 100)
        self.target_frames.setValue(20)
        self.target_frames.setToolTip("Number of board captures to collect before calibrating (more, from varied angles/distances, gives a better calibration)")
        self.capture_frame_button = QPushButton("Capture Frame")
        self.capture_frame_button.setToolTip("Capture the current frame as one calibration sample; move the board between captures")
        self.capture_frame_button.setEnabled(False)
        self.capture_frame_button.clicked.connect(self.capture_calibration_frame)
        self.calibration_button = QPushButton("Start Calibration")
        self.calibration_button.setToolTip("Start/finish collecting ChArUco board frames and compute camera calibration")
        self.calibration_button.clicked.connect(self.toggle_calibration)
        self.calibration_progress = QProgressBar()
        self.calibration_progress.setRange(0, 0)  # indeterminate: computing/saving runs on a background thread
        self.calibration_progress.setMaximumWidth(80)
        self.calibration_progress.setTextVisible(False)
        self.calibration_progress.setVisible(False)
        self.history_button = QPushButton("History")
        self.history_button.setToolTip("Browse past calibration runs and restore one as the active calibration")
        self.history_button.clicked.connect(self.show_calibration_history)
        calibration_box = QGroupBox("Calibration")
        calibration_layout = QVBoxLayout()
        calibration_layout.addLayout(self._labeled_row("Frames:", self.target_frames))
        calibration_layout.addWidget(self.capture_frame_button)
        button_and_progress = QHBoxLayout()
        button_and_progress.addWidget(self.calibration_button)
        button_and_progress.addWidget(self.calibration_progress)
        calibration_layout.addLayout(button_and_progress)
        calibration_layout.addWidget(self.history_button)
        calibration_box.setLayout(calibration_layout)

        self.capture_mode_button = QPushButton("Capture Mode: Off")
        self.capture_mode_button.setCheckable(True)
        self.capture_mode_button.setToolTip(
            "When on, press Enter to save the current raw frame to the capture "
            "folder below (for building a machine-learning image dataset)"
        )
        self.capture_mode_button.toggled.connect(self._on_capture_mode_toggled)
        self.capture_count_label = QLabel("Captured: 0")
        self.capture_dir_edit = QLineEdit("captures")
        self.capture_dir_edit.setToolTip("Folder captured photos are saved to (relative paths are resolved from the current working directory)")
        self.capture_dir_browse_button = QPushButton("Browse...")
        self.capture_dir_browse_button.setToolTip("Choose the capture folder")
        self.capture_dir_browse_button.clicked.connect(self._browse_capture_dir)
        self.pan_spin = QSpinBox()
        self.pan_spin.setRange(0, 180)
        self.pan_spin.setValue(90)
        self.pan_spin.setToolTip("Camera pan servo angle (0-180, entered manually) — embedded in capture filenames")
        self.tilt_spin = QSpinBox()
        self.tilt_spin.setRange(0, 180)
        self.tilt_spin.setValue(90)
        self.tilt_spin.setToolTip("Camera tilt servo angle (0-180, entered manually) — embedded in capture filenames")
        self.yaw_spin = QDoubleSpinBox()
        self.yaw_spin.setRange(-180.0, 180.0)
        self.yaw_spin.setSingleStep(0.1)
        self.yaw_spin.setDecimals(1)
        self.yaw_spin.setValue(0.0)
        self.yaw_spin.setToolTip(
            "Vehicle yaw angle in degrees, entered manually (not read from marker pose) — embedded in capture filenames"
        )
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(0.0, 100.0)
        self.distance_spin.setSingleStep(0.01)
        self.distance_spin.setDecimals(3)
        self.distance_spin.setValue(0.0)
        self.distance_spin.setSuffix(" m")
        self.distance_spin.setToolTip(
            "Fallback distance when a marker isn't being measured (e.g. no marker in "
            "frame or no calibration loaded). Ignored whenever a single marker's "
            "measured distance is available — that value is used instead."
        )
        capture_box = QGroupBox("Photo Capture")
        capture_top_row = QHBoxLayout()
        capture_top_row.addWidget(self.capture_mode_button)
        capture_top_row.addWidget(self.capture_count_label)
        capture_dir_row = QHBoxLayout()
        capture_dir_row.addWidget(QLabel("Folder:"))
        capture_dir_row.addWidget(self.capture_dir_edit, 1)
        capture_dir_row.addWidget(self.capture_dir_browse_button)
        capture_angles_row = QHBoxLayout()
        capture_angles_row.addWidget(QLabel("Dist (fallback):"))
        capture_angles_row.addWidget(self.distance_spin)
        capture_angles_row.addWidget(QLabel("Yaw:"))
        capture_angles_row.addWidget(self.yaw_spin)
        capture_angles_row.addWidget(QLabel("Pan:"))
        capture_angles_row.addWidget(self.pan_spin)
        capture_angles_row.addWidget(QLabel("Tilt:"))
        capture_angles_row.addWidget(self.tilt_spin)
        capture_layout = QVBoxLayout()
        capture_layout.addLayout(capture_top_row)
        capture_layout.addLayout(capture_dir_row)
        capture_layout.addLayout(capture_angles_row)
        capture_box.setLayout(capture_layout)

        self.status_label = QLabel()
        self._set_status("Disconnected", "info")
        self.metrics_label = QLabel("FPS: -- | Latency: -- ms")
        self.video_label = QLabel("No Video")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background: #111; color: #ddd;")

        self.marker_info_label = QLabel("Marker: --")
        self.marker_info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.marker_info_label.setFixedWidth(240)
        self.marker_info_label.setWordWrap(True)
        self.marker_info_label.setStyleSheet("background: #111; color: #ddd; padding: 8px; font-family: monospace;")

        # Object Detection and Calibration have grown enough controls that they
        # crowded out other settings in a single horizontal row; they live in
        # a scrollable left sidebar instead so nothing gets clipped.
        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(detection_box)
        sidebar_layout.addWidget(calibration_box)
        sidebar_layout.addStretch(1)
        sidebar_content = QWidget()
        sidebar_content.setLayout(sidebar_layout)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidget(sidebar_content)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(260)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = QHBoxLayout()
        header.addWidget(connection_box, 1)
        header.addWidget(capture_box, 0)
        video_row = QHBoxLayout()
        video_row.addWidget(self.video_label, 1)
        video_row.addWidget(self.marker_info_label)
        right_column = QVBoxLayout()
        right_column.addLayout(header)
        right_column.addLayout(video_row, 1)
        right_column.addWidget(self.status_label)
        right_column.addWidget(self.metrics_label)

        body = QHBoxLayout()
        body.addWidget(sidebar_scroll)
        body.addLayout(right_column, 1)
        container = QWidget()
        container.setLayout(body)
        self.setCentralWidget(container)

    @staticmethod
    def _labeled_row(label_text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addWidget(widget, 1)
        return row

    def _load_settings(self) -> None:
        settings = QSettings("esp32_mjpeg_detector", "Viewer")
        self.url_edit.setText(settings.value("url", self.url_edit.text()))
        resolution = settings.value("resolution")
        if resolution and resolution in STREAM_RESOLUTIONS:
            self.resolution_combo.setCurrentText(resolution)
        self.quality_spin.setValue(int(settings.value("quality", self.quality_spin.value())))
        detector = settings.value("detector")
        if detector:
            self.detector_combo.setCurrentText(detector)
        self.detect_check.setChecked(settings.value("detection_enabled", self.detect_check.isChecked(), type=bool))
        self.confidence.setValue(float(settings.value("confidence", self.confidence.value())))
        self.marker_size.setValue(float(settings.value("marker_size", self.marker_size.value())))
        self.target_frames.setValue(int(settings.value("target_frames", self.target_frames.value())))
        self.pan_spin.setValue(int(settings.value("pan", self.pan_spin.value())))
        self.tilt_spin.setValue(int(settings.value("tilt", self.tilt_spin.value())))
        self.yaw_spin.setValue(float(settings.value("yaw", self.yaw_spin.value())))
        self.distance_spin.setValue(float(settings.value("distance_fallback", self.distance_spin.value())))
        self.capture_dir_edit.setText(settings.value("capture_dir", self.capture_dir_edit.text()))

    def _save_settings(self) -> None:
        settings = QSettings("esp32_mjpeg_detector", "Viewer")
        settings.setValue("url", self.url_edit.text())
        settings.setValue("resolution", self.resolution_combo.currentText())
        settings.setValue("quality", self.quality_spin.value())
        settings.setValue("detector", self.detector_combo.currentText())
        settings.setValue("detection_enabled", self.detect_check.isChecked())
        settings.setValue("confidence", self.confidence.value())
        settings.setValue("marker_size", self.marker_size.value())
        settings.setValue("target_frames", self.target_frames.value())
        settings.setValue("pan", self.pan_spin.value())
        settings.setValue("tilt", self.tilt_spin.value())
        settings.setValue("yaw", self.yaw_spin.value())
        settings.setValue("distance_fallback", self.distance_spin.value())
        settings.setValue("capture_dir", self.capture_dir_edit.text())

    def _set_status(self, text: str, level: str = "info") -> None:
        color = self._STATUS_COLORS.get(level, self._STATUS_COLORS["info"])
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(text)

    def _on_worker_status(self, message: str) -> None:
        if message.startswith("Receiving") or message.startswith("Saved"):
            level = "ok"
        elif message.startswith(("Connecting", "Reconnecting")):
            level = "warn"
        elif "error" in message.lower() or "failed" in message.lower():
            level = "error"
        else:
            level = "info"
        self._set_status(message, level)

    def toggle_connection(self) -> None:
        if self.capture:
            self.stop_workers()
        else:
            self.start_workers()

    def start_workers(self) -> None:
        self.capture_slot = LatestFrame()
        self.raw_slot = LatestFrame()
        self.display_slot = LatestFrame()
        detector_kind = self.detector_combo.currentText() if self.detect_check.isChecked() else "none"
        try:
            detector = create_detector(detector_kind, self.confidence.value(), self.marker_size.value())
        except Exception as exc:
            self._set_status(f"Detector error: {exc}", "error")
            self.capture_slot.close()
            self.raw_slot.close()
            self.display_slot.close()
            self.capture_slot = self.raw_slot = self.display_slot = None
            return
        self.capture = CaptureWorker(
            normalize_url(self.url_edit.text(), self.resolution_combo.currentText()),
            self.capture_slot,
            self.raw_slot,
            status=self.status_signal.emit,
            quality=self.quality_spin.value(),
        )
        self.inference = InferenceWorker(self.capture_slot, self.display_slot, detector, self.status_signal.emit)
        self.capture.start()
        self.inference.start()
        self.connect_button.setText("Disconnect")
        self.url_edit.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        self.quality_spin.setEnabled(False)
        self._save_settings()
        if self.follow_check.isChecked():
            self.follow_controller = FollowController(lambda cmd: print(f"[Follow] {cmd}"))

    def stop_workers(self) -> None:
        if self.follow_controller:
            self.follow_controller.stop()
            self.follow_controller = None
        if self.capture:
            self.capture.stop()
        if self.inference:
            self.inference.stop()
        self.capture = self.inference = None
        self.capture_slot = self.raw_slot = self.display_slot = None
        self._last_raw_image = None
        self.marker_tracker = MarkerTracker(hold_seconds=self.marker_tracker.hold_seconds)
        self._last_track_result = MarkerTrackResult(status="none")
        self.connect_button.setText("Connect")
        self.url_edit.setEnabled(True)
        self.resolution_combo.setEnabled(True)
        self.quality_spin.setEnabled(True)
        self._set_status("Disconnected", "info")

    def toggle_calibration(self) -> None:
        if self.calibration_session is None:
            if not self.capture:
                self._set_status("Connect to the stream first", "warn")
                return
            self.calibration_session = CharucoCalibrationSession()
            self.calibration_button.setText("Finish && Save")
            self.capture_frame_button.setEnabled(True)
            self.target_frames.setEnabled(False)
            target = self.target_frames.value()
            self._set_status(f"Position the ChArUco board, then click Capture Frame (target: {target} frames)", "info")
            return
        self._start_calibration_compute()

    def _start_calibration_compute(self) -> None:
        # cv2.calibrateCamera plus the JSON writes can take a few seconds for
        # many frames; running it inline on the GUI thread froze the window
        # (Qt can't repaint/respond while its main thread is busy). Run it on
        # a background thread instead and report back through a signal, which
        # Qt marshals onto the GUI thread automatically for a cross-thread
        # emit -> connected slot.
        session = self.calibration_session
        self.calibration_session = None
        self.calibration_button.setEnabled(False)
        self.capture_frame_button.setEnabled(False)
        self.target_frames.setEnabled(True)
        self.calibration_progress.setVisible(True)
        self._set_status("Calibrating…", "info")
        extra = {
            "url": self.url_edit.text().strip(),
            "resolution": self.resolution_combo.currentText(),
            "quality": self.quality_spin.value(),
            "frame_count": session.frame_count,
        }
        coverage_tips = summarize_coverage(session.coverage)

        def work() -> None:
            try:
                data = session.calibrate()
                save_calibration("camera_calibration.json", data)
                append_calibration_history("calibration_history.json", data, extra=extra)
                self.calibration_result_signal.emit((data, coverage_tips))
            except Exception as exc:
                self.calibration_result_signal.emit(exc)

        threading.Thread(target=work, name="calibration-compute", daemon=True).start()

    def _on_calibration_result(self, result: object) -> None:
        self.calibration_progress.setVisible(False)
        self.calibration_button.setText("Start Calibration")
        self.calibration_button.setEnabled(True)
        self.capture_frame_button.setEnabled(False)
        if isinstance(result, Exception):
            self._set_status(f"Calibration failed: {result}", "error")
            return
        data, coverage_tips = result
        tier = error_quality_tier(data.reprojection_error)
        tier_label = TIER_LABELS_JA[tier]
        self._set_status(f"Saved: {data.reprojection_error:.3f}px ({tier_label})", TIER_STATUS_LEVELS[tier])

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Calibration Result")
        dialog.setIcon(QMessageBox.Icon.Information if tier != "poor" else QMessageBox.Icon.Warning)
        dialog.setText(
            f"再投影誤差: {data.reprojection_error:.3f}px（{tier_label}）\n画像サイズ: {data.image_size[0]}x{data.image_size[1]}"
        )
        dialog.setInformativeText("\n".join(f"・{tip}" for tip in coverage_tips))
        dialog.exec()

    def show_calibration_history(self) -> None:
        entries = list(reversed(load_calibration_history("calibration_history.json")))  # newest first
        dialog = QDialog(self)
        dialog.setWindowTitle("Calibration History")
        dialog.resize(520, 320)
        layout = QVBoxLayout(dialog)
        list_widget = None
        if not entries:
            layout.addWidget(QLabel("履歴がありません。"))
        else:
            list_widget = QListWidget()
            list_widget.addItems([format_history_entry(entry) for entry in entries])
            layout.addWidget(list_widget)
        buttons = QDialogButtonBox()
        restore_button = buttons.addButton("Restore", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole)
        restore_button.setEnabled(False)
        buttons.rejected.connect(dialog.reject)
        if list_widget is not None:
            list_widget.currentRowChanged.connect(lambda row: restore_button.setEnabled(row >= 0))
            restore_button.clicked.connect(lambda: self._restore_history_entry(entries[list_widget.currentRow()], dialog))
        layout.addWidget(buttons)
        dialog.exec()

    def _restore_history_entry(self, entry: dict, dialog: QDialog) -> None:
        data = calibration_from_dict(entry)
        save_calibration("camera_calibration.json", data)
        dialog.accept()
        self._set_status(f"Restored: {entry.get('timestamp', '?')}", "ok")

    def capture_calibration_frame(self) -> None:
        if self.calibration_session is None or self._last_raw_image is None:
            return
        corner_count = self.calibration_session.add_frame(self._last_raw_image)
        target = self.target_frames.value()
        collected = self.calibration_session.frame_count
        if corner_count == 0:
            self._set_status(f"Board not detected, try again ({collected}/{target} captured)", "warn")
            return
        level = "ok" if collected >= target else "warn"
        self._set_status(f"Captured {collected}/{target} ({corner_count} corners) — move the board and capture again", level)

    def _on_capture_mode_toggled(self, checked: bool) -> None:
        self.capture_mode_button.setText(f"Capture Mode: {'On' if checked else 'Off'}")
        if checked:
            self._set_status(f"Capture Mode ON — Enterで撮影 ({self.capture_dir_edit.text()})", "info")

    def _browse_capture_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select capture folder", self.capture_dir_edit.text())
        if directory:
            self.capture_dir_edit.setText(directory)

    def capture_photo(self) -> None:
        if self._last_raw_image is None:
            self._set_status("撮影するには接続してください", "warn")
            return
        suffix = (
            capture_filename_suffix(self._last_track_result, self.distance_spin.value())
            + yaw_suffix(self.yaw_spin.value())
            + camera_pose_suffix(self.pan_spin.value(), self.tilt_spin.value())
        )
        path = save_capture(self._last_raw_image, self.capture_dir_edit.text(), suffix=suffix)
        self.capture_count += 1
        self.capture_count_label.setText(f"Captured: {self.capture_count}")
        self._set_status(f"Saved: {path.name}", "ok")

    def keyPressEvent(self, event) -> None:
        # QLineEdit/QSpinBox etc. *ignore* the Return key (that's how Enter
        # reaches a dialog's default button while typing) rather than
        # consuming it, so it still reaches here even while e.g. url_edit
        # has focus. Only url_edit (submitting/connecting) and combo boxes
        # (Enter opens/confirms the dropdown) should block capture; the
        # distance/yaw/pan/tilt spin boxes are capture metadata, so typing a
        # number there and pressing Enter should still take the photo.
        is_blocking_widget_focused = isinstance(self.focusWidget(), (QLineEdit, QComboBox))
        if self.capture_mode_button.isChecked() and not is_blocking_widget_focused and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self.capture_photo()
            return
        super().keyPressEvent(event)

    def _display_latest(self) -> None:
        if not self.display_slot:
            return
        processed = self.display_slot.get(timeout=0)
        raw = self.raw_slot.get(timeout=0) if self.raw_slot else None
        if raw is not None:
            self._last_raw_image = raw.image
        candidates = [packet for packet in (processed, raw) if packet is not None]
        packet = max(candidates, key=lambda item: item.timestamp, default=None)
        if packet is None:
            return
        frame = packet.image.copy()
        if packet.detection:
            for (x, y, w, h), label, score in zip(
                packet.detection.boxes, packet.detection.labels, packet.detection.scores
            ):
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 80), 2)
                cv2.putText(frame, f"{label} {score:.2f}", (x, max(20, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 80), 2)
        self._last_track_result = self.marker_tracker.update(packet.detection, now=monotonic())
        self.marker_info_label.setText(format_marker_panel(self._last_track_result))
        if self.follow_check.isChecked() and self.follow_controller and packet.detection and packet.detection.yaw_deg is not None:
            self.follow_controller.update(packet.detection.yaw_deg, packet.detection.dist_m or 0.0)
        height, width, channels = frame.shape
        image = QImage(frame.data, width, height, channels * width, QImage.Format.Format_BGR888).copy()
        self.video_label.setPixmap(QPixmap.fromImage(image).scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))
        self.frames += 1
        now = monotonic()
        elapsed = now - self.last_fps_time
        if elapsed >= 1:
            self.metrics_label.setText(f"FPS: {self.frames / elapsed:.1f} | Latency: {(now - packet.timestamp) * 1000:.0f} ms")
            self.frames = 0
            self.last_fps_time = now

    def closeEvent(self, event) -> None:
        self._save_settings()
        self.stop_workers()
        event.accept()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ESP32-CAM MJPEG live viewer")
    parser.add_argument("--url", default=None, help="ESP32 MJPEG URL")
    parser.add_argument("--detector", choices=("aruco", "hog", "none", "rccar", "yolo"), default=None)
    parser.add_argument("--no-detection", action="store_true")
    args = parser.parse_args(argv)
    config = AppConfig()
    if args.url:
        config.url = normalize_url(args.url)
    if args.detector:
        config.detector_kind = args.detector
    if args.no_detection:
        config.detection_enabled = False
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    window = MainWindow(config)
    window.show()
    return app.exec()
