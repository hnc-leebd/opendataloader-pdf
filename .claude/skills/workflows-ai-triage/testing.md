# AI Triage Testing Framework

A test framework for validating AI Triage workflow decisions.

## Purpose

- Prevent regressions when prompts or policies change
- Verify expected decisions for various issue types
- Test cases serve as living documentation

## Directory Structure

```
tests/
└── ai-triage/
    ├── runner.ts                    # Test runner
    ├── prompt-builder.ts            # Build prompts identical to workflows
    ├── validator.ts                 # Result validation logic
    ├── cases/
    │   ├── stage1-quick/            # Stage 1 test cases
    │   │   ├── invalid-spam.json
    │   │   ├── invalid-gibberish.json
    │   │   ├── duplicate-existing.json
    │   │   ├── question-missing-steps.json
    │   │   ├── question-missing-env.json
    │   │   ├── valid-bug-report.json
    │   │   └── valid-feature-request.json
    │   └── stage2-deep/             # Stage 2 test cases
    │       ├── auto-fix-simple-typo.json
    │       ├── auto-fix-type-error.json
    │       ├── manual-architecture.json
    │       └── manual-security.json
    └── fixtures/
        ├── existing-issues.json     # Existing issues for duplicate detection
        └── readme-excerpt.txt       # README excerpt
```

## Test Case Format

### Stage 1 (Quick Triage)

```json
{
  "name": "Valid bug report with reproduction steps",
  "description": "Clear bug report with repro steps should be classified as valid",
  "input": {
    "title": "PDF parsing fails for password-protected files",
    "body": "## Description\nWhen trying to parse a password-protected PDF...\n\n## Steps to Reproduce\n1. Create a password-protected PDF\n2. Run `parse(file)`\n3. Error thrown\n\n## Environment\n- OS: macOS 14.0\n- Node: 20.10.0"
  },
  "expected": {
    "decision": "valid",
    "duplicate_of": null,
    "reason_contains": ["password", "protected"]
  }
}
```

### Stage 2 (Deep Triage)

```json
{
  "name": "Simple typo fix should be auto-eligible",
  "description": "Simple typo corrections should be eligible for auto-fix",
  "input": {
    "title": "Typo in error message",
    "body": "The error message says 'Invlaid input' instead of 'Invalid input'",
    "labels": ["triage/valid", "triage/quick"],
    "comments": []
  },
  "expected": {
    "action": "auto_fix",
    "labels_include": ["type/bug", "fix/auto-eligible"],
    "labels_exclude": ["fix/manual-required"],
    "priority_in": ["P2"],
    "analysis_contains": ["typo", "error message"]
  }
}
```

## Validation Rules

| Field | Validation Method | Example |
|-------|-------------------|---------|
| `decision` | Exact match | `"decision": "valid"` |
| `action` | Exact match | `"action": "auto_fix"` |
| `duplicate_of` | null or specific value | `"duplicate_of": null` |
| `reason_contains` | Keywords in reason string | `["spam", "gibberish"]` |
| `labels_include` | Labels present in output | `["type/bug"]` |
| `labels_exclude` | Labels absent from output | `["fix/manual-required"]` |
| `priority_in` | Priority within range | `["P0", "P1"]` |
| `analysis_contains` | Keywords in analysis | `["affected_files"]` |

## Test Case Categories

### Stage 1: Quick Triage

| Category | Expected Result | Example Cases |
|----------|----------------|---------------|
| **Invalid** | `decision: "invalid"` | Spam, ads, gibberish, unrelated to project |
| **Duplicate** | `decision: "duplicate"` | Same problem as existing issue, similar title/content |
| **Question** | `decision: "question"` | Missing repro steps, no environment info, unclear description |
| **Valid** | `decision: "valid"` | Clear bug report, feature request, docs improvement |

### Stage 2: Deep Triage

| Category | Expected Result | Example Cases |
|----------|----------------|---------------|
| **Auto-fix Eligible** | `action: "auto_fix"` | Typo fix, type error, lint error, simple bug |
| **Manual Required** | `action: "assign"` | Architecture change, security-related, UX decision needed |

## Test Runner Logic

```typescript
// runner.ts pseudocode
async function runTests() {
  const cases = loadTestCases();
  const results = [];

  for (const testCase of cases) {
    // 1. Build prompt identical to workflow
    const prompt = buildPrompt(testCase.input);

    // 2. Call Claude API
    const response = await callClaude(prompt);

    // 3. Parse JSON response
    const parsed = parseResponse(response);

    // 4. Compare with expected values
    const validation = validate(parsed, testCase.expected);

    results.push({
      name: testCase.name,
      passed: validation.passed,
      details: validation.details
    });
  }

  return generateReport(results);
}
```

## Workflow Integration

```yaml
# .github/workflows/ai-triage-test.yml
name: "AI Triage Tests"

on:
  pull_request:
    paths:
      - '.github/workflows/ai-triage-*.yml'
      - '.claude/skills/workflows-ai-triage/**'
      - 'tests/ai-triage/**'
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: cd tests/ai-triage && npm install
      - name: Run AI Triage Tests
        run: cd tests/ai-triage && npm test
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Running Tests

```bash
# Run all tests
npm run test:ai-triage

# Run Stage 1 only
npm run test:ai-triage -- --stage=1

# Run specific case
npm run test:ai-triage -- --case=valid-bug-report

# Verbose output
npm run test:ai-triage -- --verbose
```

## Report Format

```
AI Triage Test Results
======================

Stage 1: Quick Triage
  ✓ invalid-spam.json (decision: invalid)
  ✓ invalid-gibberish.json (decision: invalid)
  ✓ duplicate-existing.json (decision: duplicate, duplicate_of: 42)
  ✗ question-missing-steps.json
    Expected: decision = "question"
    Actual:   decision = "valid"
  ✓ valid-bug-report.json (decision: valid)

Stage 2: Deep Triage
  ✓ auto-fix-simple-typo.json (action: auto_fix)
  ✓ manual-architecture.json (action: assign)

Summary: 6/7 passed (85.7%)
```

## Cost Considerations

- Each test case requires 1 Claude API call
- Stage 1: Uses Sonnet 4.5 (affordable)
- Stage 2: Uses Haiku 4.5 (more affordable)
- Only runs on PR changes to minimize cost
- Manual execution available via `workflow_dispatch`

## Test Case Writing Guidelines

1. **Clear naming**: Immediately understand what is being tested
2. **Include description**: Explain why this result is expected
3. **Realistic input**: Use issue formats that occur in practice
4. **Edge cases**: Include ambiguous cases (e.g., partial information)
5. **Negative cases**: Verify incorrect classifications don't occur
