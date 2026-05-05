# CircuitSage Architecture

CircuitSage is built as a simple monorepo.

## Backend

FastAPI exposes session, upload, bench pairing, measurement, diagnosis, chat, and report endpoints. SQLite stores persistent lab sessions, artifacts, measurements, diagnoses, messages, and reports.

The agent flow is:

1. Load session, artifacts, and measurements.
2. Run `safety_check`.
3. Parse the netlist when present.
4. Analyze observed waveform CSV when present.
5. Retrieve relevant lab manual snippets.
6. Compare expected behavior with observed behavior.
7. Ask Ollama/Gemma for structured JSON.
8. Fall back to deterministic diagnosis if Ollama is unavailable.
9. Save and return the diagnosis.

## Frontend

React/Vite provides three routes:

- `/`: session list and one-click op-amp demo seed.
- `/studio/:sessionId`: PC Studio for artifacts, measurements, diagnosis, QR pairing, tool calls, and reports.
- `/bench/:sessionId`: mobile-first Bench Mode for image upload, measurement entry, and short bench questions.
- `/companion`: screen-share based Companion Mode that watches a shared Tinkercad/LTspice/MATLAB window, captures frames, and asks Gemma for contextual help.

## Native Clients

`apps/desktop` is an Electron macOS companion. It is the path to a true desktop lab buddy because it can enumerate windows/screens via `desktopCapturer`, float above LTspice/MATLAB/Tinkercad, and eventually perform guarded Accessibility actions through AppleScript.

`apps/ios` is an Expo iOS bench companion. It captures oscilloscope, multimeter, and breadboard photos and sends them to the same backend analysis endpoint. It is designed for phone-at-the-bench use, not desktop screen watching.

## Companion Analysis

`POST /api/companion/analyze` accepts:

- `question`
- `image_data_url`
- `app_hint`
- optional `session_id`
- optional `save_snapshot`

The backend sends the base64 screenshot to Ollama chat as an image when possible. If the local model is unavailable or cannot process images, CircuitSage returns deterministic guidance tuned to Tinkercad, LTspice, MATLAB, or general electronics workflows.

## Data

`sample_data/op_amp_lab` contains a lab manual excerpt, netlist, expected waveform CSV, saturated waveform CSV, student question, and generated placeholder images.
