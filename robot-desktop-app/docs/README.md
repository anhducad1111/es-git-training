# Space Rover Desktop Teleoperation Cockpit

## Overview
PyQt6 desktop application for teleoperation of ESP32-based rover with FPV video, gimbal control, telemetry, AI chat, and object detection.

## Features
- **Video Streaming**: MJPEG from ESP32-Cam
- **Rover Control**: WebSocket commands (WASD, speed, gimbal)
- **Telemetry**: Temperature, humidity, gas, distance sensors
- **Object Detection**: HOG and YOLOv8m
- **Gimbal Control**: Mouse drag, IJKL keys, HUD overlay
- **Snapshot**: Capture frames with sensor overlay, upload to server
- **Cloud Integration**: Telemetry upload to backend API
- **AI Chat**: Ollama integration

## Installation
```bash
pip install PyQt6 requests websocket-client opencv-contrib-python ultralytics matplotlib
```

## Usage
```bash
python main.py
```

## File Structure
- `main.py` - Entry point
- `app.py` - Main application class
- `config.py` - Configuration management
- `styles.py` - UI styling
- `esp32_api.py` - ESP32 REST API client
- `cloud_api.py` - Cloud backend API client
- `rover_ws.py` - WebSocket client
- `mjpeg_receiver.py` - Video stream receiver
- `hog_detector.py` - HOG person detection
- `yolo_detector.py` - YOLOv8 object detection
- `super_resolution.py` - Image super resolution
- `views/` - UI panels
- `widgets/` - Custom widgets
