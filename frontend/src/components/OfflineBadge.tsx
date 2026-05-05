import { WifiOff } from "lucide-react";
import type { ModelHealth } from "../lib/types";

export function OfflineBadge({ health }: { health: ModelHealth | null }) {
  if (health?.available && health.loaded) return null;
  return (
    <span className="offline-badge">
      <WifiOff size={14} />
      Offline fallback
    </span>
  );
}
