import { AlertTriangle } from "lucide-react";
import type { ModelHealth } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function GemmaStatusBanner({ health }: { health: ModelHealth | null }) {
  const { t } = useI18n();
  if (!health || (health.available && health.loaded)) return null;
  return (
    <div className="gemma-banner" role="status" aria-live="polite">
      <AlertTriangle size={17} />
      <span>{t.gemmaNotLoaded} {health.model || "gemma4:e4b"}</span>
    </div>
  );
}
