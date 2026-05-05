import { useState } from "react";
import { api } from "../lib/api";

export function useChat(sessionId: string, mode = "bench") {
  const [busy, setBusy] = useState(false);
  async function send(message: string, lang = "en") {
    setBusy(true);
    try {
      return await api.chat(sessionId, message, mode, lang);
    } finally {
      setBusy(false);
    }
  }
  return { busy, send };
}
