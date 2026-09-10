# Rover Web Teleoperation via Desktop-App Relay — Design

**Date:** 2026-09-10
**Branch:** `feat/rover-dashboard-gallery-tab` (or a follow-up branch off it)
**Related:** `docs/superpowers/specs/2026-09-08-rover-telemetry-dashboard-design.md` (explicitly scoped Cockpit/teleop *out* of the web dashboard, assuming direct rover control from `robot-desktop-app-tokura` over UDP). This design supersedes that exclusion for a different use case: relaying commands *through* `robot-desktop-app` (the WebSocket-based client, not `-tokura`) so the web operator and the desktop operator can never both hold the rover link at once.

## 1. Problem

`robot-desktop-app` connects directly to the rover over WebSocket (`ws://car_ip:81/`, see `robot-desktop-app/rover_ws.py`) and is the only client speaking to it. We want a rover-operation screen in `rover-telemetry-frontend` for use from another PC on the same LAN. If the web screen also opened a second connection straight to the rover, the two operators could issue conflicting commands simultaneously with no arbitration.

Instead, the web screen sends commands to `robot-desktop-app`, which forwards them through its existing `RoverWebSocket` connection — the same single path local operation already uses.

## 2. Architecture

```
[rover-telemetry-frontend]  --WebSocket (ws://desktop_ip:PORT)-->  [robot-desktop-app]  --RoverWebSocket (ws://car_ip:81/)-->  [rover]
```

The existing telemetry path (`robot-desktop-app` → `cloud_api.py` → `rover-telemetry-backend` → frontend polling) is unchanged. This design adds a second, independent WebSocket link that carries only control commands, direct from browser to desktop app, on the same LAN. The PHP backend is not involved in the control path.

## 3. Desktop app changes (`robot-desktop-app`)

### 3.1 `remote_control_server.py` (new)
- A `websockets`-based WS server run on a background thread (or an `asyncio` loop driven from a `QThread`, following the existing `QThread` pattern used by `RoverWebSocket`/`TelemetryPoller`).
- Listens on `0.0.0.0:<remote_control_port>` (new `config.json` key, e.g. `"remote_control_port": 8765`).
- Message format (JSON), browser → desktop app:
  ```json
  {"type": "command", "command": "forward"}
  ```
  `command` is one of the existing string commands already produced by `app.py`: `forward`, `backward`, `left`, `right`, `stop`, `speed:<N>`, `servo:<pan>,<tilt>`. The server does not interpret the command string — it hands it to the same `_send_command()` used by local controls.
- Message format, desktop app → browser (broadcast to all connected web clients on every change):
  ```json
  {"type": "status", "allowed": true, "rover_connected": true}
  ```
  Sent on connect and whenever `allowed` or `rover_connected` changes.
- Rejection reply when `allowed` is `false` and a command arrives anyway:
  ```json
  {"type": "rejected", "reason": "not_allowed"}
  ```
