import type { Diagnosis, LabSession } from "../lib/types";
import { titleize } from "../lib/format";

export function EvidenceStrip({ session, diagnosis }: { session: LabSession; diagnosis?: Diagnosis }) {
  return (
    <div className="evidence-strip">
      <div><span>Experiment</span><strong>{titleize(session.experiment_type)}</strong></div>
      <div><span>Expected gain</span><strong>{diagnosis?.expected_behavior?.gain ?? "-4.7"}</strong></div>
      <div><span>Current issue</span><strong>{diagnosis?.observed_behavior?.summary ?? "Awaiting diagnosis"}</strong></div>
    </div>
  );
}
