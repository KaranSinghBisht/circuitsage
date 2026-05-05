import type { Diagnosis, LabSession } from "../lib/types";
import { titleize } from "../lib/format";
import { useI18n } from "../hooks/useI18n";

export function EvidenceStrip({ session, diagnosis }: { session: LabSession; diagnosis?: Diagnosis }) {
  const { t } = useI18n();
  return (
    <div className="evidence-strip">
      <div><span>{t.experiment}</span><strong>{titleize(session.experiment_type)}</strong></div>
      <div><span>{t.expectedGain}</span><strong>{diagnosis?.expected_behavior?.gain ?? "-4.7"}</strong></div>
      <div><span>{t.currentIssue}</span><strong>{diagnosis?.observed_behavior?.summary ?? t.awaitingDiagnosis}</strong></div>
    </div>
  );
}
