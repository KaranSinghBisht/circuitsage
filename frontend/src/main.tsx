import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bot,
  Camera,
  CheckCircle2,
  CircuitBoard,
  ClipboardList,
  Eye,
  EyeOff,
  ExternalLink,
  FileUp,
  Gauge,
  Loader2,
  MessageSquareText,
  MonitorUp,
  Plus,
  QrCode,
  RefreshCw,
  ScanEye,
  Send,
  Smartphone,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { api } from "./lib/api";
import type { Artifact, CompanionAnalysis, Diagnosis, LabSession, Measurement, ModelHealth, ToolCall } from "./lib/types";
import "./styles.css";

function useRoute() {
  const [path, setPath] = useState(window.location.pathname + window.location.search);
  useEffect(() => {
    const sync = () => setPath(window.location.pathname + window.location.search);
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  const go = (next: string) => {
    window.history.pushState({}, "", next);
    setPath(next);
  };
  return { path, go };
}

function Home({ go }: { go: (path: string) => void }) {
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState("Inverting Op-Amp Amplifier");

  const load = async () => setSessions(await api.sessions());
  useEffect(() => {
    load().catch(console.error);
  }, []);

  async function seed() {
    setLoading(true);
    try {
      const session = await api.seedDemo();
      go(`/studio/${session.id}`);
    } finally {
      setLoading(false);
    }
  }

  async function create() {
    setLoading(true);
    try {
      const session = await api.create(title);
      go(`/studio/${session.id}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="home-shell">
      <section className="hero-band">
        <div>
          <div className="eyebrow"><CircuitBoard size={16} /> CircuitSage</div>
          <h1>Stack traces for circuits.</h1>
          <p>
            A local-first Gemma lab partner that follows electronics students from simulation to oscilloscope,
            asks for the next measurement, and turns silent bench failures into a debugging path.
          </p>
        </div>
        <div className="hero-actions">
          <button onClick={() => go("/companion")}>
            <Bot size={18} />
            Open Companion
          </button>
          <button className="primary" onClick={seed} disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
            Load Op-Amp Demo
          </button>
          <div className="create-row">
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
            <button onClick={create} disabled={loading}><Plus size={18} /> New</button>
          </div>
        </div>
      </section>

      <section className="session-grid">
        {sessions.map((session) => (
          <button className="session-tile" key={session.id} onClick={() => go(`/studio/${session.id}`)}>
            <span>{session.status}</span>
            <strong>{session.title}</strong>
            <small>{session.student_level}</small>
          </button>
        ))}
      </section>
    </main>
  );
}

function Studio({ sessionId, go }: { sessionId: string; go: (path: string) => void }) {
  const [session, setSession] = useState<LabSession | null>(null);
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("My output is stuck near +12V. What should I check first?");
  const [qr, setQr] = useState<{ url: string; data_url: string } | null>(null);

  const refresh = async () => setSession(await api.session(sessionId));
  useEffect(() => {
    refresh().catch(console.error);
    const interval = window.setInterval(() => refresh().catch(() => undefined), 3500);
    return () => window.clearInterval(interval);
  }, [sessionId]);

  useEffect(() => {
    const refreshModel = () => api.modelHealth().then(setModelHealth).catch(() => {
      setModelHealth({ available: false, model: "gemma3:4b", loaded: false, models: [], hint: "Run: ollama pull gemma3:4b" });
    });
    refreshModel();
    const interval = window.setInterval(refreshModel, 10000);
    return () => window.clearInterval(interval);
  }, []);

  async function runDiagnosis() {
    setBusy(true);
    try {
      await api.diagnose(sessionId, message);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function startBench() {
    await api.benchStart(sessionId);
    setQr(await api.benchQr(sessionId));
    await refresh();
  }

  async function generateReport() {
    setBusy(true);
    try {
      await api.report(sessionId);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!session) return <LoadingScreen />;
  const diagnosis = session.latest_diagnosis;

  return (
    <main className="studio-shell">
      <header className="topbar">
        <button className="ghost" onClick={() => go("/")}>CircuitSage</button>
        <div>
          <h1>{session.title}</h1>
          <span className="status-pill">{session.status}</span>
        </div>
        <div className="top-actions">
          <button onClick={() => go(`/companion?session=${sessionId}`)}><Bot size={17} /> Companion</button>
          <button onClick={startBench}><QrCode size={17} /> Start Bench</button>
          <button onClick={generateReport}><ClipboardList size={17} /> Report</button>
          <button className="icon-button" onClick={refresh} aria-label="Refresh"><RefreshCw size={17} /></button>
        </div>
      </header>

      <GemmaStatusBanner health={modelHealth} />

      <section className="studio-grid">
        <aside className="panel artifacts-panel">
          <PanelTitle icon={<FileUp size={17} />} title="Artifacts" detail="manual, netlist, waveforms, bench images" />
          <UploadPanel sessionId={sessionId} onDone={refresh} />
          <ArtifactList artifacts={session.artifacts} />
        </aside>

        <section className="panel center-panel">
          <PanelTitle icon={<Gauge size={17} />} title="Session Context" detail="simulation vs bench evidence" />
          <EvidenceStrip session={session} diagnosis={diagnosis ?? undefined} />
          <MeasurementEditor sessionId={sessionId} onDone={refresh} />
          <MeasurementList measurements={session.measurements} />
          <ToolTimeline calls={diagnosis?.tool_calls ?? []} />
        </section>

        <aside className="panel agent-panel">
          <PanelTitle icon={<Stethoscope size={17} />} title="CircuitSage Agent" detail={diagnosis?.gemma_status ?? "ready"} />
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
          <button className="primary full" onClick={runDiagnosis} disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
            Run Diagnosis
          </button>
          <DiagnosisCard diagnosis={diagnosis ?? undefined} />
          {qr && <QrPanel qr={qr} />}
        </aside>
      </section>

      {session.report && (
        <section className="report-band">
          <h2>Post-Lab Reflection</h2>
          <pre>{session.report}</pre>
        </section>
      )}
    </main>
  );
}

function GemmaStatusBanner({ health }: { health: ModelHealth | null }) {
  if (!health || (health.available && health.loaded)) return null;
  return (
    <div className="gemma-banner">
      <AlertTriangle size={17} />
      <span>Gemma not loaded &mdash; running in deterministic mode. Run: ollama pull {health.model || "gemma3:4b"}</span>
    </div>
  );
}

function Bench({ sessionId, go }: { sessionId: string; go: (path: string) => void }) {
  const [session, setSession] = useState<LabSession | null>(null);
  const [question, setQuestion] = useState("What should I measure next?");
  const [busy, setBusy] = useState(false);
  const refresh = async () => setSession(await api.session(sessionId));
  useEffect(() => {
    refresh().catch(console.error);
  }, [sessionId]);

  async function ask() {
    setBusy(true);
    try {
      await api.chat(sessionId, question, "bench");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!session) return <LoadingScreen />;

  return (
    <main className="bench-shell">
      <header className="bench-head">
        <button className="ghost" onClick={() => go(`/studio/${sessionId}`)}>Studio</button>
        <Smartphone size={22} />
        <div>
          <h1>Bench Mode</h1>
          <p>{session.title}</p>
        </div>
      </header>

      <section className="bench-stack">
        <div className="panel">
          <PanelTitle icon={<Camera size={17} />} title="Capture Evidence" detail="scope, multimeter, breadboard" />
          <UploadPanel sessionId={sessionId} onDone={refresh} compact />
        </div>
        <div className="panel">
          <PanelTitle icon={<Gauge size={17} />} title="Measurement" detail="enter what the instrument says" />
          <MeasurementEditor sessionId={sessionId} onDone={refresh} compact />
        </div>
        <div className="panel">
          <PanelTitle icon={<MessageSquareText size={17} />} title="Ask CircuitSage" detail="short bench guidance" />
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button className="primary full" onClick={ask} disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Stethoscope size={18} />}
            Ask What To Measure Next
          </button>
        </div>
        <DiagnosisCard diagnosis={session.latest_diagnosis ?? undefined} />
      </section>
    </main>
  );
}

function Companion({ go }: { go: (path: string) => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [lastShot, setLastShot] = useState<string>("");
  const [question, setQuestion] = useState("Look at my screen and tell me what I should check next.");
  const [appHint, setAppHint] = useState("auto");
  const [sessionId, setSessionId] = useState(new URLSearchParams(window.location.search).get("session") ?? "");
  const [saveSnapshot, setSaveSnapshot] = useState(false);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [analysis, setAnalysis] = useState<CompanionAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.sessions().then(setSessions).catch(() => undefined);
  }, []);

  function stopWatching() {
    stream?.getTracks().forEach((track) => track.stop());
    setStream(null);
  }

  async function startWatching() {
    setError("");
    try {
      const media = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 2 },
        audio: false,
      });
      setStream(media);
      if (videoRef.current) {
        videoRef.current.srcObject = media;
        await videoRef.current.play();
      }
      media.getVideoTracks()[0]?.addEventListener("ended", () => setStream(null));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Screen capture permission was denied.");
    }
  }

  function captureFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      return "";
    }
    const maxWidth = 1280;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) return "";
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.72);
  }

  async function analyzeCurrent() {
    setBusy(true);
    setError("");
    try {
      const shot = captureFrame() || lastShot;
      if (shot) setLastShot(shot);
      const result = await api.companionAnalyze({
        question,
        image_data_url: shot || undefined,
        app_hint: appHint,
        session_id: sessionId || undefined,
        save_snapshot: saveSnapshot,
      });
      setAnalysis(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Companion analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!stream) return undefined;
    const frameTimer = window.setInterval(() => {
      const shot = captureFrame();
      if (shot) setLastShot(shot);
    }, 3500);
    return () => window.clearInterval(frameTimer);
  }, [stream]);

  useEffect(() => {
    if (!stream || !autoAnalyze || busy) return undefined;
    const analyzeTimer = window.setInterval(() => {
      analyzeCurrent().catch(() => undefined);
    }, 22000);
    return () => window.clearInterval(analyzeTimer);
  }, [stream, autoAnalyze, busy, question, appHint, sessionId, saveSnapshot]);

  const watching = Boolean(stream);

  return (
    <main className="companion-shell">
      <section className="companion-stage">
        <header className="companion-top">
          <button className="ghost" onClick={() => go("/")}>CircuitSage</button>
          <div>
            <div className="eyebrow"><Bot size={16} /> Companion Mode</div>
            <h1>Put it on, share your lab window, ask anytime.</h1>
          </div>
          <button onClick={() => window.open("/companion", "CircuitSageCompanion", "width=420,height=720")}>
            <ExternalLink size={17} />
            Pop Out
          </button>
        </header>

        <div className="companion-grid">
          <div className="screen-panel">
            <div className="screen-toolbar">
              <span className={watching ? "live-dot on" : "live-dot"}>{watching ? "watching" : "off"}</span>
              <div>
                <button className={watching ? "" : "primary"} onClick={watching ? stopWatching : startWatching}>
                  {watching ? <EyeOff size={17} /> : <MonitorUp size={17} />}
                  {watching ? "Stop" : "Share Screen"}
                </button>
                <button onClick={() => setLastShot(captureFrame())} disabled={!watching}>
                  <Camera size={17} />
                  Snapshot
                </button>
              </div>
            </div>
            <div className="screen-preview">
              <video ref={videoRef} muted playsInline />
              {!watching && <div className="screen-empty"><Eye size={28} /> Waiting for screen permission</div>}
            </div>
            <canvas ref={canvasRef} hidden />
          </div>

          <aside className="companion-card">
            <div className="pet-orb">
              <ScanEye size={34} />
            </div>
            <h2>CircuitSage Buddy</h2>
            <p className="muted">
              Watches the shared window while enabled. Works with Tinkercad, LTspice, MATLAB, plots, manuals, and bench screenshots.
            </p>

            <label>
              <span>Workspace</span>
              <select value={appHint} onChange={(event) => setAppHint(event.target.value)}>
                <option value="auto">Auto detect</option>
                <option value="tinkercad">Tinkercad</option>
                <option value="ltspice">LTspice</option>
                <option value="matlab">MATLAB / Simulink</option>
                <option value="electronics_workspace">General electronics</option>
              </select>
            </label>

            <label>
              <span>Attach to session</span>
              <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
                <option value="">No session</option>
                {sessions.map((session) => <option value={session.id} key={session.id}>{session.title}</option>)}
              </select>
            </label>

            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />

            <div className="toggle-row">
              <label><input type="checkbox" checked={autoAnalyze} onChange={(event) => setAutoAnalyze(event.target.checked)} /> Auto analyze</label>
              <label><input type="checkbox" checked={saveSnapshot} onChange={(event) => setSaveSnapshot(event.target.checked)} /> Save snapshots</label>
            </div>

            <button className="primary full" onClick={analyzeCurrent} disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              Analyze Current Screen
            </button>
            {error && <p className="error-text">{error}</p>}
          </aside>
        </div>
      </section>

      <section className="companion-output">
        <div className="snapshot-card">
          <h2>Latest Frame</h2>
          {lastShot ? <img src={lastShot} alt="Latest captured screen" /> : <p className="muted">No frame captured yet.</p>}
        </div>
        <CompanionResult analysis={analysis} />
      </section>
    </main>
  );
}

function CompanionResult({ analysis }: { analysis: CompanionAnalysis | null }) {
  if (!analysis) {
    return (
      <section className="analysis-card">
        <h2>Live Help</h2>
        <p className="muted">Share your screen, open Tinkercad/LTspice/MATLAB, then ask what to check.</p>
      </section>
    );
  }
  return (
    <section className="analysis-card">
      <div className="card-head">
        <Bot size={18} />
        <span>{analysis.mode ?? "analysis"} · {analysis.confidence ?? "unknown"} confidence</span>
      </div>
      <h2>{analysis.workspace}</h2>
      <p>{analysis.visible_context}</p>
      <strong>{analysis.answer}</strong>
      <div className="next-measure">
        <span>Next actions</span>
        <ul>
          {(analysis.next_actions ?? []).map((action) => <li key={action}>{action}</li>)}
        </ul>
      </div>
      {analysis.gemma_error && <small className="error-text">{analysis.gemma_error}</small>}
      {analysis.raw && <pre>{analysis.raw}</pre>}
    </section>
  );
}

function UploadPanel({ sessionId, onDone, compact = false }: { sessionId: string; onDone: () => void; compact?: boolean }) {
  const [kind, setKind] = useState("image");
  async function upload(file: File | null) {
    if (!file) return;
    await api.upload(sessionId, file, kind);
    onDone();
  }
  return (
    <div className={compact ? "upload compact" : "upload"}>
      <select value={kind} onChange={(event) => setKind(event.target.value)}>
        <option value="image">Image</option>
        <option value="manual">Manual</option>
        <option value="netlist">Netlist</option>
        <option value="waveform_csv">Waveform CSV</option>
        <option value="note">Note</option>
      </select>
      <label className="file-input">
        <FileUp size={18} />
        <span>Upload</span>
        <input type="file" accept={kind === "image" ? "image/*" : undefined} capture={kind === "image" ? "environment" : undefined} onChange={(event) => upload(event.target.files?.[0] ?? null)} />
      </label>
    </div>
  );
}

function MeasurementEditor({ sessionId, onDone, compact = false }: { sessionId: string; onDone: () => void; compact?: boolean }) {
  const [form, setForm] = useState({ label: "V_noninv", value: "2.8", unit: "V", mode: "DC", context: "Non-inverting input floating", source: "manual_entry" });
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    await api.addMeasurement(sessionId, { ...form, value: Number(form.value) });
    onDone();
  }
  return (
    <form className={compact ? "measurement-form compact" : "measurement-form"} onSubmit={submit}>
      <input value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} placeholder="Node" />
      <input value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} placeholder="Value" inputMode="decimal" />
      <input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} placeholder="Unit" />
      <select value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
        <option>DC</option>
        <option>AC</option>
        <option>peak</option>
        <option>peak-to-peak</option>
      </select>
      <input className="wide" value={form.context} onChange={(event) => setForm({ ...form, context: event.target.value })} placeholder="Context" />
      <button><Plus size={17} /> Add</button>
    </form>
  );
}

function EvidenceStrip({ session, diagnosis }: { session: LabSession; diagnosis?: Diagnosis }) {
  return (
    <div className="evidence-strip">
      <div><span>Experiment</span><strong>{session.experiment_type.replaceAll("_", " ")}</strong></div>
      <div><span>Expected gain</span><strong>{diagnosis?.expected_behavior?.gain ?? "-4.7"}</strong></div>
      <div><span>Current issue</span><strong>{diagnosis?.observed_behavior?.summary ?? "Awaiting diagnosis"}</strong></div>
    </div>
  );
}

function ArtifactList({ artifacts }: { artifacts: Artifact[] }) {
  return (
    <div className="artifact-list">
      {artifacts.map((artifact) => (
        <a href={api.artifactUrl(artifact.id)} key={artifact.id} target="_blank" rel="noreferrer">
          <span>{artifact.kind}</span>
          <strong>{artifact.filename}</strong>
        </a>
      ))}
    </div>
  );
}

function MeasurementList({ measurements }: { measurements: Measurement[] }) {
  return (
    <div className="measurement-list">
      {measurements.map((measurement) => (
        <div key={measurement.id}>
          <strong>{measurement.label}</strong>
          <span>{measurement.value} {measurement.unit} {measurement.mode}</span>
          <small>{measurement.context}</small>
        </div>
      ))}
    </div>
  );
}

function DiagnosisCard({ diagnosis }: { diagnosis?: Diagnosis }) {
  if (!diagnosis) {
    return (
      <section className="diagnosis-card empty">
        <AlertTriangle size={18} />
        <p>Run diagnosis after loading the op-amp demo or uploading bench evidence.</p>
      </section>
    );
  }
  const topFault = diagnosis.likely_faults?.[0];
  const status = diagnosis.gemma_status ?? "deterministic_fallback";
  return (
    <section className="diagnosis-card">
      <div className="card-head">
        <CheckCircle2 size={18} />
        <span>{diagnosis.confidence ?? "medium"} confidence</span>
        <GemmaStatusChip status={status} />
      </div>
      <h2>{topFault?.fault ?? "Need more evidence"}</h2>
      <p>{diagnosis.student_explanation}</p>
      <div className="next-measure">
        <span>Next measurement</span>
        <strong>{diagnosis.next_measurement?.label}</strong>
        <small>{diagnosis.next_measurement?.instruction}</small>
      </div>
      <ul>
        {(diagnosis.safety?.warnings ?? []).slice(0, 2).map((warning) => <li key={warning}>{warning}</li>)}
      </ul>
    </section>
  );
}

function GemmaStatusChip({ status }: { status: string }) {
  const tone = status.startsWith("ollama_gemma")
    ? "green"
    : status.startsWith("blocked_by_safety")
      ? "red"
      : "amber";
  const label = status.startsWith("deterministic_fallback") ? "deterministic_fallback" : status;
  return <span className={`gemma-chip ${tone}`}>{label}</span>;
}

function ToolTimeline({ calls }: { calls: ToolCall[] }) {
  return (
    <div className="tool-timeline">
      <h3>Tool Calls</h3>
      {calls.map((call) => (
        <div key={`${call.tool_name}-${call.duration_ms}`}>
          <span>{call.tool_name}</span>
          <small>{call.status} · {call.duration_ms}ms</small>
        </div>
      ))}
    </div>
  );
}

function QrPanel({ qr }: { qr: { url: string; data_url: string } }) {
  return (
    <div className="qr-panel">
      <img src={qr.data_url} alt="Bench Mode QR" />
      <a href={qr.url} target="_blank" rel="noreferrer">{qr.url}</a>
    </div>
  );
}

function PanelTitle({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return (
    <div className="panel-title">
      {icon}
      <div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
    </div>
  );
}

function LoadingScreen() {
  return <main className="loading"><Loader2 className="spin" /> Loading CircuitSage</main>;
}

function App() {
  const { path, go } = useRoute();
  const pathname = path.split("?")[0];
  const studioMatch = useMemo(() => pathname.match(/^\/studio\/([^/]+)/), [pathname]);
  const benchMatch = useMemo(() => pathname.match(/^\/bench\/([^/]+)/), [pathname]);
  if (pathname === "/companion") return <Companion go={go} />;
  if (studioMatch) return <Studio sessionId={studioMatch[1]} go={go} />;
  if (benchMatch) return <Bench sessionId={benchMatch[1]} go={go} />;
  return <Home go={go} />;
}

createRoot(document.getElementById("root")!).render(<App />);
