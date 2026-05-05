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
};

