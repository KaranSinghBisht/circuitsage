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

export function Studio({ sessionId }: { sessionId: string }) {
  const [, setLocation] = useLocation();
  const { locale } = useI18n();
  const { session, refresh } = useSession(sessionId);
  const modelHealth = useGemmaHealth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("My output is stuck near +12V. What should I check first?");
  const [qr, setQr] = useState<{ url: string; data_url: string } | null>(null);

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

  if (!session) return <LoadingScreen />;
  const diagnosis = session.latest_diagnosis ?? undefined;

  return (
    <main className="studio-shell">
      <header className="topbar">
        <button className="ghost" onClick={() => setLocation("/")}>CircuitSage</button>
        <div>
          <h1>{session.title}</h1>
          <span className="status-pill">{session.status}</span>
          <OfflineBadge health={modelHealth} />
        </div>
        <div className="top-actions">
          <button onClick={() => setLocation(`/companion?session=${sessionId}`)}><Bot size={17} /> Companion</button>
          <button onClick={() => setLocation("/faults")}>Faults</button>
          <button onClick={() => setLocation("/educator")}>Educator</button>
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
          <SchematicPreview artifacts={session.artifacts} />
        </aside>

        <section className="panel center-panel">
          <PanelTitle icon={<Gauge size={17} />} title="Session Context" detail="simulation vs bench evidence" />
          <EvidenceStrip session={session} diagnosis={diagnosis} />
          <WaveformPlot artifacts={session.artifacts} />
          <MeasurementForm sessionId={sessionId} onDone={refresh} />
          <MeasurementList measurements={session.measurements} />
          <FaultRanking diagnosis={diagnosis} />
          <ToolTimeline calls={diagnosis?.tool_calls ?? []} />
        </section>

        <aside className="panel agent-panel">
          <PanelTitle icon={<Stethoscope size={17} />} title="CircuitSage Agent" detail={diagnosis?.gemma_status ?? "ready"} />
          <label><span>Prompt</span><textarea value={message} onChange={(event) => setMessage(event.target.value)} /></label>
          <button className="primary full" onClick={runDiagnosis} disabled={busy}>
            <Activity size={18} />
            Run Diagnosis
          </button>
          <DiagnosisCard diagnosis={diagnosis} />
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
