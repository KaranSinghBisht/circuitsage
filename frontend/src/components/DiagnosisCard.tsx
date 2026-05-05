import { useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Diagnosis } from "../lib/types";
import { playChime } from "../lib/sounds";
import { useI18n } from "../hooks/useI18n";

export function DiagnosisCard({ diagnosis }: { diagnosis?: Diagnosis }) {
  const { t } = useI18n();
  useEffect(() => {
    if (diagnosis) playChime();
  }, [diagnosis?.student_explanation]);

  if (!diagnosis) {
    return (
      <section className="diagnosis-card empty">
        <AlertTriangle size={18} />
        <p>{t.diagnosisEmpty}</p>
      </section>
    );
  }
  const topFault = diagnosis.likely_faults?.[0];
  const status = diagnosis.gemma_status ?? "deterministic_fallback";
  return (
    <motion.section
      className="diagnosis-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
    >
      <div className="card-head">
        <CheckCircle2 size={18} />
        <span>{diagnosis.confidence ?? "medium"} {t.confidence}</span>
        <GemmaStatusChip status={status} />
      </div>
      <h2>{topFault?.fault ?? t.needMoreEvidence}</h2>
      <p>{diagnosis.student_explanation}</p>
      {topFault && <ConfidenceBar confidence={topFault.confidence} />}
      <motion.div className="next-measure" animate={{ scale: [1, 1.02, 1] }} transition={{ duration: 0.7 }}>
        <span>{t.nextMeasurement}</span>
        <strong>{diagnosis.next_measurement?.label}</strong>
        <small>{diagnosis.next_measurement?.instruction}</small>
      </motion.div>
      <ul>
        {(diagnosis.safety?.warnings ?? []).slice(0, 2).map((warning) => <li key={warning}>{warning}</li>)}
      </ul>
    </motion.section>
  );
}

export function GemmaStatusChip({ status }: { status: string }) {
  const tone = status.startsWith("ollama_gemma")
    ? "green"
    : status.startsWith("blocked_by_safety")
      ? "red"
      : "amber";
  const label = status.startsWith("deterministic_fallback") ? "deterministic_fallback" : status;
  return <span className={`gemma-chip ${tone}`}>{label}</span>;
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  return (
    <div className="confidence-track" aria-label={`Fault confidence ${Math.round(confidence * 100)} percent`}>
      <motion.i initial={{ width: 0 }} animate={{ width: `${Math.round(confidence * 100)}%` }} transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }} />
    </div>
  );
}
