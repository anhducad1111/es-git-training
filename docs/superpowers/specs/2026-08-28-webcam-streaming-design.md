# Webcam Streaming to Desktop App — Design

## Background

`haru-app2` is an existing PyQt6 desktop app that polls the Sensor
Dashboard PHP API every 5 seconds to display sensor data. The user
wants to add a second, unrelated capability: stream a laptop's webcam
video into `haru-app2` so it can be viewed live on the desktop
machine.

## Requirements

- Laptop (webcam) and desktop app are on the same LAN.
- Latency should be as low as possible — target under ~100ms.
- Connection setup should go through an HTTP API call ("API経由"),
  not a manual/out-of-band step.
- Video display should live inside `haru-app2` as a new panel, not a
  separate app.
- Signaling should use a new, dedicated small server rather than
  extending the unrelated Sensor Dashboard PHP backend.

## Approach

WebRTC (via the `aiortc` Python library) is used for the actual video
transport. On a shared LAN, ICE can establish a direct peer-to-peer
UDP path using host candidates alone — no STUN/TURN server is needed.
This satisfies both the low-latency requirement and the "connect via
an HTTP API" requirement: the API call is used only for the one-time
SDP offer/answer exchange (signaling); the actual video stream flows
peer-to-peer afterward, bypassing the HTTP layer entirely.

The alternative considered was MJPEG-over-HTTP (repeated JPEG frames
over a long-lived HTTP response). It's simpler to implement and fits
the "just an API" mental model more literally, but typically lands in
the 200–500ms latency range and was rejected given the user's <100ms
target.

## Components

### 1. `webcam-stream/sender.py` (runs on the laptop)

A small `aiohttp` HTTP server that also acts as the WebRTC media
source, following aiortc's standard offer/answer server pattern:

- `POST /offer` — accepts a JSON body `{sdp, type}` (the desktop's
  SDP offer), creates an `RTCPeerConnection`, attaches a webcam video
  track (via aiortc's `MediaPlayer` reading the OS camera device —
  DirectShow (`dshow`) on Windows), sets the remote description, and
  responds with `{sdp, type}` (the local SDP answer).
- Binds to `0.0.0.0:<port>` so it's reachable from the desktop machine
  on the LAN. The operator supplies the laptop's LAN IP.
- Single-purpose script — no persistence, no auth (LAN-only, trusted
  network assumption consistent with how the rest of this project
  treats local/dev tooling).

### 2. `haru-app2/webrtc_client.py` (new)

- `WebcamWorker(QThread)` — mirrors the existing `Worker` /
  `GeminiWorker` pattern already used in `haru-app2` for background
  I/O.
- Owns its own asyncio event loop (run inside the thread, since Qt's
  event loop and asyncio don't share one directly).
- On start: builds an `RTCPeerConnection`, adds a transceiver for
  receiving video, creates an SDP offer, `POST`s it as JSON to the
  configured sender URL (e.g. `http://192.168.1.50:8080/offer`) using
  `aiohttp`, and sets the returned SDP answer as the remote
  description.
- Registers an `on("track")` handler; while the connection is open,
  loops on `await track.recv()`, converts each `av.VideoFrame` to a
  `QImage` (via `frame.to_ndarray(format="rgb24")` →
  `QImage(...)`), and emits it through a `frame_ready = pyqtSignal(QImage)`
  signal so the UI thread can safely repaint.
- Emits `connection_state_changed = pyqtSignal(str)` for
  connected/disconnected/failed states, mirroring the
  `status_label` pattern already used for API polling.
- `stop()` cancels the peer connection and stops the asyncio loop
  cleanly.

### 3. `haru-app2/app.py` additions

- New `QGroupBox("Webcam")` panel containing:
  - A `QLineEdit` for the sender URL (e.g.
    `http://192.168.1.50:8080/offer`), persisted the same way
    `api_url` is today.
  - Start/Stop button, mirroring `poll_btn`.
  - A status label (Connected/Disconnected/Failed), mirroring
    `status_label`.
  - A `QLabel` used as the video surface; `frame_ready` sets its
    pixmap via `QPixmap.fromImage(...)`.
- `config.py`: extend the saved config dict with `webcam_url`
  (default `""`), following the existing `load_config`/`save_config`
  pattern — no schema/versioning needed since config is a plain dict.

## Data Flow

1. Operator runs `sender.py` on the laptop; it starts listening on
   `0.0.0.0:8080`.
2. Operator enters `http://<laptop-ip>:8080/offer` in the new Webcam
   panel's URL field in `haru-app2` and clicks Start.
3. `WebcamWorker` creates an SDP offer and `POST`s it to that URL.
4. `sender.py` attaches the webcam track to a new peer connection and
   responds with an SDP answer.
5. ICE establishes a direct P2P UDP path (host candidates only, since
   both sides are on the same LAN).
6. Video frames flow directly over that UDP path (SRTP), decoded by
   aiortc/PyAV on the receiving side, and painted into the `QLabel` as
   they arrive — no HTTP request/response round-trip per frame.

## Error Handling

- Sender unreachable / URL wrong: the initial `POST /offer` fails;
  `WebcamWorker` emits `connection_state_changed("failed")` and the
  panel shows an error state, mirroring how `on_fetch_error` already
  surfaces polling failures in the log panel.
- Camera busy or unavailable on the laptop: `sender.py` returns HTTP
  500 for `/offer`; treated the same as "unreachable" on the desktop
  side.
- Mid-stream disconnect (ICE failure, laptop closed): `WebcamWorker`
  listens for `RTCPeerConnection`'s `on("connectionstatechange")` and
  emits `connection_state_changed("disconnected")` so the panel can
  show a clear status instead of a frozen frame.

## Testing

WebRTC video isn't practical to cover with automated tests, and
`haru-app2` has no existing automated test suite to extend. Verification
is manual, consistent with how this project already validates GUI
behavior:

- Run `sender.py` on the laptop, start the Webcam panel in `haru-app2`
  on the desktop, confirm live video appears.
- Sanity-check latency subjectively (wave a hand, watch for the
  display to keep up) — no formal latency measurement tooling is in
  scope for this change.
- Confirm Stop/Start and sender-offline error states behave as
  described above.

## New Dependencies

- `aiortc` (WebRTC implementation)
- `aiohttp` (signaling HTTP server on the sender side, and the client
  call from `WebcamWorker`)
- `av` (PyAV; pulled in by `aiortc`, used for frame decoding /
  `to_ndarray`)

## Out of Scope

- Audio.
- Multiple simultaneous viewers of one sender.
- Authentication/encryption beyond what WebRTC (SRTP) provides by
  default — acceptable given the trusted-LAN assumption.
- Internet/NAT traversal (STUN/TURN) — explicitly out of scope since
  both ends are confirmed to be on the same LAN.
