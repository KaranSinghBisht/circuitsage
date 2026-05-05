import { useState } from "react";
import { useLocation } from "wouter";
import { Activity, Bot, ClipboardList, FileUp, Gauge, QrCode, RefreshCw, Stethoscope } from "lucide-react";
import { api } from "../lib/api";
import type { Artifact, Measurement } from "../lib/types";
import { useSession } from "../hooks/useSession";
import { useGemmaHealth } from "../hooks/useGemmaHealth";
import { useI18n } from "../hooks/useI18n";
import { GemmaStatusBanner } from "../components/GemmaStatusBanner";
import { LoadingScreen } from "../components/LoadingScreen";
import { PanelTitle } from "../components/PanelTitle";
import { UploadPanel } from "../components/UploadPanel";
import { EvidenceStrip } from "../components/EvidenceStrip";
import { MeasurementForm } from "../components/MeasurementForm";
import { DiagnosisCard } from "../components/DiagnosisCard";
import { ToolTimeline } from "../components/ToolTimeline";
import { QrPanel } from "../components/QrPanel";
import { SchematicPreview } from "../components/SchematicPreview";
import { WaveformPlot } from "../components/WaveformPlot";
import { FaultRanking } from "../components/FaultRanking";
import { OfflineBadge } from "../components/OfflineBadge";
import { LivePanel } from "../components/LivePanel";

export function Studio({ sessionId }: { sessionId: string }) {
  const [, setLocation] = useLocation();
  const { locale, t } = useI18n();
  const { session, refresh } = useSession(sessionId);
  const modelHealth = useGemmaHealth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(t.defaultDiagnosisPrompt);
  const [qr, setQr] = useState<{ url: string; data_url: string } | null>(null);
  const [recognizedNetlist, setRecognizedNetlist] = useState<{ netlist: string; confidence: number; missing: string[]; detected_topology: string } | null>(null);

  async function runDiagnosis() {
    setBusy(true);
    try {
      await api.diagnose(sessionId, message, locale);
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

  async function recognize(artifact: Artifact) {
    const result = await api.schematicToNetlist(artifact.id);
    setRecognizedNetlist(result);
  }

  async function acceptRecognized() {
    if (!recognizedNetlist?.netlist) return;
    await api.createNetlistArtifact(sessionId, recognizedNetlist.netlist);
    setRecognizedNetlist(null);
    await refresh();
  }

  if (!session) return <LoadingScreen />;
  const diagnosis = session.latest_diagnosis ?? undefined;

  return (
    <main className="studio-shell">
      <header className="topbar">
        <button className="ghost" onClick={() => setLocation("/")}>{t.app}</button>
        <div>
          <h1>{session.title}</h1>
          <span className="status-pill">{session.status}</span>
          <OfflineBadge health={modelHealth} />
        </div>
        <div className="top-actions">
          <button onClick={() => setLocation(`/companion?session=${sessionId}`)}><Bot size={17} /> {t.companion}</button>
          <button onClick={() => setLocation("/faults")}>{t.faults}</button>
          <button onClick={() => setLocation("/educator")}>{t.educator}</button>
          <button onClick={startBench}><QrCode size={17} /> {t.startBench}</button>
          <button onClick={generateReport}><ClipboardList size={17} /> {t.report}</button>
          <a className="button-link" href={api.reportPdfUrl(sessionId)} target="_blank" rel="noreferrer">{t.pdf}</a>
          <button className="icon-button" onClick={refresh} aria-label={t.refresh}><RefreshCw size={17} /></button>
        </div>
      </header>

      <GemmaStatusBanner health={modelHealth} />

      <section className="studio-grid">
        <aside className="panel artifacts-panel">
          <PanelTitle icon={<FileUp size={17} />} title={t.artifacts} detail={t.artifactsDetail} />
          <UploadPanel sessionId={sessionId} onDone={refresh} />
          <ArtifactList artifacts={session.artifacts} onRecognize={recognize} />
          {recognizedNetlist && (
            <div className="schematic-preview">
              <span>{t.recognizedNetlist} · {recognizedNetlist.detected_topology} · {Math.round(recognizedNetlist.confidence * 100)}%</span>
              <pre>{recognizedNetlist.netlist || `${t.need}: ${recognizedNetlist.missing.join(", ")}`}</pre>
              <button onClick={acceptRecognized} disabled={!recognizedNetlist.netlist}>{t.acceptNetlist}</button>
            </div>
          )}
          <SchematicPreview artifacts={session.artifacts} />
        </aside>

        <section className="panel center-panel">
          <PanelTitle icon={<Gauge size={17} />} title={t.sessionContext} detail={t.sessionContextDetail} />
          <EvidenceStrip session={session} diagnosis={diagnosis} />
          <WaveformPlot artifacts={session.artifacts} />
          <MeasurementForm sessionId={sessionId} onDone={refresh} />
          <MeasurementList measurements={session.measurements} />
          <LivePanel sessionId={sessionId} />
          <FaultRanking diagnosis={diagnosis} />
          <ToolTimeline calls={diagnosis?.tool_calls ?? []} />
        </section>

        <aside className="panel agent-panel">
          <PanelTitle icon={<Stethoscope size={17} />} title={t.circuitSageAgent} detail={diagnosis?.gemma_status ?? t.ready} />
          <label><span>{t.prompt}</span><textarea value={message} onChange={(event) => setMessage(event.target.value)} /></label>
          <button className="primary full" onClick={runDiagnosis} disabled={busy}>
            <Activity size={18} />
            {t.runDiagnosis}
          </button>
          <DiagnosisCard diagnosis={diagnosis} />
          {qr && <QrPanel qr={qr} />}
        </aside>
      </section>

      {session.report && (
        <section className="report-band">
          <h2>{t.postLabReflection}</h2>
          <pre>{session.report}</pre>
        </section>
      )}
    </main>
  );
}

function ArtifactList({ artifacts, onRecognize }: { artifacts: Artifact[]; onRecognize: (artifact: Artifact) => void }) {
  const { t } = useI18n();
  return (
    <div className="artifact-list">
      {artifacts.map((artifact) => (
        <div key={artifact.id}>
          <a href={api.artifactUrl(artifact.id)} target="_blank" rel="noreferrer">
            <span>{artifact.kind}</span>
            <strong>{artifact.filename}</strong>
          </a>
          {["image", "breadboard"].includes(artifact.kind) && (
            <button onClick={() => onRecognize(artifact)}>{t.recognizeFromPhoto}</button>
          )}
        </div>
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
