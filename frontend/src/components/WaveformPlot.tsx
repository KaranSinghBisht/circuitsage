import type { Artifact } from "../lib/types";
import { useI18n } from "../hooks/useI18n";

export function WaveformPlot({ artifacts }: { artifacts: Artifact[] }) {
  const { t } = useI18n();
  const count = artifacts.filter((artifact) => artifact.kind === "waveform_csv").length;
  return (
    <div className="waveform-plot" role="img" aria-label={`${count} ${t.waveformArtifactsAvailable}`}>
      <svg viewBox="0 0 240 72" aria-hidden="true">
        <path d="M0 36 C20 8 40 8 60 36 S100 64 120 36 160 8 180 36 220 64 240 36" />
      </svg>
      <span>{count ? `${count} ${t.waveformCsvFiles}` : t.noWaveformCsv}</span>
    </div>
  );
}
