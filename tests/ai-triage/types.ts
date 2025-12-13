// Stage 1 test case types
export interface Stage1Input {
  title: string;
  body: string;
}

export interface Stage1Expected {
  decision: 'invalid' | 'duplicate' | 'question' | 'valid';
  duplicate_of?: number | null;
  reason_contains?: string[];
  questions_min_count?: number;
}

export interface Stage1TestCase {
  name: string;
  description: string;
  input: Stage1Input;
  expected: Stage1Expected;
}

export interface Stage1Response {
  decision: string;
  duplicate_of: number | null;
  reason: string;
  questions?: string[];
}

// Stage 2 test case types
export interface Stage2Input {
  title: string;
  body: string;
  labels: string[];
  comments: Array<{ author: string; body: string }>;
}

export interface Stage2Expected {
  action: 'auto_fix' | 'assign';
  labels_include?: string[];
  labels_exclude?: string[];
  priority_in?: string[];
  analysis_contains?: string[];
}

export interface Stage2TestCase {
  name: string;
  description: string;
  input: Stage2Input;
  expected: Stage2Expected;
}

export interface Stage2Response {
  action: string;
  labels: string[];
  priority: string;
  estimated: number;
  assignee: string;
  analysis: {
    summary: string;
    expected_behavior: string;
    current_behavior: string;
    affected_files: string[];
    root_cause: string;
    suggested_approach: string;
  };
  auto_fix_rationale: string;
}

// Test result types
export interface TestResult {
  name: string;
  stage: number;
  passed: boolean;
  expected: Record<string, unknown>;
  actual: Record<string, unknown>;
  errors: string[];
  duration: number;
}

export interface TestReport {
  total: number;
  passed: number;
  failed: number;
  results: TestResult[];
  duration: number;
}
