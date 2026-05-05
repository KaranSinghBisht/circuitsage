import type { CompanionAnalysis, LabSession, Measurement, ModelHealth } from "./types";

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
  upload: (sessionId: string, file: File, kind: string) => {
    const body = new FormData();
    body.append("file", file);
    body.append("kind", kind);
    return request(`/api/sessions/${sessionId}/artifacts`, { method: "POST", body });
  },
  addMeasurement: (sessionId: string, payload: Omit<Measurement, "id">) =>
    request<Measurement>(`/api/sessions/${sessionId}/measurements`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  diagnose: (sessionId: string, message?: string) =>
    request(`/api/sessions/${sessionId}/diagnose`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  chat: (sessionId: string, message: string, mode = "bench") =>
    request(`/api/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, mode }),
    }),
  benchStart: (sessionId: string) => request<{ bench_url: string }>(`/api/sessions/${sessionId}/bench/start`, { method: "POST" }),
  benchQr: (sessionId: string) => request<{ url: string; data_url: string }>(`/api/sessions/${sessionId}/bench/qr`),
  report: (sessionId: string) => request<{ markdown: string }>(`/api/sessions/${sessionId}/report`, { method: "POST" }),
  artifactUrl: (artifactId: string) => `${API_BASE}/api/artifacts/${artifactId}/download`,
  companionAnalyze: (payload: {
    question: string;
    image_data_url?: string;
    app_hint: string;
    session_id?: string;
    save_snapshot?: boolean;
  }) =>
    request<CompanionAnalysis>("/api/companion/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
