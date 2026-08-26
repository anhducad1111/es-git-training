# Haru App - Sensor Logger Client

A PyQt6 desktop application for sending sensor data and uploading firmware files to a PHP API.

## Quick Start

```
python main.py
```

## Dependencies

```
pip install PyQt6 requests matplotlib
```

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `app.py` | Main application class and logic |
| `panels.py` | UI panel creation |
| `upload.py` | File upload with rename |
| `worker.py` | Background network threads |
| `chart.py` | Matplotlib line chart |

---

## `main.py`

Entry point. Creates `QApplication`, instantiates `SensorClientApp`, shows window, and runs event loop.

---

## `app.py`

Main class `SensorClientApp(QWidget)`. Handles:

- **UI initialization** - Assembles panels with log screen below input
- **Auto mode** - Drift timer (1s) generates natural values, send timer (5s), fetch timer (5s offset by 2.5s)
- **Sensor data generation** - Sine waves + random noise for realistic temperature/humidity
- **Send data** - POST to `?action=log` via background thread
- **Fetch logs** - GET from API, update chart
- **Disconnect popup** - Custom `DisconnectDialog` (click outside to dismiss)

Key methods:
| Method | Description |
|--------|-------------|
| `toggle_auto()` | Start/stop auto mode |
| `send_data()` | POST sensor data |
| `fetch_logs()` | GET data and refresh chart |
| `append_log(msg)` | Add color-coded log entry (red=error, green=ok, white=info) |
| `show_disconnect_popup()` | Display error dialog |

---

## `panels.py`

UI panel creation functions. Each returns a `QGroupBox` with bold title:

| Function | Creates |
|----------|---------|
| `create_config_group()` | Server URL and device name inputs |
| `create_input_group()` | Temp/humidity sliders, send/auto buttons |
| `create_upload_group()` | File selector, version/info inputs, upload button, progress bar |

Log display (`QTextEdit`) is positioned below the input group.

---

## `upload.py`

File upload with automatic rename.

| Function | Description |
|----------|-------------|
| `select_file()` | Open file dialog (`.bin` only) |
| `upload_file()` | Rename file and upload |
| `build_ota_filename()` | Generate `filename-version-info-client.bin` |
| `on_upload_done()` | Handle response, clear form on success |
| `on_upload_error()` | Handle connection failure |

**File rules:**
- Only `.bin` files allowed
- Max size: 10 GB

**Rename format:** `filename-version-info-client.bin`
- filename, info, client: alphanumeric only
- version: alphanumeric + underscores (e.g., `1.1.1` → `1_1_1`)
- Example: `firmware-1_1_1-hotfix-taro.bin`

**Upload details:**
- Endpoint: `{base_url}?action=ota`
- Header: `X-OTA-Key: shodai-haru-2026-8-25`
- Field name: `file`
- Only file is sent (no extra form data)

---

## `worker.py`

Background thread worker `Worker(QThread)` for non-blocking network requests.

| Task | Description |
|------|-------------|
| `post` | Send JSON payload via POST |
| `get` | Fetch data via GET |
| `upload` | Upload file with progress tracking (8KB chunks) |

`ProgressFileReader` reads files in chunks and emits progress signals.

Signals:
| Signal | Description |
|--------|-------------|
| `finished(task, response)` | Request completed |
| `error(message)` | Connection failed |
| `progress(percent)` | Upload progress (0-100%) |

---

## `chart.py`

`ChartWidget(QGroupBox)` - Matplotlib line chart with bold title.

- Dual Y-axis: temperature (red) and humidity (blue)
- X-axis: time in `HH:MM:SS` format
- Refresh button triggers GET and redraws chart

---

## API Endpoints

| Action | Method | Field | Purpose |
|--------|--------|-------|---------|
| `?action=log` | POST | JSON | Send sensor data |
| `?action=ota` | POST | `file` | Upload firmware |

## Log Color Coding

| Color | Meaning |
|-------|---------|
| 🔴 Red | ERROR, FAIL, BLOCKED |
| 🟢 Green | OK |
| ⚪ White | Other messages |
