import { useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";
import { Bot, Camera, ExternalLink, Eye, EyeOff, MonitorUp, ScanEye, Send } from "lucide-react";
import { api } from "../lib/api";
import type { CompanionAnalysis, LabSession } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function Companion() {
  const [, setLocation] = useLocation();
  const { locale } = useI18n();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [lastShot, setLastShot] = useState("");
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
      const media = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 2 }, audio: false });
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
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) return "";
    const scale = Math.min(1, 1280 / video.videoWidth);
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
      setAnalysis(await api.companionAnalyze({ question, image_data_url: shot || undefined, app_hint: appHint, session_id: sessionId || undefined, save_snapshot: saveSnapshot, lang: locale }));
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
    const analyzeTimer = window.setInterval(() => analyzeCurrent().catch(() => undefined), 22000);
    return () => window.clearInterval(analyzeTimer);
  }, [stream, autoAnalyze, busy, question, appHint, sessionId, saveSnapshot]);

  const watching = Boolean(stream);
  return (
    <main className="companion-shell">
      <section className="companion-stage">
        <header className="companion-top">
          <button className="ghost" onClick={() => setLocation("/")}>CircuitSage</button>
          <div>
            <div className="eyebrow"><Bot size={16} /> Companion Mode</div>
            <h1>Put it on, share your lab window, ask anytime.</h1>
          </div>
          <button onClick={() => window.open("/companion", "CircuitSageCompanion", "width=420,height=720")}><ExternalLink size={17} /> Pop Out</button>
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
                <button onClick={() => setLastShot(captureFrame())} disabled={!watching}><Camera size={17} /> Snapshot</button>
              </div>
            </div>
            <div className="screen-preview">
              <video ref={videoRef} muted playsInline />
              {!watching && <div className="screen-empty"><Eye size={28} /> Waiting for screen permission</div>}
            </div>
            <canvas ref={canvasRef} hidden />
          </div>

          <aside className="companion-card">
            <div className="pet-orb"><ScanEye size={34} /></div>
            <h2>CircuitSage Buddy</h2>
            <p className="muted">Watches the shared window while enabled. Works with Tinkercad, LTspice, MATLAB, plots, manuals, and bench screenshots.</p>
            <label><span>Workspace</span><select value={appHint} onChange={(event) => setAppHint(event.target.value)}><option value="auto">Auto detect</option><option value="tinkercad">Tinkercad</option><option value="ltspice">LTspice</option><option value="matlab">MATLAB / Simulink</option><option value="electronics_workspace">General electronics</option></select></label>
            <label><span>Attach to session</span><select value={sessionId} onChange={(event) => setSessionId(event.target.value)}><option value="">No session</option>{sessions.map((session) => <option value={session.id} key={session.id}>{session.title}</option>)}</select></label>
            <label><span>Question</span><textarea value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
            <div className="toggle-row">
              <label><input type="checkbox" checked={autoAnalyze} onChange={(event) => setAutoAnalyze(event.target.checked)} /> Auto analyze</label>
              <label><input type="checkbox" checked={saveSnapshot} onChange={(event) => setSaveSnapshot(event.target.checked)} /> Save snapshots</label>
            </div>
            <button className="primary full" onClick={analyzeCurrent} disabled={busy}><Send size={18} /> Analyze Current Screen</button>
            {error && <p className="error-text">{error}</p>}
          </aside>
        </div>
      </section>
      <section className="companion-output">
        <div className="snapshot-card"><h2>Latest Frame</h2>{lastShot ? <img src={lastShot} alt="Latest captured screen" /> : <p className="muted">No frame captured yet.</p>}</div>
        <CompanionResult analysis={analysis} />
      </section>
    </main>
  );
}

function CompanionResult({ analysis }: { analysis: CompanionAnalysis | null }) {
  if (!analysis) return <section className="analysis-card"><h2>Live Help</h2><p className="muted">Share your screen, open Tinkercad/LTspice/MATLAB, then ask what to check.</p></section>;
  return (
    <section className="analysis-card">
      <div className="card-head"><Bot size={18} /><span>{analysis.mode ?? "analysis"} · {analysis.confidence ?? "unknown"} confidence</span></div>
      <h2>{analysis.workspace}</h2>
      <p>{analysis.visible_context}</p>
      <strong>{analysis.answer}</strong>
      <div className="next-measure"><span>Next actions</span><ul>{(analysis.next_actions ?? []).map((action) => <li key={action}>{action}</li>)}</ul></div>
      {analysis.gemma_error && <small className="error-text">{analysis.gemma_error}</small>}
      {analysis.raw && <pre>{analysis.raw}</pre>}
    </section>
  );
}
