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

## How to Use

### 1. Server Configuration

| Field | Description |
|-------|-------------|
| API URL | Server endpoint (default: `http://192.168.1.116/es-git-training/esp32-ota/api/api.php`) |
| Device Name | Your device identifier |
| Latest Version | Shows current version from server (auto-updates when Auto is ON) |

### 2. Sensor Data Input

- **Temperature/Humidity Sliders** - Adjust values manually or let Auto mode generate natural values
- **Send Data (POST)** - Send sensor data to server
- **Auto: OFF/ON** - Toggle auto mode (sends every 5s, fetches every 5s with 2.5s offset)

### 3. File Upload 

1. Enter **Version** (e.g., `1.0.3`)
2. Enter **Version Information** (e.g., `initial`)
3. Click **Select File** (only `.bin` files allowed)
4. Click **Upload**

**File is automatically renamed to:** `filename-version-info-client.bin`
- Example: `firmware-1_0_3-initial-Haru_Client.bin`

### 4. Version Management

#### Auto Version Check
- **Auto: OFF/ON** button next to Latest Version
- When ON, fetches latest version every 5 seconds
- Logs when version changes

#### Unpin Version
- **Unpin** button (orange) clears pinned version on server
- Use when you want device to use newly uploaded version

#### After Upload Version Check
- After successful upload, app automatically checks if uploaded version matches current version
- If **mismatch**, popup appears:
  - **Unpin Now** - Clears pin and allows device to update
  - **Close** - Dismisses popup

---

## API Endpoints

| Action | Method | Header | Field | Purpose |
|--------|--------|--------|-------|---------|
| `?action=log` | POST | - | JSON | Send sensor data |
| `?action=ota` | POST | `X-OTA-Key: shodai-haru-2026-8-25` | `file` | Upload firmware |
| `latest.php` | GET | `X-OTA-Key: ota-device-2026-8-25` | - | Get latest version |
| `target.php` | POST | `X-OTA-Key: shodai-haru-2026-8-25` | `action=clear` | Unpin version |

---

## `app.py`

Main class `SensorClientApp(QWidget)`. Handles:

- **UI initialization** - Assembles panels with log screen below input
- **Auto mode** - Drift timer (1s) generates natural values, send timer (5s), fetch timer (5s offset by 2.5s)
- **Sensor data generation** - Sine waves + random noise for realistic temperature/humidity
- **Send data** - POST to `?action=log` via background thread
- **Fetch logs** - GET from API, update chart
- **Version management** - Fetch latest, check after upload, unpin
- **Disconnect popup** - Custom `DisconnectDialog` (click outside to dismiss)

Key methods:
| Method | Description |
|--------|-------------|
| `toggle_auto()` | Start/stop auto mode for sensor data |
| `send_data()` | POST sensor data |
| `fetch_logs()` | GET data and refresh chart |
| `append_log(msg)` | Add color-coded log entry |
| `toggle_version_fetch()` | Start/stop auto version check (5s) |
| `fetch_latest_version()` | GET latest version from server |
| `unpin_version()` | POST to clear pinned version |
| `check_version_after_upload()` | Check if uploaded version matches current |
| `show_disconnect_popup()` | Display error dialog |

---

## `panels.py`

UI panel creation functions. Each returns a `QGroupBox` with bold title:

| Function | Creates |
|----------|---------|
| `create_config_group()` | Server URL, device name, latest version with Auto/Unpin buttons |
| `create_input_group()` | Temp/humidity sliders, send/auto buttons |
| `create_upload_group()` | File selector, version/info inputs, upload button, progress bar |

---

## `upload.py`

File upload with automatic rename.

| Function | Description |
|----------|-------------|
| `select_file()` | Open file dialog (`.bin` only) |
| `upload_file()` | Rename file and upload |
| `build_ota_filename()` | Generate `filename-version-info-client.bin` |
| `on_upload_done()` | Handle response, check version after success |
| `on_upload_error()` | Handle connection failure |

**File rules:**
- Only `.bin` files allowed
- Max size: 10 GB

**Rename format:** `filename-version-info-client.bin`
- filename, info, client: alphanumeric only
- version: alphanumeric + underscores (e.g., `1.1.1` → `1_1_1`)
- Example: `firmware-1_1_1-hotfix-taro.bin`

---

## `worker.py`

Background thread worker `Worker(QThread)` for non-blocking network requests.

| Task | Description |
|------|-------------|
| `post` | Send JSON or form data via POST |
| `get` | Fetch data via GET |
| `upload` | Upload file with progress tracking (8KB chunks) |

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

## Log Color Coding

| Color | Meaning |
|-------|---------|
| Red | ERROR, FAIL, BLOCKED |
| Green | OK, Match |
| White | Other messages |
