import { useLocation } from "wouter";
import { Camera, Gauge, MessageSquareText, Smartphone } from "lucide-react";
import { useSession } from "../hooks/useSession";
import { LoadingScreen } from "../components/LoadingScreen";
import { PanelTitle } from "../components/PanelTitle";
import { UploadPanel } from "../components/UploadPanel";
import { MeasurementForm } from "../components/MeasurementForm";
import { DiagnosisCard } from "../components/DiagnosisCard";
import { ChatPanel } from "../components/ChatPanel";
import { useI18n } from "../hooks/useI18n";

export function Bench({ sessionId }: { sessionId: string }) {
  const [, setLocation] = useLocation();
  const { t } = useI18n();
  const { session, refresh } = useSession(sessionId, 0);

  if (!session) return <LoadingScreen />;

  return (
    <main className="bench-shell">
      <header className="bench-head">
        <button className="ghost" onClick={() => setLocation(`/studio/${sessionId}`)}>{t.studio}</button>
        <Smartphone size={22} />
        <div>
          <h1>{t.bench}</h1>
          <p>{session.title}</p>
        </div>
      </header>

      <section className="bench-stack">
        <div className="panel">
          <PanelTitle icon={<Camera size={17} />} title={t.captureEvidence} detail={t.captureEvidenceDetail} />
          <UploadPanel sessionId={sessionId} onDone={refresh} compact />
        </div>
        <div className="panel">
          <PanelTitle icon={<Gauge size={17} />} title={t.measurements} detail={t.measurementDetail} />
          <MeasurementForm sessionId={sessionId} onDone={refresh} compact />
        </div>
        <div className="panel">
          <PanelTitle icon={<MessageSquareText size={17} />} title={t.askCircuitSage} detail={t.benchGuidance} />
          <ChatPanel sessionId={sessionId} onDone={refresh} />
        </div>
        <DiagnosisCard diagnosis={session.latest_diagnosis ?? undefined} />
      </section>
    </main>
  );
}
