import { useState } from "react";
import { FileUp } from "lucide-react";
import { api } from "../lib/api";

export function UploadPanel({ sessionId, onDone, compact = false }: { sessionId: string; onDone: () => void; compact?: boolean }) {
  const [kind, setKind] = useState("image");
  async function upload(file: File | null) {
    if (!file) return;
    await api.upload(sessionId, file, kind);
    onDone();
  }
  return (
    <div className={compact ? "upload compact" : "upload"}>
      <label>
        <span>Artifact kind</span>
        <select value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="image">Image</option>
          <option value="breadboard">Breadboard</option>
          <option value="oscilloscope">Oscilloscope</option>
          <option value="manual">Manual</option>
          <option value="netlist">Netlist</option>
          <option value="waveform_csv">Waveform CSV</option>
          <option value="audio">Audio</option>
          <option value="matlab">MATLAB Script</option>
          <option value="tinkercad_code">Arduino Sketch</option>
          <option value="note">Note</option>
        </select>
      </label>
      <label className="file-input">
        <FileUp size={18} />
        <span>Upload</span>
        <input type="file" accept={kind === "image" ? "image/*" : undefined} capture={kind === "image" ? "environment" : undefined} onChange={(event) => upload(event.target.files?.[0] ?? null)} />
      </label>
    </div>
  );
}
