import { useLocation } from "wouter";
import { Camera, Gauge, MessageSquareText, Smartphone } from "lucide-react";
import { useSession } from "../hooks/useSession";
import { LoadingScreen } from "../components/LoadingScreen";
import { PanelTitle } from "../components/PanelTitle";
import { UploadPanel } from "../components/UploadPanel";
import { MeasurementForm } from "../components/MeasurementForm";
import { DiagnosisCard } from "../components/DiagnosisCard";
import { ChatPanel } from "../components/ChatPanel";

export function Bench({ sessionId }: { sessionId: string }) {
  const [, setLocation] = useLocation();
  const { session, refresh } = useSession(sessionId, 0);

  if (!session) return <LoadingScreen />;

  return (
    <main className="bench-shell">
      <header className="bench-head">
        <button className="ghost" onClick={() => setLocation(`/studio/${sessionId}`)}>Studio</button>
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
          <MeasurementForm sessionId={sessionId} onDone={refresh} compact />
        </div>
        <div className="panel">
          <PanelTitle icon={<MessageSquareText size={17} />} title="Ask CircuitSage" detail="short bench guidance" />
          <ChatPanel sessionId={sessionId} onDone={refresh} />
        </div>
        <DiagnosisCard diagnosis={session.latest_diagnosis ?? undefined} />
      </section>
    </main>
  );
}
