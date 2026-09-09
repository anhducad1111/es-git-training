# Documentation Index

## Getting Started
- [README](README.md) - Project overview and installation
- [Configuration](CONFIGURATION.md) - Config system and settings

## Features
- [Object Detection](OBJECT_DETECTION.md) - HOG and YOLOv8 detection
- [Snapshot](SNAPSHOT.md) - Frame capture with sensor overlay
- [Gimbal Control](GIMBAL_CONTROL.md) - Pan/tilt control and HUD
- [Speed Control](SPEED_CONTROL.md) - Motor speed and auto-brake

## Integration
- [Cloud API](CLOUD_API.md) - Backend telemetry upload
- [ESP32 API](ESP32_API.md) - Rover REST API client

## UI
- [UI Layout](UI_LAYOUT.md) - Interface structure and controls

## Quick Reference

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| WASD | Movement |
| IJKL | Gimbal control |
| C | Center gimbal |
| X | Snapshot |
| Space | Stop |
| Shift/Ctrl | Speed +/- |

### File Structure
```
robot-desktop-app/
├── main.py              # Entry point
├── app.py               # Main application
├── config.py            # Configuration
├── styles.py            # UI styling
├── esp32_api.py         # ESP32 client
├── cloud_api.py         # Cloud client
├── rover_ws.py          # WebSocket
├── mjpeg_receiver.py    # Video stream
├── hog_detector.py      # HOG detection
├── yolo_detector.py     # YOLOv8 detection
├── super_resolution.py  # Image upscale
├── views/               # UI panels
├── widgets/             # Custom widgets
├── design/              # HTML designs
├── docs/                # Documentation
└── snapshot/            # Captured frames
```
