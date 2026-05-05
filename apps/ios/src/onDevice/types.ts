export type Measurement = {
  label: string;
  value: number;
  unit: string;
  mode?: string;
  context?: string;
  source?: string;
};

export type FaultCandidate = {
  id: string;
  fault: string;
  confidence: number;
  why: string;
  verification_test?: string;
  fix_recipe?: string;
};

export type StructuredDiagnosis = {
  experiment_type: string;
  expected_behavior: Record<string, unknown>;
  observed_behavior: { summary: string; evidence: string[] };
  likely_faults: FaultCandidate[];
  next_measurement: { label: string; expected: string; instruction: string };
  safety: { risk_level: string; warnings: string[] };
  student_explanation: string;
  confidence: string;
  gemma_status?: string;
  gemma_model?: string;
};

export type OnDeviceInput = {
  question: string;
  measurements: Measurement[];
  image_b64?: string;
};

export interface OnDeviceEngine {
  ready(): Promise<boolean>;
  modelInfo(): Promise<{ name: string; quant: string; sizeMB: number }>;
  diagnose(input: OnDeviceInput): Promise<StructuredDiagnosis>;
  cancel(): void;
}

export type OnDeviceProvider = "cactus" | "mediapipe";
