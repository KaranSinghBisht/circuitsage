import { useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";
import { Bot, Camera, ExternalLink, Eye, EyeOff, MonitorUp, Play, ScanEye, Send } from "lucide-react";
import { api } from "../lib/api";
import type { CompanionAnalysis, CompanionTypedAction, LabSession } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function Companion() {
  const [, setLocation] = useLocation();
  const { locale, t } = useI18n();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [lastShot, setLastShot] = useState("");
  const [question, setQuestion] = useState(t.companionDefaultQuestion);
  const [appHint, setAppHint] = useState("auto");
  const [sessionId, setSessionId] = useState(new URLSearchParams(window.location.search).get("session") ?? "");
  const [saveSnapshot, setSaveSnapshot] = useState(false);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [analysis, setAnalysis] = useState<CompanionAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [actionResults, setActionResults] = useState<Record<string, unknown>>({});
  const [actionBusy, setActionBusy] = useState<string | null>(null);

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
      setError(exc instanceof Error ? exc.message : t.screenCaptureDenied);
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
    setActionResults({});
    try {
      const shot = captureFrame() || lastShot;
      if (shot) setLastShot(shot);
      const next = await api.companionAnalyze({
        question,
        image_data_url: shot || undefined,
        app_hint: appHint,
        session_id: sessionId || undefined,
        save_snapshot: saveSnapshot,
        lang: locale,
      });
      setAnalysis(next);
      if (next.session_id && next.session_id !== sessionId) setSessionId(next.session_id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : t.companionAnalysisFailed);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(action: CompanionTypedAction, idx: number) {
    // Key by index so two actions with identical labels don't overwrite
    // each other in actionResults.
    const key = `${idx}::${action.label}`;
    if (action.action === "capture") {
      analyzeCurrent().catch(() => undefined);
      return;
    }
    if (action.action === "measurement") {
      setActionResults((prior) => ({
        ...prior,
        [key]: { hint: "Open Bench Mode to enter this measurement, then re-ask.", args: action.args },
      }));
      return;
    }
    const toolName = (action.args?.tool as string) || "";
    if (!toolName || !["score_faults", "lookup_datasheet", "retrieve_rag"].includes(toolName)) {
      setActionResults((prior) => ({ ...prior, [key]: { error: "Unknown tool" } }));
      return;
    }
    const { tool: _ignored, already_ran: _ran, ...args } = action.args as Record<string, unknown>;
    setActionBusy(key);
    try {
      const response = await api.companionRunTool({
        tool: toolName as "score_faults" | "lookup_datasheet" | "retrieve_rag",
        args,
        session_id: analysis?.session_id || sessionId || undefined,
      });
      setActionResults((prior) => ({ ...prior, [key]: response.result }));
    } catch (exc) {
      setActionResults((prior) => ({
        ...prior,
        [key]: { error: exc instanceof Error ? exc.message : "tool failed" },
      }));
    } finally {
      setActionBusy(null);
    }
  }

  // Hold the latest analyzeCurrent in a ref so the auto-analyze interval
  // doesn't restart every keystroke (which would never let it fire steady).
  const analyzeCurrentRef = useRef(analyzeCurrent);
  useEffect(() => {
    analyzeCurrentRef.current = analyzeCurrent;
  });

  useEffect(() => {
    if (!stream) return undefined;
    const frameTimer = window.setInterval(() => {
      const shot = captureFrame();
      if (shot) setLastShot(shot);
    }, 3500);
    return () => window.clearInterval(frameTimer);
  }, [stream]);

  useEffect(() => {
    if (!stream || !autoAnalyze) return undefined;
    const analyzeTimer = window.setInterval(() => {
      // Read the latest analyzeCurrent through the ref so the timer keeps
      // firing on a stable schedule even as inputs change.
      analyzeCurrentRef.current().catch(() => undefined);
    }, 22000);
    return () => window.clearInterval(analyzeTimer);
  }, [stream, autoAnalyze]);

  const watching = Boolean(stream);
  return (
    <main className="companion-shell">
      <section className="companion-stage">
        <header className="companion-top">
          <button className="ghost" onClick={() => setLocation("/")}>{t.app}</button>
          <div>
            <div className="eyebrow"><Bot size={16} /> {t.companion}</div>
            <h1>{t.companionHero}</h1>
          </div>
          <button onClick={() => window.open("/companion", "CircuitSageCompanion", "width=420,height=720")}><ExternalLink size={17} /> {t.popOut}</button>
        </header>

        <div className="companion-grid">
          <div className="screen-panel">
            <div className="screen-toolbar">
              <span className={watching ? "live-dot on" : "live-dot"}>{watching ? "watching" : "off"}</span>
              <div>
                <button className={watching ? "" : "primary"} onClick={watching ? stopWatching : startWatching}>
                  {watching ? <EyeOff size={17} /> : <MonitorUp size={17} />}
                  {watching ? t.stop : t.shareScreen}
                </button>
                <button onClick={() => setLastShot(captureFrame())} disabled={!watching}><Camera size={17} /> {t.snapshot}</button>
              </div>
            </div>
            <div className="screen-preview">
              <video ref={videoRef} muted playsInline />
              {!watching && <div className="screen-empty"><Eye size={28} /> {t.waitingForScreenPermission}</div>}
            </div>
            <canvas ref={canvasRef} hidden />
          </div>

          <aside className="companion-card">
            <div className="pet-orb"><ScanEye size={34} /></div>
            <h2>{t.circuitSageBuddy}</h2>
            <p className="muted">{t.companionDescription}</p>
            <label><span>{t.workspace}</span><select value={appHint} onChange={(event) => setAppHint(event.target.value)}><option value="auto">{t.autoDetect}</option><option value="tinkercad">Tinkercad</option><option value="ltspice">LTspice</option><option value="matlab">MATLAB / Simulink</option><option value="electronics_workspace">{t.generalElectronics}</option></select></label>
            <label><span>{t.attachToSession}</span><select value={sessionId} onChange={(event) => setSessionId(event.target.value)}><option value="">{t.noSession}</option>{sessions.map((session) => <option value={session.id} key={session.id}>{session.title}</option>)}</select></label>
            <label><span>{t.question}</span><textarea value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
            <div className="toggle-row">
              <label><input type="checkbox" checked={autoAnalyze} onChange={(event) => setAutoAnalyze(event.target.checked)} /> {t.autoAnalyze}</label>
              <label><input type="checkbox" checked={saveSnapshot} onChange={(event) => setSaveSnapshot(event.target.checked)} /> {t.saveSnapshots}</label>
            </div>
            <button className="primary full" onClick={analyzeCurrent} disabled={busy}><Send size={18} /> {t.analyzeCurrentScreen}</button>
            {error && <p className="error-text">{error}</p>}
          </aside>
        </div>
      </section>
      <section className="companion-output">
        <div className="snapshot-card"><h2>{t.latestFrame}</h2>{lastShot ? <img src={lastShot} alt={t.latestCapturedScreen} /> : <p className="muted">{t.noFrameCaptured}</p>}</div>
        <CompanionResult
          analysis={analysis}
          onAction={runAction}
          actionResults={actionResults}
          actionBusy={actionBusy}
        />
      </section>
    </main>
  );
}

function CompanionResult({
  analysis,
  onAction,
  actionResults,
  actionBusy,
}: {
  analysis: CompanionAnalysis | null;
  onAction: (action: CompanionTypedAction, idx: number) => void;
  actionResults: Record<string, unknown>;
  actionBusy: string | null;
}) {
  const { t } = useI18n();
  if (!analysis) return <section className="analysis-card"><h2>{t.liveHelp}</h2><p className="muted">{t.companionEmptyHelp}</p></section>;
  const typedActions = analysis.actions ?? [];
  return (
    <section className="analysis-card">
      <div className="card-head">
        <Bot size={18} />
        <span>{analysis.mode ?? "analysis"} · {analysis.confidence ?? "unknown"} {t.confidence}{analysis.duration_ms ? ` · ${analysis.duration_ms} ms` : ""}</span>
      </div>
      <h2>{analysis.workspace}{analysis.detected_topology && analysis.detected_topology !== "unknown" ? ` · ${analysis.detected_topology}` : ""}</h2>
      <p>{analysis.visible_context}</p>
      <strong>{analysis.answer}</strong>
      {analysis.suspected_faults && analysis.suspected_faults.length > 0 && (
        <ul className="suspected-faults">
          {analysis.suspected_faults.map((fault, i) => <li key={`${i}-${fault}`}>{fault}</li>)}
        </ul>
      )}
      {typedActions.length > 0 && (
        <div className="action-buttons">
          <span>{t.nextActions}</span>
          <div className="action-row">
            {typedActions.map((action, idx) => {
              const key = `${idx}::${action.label}`;
              return (
                <button
                  key={key}
                  className="action-chip"
                  onClick={() => onAction(action, idx)}
                  disabled={actionBusy === key}
                >
                  <Play size={14} /> {actionBusy === key ? "…" : action.label}
                </button>
              );
            })}
          </div>
          {Object.entries(actionResults).map(([key, value]) => {
            const displayLabel = key.includes("::") ? key.split("::").slice(1).join("::") : key;
            return (
              <pre key={key} className="action-result"><strong>{displayLabel}</strong>{"\n"}{JSON.stringify(value, null, 2).slice(0, 1200)}</pre>
            );
          })}
        </div>
      )}
      {typedActions.length === 0 && (
        <div className="next-measure">
          <span>{t.nextActions}</span>
          <ul>{(analysis.next_actions ?? []).map((action) => <li key={action}>{action}</li>)}</ul>
        </div>
      )}
      {analysis.gemma_error && <small className="error-text">{analysis.gemma_error}</small>}
      {analysis.raw && <pre>{analysis.raw}</pre>}
    </section>
  );
}
