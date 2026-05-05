# CircuitSage

**Stack traces for circuits.**

CircuitSage is a local-first Gemma-powered lab partner for electronics students. Software students get stack traces. Electronics students get silence. CircuitSage gives circuits a debugging voice by connecting lab manuals, simulation files, waveform data, bench measurements, and phone-captured evidence into one persistent workflow.

## Demo Story

The included hero demo is an inverting op-amp amplifier:

- Rin = 10 kΩ and Rf = 47 kΩ.
- Expected gain is -4.7.
- Simulation looks correct.
- Bench output is stuck near +12 V.
- CircuitSage compares expected vs observed behavior, asks for the non-inverting input voltage, then identifies a likely floating reference input.

CircuitSage is not replacing teachers. It gives every student a patient lab partner, one that can see the circuit, remember the simulation, ask for the next measurement, and explain the mistake.

## Screenshots / Media

Generated demo media is included in `sample_data/op_amp_lab/`:

- `scope_saturated_placeholder.png`: saturated output near the positive rail.
- `fixed_scope_placeholder.png`: corrected output waveform after grounding the reference input.
- `breadboard_placeholder.png`: bench-mode breadboard placeholder.

## Architecture

```text
frontend React/Vite PWA
  Home -> Studio -> Bench Mode
        |
        v
backend FastAPI
  SQLite session memory
  file uploads
  deterministic tools
  Ollama Gemma client with fallback
        |
        v
sample_data/op_amp_lab
```

Gemma is used through Ollama for natural-language diagnosis and explanation. Deterministic tools handle netlist parsing, waveform analysis, safety checks, manual retrieval, expected-vs-observed comparison, and report generation. If Ollama is unavailable, the deterministic fallback still runs the full demo.

## Quickstart

```bash
make install
make demo
```

`make demo` starts the FastAPI backend, opens the web app, and runs the Vite dev server.

## Local Setup

Backend:

```bash
cd backend
python3.12 -m venv .venv  # Python 3.11-3.13 recommended; this build was verified on 3.12
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Ollama Setup

```bash
ollama serve
ollama pull gemma3:4b
export OLLAMA_MODEL=gemma3:4b
export OLLAMA_BASE_URL=http://localhost:11434
bash scripts/check_ollama.sh
```

The model tag is configurable via `OLLAMA_MODEL`, but the default is `gemma3:4b` until a newer published Ollama tag is verified.

## Demo Flow

1. Click **Load Op-Amp Demo**.
2. Review the seeded manual, netlist, waveform CSVs, and measurements.
3. Click **Start Bench** and open the QR/Bench Mode link.
4. Add `V_noninv = 2.8 V DC` from Bench Mode or Studio.
5. Run diagnosis again.
6. Generate the post-lab reflection report.

## Companion Mode

Open `http://localhost:5173/companion` for the real working-buddy mode.

What it does:

- asks the browser for screen/window sharing permission,
- keeps the shared Tinkercad, LTspice, MATLAB, Simulink, plot, or lab-manual window visible inside CircuitSage,
- captures the current frame on demand,
- can auto-sample frames while watching,
- sends the screenshot plus your question to `/api/companion/analyze`,
- uses Ollama/Gemma vision if the configured model supports images,
- falls back to workspace-specific guidance when Gemma is unavailable,
- can save snapshots back into a CircuitSage lab session.

The browser version cannot directly click native apps like LTspice or MATLAB. It can inspect the shared screen, explain what to check, and produce concrete next actions. True OS-level clicking would require an Electron/Tauri desktop agent with accessibility permissions.

## macOS Desktop Companion

The desktop target lives in `apps/desktop`.

```bash
cd apps/desktop
npm install
npm run dev
```

It provides:

- always-on-top companion window,
- macOS screen/window source picker,
- live thumbnail polling of LTspice, MATLAB, Tinkercad, browser, or any visible window,
- global shortcut prompt: `CommandOrControl+Shift+Space`,
- tray/menu-bar persistence so closing the window keeps the buddy running,
- current-window selection using the frontmost macOS app/window name,
- glowing watch/listen state,
- typed or voice prompt entry,
- screenshot-to-Gemma analysis through the FastAPI backend,
- screen-recording permission shortcut,
- accessibility permission shortcut,
- guarded AppleScript helpers for future click/type automation.

Set `CIRCUITSAGE_API_URL` if your backend is not on `http://127.0.0.1:8000`.

## iOS Bench Companion

The iOS target lives in `apps/ios`.

```bash
cd apps/ios
npm install
npm run ios
```

It provides:

- camera capture for breadboard, oscilloscope, and multimeter evidence,
- photo-library attachment,
- backend URL field for your Mac’s LAN IP,
- optional CircuitSage session attachment,
- snapshot saving into the backend,
- same `/api/companion/analyze` Gemma flow as desktop and web.

When testing on a physical iPhone, use your Mac’s local network IP instead of `127.0.0.1`.

## Safety

CircuitSage is for low-voltage educational circuits: op-amp labs, RC filters, voltage dividers, Arduino-style circuits, and signal-generator/oscilloscope exercises. It refuses detailed live debugging for mains, wall outlets, SMPS primary sides, CRT/flyback circuits, microwave ovens, EV packs, or large capacitor banks.

## Hackathon Tracks

- Primary: Future of Education
- Secondary: Digital Equity & Inclusivity
- Secondary: Safety & Trust
