import os
import queue
import threading
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage


class VideoManager:
    """Manages video recording, snapshots, and super resolution."""

    def __init__(self, cloud_api, log_callback):
        self._cloud_api = cloud_api
        self._log = log_callback
        self._recording = False
        self._rec_path = None
        # 録画の実処理(JPEG再エンコード -> cv2デコード -> VideoWriter.write)は
        # 専用スレッドで行う。以前はsave_frame()がGUIスレッド(app._update_video_frame,
        # 33ms周期)から直接この3段階を同期実行しており、録画中は毎フレーム
        # GUIスレッドをブロックして映像・操作全体がラグる原因になっていた
        # (esp32_mjpeg_detectorがネットワーク受信/デコード/推論を全て専用スレッドに
        # 分離し、GUIスレッドを描画専任にしているのと同じ考え方に合わせる)。
        self._rec_queue = queue.Queue(maxsize=4)
        self._rec_thread = None
        self._rec_thread_running = False

    def start_recording(self):
        """Start video recording."""
        os.makedirs("recordings", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._rec_path = f"recordings/rec_{timestamp}.mp4"
        self._recording = True
        self._rec_thread_running = True
        self._rec_thread = threading.Thread(target=self._recording_worker, daemon=True)
        self._rec_thread.start()
        self._log("REC", f"Recording started: {self._rec_path}")

    def stop_recording(self):
        """Stop video recording."""
        if not self._recording:
            return

        self._recording = False
        self._rec_thread_running = False
        if self._rec_thread:
            self._rec_queue.put(None)  # sentinel: unblock a queue.get() wait
            self._rec_thread.join(timeout=5)
            self._rec_thread = None

        if os.path.exists(self._rec_path):
            size = os.path.getsize(self._rec_path)
            self._log("REC", f"Recording saved: {self._rec_path} ({size} bytes)")
            self._upload_recording(self._rec_path)
        else:
            self._log("REC", f"Recording file not found: {self._rec_path}")

    def save_frame(self, image):
        """Queue a frame for the background recording thread.

        Non-blocking: if the encoder thread is behind, drop this frame
        rather than stall the caller (which runs on the GUI thread)."""
        if not self._recording:
            return
        try:
            self._rec_queue.put_nowait(image)
        except queue.Full:
            pass

    def _recording_worker(self):
        """Runs on its own thread: JPEG re-encode -> cv2 decode -> VideoWriter.write."""
        import cv2
        import numpy as np

        rec_dir = os.path.dirname(self._rec_path)
        if rec_dir and not os.path.exists(rec_dir):
            os.makedirs(rec_dir, exist_ok=True)

        writer = None
        try:
            while self._rec_thread_running or not self._rec_queue.empty():
                try:
                    image = self._rec_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if image is None:
                    break

                try:
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    image.save(buffer, "JPEG")
                    jpeg_data = buffer.data().data()
                    buffer.close()

                    nparr = np.frombuffer(jpeg_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if img is not None:
                        if writer is None:
                            h, w = img.shape[:2]
                            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                            writer = cv2.VideoWriter(
                                self._rec_path, fourcc, 10.0, (w, h)
                            )
                            self._log("REC", f"VideoWriter: {w}x{h}")
                        writer.write(img)
                    else:
                        self._log("REC", "Frame decode failed")
                except Exception as e:
                    self._log("REC", f"Save frame error: {e}")
        finally:
            if writer:
                writer.release()
            
    def _upload_recording(self, filepath):
        """Upload recording to cloud."""
        if not self._cloud_api:
            self._log("REC", "Cloud API not available")
            return
            
        if not os.path.exists(filepath):
            self._log("REC", f"File not found: {filepath}")
            return
            
        self._log("REC", "Uploading to cloud...")
        
        try:
            result = self._cloud_api.upload_media(filepath, media_type="video")
            
            if result and "error" not in result:
                self._log("REC", f"Uploaded to cloud: {os.path.basename(filepath)}")
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                self._log("REC", f"Upload failed: {error_msg[:60]}")
        except Exception as e:
            self._log("REC", f"Upload error: {str(e)[:60]}")
            
    def take_snapshot(self, pixmap, telemetry=None):
        """Take a snapshot with optional telemetry overlay."""
        if pixmap is None or pixmap.isNull():
            self._log("SNAPSHOT", "No frame to capture")
            return None
            
        overlay = pixmap.copy()
        
        if telemetry:
            from PyQt6.QtGui import QPainter, QFont, QColor, QPen
            
            painter = QPainter(overlay)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            temp = telemetry.get("temperature", 0)
            humidity = telemetry.get("humidity", 0)
            gas = telemetry.get("gas", 0)
            
            vn_tz = timezone(timedelta(hours=7))
            vn_time = datetime.now(vn_tz).strftime("%H:%M:%S")
            
            panel_x = overlay.width() - 120
            panel_y = 15
            line_h = 18
            
            painter.setPen(QPen(QColor(16, 185, 129), 1))
            painter.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
            painter.drawText(panel_x, panel_y, f"T: {temp}°C")
            painter.drawText(panel_x, panel_y + line_h, f"H: {humidity}%")
            painter.drawText(panel_x, panel_y + line_h * 2, f"G: {int(gas)} PPM")
            painter.drawText(panel_x, panel_y + line_h * 3, vn_time)
            
            painter.end()
            
        snapshot_dir = os.path.join(os.path.dirname(__file__), "snapshot")
        os.makedirs(snapshot_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.png"
        filepath = os.path.join(snapshot_dir, filename)
        
        overlay.save(filepath, "PNG")
        self._log("SNAPSHOT", f"Saved: {filename}")
        
        self._upload_snapshot(filepath)
        
        return filepath
        
    def _upload_snapshot(self, filepath):
        """Upload snapshot to cloud."""
        if not self._cloud_api:
            self._log("SNAPSHOT", "Cloud API not available")
            return
            
        try:
            result = self._cloud_api.upload_media(filepath, media_type="photo")
            
            if result and "error" not in result:
                self._log("SNAPSHOT", f"Uploaded: {os.path.basename(filepath)}")
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                self._log("SNAPSHOT", f"Upload failed: {error_msg[:60]}")
        except Exception as e:
            self._log("SNAPSHOT", f"Upload error: {str(e)[:80]}")
            
    @property
    def is_recording(self):
        return self._recording
