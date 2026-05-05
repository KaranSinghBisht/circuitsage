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

- Runs as a tray/menu-bar companion and hides instead of quitting.
- `CommandOrControl+Shift+Space` opens the ask overlay from LTspice, MATLAB, Tinkercad, or any browser tab.
- `watch` keeps the selected screen/window preview fresh.
- `follow` reselects the current frontmost macOS app while watch mode is enabled.
- `insight` sends the current frame to the local `/api/companion/analyze` endpoint about every 25 seconds while watch mode is enabled.
- The app sends the active source title to the backend so Gemma can infer LTspice/Tinkercad/MATLAB context without relying on a canned demo.
