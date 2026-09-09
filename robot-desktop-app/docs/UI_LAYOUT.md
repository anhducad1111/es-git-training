# UI Layout & Controls

## Overview
Cyberpunk dark theme with modular panels.

## Theme
- Background: #0a0e1a
- Surface: #0f172a
- Accent: #06b6d4 (cyan)
- Text: #e2e8f0

## Layout Structure

### Header Bar
- IP inputs for ESP32-Car and ESP32-Cam
- Rover/Camera status indicators

### Main View
- Video canvas with crosshair overlay
- GimbalHUD (bottom-left)
- Resolution dropdown

### Sidebar (320px)
- **Sensors Page**: Compact T/H/G row, distance gauge, health status
- **Settings Page**: PID controls, camera controls, cloud controls

### Bottom Controls
- Speed slider
- Brake toggle
- Gimbal controls (C, MOUSE buttons)
- Snapshot button
- Super-Res checkbox
- Detection dropdown (HOG/YOLO)
- Detect button

### Log Panel
- Collapsible (28px collapsed, 180px expanded)
- Color-coded messages

## Keyboard Shortcuts

### Movement
- **W** - Forward
- **S** - Backward
- **A** - Turn left
- **D** - Turn right
- **Space** - Stop

### Gimbal
- **I** - Tilt up
- **K** - Tilt down
- **J** - Pan left
- **L** - Pan right
- **C** - Center gimbal
- **Escape** - Disable mouse gimbal

### Speed
- **Shift** - Accelerate (+1 per tick)
- **Ctrl** - Decelerate (-1 per tick)

### Other
- **X** - Take snapshot
- **1-4** - Change resolution

## Widget Files
- `widgets/video_canvas.py` - Video display
- `widgets/sensor_card.py` - Sensor gauges
- `widgets/gimbal_hud.py` - Gimbal overlay
- `widgets/sensor_chart.py` - Matplotlib charts
- `views/sidebar.py` - Sidebar panels
- `views/bottom_controls.py` - Bottom control bar
- `views/main_view.py` - Main video area
- `views/header.py` - Header bar
- `views/log_panel.py` - Log panel
