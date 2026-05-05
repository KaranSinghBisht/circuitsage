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

export function gemmaRuntimeKind(status?: string, safetyRisk?: string) {
  if (status === "blocked_by_safety" || safetyRisk === "high_voltage_or_mains") return "safety_refusal";
  if (status === "ollama_gemma_agentic") return "agentic";
  if (status === "ollama_gemma_single_shot") return "single_shot";
  return "deterministic";
}

export function GemmaStatusChip({ status, safetyRisk, busy = false }: { status?: string; safetyRisk?: string; busy?: boolean }) {
  const kind = gemmaRuntimeKind(status, safetyRisk);
  return <span className={`gemma-runtime-chip ${kind}${busy ? " pulse" : ""}`}>{kind}</span>;
}
