import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { StreamSnapshot } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function LivePanel({ sessionId }: { sessionId: string }) {
  const { t } = useI18n();
  const [snapshot, setSnapshot] = useState<StreamSnapshot | null>(null);
  useEffect(() => {
    const refresh = () => api.streamSnapshot(sessionId).then(setSnapshot).catch(() => undefined);
    refresh();
    const interval = window.setInterval(refresh, 1200);
    return () => window.clearInterval(interval);
  }, [sessionId]);
  const labels = Object.entries(snapshot?.labels ?? {});
  return (
    <div className="live-panel">
      <h3>{t.liveScope}</h3>
      {labels.length === 0 && <p className="muted">{t.noStreamingMeasurements}</p>}
      {labels.map(([label, samples]) => <Sparkline key={label} label={label} samples={samples} />)}
      {(snapshot?.events ?? []).map((event) => <p className="error-text" key={`${event.label}-${event.stddev}`}>{event.message}</p>)}
    </div>
  );
}

function Sparkline({ label, samples }: { label: string; samples: Array<{ value: number; unit: string }> }) {
  const values = samples.slice(-80).map((sample) => sample.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = max - min || 1;
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 220},${48 - ((value - min) / span) * 42}`).join(" ");
  return (
    <div className="sparkline">
      <span>{label}</span>
      <svg viewBox="0 0 220 54" role="img" aria-label={`${label} live sparkline`}>
        <polyline points={points} />
      </svg>
    </div>
  );
}
