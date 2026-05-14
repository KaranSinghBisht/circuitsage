# CircuitSage Desktop Companion

Pinned runtime:

- Electron: `^41.5.0` (`npm view electron version` reported `41.5.0`)

Command order:

```bash
npm --prefix apps/desktop install
npm --prefix apps/desktop run check
npm --prefix apps/desktop start
```

The desktop app can launch without the backend. If the backend is not running, screen analysis requests fail until `make demo` or the FastAPI server is started on `http://127.0.0.1:8000`.

Runtime behavior:

- Runs as a **menu-bar resident** (no dock icon by default) and hides instead of quitting. Set `CIRCUITSAGE_SHOW_DOCK=1` to keep the dock icon visible during development.
- `CommandOrControl+Shift+Space` opens the ask overlay using the *whole active window or screen* as input.
- `CommandOrControl+Shift+X` opens a **freeform highlight overlay** — drag a rectangle around just the part of the screen you care about (a specific component, one waveform trace, one error message). Only that crop is sent to Gemma vision, which dramatically improves recognition vs. a full-screen capture. Esc cancels. Override via `CIRCUITSAGE_HIGHLIGHT_SHORTCUT`.
- `watch` keeps the selected screen/window preview fresh.
- `follow` reselects the current frontmost macOS app while watch mode is enabled.
- `insight` sends the current frame to the local `/api/companion/analyze` endpoint about every 25 seconds while watch mode is enabled.
- The app sends the active source title to the backend so Gemma can infer LTspice/Tinkercad/MATLAB context without relying on a canned demo.

Highlight flow (file map):

- `highlight-overlay.html` / `.js` — fullscreen translucent canvas that captures the drag rectangle.
- `highlight-overlay-preload.js` — IPC bridge exposing `circuitSageHighlight` to the overlay.
- `main.js::startHighlight` — captures the screen via `desktopCapturer` at native resolution, hands the screenshot to the overlay as a backdrop, then crops the result (with proper retina scale-factor math) and pushes it into the main companion window via the existing `companion:invoke` channel with an `image_data_url` payload.
- `renderer/renderer.js` — when `companion:invoke` arrives with `image_data_url`, sets `state.usingPreCaptured = true` so `analyze()` does not recapture and clobber the crop.

## Desktop pet (DIP-Sage)

A small (140×160) frameless transparent always-on-top floating window — a stylized DIP chip with two LED eyes — sits at the bottom-right of the primary display. It mirrors the Companion's state visually so you have an ambient signal even when the main window is hidden.

| State | Visual | Trigger |
| --- | --- | --- |
| **Idle** | Slow breathing, green eyes | No active vision call for 9 s |
| **Watching** | Eyes dart left/right | (Reserved — wire to autoWatch later) |
| **Thinking** | Blue eyes, pulsing blue aura | A `companion:analyze` request is in flight |
| **Found** | Bouncy chip, green aura | Response with `confidence: high/medium_high/medium` |
| **Cautious** | Yellow squinted eyes | Response with `confidence: low`, backend error, or Ollama unavailable |
| **Refused** | Red flat eyes, red aura | Response with `mode: safety_refusal` |

Pet controls:

- **Single click** — show the main companion window
- **Double click** — start highlight mode (`Cmd+Shift+X`)
- **Right click** — context menu (open companion, highlight, hide pet, quit)
- **Drag** — move it anywhere on screen (the chip body is the drag region; click zone passes through clicks)
- **Hide/show** — Tray menu → "Toggle desktop pet"

Pet flow (file map):

- `pet-window.html` / `.js` — CSS-only character with a state machine: `idle`, `watching`, `thinking`, `found`, `cautious`, `refused`. Transient states auto-return to `idle` after 9 s. A bubble below the chip shows the detected topology, refusal reason, or backend error for ~6 s.
- `pet-window-preload.js` — IPC bridge exposing `circuitSagePet` to the pet window: `onState`, `onBubble`, `showCompanion`, `startHighlight`, `openMenu`.
- `main.js::createPetWindow` — boots the floating window with `focusable: false` so it never steals focus from LTspice.
- `main.js::postCompanionAnalyze` — broadcasts `pet:state = "thinking"` before the fetch, then `found` / `cautious` / `refused` based on the response's `mode` and `confidence`.
