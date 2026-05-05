import { useEffect, useState } from "react";
import { Loader2, Stethoscope } from "lucide-react";
import { useChat } from "../hooks/useChat";
import { useI18n } from "../hooks/useI18n";
import { GemmaStatusChip } from "./GemmaStatusBanner";

type ChatResponse = {
  diagnosis?: {
    gemma_status?: string;
    safety?: { risk_level?: string };
  };
};

export function ChatPanel({
  sessionId,
  onDone,
  gemmaStatus,
  safetyRisk,
}: {
  sessionId: string;
  onDone: () => void;
  gemmaStatus?: string;
  safetyRisk?: string;
}) {
  const { locale, t } = useI18n();
  const [question, setQuestion] = useState(t.defaultBenchQuestion);
  const [liveStatus, setLiveStatus] = useState(gemmaStatus);
  const [liveSafetyRisk, setLiveSafetyRisk] = useState(safetyRisk);
  const { busy, send } = useChat(sessionId, "bench");
  useEffect(() => {
    setLiveStatus(gemmaStatus);
    setLiveSafetyRisk(safetyRisk);
  }, [gemmaStatus, safetyRisk]);
  async function ask() {
    const result = await send(question, locale) as ChatResponse;
    setLiveStatus(result.diagnosis?.gemma_status);
    setLiveSafetyRisk(result.diagnosis?.safety?.risk_level);
    onDone();
  }
  return (
    <div className="chat-panel">
      <label>
        <div className="chat-status-row">
          <span>{t.question}</span>
          <GemmaStatusChip status={liveStatus} safetyRisk={liveSafetyRisk} busy={busy} />
        </div>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button className="primary full" onClick={ask} disabled={busy}>
        {busy ? <Loader2 className="spin" size={18} /> : <Stethoscope size={18} />}
        {t.askNextMeasurement}
      </button>
    </div>
  );
}
