# ESP32-Cam FPV Client

A PyQt6 desktop application for viewing live MJPEG streams from ESP32-Cam modules.

## Features

- Live MJPEG stream viewer with crosshair overlay
- Resolution selector (QVGA to UXGA)
- LED brightness control (0-255)
- JPEG quality adjustment (0-63)
- FPS counter and connection status
- Dark theme UI
- Configuration persistence (IP, resolution, settings)

## Requirements

- Python 3.10+
- ESP32-Cam module on the same network

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

1. Enter the ESP32-Cam IP address in the URL bar (default: `192.168.1.114`)
2. Click **Connect** to start the stream
3. Adjust resolution, LED brightness, and quality using the controls

## Configuration

Settings are saved to `config.json` on exit:

| Key | Default | Description |
|-----|---------|-------------|
| `cam_ip` | `192.168.1.114` | Camera IP address |
| `cam_port` | `80` | Camera port |
| `stream_path` | `/640x480.mjpeg` | MJPEG stream endpoint |
| `led_brightness` | `0` | LED brightness (0-255) |
| `jpeg_quality` | `14` | JPEG quality (0-63) |

## ESP32-Cam Firmware

This client expects the camera to expose:
- `/{resolution}.mjpeg` — MJPEG stream endpoint
- `/api/led?val={0-255}` — LED brightness control
- `/api/quality?val={0-63}` — JPEG quality control

## Project Structure

```
camera-screen-app/
├── main.py            # Entry point
├── app.py             # GUI (CameraApp, CameraCanvas)
├── camera_thread.py   # MJPEG stream reader (QThread)
├── config.py          # Config load/save
├── config.json        # Persisted settings
└── requirements.txt   # Dependencies
```
