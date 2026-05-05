import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { LabSession } from "../lib/types";

export function useSession(sessionId: string, pollMs = 3500) {
  const [session, setSession] = useState<LabSession | null>(null);
  const refresh = async () => setSession(await api.session(sessionId));
  useEffect(() => {
    refresh().catch(console.error);
    if (!pollMs) return undefined;
    const interval = window.setInterval(() => refresh().catch(() => undefined), pollMs);
    return () => window.clearInterval(interval);
  }, [sessionId, pollMs]);
  return { session, refresh };
}
