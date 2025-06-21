export interface Hypothesis {
  id: string;
  session_id: string;
  hypothesis_number: number;
  version: string;
  title: string;
  description: string;
  hallmarks: {
    testability: string;
    specificity: string;
    grounded_knowledge: string;
    predictive_power: string;
    parsimony: string;
  };
  references: Array<{
    citation: string;
    annotation: string;
  }>;
  hypothesis_type: 'original' | 'improvement' | 'new_alternative';
  user_feedback?: string;
  original_hypothesis_id?: string;
  generation_timestamp: string;
  improvements_count: number;
}

export interface Session {
  id: string;
  research_goal: string;
  model_name: string;
  model_shortname: string;
  created_at: string;
  updated_at: string;
  hypothesis_count: number;
  hypotheses?: Hypothesis[];
}

export interface Model {
  shortname: string;
  model_name: string;
  server: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
} 