import { useState } from "react";
import { Loader2, Stethoscope } from "lucide-react";
import { useChat } from "../hooks/useChat";
import { useI18n } from "../hooks/useI18n";

export function ChatPanel({ sessionId, onDone }: { sessionId: string; onDone: () => void }) {
  const [question, setQuestion] = useState("What should I measure next?");
  const { locale } = useI18n();
  const { busy, send } = useChat(sessionId, "bench");
  async function ask() {
    await send(question, locale);
    onDone();
  }
  return (
    <div className="chat-panel">
      <label>
        <span>Question</span>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button className="primary full" onClick={ask} disabled={busy}>
        {busy ? <Loader2 className="spin" size={18} /> : <Stethoscope size={18} />}
        Ask What To Measure Next
      </button>
    </div>
  );
}