- No authentication — the LAN is treated as the trust boundary (matches this design's approved scope; do not add tokens or auth later without revisiting this doc).

### 3.2 "Allow web control" toggle
- A new toggle in the desktop UI (sidebar, alongside existing controls). Default **off**. Not persisted to `config.json` — resets to off on every app restart, so a forgotten toggle never survives a relaunch.
- While **off**: incoming `command` messages are ignored and answered with `{"type":"rejected","reason":"not_allowed"}`. The WebSocket connection itself is still accepted (per approved design) so the web UI can distinguish "desktop app not running" from "running but not allowing control".
- While **on**: incoming commands are passed to `_send_command()` exactly like a local key press.
- **Auto-revert on local input:** any local control action that already calls `_send_command()` (arrow keys, on-screen drive buttons, joystick, gimbal drag, emergency stop) flips the toggle back to off first, then sends the local command. This is the sole arbitration rule — local input always wins by silently reclaiming control. Implement as a single guard at the top of `_send_command()`: if the call originates from a local UI handler and the toggle is on, set it off (and push the new `status` broadcast) before proceeding. Commands relayed from the web path call a separate thin wrapper that does *not* touch the toggle.

### 3.3 Wiring into `app.py`
- Instantiate `RemoteControlServer` alongside the other workers in `start_connections()`, stop it in `_stop_real_connections()`, following the existing lifecycle pattern for `RoverWebSocket`/`MJPEGReceiver`/`TelemetryPoller`.
- New signal from the server (`command_received`) is connected to a handler that checks the toggle and calls `_send_command()` — do not let the WS server thread call into Qt widgets directly; go through a `pyqtSignal` like the existing `message_received` pattern in `rover_ws.py`.

### 3.4 Camera handoff on "allow web control"
The web Control tab (§4.6) connects to the camera unit's MJPEG stream directly (`http://cam_ip/640x480.mjpeg`), bypassing the desktop app entirely — there is no relay for video, only for drive/speed/gimbal commands. This is a separate concern from §3.2's command-arbitration toggle, but the two interact: the camera unit (ESP32-CAM class hardware) is assumed to serve a limited number of concurrent MJPEG clients (commonly one), so the desktop app's own `MJPEGReceiver` and the web client's direct connection can starve each other of frames or fail to connect at all if both hold a stream open.

- When the "Web操作を許可" toggle (§3.2) is switched **on**, the desktop app stops its own `MJPEGReceiver` (same call path as `_stop_real_connections()`'s existing `self._video_receiver.stop()`), freeing the camera unit for the web client's connection. The desktop video panel goes blank/shows a "web operator has the camera" placeholder while the toggle is on.
- When the toggle is switched back **off** (manually, or via the existing §3.2 auto-revert-on-local-input rule), the desktop app restarts its own `MJPEGReceiver` immediately, exactly like `start_connections()` initializes it.
- This handoff is best-effort: nothing on the desktop app tells the web client to disconnect its own MJPEG `<img>`, and nothing confirms the camera unit actually freed the resource before the desktop app reconnects. If the camera unit does support multiple concurrent clients, this handoff is unnecessary but harmless (stopping and restarting the desktop's own receiver is a no-op cost). This limitation is accepted for this iteration; do not build a coordination protocol for it.

## 4. Frontend changes (`rover-telemetry-frontend`)

### 4.1 New tab: "操作" (Control)
- Added to the existing tab shell in `index.html` alongside Live/History/System/Gallery, with its own `js/control.js` module — same per-tab-file convention as `live.js`/`history.js`/`gallery.js`.

### 4.2 Desktop app address
- On first use, a small form asks for `desktop_ip:port`; saved to `localStorage` and reused on subsequent visits (editable later from the same tab). No auto-discovery.

### 4.3 Connection/status states
Rendered from the WS connection state plus the last `status` message:
- **未接続** (Not connected) — WS not open (desktop app not running, wrong address, or network issue).
- **接続済み・操作不可** (Connected, control not allowed) — WS open, `allowed: false`.
- **接続済み・操作可** (Connected, control allowed) — WS open, `allowed: true`.

Controls (drive buttons, speed slider, gimbal pad) are rendered but disabled/grayed out unless the state is 操作可, per the approved "connect but show not-allowed" behavior.

### 4.4 Controls (full set, matching desktop app parity)
- Forward / backward / left / right, on-screen buttons plus arrow-key bindings.
- STOP button (always sends `stop` regardless of debouncing on other controls).
- Speed slider, sends `speed:<N>` on change.
- Gimbal pan/tilt control (drag pad or two sliders), sends `servo:<pan>,<tilt>`.
- Every outgoing command is wrapped as `{"type":"command","command":"<string>"}` before sending.

### 4.5 Reconnection
- On WS close/error, retry with backoff (e.g. 2s fixed, matching the simplicity of `RoverWebSocket`'s own 2s retry), updating the status banner to 未接続 while retrying.

### 4.6 Camera video panel
- A separate "Camera address" field (e.g. `192.168.1.117`), independently entered and persisted to `localStorage` from the desktop-app address field — `car_ip` (rover/relay) and `cam_ip` (camera unit) are different physical devices on the LAN in `robot-desktop-app/config.json`, so they need independent inputs.
- The video panel is a plain `<img src="http://<camera_address>/640x480.mjpeg">`, refreshed only by reassigning `src` when the address field changes (the browser handles the MJPEG multipart stream natively — no polling, no canvas, no JS frame handling).
- This connection is direct browser-to-camera-unit and entirely independent of the WebSocket relay in §4.2–§4.5: it works (or fails) regardless of the desktop app's connection/allow state. It is not gated by `allowState` — an operator can watch video without control permission.
- No coordination signal exists between this `<img>` and the desktop app's own camera handoff (§3.4); if the camera unit only serves one client, the web `<img>` may simply fail to load (broken-image icon) until the desktop app's `MJPEGReceiver` actually releases the stream after the toggle flips on. This is accepted per §3.4.

## 5. Command vocabulary (unchanged, reused as-is)

| Command | Meaning |
|---|---|
| `forward` / `backward` | Drive |
| `left` / `right` | Turn |
| `stop` | Emergency/normal stop |
| `speed:<N>` | Set motor speed |
| `servo:<pan>,<tilt>` | Set camera gimbal angles |

No new commands are introduced; the relay is transport-only.

## 6. Error handling

- Desktop app not reachable: web tab shows 未接続, controls disabled, no retries flood the console (backoff as above).
- Rover itself disconnected from desktop app (`RoverWebSocket` not connected): desktop app still accepts and would forward commands, but `_send_command()` already no-ops when `self._rover_ws.is_connected` is false (existing behavior, `app.py:600`) — reflect this to the web client via `rover_connected` in the `status` message so the tab can show a distinct warning ("desktop app connected, rover offline") without needing a new rejection path.
- Malformed/unknown JSON from a web client: server ignores the message (parity with `rover_ws.py`'s own `json.JSONDecodeError` handling on the rover side).

## 7. Testing

- Desktop app: unit test `remote_control_server` — toggle on/off command handling, rejection message, auto-revert-on-local-input behavior, status broadcast on connect/change.
- Manual end-to-end: from a second LAN PC's browser, open the Control tab, connect, flip the toggle on the desktop app, drive the rover; confirm a local desktop key press immediately reclaims control (toggle flips off, web commands rejected) and the web tab reflects 操作不可 without a page reload.

## 8. Out of scope

- Authentication/authorization beyond LAN trust.
- Auto-discovery of the desktop app's address.
- Any change to the existing HTTP telemetry path or `rover-telemetry-backend`.
- Persisting the "allow web control" toggle across desktop app restarts.
- `robot-desktop-app-tokura` (separate UDP-based client, unaffected).
