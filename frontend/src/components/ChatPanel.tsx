import { useState } from "react";
import { Loader2, Stethoscope } from "lucide-react";
import { useChat } from "../hooks/useChat";
import { useI18n } from "../hooks/useI18n";

export function ChatPanel({ sessionId, onDone }: { sessionId: string; onDone: () => void }) {
  const { locale, t } = useI18n();
  const [question, setQuestion] = useState(t.defaultBenchQuestion);
  const { busy, send } = useChat(sessionId, "bench");
  async function ask() {
    await send(question, locale);
    onDone();
  }
  return (
    <div className="chat-panel">
      <label>
        <span>{t.question}</span>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button className="primary full" onClick={ask} disabled={busy}>
        {busy ? <Loader2 className="spin" size={18} /> : <Stethoscope size={18} />}
        {t.askNextMeasurement}
      </button>
    </div>
  );
}
