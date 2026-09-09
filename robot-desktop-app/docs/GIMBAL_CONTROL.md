# Gimbal Control & HUD

## Overview
Pan/tilt gimbal control with visual HUD overlay showing direction and angles.

## Controls

### Keyboard
- **I** - Tilt up
- **K** - Tilt down
- **J** - Pan left
- **L** - Pan right
- **C** - Center gimbal (90°, 90°)

### Mouse
- **Left-click + drag** on video canvas to control gimbal
- **MOUSE** button in GIMBAL group to toggle
- **Escape** to disable mouse control

## HUD Overlay
Visual compass and pitch ladder displayed on video canvas.

### Components
1. **Pan Compass** (bottom) - Shows horizontal direction (N/S/E/W)
2. **Tilt Ladder** (top) - Shows vertical angle (UP/LVL/DN)

### GimbalHUD Widget
- Location: `widgets/gimbal_hud.py`
- Size: 120x180 pixels
- Position: Bottom-left of video canvas
- Color: Pink (#ff2a85)

### Pan Display
- Circular compass with direction markers
- Needle shows current pan angle
- Range: 0° (W) to 180° (E), center 90° (N)
- Offset display: -90° to +90°

### Tilt Display
- Pitch ladder with level markers
- Needle shows current tilt angle
- Range: 0° (DN) to 180° (UP), center 90° (LVL)
- Offset display: -90° to +90°

## Animation
- Smooth transitions using QTimer (30ms interval)
- Interpolation factor: 0.22

## ESP32 Commands
```
servo:pan,tilt    # Set pan/tilt angles
servo:90,90       # Center gimbal
```

## Integration
```python
# In app.py
def _center_gimbal(self):
    self._gimbal_pan = 90
    self._gimbal_tilt = 90
    self._send_command("servo:90,90")
    self._gimbal_hud.set_gimbal(90, 90)
```
