# Space Rover Desktop Teleoperation Cockpit — Documentation

This folder contains all design and specification documents for the project.

---

## Files

### HARU-PRD-DESIGN-PROPOSAL.md

**Purpose:** Phase 1 design proposal submitted for mentor Duke's review.

**Contents:**
- System architecture diagram
- UI wireframes (Main View + Diagnostics View)
- Keyboard state machines (Drive + Gimbal)
- Thread architecture diagram
- Communication protocol (WebSocket commands, telemetry)
- Feature requirements
- Safety features (HW-008, auto-brake)
- OTA firmware update design
- Implementation plan (12 phases)
- Technical reference (workers, config, Gemini AI, charts, cloud API)

**Audience:** Duke (Mentor)

**Status:** Awaiting review

---

### wireframe.md

**Purpose:** Detailed UI specification with wireframes, component descriptions, and architecture diagrams.

**Contents:**
- Main View wireframe (header, video, sidebar, bottom controls, log)
- Diagnostics View wireframe (analytics deck, charts, Gemini chat)
- Video overlay status bar
- Screen zones summary (Main + Diagnostics)
- Component descriptions (all zones)
- Floating button behavior
- Color scheme (Tailwind config)
- Chart customization (/chart commands)
- Keyboard state machines
- Thread architecture
- Resolution change state machine

**Audience:** Developer (Haru)

**Use:** Visual reference during implementation

---

### README.md (this file)

**Purpose:** Documentation index and file reference.

**Contents:**
- File listing with one-line descriptions
- Quick reference for each document's purpose and audience

---

## Document Relationships

```
HARU-PRD-DESIGN-PROPOSAL.md
        │
        ├── Wireframes ──────────► wireframe.md
        │
        ├── Technical Spec ──────► README.md (root)
        │
        └── Implementation ──────► main.py, app.py, ...
```

- `HARU-PRD-DESIGN-PROPOSAL.md` → Submitted to Duke for approval
- `wireframe.md` → Used during coding as visual reference
- `README.md` (root) → Project overview and file descriptions
