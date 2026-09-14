# Remote Snapshot Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add snapshot action handling to the remote control server so web clients can trigger snapshots via `{"type": "action", "action": "snapshot"}`.

**Architecture:** Extend `RemoteControlServer` with a new `snapshot_requested` pyqtSignal. Route `action:"snapshot"` messages through this signal (same pattern as `command_received`). Connect signal to `_take_snapshot()` in `app.py`. No changes needed for sections 3.6 (resolution — already works via relay) and 3.7 (flip — frontend-only CSS).

**Tech Stack:** Python 3.12, PyQt6, websockets

**Spec:** `C:\Users\haru0\Downloads\2026-09-10-rover-web-teleop-relay-design (1).md` sections 3.5–3.7

## Global Constraints

- Python 3.12+
- PyQt6
- `websockets` library (already imported in remote_control_server.py)
- No authentication — LAN trust boundary
- Cross-thread safety: WS server thread must NOT call Qt widgets directly; use pyqtSignal
- Gating: snapshot action only honored while "Allow web control" toggle is on

---

## Task 1: Add `snapshot_requested` signal to `RemoteControlServer`

**Files:**
- Modify: `robot-desktop-app/remote_control_server.py:14-18`

**Interfaces:**
- Produces: `snapshot_requested = pyqtSignal()` — emitted when `{"type": "action", "action": "snapshot"}` is received and `allowed` is True

- [ ] **Step 1: Add the signal**

In `remote_control_server.py`, add a new signal to the class:

```python
class RemoteControlServer(QThread):
    command_received = pyqtSignal(str)
    snapshot_requested = pyqtSignal()  # NEW
    status_changed = pyqtSignal(bool, bool)
```

- [ ] **Step 2: Update `_handle_message` to route action messages**

Replace the current `_handle_message` (lines 57-70) with:

```python
async def _handle_message(self, raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    msg_type = data.get("type", "")
    if msg_type == "command":
        command = data.get("command", "")
        if not command:
            return
        if not self._allowed:
            await self._send_rejected("not_allowed")
            return
        self.command_received.emit(command)
    elif msg_type == "action":
        action = data.get("action", "")
        if action == "snapshot":
            if not self._allowed:
                await self._send_rejected("not_allowed")
                return
            self.snapshot_requested.emit()
        # Unknown actions are silently ignored (per spec §6)
    # Unknown types are silently ignored (per spec §6)
```

- [ ] **Step 3: Add `_send_rejected` helper**

Add this method to the class (after `_handle_message`):

```python
async def _send_rejected(self, reason):
    await self._broadcast({"type": "rejected", "reason": reason})
```

- [ ] **Step 4: Verify import**

Run: `python.exe -c "from remote_control_server import RemoteControlServer; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add robot-desktop-app/remote_control_server.py
git commit -m "feat: add snapshot_requested signal to RemoteControlServer"
```

---

## Task 2: Wire `snapshot_requested` to `_take_snapshot()` in `app.py`

**Files:**
- Modify: `robot-desktop-app/app.py:103-104` (connection setup)

**Interfaces:**
- Consumes: `RemoteControlServer.snapshot_requested` signal
- Produces: calls `self._take_snapshot()`

- [ ] **Step 1: Connect signal in `start_connections()`**

In `app.py`, after the `command_received.connect` line (line 103), add:

```python
self._remote_server.command_received.connect(self._relay_command)
self._remote_server.snapshot_requested.connect(self._on_remote_snapshot)  # NEW
```

- [ ] **Step 2: Add `_on_remote_snapshot` handler**

Add this method to the `RoverTeleopApp` class (after `_relay_command`):

```python
def _on_remote_snapshot(self):
    self._add_log("REMOTE", "Snapshot requested by web client")
    self._take_snapshot()
```

- [ ] **Step 3: Verify import**

Run: `python.exe -c "from app import RoverTeleopApp; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add robot-desktop-app/app.py
git commit -m "feat: wire snapshot_requested to _take_snapshot in app.py"
```

---

## Task 3: Add rejection broadcast for action messages when not allowed

**Files:**
- Modify: `robot-desktop-app/remote_control_server.py` (already modified in Task 1)

**Note:** This is already handled in Task 1's `_handle_message` update. The `action:"snapshot"` path calls `await self._send_rejected("not_allowed")` when `self._allowed` is False. This task exists for verification only.

- [ ] **Step 1: Verify the rejection logic is correct**

Read `remote_control_server.py` and confirm:
1. `action:"snapshot"` when `allowed=False` → sends `{"type": "rejected", "reason": "not_allowed"}`
2. `action:"snapshot"` when `allowed=True` → emits `snapshot_requested` signal
3. Unknown `action` values → silently ignored

- [ ] **Step 2: Verify `_send_rejected` helper is correct**

Confirm `_send_rejected` calls `_broadcast` with `{"type": "rejected", "reason": reason}`.

---

## Task 4: End-to-end verification

- [ ] **Step 1: Start desktop app**

Run the desktop app and confirm:
- No startup errors
- Remote control server starts on port 8765
- "WEB CONTROL: OFF" toggle visible in sidebar

- [ ] **Step 2: Test from browser console**

Open browser console and run:

```javascript
const ws = new WebSocket('ws://localhost:8765');
ws.onmessage = e => console.log(JSON.parse(e.data));

// After connection, test snapshot rejection (toggle is OFF):
ws.send(JSON.stringify({type: "action", action: "snapshot"}));
// Should receive: {type: "rejected", reason: "not_allowed"}
```

- [ ] **Step 3: Test with toggle ON**

1. Click "WEB CONTROL: ON" toggle in desktop app
2. Send snapshot from browser:

```javascript
ws.send(JSON.stringify({type: "action", action: "snapshot"}));
// Should trigger snapshot in desktop app (check logs)
```

- [ ] **Step 4: Test auto-revert on local input**

1. With toggle ON, send snapshot from browser (works)
2. Press any arrow key locally in desktop app
3. Confirm toggle reverts to OFF
4. Send another snapshot from browser → should be rejected

---

## Summary

| Section | Desktop-App Work | Status |
|---------|-----------------|--------|
| **3.5 Snapshot** | Add `snapshot_requested` signal, route `action:"snapshot"`, wire to `_take_snapshot()` | Tasks 1-2 |
| **3.6 Resolution** | No work needed — already works via relay (`resolution:<w>,<h>` is in command vocabulary) | Already done |
| **3.7 Flip H/V** | No work needed — frontend-only CSS transform on `<img>` element | N/A |
