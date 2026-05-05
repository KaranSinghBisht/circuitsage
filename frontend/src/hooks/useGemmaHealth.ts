import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ModelHealth } from "../lib/types";

export function useGemmaHealth() {
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  useEffect(() => {
    const refreshModel = () => api.modelHealth().then(setModelHealth).catch(() => {
      setModelHealth({ available: false, model: "gemma4:e4b", loaded: false, models: [], hint: "Run: ollama pull gemma4:e4b" });
    });
    refreshModel();
    const interval = window.setInterval(refreshModel, 10000);
    return () => window.clearInterval(interval);
  }, []);
  return modelHealth;
}
