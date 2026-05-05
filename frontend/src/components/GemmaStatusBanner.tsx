import { AlertTriangle } from "lucide-react";
import type { ModelHealth } from "../lib/types";

export function GemmaStatusBanner({ health }: { health: ModelHealth | null }) {
  if (!health || (health.available && health.loaded)) return null;
  return (
    <div className="gemma-banner" role="status" aria-live="polite">
      <AlertTriangle size={17} />
      <span>Gemma not loaded &mdash; running in deterministic mode. Run: ollama pull {health.model || "gemma4:e4b"}</span>
    </div>
  );
}
