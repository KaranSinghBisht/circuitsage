import { pct } from "../lib/format";
import type { Diagnosis } from "../lib/types";

export function FaultRanking({ diagnosis }: { diagnosis?: Diagnosis }) {
  const faults = diagnosis?.likely_faults ?? [];
  return (
    <div className="fault-ranking">
      {faults.slice(0, 4).map((fault) => (
        <div key={fault.fault}>
          <span>{fault.fault}</span>
          <strong>{pct(fault.confidence)}</strong>
          <div className="confidence-track"><i style={{ width: pct(fault.confidence) }} /></div>
        </div>
      ))}
    </div>
  );
}
