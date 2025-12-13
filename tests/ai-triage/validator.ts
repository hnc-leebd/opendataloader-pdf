import type {
  Stage1Expected,
  Stage1Response,
  Stage2Expected,
  Stage2Response,
} from './types.js';

interface ValidationResult {
  passed: boolean;
  errors: string[];
}

/**
 * Validate Stage 1 response against expected values
 */
export function validateStage1(
  response: Stage1Response,
  expected: Stage1Expected
): ValidationResult {
  const errors: string[] = [];

  // Check decision (exact match)
  if (response.decision !== expected.decision) {
    errors.push(
      `decision: expected "${expected.decision}", got "${response.decision}"`
    );
  }

  // Check duplicate_of
  if (expected.duplicate_of !== undefined) {
    if (expected.duplicate_of === null && response.duplicate_of !== null) {
      errors.push(
        `duplicate_of: expected null, got ${response.duplicate_of}`
      );
    } else if (
      expected.duplicate_of !== null &&
      response.duplicate_of !== expected.duplicate_of
    ) {
      errors.push(
        `duplicate_of: expected ${expected.duplicate_of}, got ${response.duplicate_of}`
      );
    }
  }

  // Check reason_contains
  if (expected.reason_contains && expected.reason_contains.length > 0) {
    const reasonLower = (response.reason || '').toLowerCase();
    for (const keyword of expected.reason_contains) {
      if (!reasonLower.includes(keyword.toLowerCase())) {
        errors.push(`reason: expected to contain "${keyword}"`);
      }
    }
  }

  // Check questions count (for "question" decision)
  if (expected.questions_min_count !== undefined) {
    const questionsCount = response.questions?.length || 0;
    if (questionsCount < expected.questions_min_count) {
      errors.push(
        `questions: expected at least ${expected.questions_min_count}, got ${questionsCount}`
      );
    }
  }

  return {
    passed: errors.length === 0,
    errors,
  };
}

/**
 * Validate Stage 2 response against expected values
 */
export function validateStage2(
  response: Stage2Response,
  expected: Stage2Expected
): ValidationResult {
  const errors: string[] = [];

  // Check action (exact match)
  if (response.action !== expected.action) {
    errors.push(
      `action: expected "${expected.action}", got "${response.action}"`
    );
  }

  // Check labels_include
  if (expected.labels_include && expected.labels_include.length > 0) {
    const responseLabels = response.labels || [];
    for (const label of expected.labels_include) {
      if (!responseLabels.includes(label)) {
        errors.push(`labels: expected to include "${label}"`);
      }
    }
  }

  // Check labels_exclude
  if (expected.labels_exclude && expected.labels_exclude.length > 0) {
    const responseLabels = response.labels || [];
    for (const label of expected.labels_exclude) {
      if (responseLabels.includes(label)) {
        errors.push(`labels: expected to NOT include "${label}"`);
      }
    }
  }

  // Check priority_in
  if (expected.priority_in && expected.priority_in.length > 0) {
    if (!expected.priority_in.includes(response.priority)) {
      errors.push(
        `priority: expected one of [${expected.priority_in.join(', ')}], got "${response.priority}"`
      );
    }
  }

  // Check analysis_contains
  if (expected.analysis_contains && expected.analysis_contains.length > 0) {
    const analysisText = JSON.stringify(response.analysis || {}).toLowerCase();
    for (const keyword of expected.analysis_contains) {
      if (!analysisText.includes(keyword.toLowerCase())) {
        errors.push(`analysis: expected to contain "${keyword}"`);
      }
    }
  }

  return {
    passed: errors.length === 0,
    errors,
  };
}

/**
 * Parse JSON from potentially wrapped response (handles ```json blocks)
 */
export function parseJsonResponse<T>(text: string): T | null {
  // Try direct parse first
  try {
    return JSON.parse(text) as T;
  } catch {
    // Ignore
  }

  // Try extracting from ```json block
  const jsonBlockMatch = text.match(/```json\s*([\s\S]*?)```/);
  if (jsonBlockMatch) {
    try {
      return JSON.parse(jsonBlockMatch[1]) as T;
    } catch {
      // Ignore
    }
  }

  // Try extracting raw JSON object
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]) as T;
    } catch {
      // Ignore
    }
  }

  return null;
}
