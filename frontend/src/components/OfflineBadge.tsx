import { WifiOff } from "lucide-react";
import type { ModelHealth } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function OfflineBadge({ health }: { health: ModelHealth | null }) {
  const { t } = useI18n();
  if (health?.available && health.loaded) return null;
  return (
    <span className="offline-badge">
      <WifiOff size={14} />
      {t.offlineFallback}
    </span>
  );
}
