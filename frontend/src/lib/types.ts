export type Artifact = {
  id: string;
  kind: string;
  filename: string;
  text_excerpt?: string;
};

export type Measurement = {
  id: string;
  label: string;
  value: number;
  unit: string;
  mode: string;
  context: string;
  source: string;
};

export type ToolCall = {
  tool_name: string;
  status: string;
  duration_ms: number;
  output: Record<string, unknown>;
};

export type Diagnosis = {
  expected_behavior?: { gain?: number; output?: string };
  observed_behavior?: { summary?: string; evidence?: string[] };
  likely_faults?: Array<{ fault: string; confidence: number; why: string }>;
  next_measurement?: { label: string; expected: string; instruction: string };
  safety?: { risk_level: string; warnings: string[] };
  student_explanation?: string;
  confidence?: string;
  tool_calls?: ToolCall[];
  gemma_status?: string;
};

export type ModelHealth = {
  available: boolean;
  model: string;
  loaded: boolean;
  models: string[];
  hint?: string;
  error?: string;
};

export type LabSession = {
  id: string;
  title: string;
  student_level: string;
  experiment_type: string;
  status: string;
  summary: string;
  artifacts: Artifact[];
  measurements: Measurement[];
  latest_diagnosis?: Diagnosis | null;
  report?: string;
};

export type CompanionAnalysis = {
  mode?: string;
  workspace: string;
  visible_context: string;
  answer: string;
  next_actions: string[];
  can_click: boolean;
  safety?: { risk_level: string; warnings: string[] };
  confidence?: string;
  gemma_error?: string;
  raw?: string;
};
