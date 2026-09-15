import os
import queue
import threading
import time
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage


class VideoManager:
    """Manages video recording, snapshots, and super resolution."""

    def __init__(self, cloud_api, log_callback):
        self._cloud_api = cloud_api
        self._log = log_callback
        self._recording = False
        self._rec_path = None
        # 録画の実実処理は専用スレッドで行う。
        # キューサイズを大きくすることで、GUIスレッドのブロックを防ぐ。
        self._rec_queue = queue.Queue(maxsize=30)
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

        import time
        time.sleep(0.5)

        if os.path.exists(self._rec_path):
            size = os.path.getsize(self._rec_path)
            self._log("REC", f"Recording saved: {self._rec_path} ({size} bytes)")
            if size > 0:
                self._upload_recording(self._rec_path)
            else:
                self._log("REC", "File is empty, skipping upload")
        else:
            self._log("REC", f"Recording file not found: {self._rec_path}")

    def save_frame(self, jpeg_data, bbox=None, detection=None):
        """Queue a frame for the background recording thread.

        Non-blocking: if the encoder thread is behind, drop this frame
        rather than stall the caller (which runs on the GUI thread).
        jpeg_data: raw JPEG bytes from camera stream (no re-encoding needed).
        bbox: optional (x, y, w, h) tuple to draw bounding box on frame.
        detection: optional detection dict with yaw_deg, dist_m, confidence."""
        if not self._recording or jpeg_data is None:
            return
        try:
            self._rec_queue.put_nowait((jpeg_data, bbox, detection))
        except queue.Full:
            # Drop frame if queue is full to prevent GUI lag
            pass

    def _recording_worker(self):
        """Runs on its own thread: JPEG decode -> draw bbox -> VideoWriter.write."""
        import cv2
        import numpy as np

        rec_dir = os.path.dirname(self._rec_path)
        if rec_dir and not os.path.exists(rec_dir):
            os.makedirs(rec_dir, exist_ok=True)

        writer = None
        frame_count = 0
        last_frame_time = time.time()
        fps_history = []
        try:
            while self._rec_thread_running or not self._rec_queue.empty():
                try:
                    item = self._rec_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if item is None:
                    break

                # Handle tuple format (jpeg_data, bbox, detection)
                if isinstance(item, tuple):
                    jpeg_data, bbox, detection = item
                else:
                    jpeg_data, bbox, detection = item, None, None

                try:
                    if jpeg_data is None:
                        continue

                    # Decode JPEG directly (no QImage re-encoding needed)
                    nparr = np.frombuffer(jpeg_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if img is not None:
                        # Draw bounding box with label if provided (scale to actual frame size)
                        if bbox is not None:
                            bx, by, bw, bh = bbox
                            yaw = detection.get("yaw_deg") if detection else None
                            dist = detection.get("dist_m") if detection else None
                            conf = detection.get("confidence", 0.0) if detection else 0.0

                            h_img, w_img = img.shape[:2]
                            orig_w, orig_h = 640, 480
                            scale_x = w_img / orig_w
                            scale_y = h_img / orig_h
                            x1 = int(bx * scale_x)
                            y1 = int(by * scale_y)
                            x2 = int((bx + bw) * scale_x)
                            y2 = int((by + bh) * scale_y)
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 165, 255), 2)

                            # Draw label
                            label_parts = ["TARGET"]
                            if yaw is not None:
                                label_parts.append(f"yaw{yaw:+.0f}deg")
                            if dist is not None:
                                label_parts.append(f"{dist:.2f}m")
                            label_parts.append(f"{conf:.0%}")
                            label = " ".join(label_parts)
                            cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

                        if writer is None:
                            h, w = img.shape[:2]
                            fourcc = cv2.VideoWriter_fourcc(*'avc1')
                            # Use 20fps as default (camera typically sends 15-30fps)
                            writer = cv2.VideoWriter(
                                self._rec_path, fourcc, 20.0, (w, h)
                            )
                            self._log("REC", f"VideoWriter: {w}x{h} @20fps")
                        writer.write(img)
                        frame_count += 1
                        
                        # Track actual FPS
                        current_time = time.time()
                        if last_frame_time:
                            fps = 1.0 / (current_time - last_frame_time)
                            fps_history.append(fps)
                            if len(fps_history) > 30:
                                fps_history.pop(0)
                        last_frame_time = current_time
                    else:
                        self._log("REC", "Frame decode failed")
                except Exception as e:
                    self._log("REC", f"Save frame error: {e}")
        finally:
            if writer:
                writer.release()
            avg_fps = sum(fps_history) / len(fps_history) if fps_history else 0
            self._log("REC", f"Recording saved: {frame_count} frames, avg {avg_fps:.1f}fps")
            
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
            
    def take_snapshot(self, pixmap, telemetry=None, bbox=None, detection=None):
        """Take a snapshot with optional telemetry overlay and bounding box."""
        if pixmap is None or pixmap.isNull():
            self._log("SNAPSHOT", "No frame to capture")
            return None
            
        overlay = pixmap.copy()
        
        from PyQt6.QtGui import QPainter, QFont, QColor, QPen
        
        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw bounding box with label if provided
        if bbox is not None:
            bx, by, bw, bh = bbox
            orig_w, orig_h = 640, 480
            scale_x = overlay.width() / orig_w
            scale_y = overlay.height() / orig_h
            x1 = int(bx * scale_x)
            y1 = int(by * scale_y)
            w = int(bw * scale_x)
            h = int(bh * scale_y)
            painter.setPen(QPen(QColor(255, 165, 0), 2))  # Orange
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x1, y1, w, h)

            # Draw label
            yaw = detection.get("yaw_deg") if detection else None
            dist = detection.get("dist_m") if detection else None
            conf = detection.get("confidence", 0.0) if detection else 0.0

            label_parts = ["TARGET"]
            if yaw is not None:
                label_parts.append(f"yaw{yaw:+.0f}°")
            if dist is not None:
                label_parts.append(f"{dist:.2f}m")
            label_parts.append(f"{conf:.0%}")
            label = " ".join(label_parts)
            painter.setFont(QFont("JetBrains Mono", 8))
            painter.setPen(QPen(QColor(255, 165, 0), 1))
            painter.drawText(x1, y1 - 5, label)
        
        if telemetry:
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
