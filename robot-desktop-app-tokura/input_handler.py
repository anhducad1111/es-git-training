from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal


class InputHandler(QObject):
    """Handles keyboard input and gimbal control."""
    
    key_state_changed = pyqtSignal(str, bool)
    
    def __init__(self, send_command_callback, log_callback, on_emergency_stop=None, on_chassis_follow_toggle=None, on_gimbal_update=None, on_snapshot=None, on_toggle_recording=None):
        super().__init__()
        self._send_command = send_command_callback
        self._log = log_callback
        self._on_emergency_stop = on_emergency_stop
        self._on_chassis_follow_toggle = on_chassis_follow_toggle
        self._on_gimbal_update = on_gimbal_update
        self._on_snapshot = on_snapshot
        self._on_toggle_recording = on_toggle_recording
        
        self._gimbal_pan = 85
        self._gimbal_tilt = 70
        self._global_speed = 220
        self._speed_delta = 0
        self._driving_forward = True
        
        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._tick_speed)
        self._speed_timer.setInterval(50)
        
    def handle_key_press(self, event):
        """Handle key press event."""
        if event.isAutoRepeat():
            return
            
        key = event.key()
        
        if key == Qt.Key.Key_W:
            self._driving_forward = True
            self._send_command("forward")
            self.key_state_changed.emit("forward", True)
        elif key == Qt.Key.Key_S:
            self._driving_forward = False
            self._send_command("backward")
            self.key_state_changed.emit("backward", True)
        elif key == Qt.Key.Key_A:
            self._send_command("left")
            self.key_state_changed.emit("left", True)
        elif key == Qt.Key.Key_D:
            self._send_command("right")
            self.key_state_changed.emit("right", True)
        elif key == Qt.Key.Key_Space:
            self._send_command("stop")
            self._log("STOP", "Emergency stop activated")
            if self._on_emergency_stop:
                self._on_emergency_stop()
        elif key == Qt.Key.Key_V:
            if self._on_chassis_follow_toggle:
                self._on_chassis_follow_toggle()
        elif key == Qt.Key.Key_I:
            self._gimbal_tilt = min(180, self._gimbal_tilt + 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_K:
            self._gimbal_tilt = max(0, self._gimbal_tilt - 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_J:
            self._gimbal_pan = max(0, self._gimbal_pan - 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_L:
            self._gimbal_pan = min(180, self._gimbal_pan + 5)
            self._update_gimbal()
        elif key == Qt.Key.Key_C:
            self.center_gimbal()
        elif key == Qt.Key.Key_Shift:
            self._speed_delta = 1
            if not self._speed_timer.isActive():
                self._speed_timer.start()
        elif key == Qt.Key.Key_Control:
            self._speed_delta = -1
            if not self._speed_timer.isActive():
                self._speed_timer.start()
        elif key == Qt.Key.Key_P:
            # Take photo (snapshot)
            if self._on_snapshot:
                self._on_snapshot()
        elif key == Qt.Key.Key_R:
            # Toggle recording
            if self._on_toggle_recording:
                self._on_toggle_recording()
                
    def handle_key_release(self, event):
        """Handle key release event."""
        if event.isAutoRepeat():
            return
            
        key = event.key()
        
        if key == Qt.Key.Key_W:
            self._send_command("stop")
            self.key_state_changed.emit("forward", False)
        elif key == Qt.Key.Key_S:
            self._send_command("stop")
            self.key_state_changed.emit("backward", False)
        elif key == Qt.Key.Key_A:
            self._send_command("stop")
            self.key_state_changed.emit("left", False)
        elif key == Qt.Key.Key_D:
            self._send_command("stop")
            self.key_state_changed.emit("right", False)
        elif key in (Qt.Key.Key_Shift, Qt.Key.Key_Control):
            self._speed_delta = 0
            self._speed_timer.stop()
            
    def center_gimbal(self):
        """Center the gimbal."""
        self._gimbal_pan = 85
        self._gimbal_tilt = 70
        self._send_command("servo:85,70")
        if self._on_gimbal_update:
            self._on_gimbal_update(85, 70)
        
    def _update_gimbal(self):
        """Send gimbal update command."""
        self._send_command(f"servo:{self._gimbal_pan},{self._gimbal_tilt}")
        if self._on_gimbal_update:
            self._on_gimbal_update(self._gimbal_pan, self._gimbal_tilt)
        
    def _tick_speed(self):
        """Tick speed adjustment."""
        if self._speed_delta != 0:
            new_speed = max(180, min(255, self._global_speed + self._speed_delta))
            if new_speed != self._global_speed:
                self._global_speed = new_speed
                self._send_command(f"speed:{self._global_speed}")
                
    def set_speed(self, speed):
        """Set the global speed."""
        self._global_speed = max(180, min(255, speed))
        self._send_command(f"speed:{self._global_speed}")
        
    @property
    def gimbal_pan(self):
        return self._gimbal_pan
        
    @property
    def gimbal_tilt(self):
        return self._gimbal_tilt
        
    @property
    def global_speed(self):
        return self._global_speed
