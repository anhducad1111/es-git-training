# Haru App - File Structure

## Entry Point

### `main.py`
The entry point of the application. Creates the `QApplication`, instantiates `SensorClientApp`, shows the window, starts auto mode, and runs the event loop.

```
python main.py
```

---

## Core Files

### `app.py`
The main application class `SensorClientApp`. Handles:

- **UI initialization** - Assembles all panels and layout
- **Auto mode** - Timer-based auto send (5s) and fetch (5s) with natural value drift (1s)
- **Sensor data generation** - Sine waves + random noise for realistic temperature/humidity
- **Send data** - POST sensor data to API via background thread
- **Fetch logs** - GET data from API and update chart
- **Disconnect popup** - Shows error popup when server is unreachable

Key methods:
| Method | Description |
|--------|-------------|
| `toggle_auto()` | Start/stop auto mode |
| `send_data()` | POST sensor data |
| `fetch_logs()` | GET data and refresh chart |
| `show_disconnect_popup()` | Display error dialog |

---

### `panels.py`
UI panel creation functions. Each function takes the app instance and creates widgets on it:

| Function | Creates |
|----------|---------|
| `create_config_group()` | Server URL and device name inputs |
| `create_input_group()` | Temp/humidity sliders, send/auto buttons, log display |
| `create_upload_group()` | File selector, upload button, progress bar |

---

### `upload.py`
File upload logic. Handles:

| Function | Description |
|----------|-------------|
| `select_file()` | Open file dialog and store path |
| `upload_file()` | Validate file (size < 10GB, no .md/.txt) and upload |
| `on_upload_done()` | Handle upload response |
| `on_upload_error()` | Handle connection failure |

File restrictions:
- Max size: 10 GB
- Blocked extensions: `.md`, `.txt`

---

### `worker.py`
Background thread worker `Worker(QThread)` for non-blocking network requests.

| Task | Description |
|------|-------------|
| `post` | Send JSON payload via POST |
| `get` | Fetch data via GET |
| `upload` | Upload file with progress tracking |

`ProgressFileReader` reads files in 8KB chunks and emits progress signals.

Signals:
| Signal | Description |
|--------|-------------|
| `finished(task, response)` | Request completed |
| `error(message)` | Connection failed |
| `progress(percent)` | Upload progress (0-100%) |

---

### `chart.py`
`ChartWidget(QGroupBox)` - Matplotlib line chart for temperature and humidity history.

- Dual Y-axis: temperature (red) and humidity (blue)
- X-axis: time in `HH:MM:SS` format
- Auto-refreshes on GET

---

## Dependencies

```
pip install PyQt6 requests matplotlib
```
