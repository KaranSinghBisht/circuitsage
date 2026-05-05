import type { OnDeviceEngine, OnDeviceInput, OnDeviceProvider, StructuredDiagnosis } from "./types";

const CACTUS_MODEL = "gemma-4-E2B-it";
const MEDIAPIPE_MODEL = "gemma-4-E2B-it.task";
const MAX_TOKENS = 768;

function extractJson(text: string): StructuredDiagnosis | null {
  const trimmed = text.trim();
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const parsed = JSON.parse(trimmed.slice(start, end + 1));
    if (!parsed || !Array.isArray(parsed.likely_faults) || !parsed.next_measurement) return null;
    return {
      experiment_type: parsed.experiment_type ?? "unknown",
      expected_behavior: parsed.expected_behavior ?? {},
      observed_behavior: parsed.observed_behavior ?? { summary: "On-device model response", evidence: [] },
      likely_faults: parsed.likely_faults,
      next_measurement: parsed.next_measurement,
      safety: parsed.safety ?? { risk_level: "low_voltage_lab", warnings: [] },
      student_explanation: parsed.student_explanation ?? "The local model returned a structured diagnosis.",
      confidence: parsed.confidence ?? "medium",
      gemma_status: "on_device_gemma",
      gemma_model: CACTUS_MODEL,
    };
  } catch {
    return null;
  }
}

function promptFor(input: OnDeviceInput): string {
  const measurements = input.measurements.length
    ? input.measurements.map((m) => `${m.label}=${m.value} ${m.unit} ${m.mode ?? ""}`).join("; ")
    : "none";
  return `You are CircuitSage running fully offline on an iPhone.

Question:
${input.question}

Measurements:
${measurements}

Return only compact JSON with exactly these keys:
experiment_type, expected_behavior, observed_behavior, likely_faults, next_measurement, safety, student_explanation, confidence.

Rules:
- Low-voltage educational circuits only.
- If evidence is incomplete, set confidence to low and ask for one concrete next measurement.
- likely_faults must be an array with id, fault, confidence, why.
- next_measurement must have label, expected, instruction.`;
}

async function structurize(generate: (prompt: string) => Promise<string>, raw: string, input: OnDeviceInput) {
  const prompt = `${promptFor(input)}

The previous local-model answer was not valid JSON. Convert it to the required schema.

Previous answer:
${raw}`;
  const second = await generate(prompt);
  const parsed = extractJson(second);
  if (!parsed) throw new Error("on_device_json_parse_failed");
  return parsed;
}

export class CactusEngine implements OnDeviceEngine {
  private lm: any | null = null;

  async ready(): Promise<boolean> {
    try {
      await this.ensureLoaded();
      return true;
    } catch {
      return false;
    }
  }

  async modelInfo() {
    return { name: CACTUS_MODEL, quant: "int4", sizeMB: 0 };
  }

  async diagnose(input: OnDeviceInput): Promise<StructuredDiagnosis> {
    await this.ensureLoaded();
    const generate = async (content: string) => {
      const result = await this.lm.complete({
        messages: [
          { role: "system", content: "Return only the final JSON. Do not include markdown." },
          { role: "user", content, images: input.image_b64 ? [input.image_b64] : undefined },
        ],
        options: { maxTokens: MAX_TOKENS, temperature: 0.2, topK: 40, enableThinking: false },
      });
      if (!result?.success) throw new Error(result?.error ?? "cactus_generation_failed");
      return result.response ?? "";
    };
    const raw = await generate(promptFor(input));
    const parsed = extractJson(raw);
    return parsed ?? structurize(generate, raw, input);
  }

  cancel() {
    void this.lm?.stop?.();
  }

  private async ensureLoaded() {
    if (this.lm) return;
    const { CactusLM } = await import("cactus-react-native");
    this.lm = new CactusLM({ model: CACTUS_MODEL, options: { quantization: "int4" } });
    await this.lm.init();
  }
}

export class MediaPipeEngine implements OnDeviceEngine {
  private handle: number | null = null;
  private module: any | null = null;

  async ready(): Promise<boolean> {
    try {
      const module = await this.getModule();
      const models = (await module.getDownloadedModels?.()) ?? [];
      return models.includes(MEDIAPIPE_MODEL);
    } catch {
      return false;
    }
  }

  async modelInfo() {
    return { name: MEDIAPIPE_MODEL, quant: "int4/task", sizeMB: 0 };
  }

  async diagnose(input: OnDeviceInput): Promise<StructuredDiagnosis> {
    const module = await this.getModule();
    if (this.handle === null) {
      this.handle = await module.createModelFromDownloaded(MEDIAPIPE_MODEL, MAX_TOKENS, 40, 0.2, 7);
    }
    const generate = async (content: string) => module.generateResponse(this.handle, Date.now(), content);
    const raw = await generate(promptFor(input));
    const parsed = extractJson(raw);
    return parsed ?? structurize(generate, raw, input);
  }

  cancel() {
    if (this.handle !== null && this.module?.releaseModel) {
      void this.module.releaseModel(this.handle);
      this.handle = null;
    }
  }

  private async getModule() {
    if (!this.module) {
      this.module = (await import("expo-llm-mediapipe")).default;
    }
    return this.module;
  }
}

export function createOnDeviceEngine(provider: OnDeviceProvider = "cactus"): OnDeviceEngine {
  return provider === "mediapipe" ? new MediaPipeEngine() : new CactusEngine();
}
