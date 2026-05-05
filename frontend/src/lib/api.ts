import type { CompanionAnalysis, LabSession, Measurement, ModelHealth, StreamSnapshot } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  modelHealth: () => request<ModelHealth>("/api/health/model"),
  sessions: () => request<LabSession[]>("/api/sessions"),
  session: (id: string) => request<LabSession>(`/api/sessions/${id}`),
  create: (title: string) =>
    request<LabSession>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ title, student_level: "2nd/3rd year EEE", notes: "" }),
    }),
  seedDemo: (slug = "op-amp") => request<LabSession>(`/api/sessions/seed/${slug}`, { method: "POST" }),
  seedFault: (topology: string, faultId: string) =>
    request<LabSession>(`/api/sessions/seed/fault/${topology}/${faultId}`, { method: "POST" }),
  upload: (sessionId: string, file: File, kind: string) => {
    const body = new FormData();
    body.append("file", file);
    body.append("kind", kind);
    return request(`/api/sessions/${sessionId}/artifacts`, { method: "POST", body });
  },
  createNetlistArtifact: (sessionId: string, netlist: string) =>
    request(`/api/sessions/${sessionId}/artifacts/netlist`, {
      method: "POST",
      body: JSON.stringify({ netlist }),
    }),
  schematicToNetlist: (artifactId: string) => {
    const body = new FormData();
    body.append("artifact_id", artifactId);
    return request<{
      netlist: string;
      confidence: number;
      missing: string[];
      needed: string[];
      detected_topology: string;
      mode: string;
      error?: string;
    }>("/api/tools/schematic-to-netlist", { method: "POST", body });
  },
  addMeasurement: (sessionId: string, payload: Omit<Measurement, "id">) =>
    request<Measurement>(`/api/sessions/${sessionId}/measurements`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  streamSnapshot: (sessionId: string) => request<StreamSnapshot>(`/api/sessions/${sessionId}/measurements/stream`),
  streamMeasurement: (sessionId: string, payload: { label: string; value: number; unit?: string; ts?: number }) =>
    request(`/api/sessions/${sessionId}/measurements/stream`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  diagnose: (sessionId: string, message?: string, lang = "en") =>
    request(`/api/sessions/${sessionId}/diagnose`, {
      method: "POST",
      body: JSON.stringify({ message, lang }),
    }),
  chat: (sessionId: string, message: string, mode = "bench", lang = "en") =>
    request(`/api/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, mode, lang }),
    }),
  benchStart: (sessionId: string) => request<{ bench_url: string }>(`/api/sessions/${sessionId}/bench/start`, { method: "POST" }),
  benchQr: (sessionId: string) => request<{ url: string; data_url: string }>(`/api/sessions/${sessionId}/bench/qr`),
  report: (sessionId: string) => request<{ markdown: string }>(`/api/sessions/${sessionId}/report`, { method: "POST" }),
  reportPdfUrl: (sessionId: string) => `${API_BASE}/api/sessions/${sessionId}/report.pdf`,
  artifactUrl: (artifactId: string) => `${API_BASE}/api/artifacts/${artifactId}/download`,
  faults: () => request<Array<{
    topology: string;
    id: string;
    name: string;
    why: string;
    requires_measurements: string[];
    verification_test: string;
    fix_recipe: string;
  }>>("/api/faults"),
  educatorOverview: () => request<{
    total_sessions: number;
    average_time_to_resolution_s: number | null;
    safety_refusals: number;
    unfinished_sessions: number;
    common_faults: Array<{ topology: string; fault: string; count: number }>;
    stalled_measurements: Array<{ label: string; count: number }>;
  }>("/api/educator/overview"),
  datasheetUrl: (part: string) => `${API_BASE}/api/datasheets/${encodeURIComponent(part)}`,
  companionAnalyze: (payload: {
    question: string;
    image_data_url?: string;
    app_hint: string;
    session_id?: string;
    save_snapshot?: boolean;
    lang?: string;
  }) =>
    request<CompanionAnalysis>("/api/companion/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
