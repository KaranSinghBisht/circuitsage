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
