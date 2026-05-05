import React, { useState } from "react";
import { Plus } from "lucide-react";
import { api } from "../lib/api";

export function MeasurementForm({ sessionId, onDone, compact = false }: { sessionId: string; onDone: () => void; compact?: boolean }) {
  const [form, setForm] = useState({ label: "V_noninv", value: "2.8", unit: "V", mode: "DC", context: "Non-inverting input floating", source: "manual_entry" });
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    await api.addMeasurement(sessionId, { ...form, value: Number(form.value) });
    onDone();
  }
  return (
    <form className={compact ? "measurement-form compact" : "measurement-form"} onSubmit={submit}>
      <label><span>Node</span><input value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} /></label>
      <label><span>Value</span><input value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} inputMode="decimal" /></label>
      <label><span>Unit</span><input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></label>
      <label>
        <span>Mode</span>
        <select value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
          <option>DC</option>
          <option>AC</option>
          <option>peak</option>
          <option>peak-to-peak</option>
        </select>
      </label>
      <label className="wide"><span>Context</span><input value={form.context} onChange={(event) => setForm({ ...form, context: event.target.value })} /></label>
      <button><Plus size={17} /> Add</button>
    </form>
  );
}
