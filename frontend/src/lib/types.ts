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
  gemma_model?: string;
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

export type CompanionTypedAction = {
  label: string;
  action: "tool_call" | "capture" | "measurement";
  args: Record<string, unknown>;
};

export type CompanionToolResult = {
  tool: string;
  label?: string;
  args?: Record<string, unknown>;
  result: unknown;
};

export type CompanionAnalysis = {
  mode?: string;
  workspace: string;
  visible_context: string;
  answer: string;
  next_actions: string[];
  actions?: CompanionTypedAction[];
  tool_results?: CompanionToolResult[];
  detected_topology?: string;
  detected_components?: Array<{ ref?: string; model?: string }>;
  detected_measurements?: Array<{ label: string; value: number; unit: string }>;
  suspected_faults?: string[];
  session_id?: string;
  session_title?: string;
  turn_count?: number;
  can_click: boolean;
  safety?: { risk_level: string; warnings: string[] };
  confidence?: string;
  duration_ms?: number;
  gemma_error?: string;
  raw?: string;
};

export type CompanionRunToolResponse = {
  tool: string;
  args: Record<string, unknown>;
  result: unknown;
  duration_ms: number;
};

export type StreamSnapshot = {
  session_id: string;
  labels: Record<string, Array<{ ts: number; value: number; unit: string }>>;
  events: Array<{ type: string; label: string; stddev: number; expected_stddev: number; message: string }>;
};
