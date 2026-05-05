import { useState } from "react";
import { FileUp } from "lucide-react";
import { api } from "../lib/api";
import { useI18n } from "../hooks/useI18n";

export function UploadPanel({ sessionId, onDone, compact = false }: { sessionId: string; onDone: () => void; compact?: boolean }) {
  const { t } = useI18n();
  const [kind, setKind] = useState("image");
  async function upload(file: File | null) {
    if (!file) return;
    await api.upload(sessionId, file, kind);
    onDone();
  }
  return (
    <div className={compact ? "upload compact" : "upload"}>
      <label>
        <span>{t.artifactKind}</span>
        <select value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="image">{t.image}</option>
          <option value="breadboard">{t.breadboard}</option>
          <option value="oscilloscope">{t.oscilloscope}</option>
          <option value="manual">{t.manual}</option>
          <option value="netlist">{t.netlist}</option>
          <option value="waveform_csv">{t.waveformCsv}</option>
          <option value="audio">{t.audio}</option>
          <option value="matlab">{t.matlabScript}</option>
          <option value="tinkercad_code">{t.arduinoSketch}</option>
          <option value="note">{t.note}</option>
        </select>
      </label>
      <label className="file-input">
        <FileUp size={18} />
        <span>{t.upload}</span>
        <input type="file" accept={kind === "image" ? "image/*" : undefined} capture={kind === "image" ? "environment" : undefined} onChange={(event) => upload(event.target.files?.[0] ?? null)} />
      </label>
    </div>
  );
}
