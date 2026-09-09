import time
from PyQt6.QtCore import QObject, pyqtSignal
from cloud_worker import CloudWorker


class AdaptiveStreamController(QObject):
    """Watches camera stream health (fps from DecodeThread's stats_updated,
    plus disconnect/error events) and automatically trades image quality for
    resilience when the link degrades - e.g. RF interference from the drive
    motors while the rover is moving - then restores quality once the link
    has been stable for a while.

    Degrade order: lower JPEG quality first (cheap, no reconnect), then as a
    last resort drop to the smallest supported resolution. Recovery reverses
    that order and always climbs back to the operator's own resolution
    choice (set via set_baseline_resolution), never past it.
    """

    level_changed = pyqtSignal(str)

    # 0-63 per the ESP32-Cam API (§3.3); lower = higher quality/larger frames.
    QUALITY_STEPS = [12, 30, 45]
    FALLBACK_RESOLUTION = (320, 240)

    LOW_FPS_THRESHOLD = 15.0
    DEGRADE_COOLDOWN_S = 3.0
    RECOVER_STABLE_S = 8.0

    def __init__(self, cam_ip, video_receiver, enabled=True):
        super().__init__()
        self.cam_ip = cam_ip
        self.video_receiver = video_receiver
        self.enabled = enabled

        self._baseline_resolution = (video_receiver.width, video_receiver.height)
        self._quality_level = 0
        self._resolution_downgraded = False
        self._last_change_time = 0.0
        self._good_since = time.time()
        self._workers = []

    def set_enabled(self, enabled):
        self.enabled = enabled

    def set_baseline_resolution(self, width, height):
        """Call when the operator manually picks a resolution - this becomes
        the 'best' state auto-recovery climbs back to, and cancels any
        in-progress auto-degradation so it doesn't fight the manual choice."""
        self._baseline_resolution = (width, height)
        self._quality_level = 0
        self._resolution_downgraded = False
        self._last_change_time = time.time()
        self._good_since = self._last_change_time
        self._set_quality(self.QUALITY_STEPS[0])

    def on_stats(self, stats):
        if not self.enabled:
            return
        fps = stats.get("fps", 0)
        if fps <= 0:
            return  # no data yet (startup / just switched resolution)

        now = time.time()
        if fps < self.LOW_FPS_THRESHOLD:
            self._degrade(now, f"fps dropped to {fps}")
        else:
            self._maybe_recover(now)

    def on_camera_trouble(self):
        """Call on the camera's disconnected/error signals."""
        if not self.enabled:
            return
        self._degrade(time.time(), "connection error")

    def _degrade(self, now, reason):
        if now - self._last_change_time < self.DEGRADE_COOLDOWN_S:
            return

        if self._quality_level < len(self.QUALITY_STEPS) - 1:
            self._quality_level += 1
            self._set_quality(self.QUALITY_STEPS[self._quality_level])
            self.level_changed.emit(f"quality lowered to q{self.QUALITY_STEPS[self._quality_level]} ({reason})")
        elif not self._resolution_downgraded and self._baseline_resolution != self.FALLBACK_RESOLUTION:
            self._resolution_downgraded = True
            w, h = self.FALLBACK_RESOLUTION
            self.video_receiver.set_resolution(w, h)
            self.level_changed.emit(f"resolution dropped to {w}x{h} ({reason})")
        else:
            self._good_since = now
            return

        self._last_change_time = now
        self._good_since = now

    def _maybe_recover(self, now):
        if self._quality_level == 0 and not self._resolution_downgraded:
            self._good_since = now
            return
        if now - self._good_since < self.RECOVER_STABLE_S:
            return
        if now - self._last_change_time < self.DEGRADE_COOLDOWN_S:
            return

        if self._resolution_downgraded:
            self._resolution_downgraded = False
            w, h = self._baseline_resolution
            self.video_receiver.set_resolution(w, h)
            self.level_changed.emit(f"resolution restored to {w}x{h}")
        elif self._quality_level > 0:
            self._quality_level -= 1
            self._set_quality(self.QUALITY_STEPS[self._quality_level])
            self.level_changed.emit(f"quality restored to q{self.QUALITY_STEPS[self._quality_level]}")

        self._last_change_time = now
        self._good_since = now

    def _set_quality(self, quality):
        url = f"http://{self.cam_ip}/api/quality?val={quality}"
        worker = CloudWorker("GET", url)
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        worker.start()
