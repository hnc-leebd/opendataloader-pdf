# AI Issue System

## Stage 1: Triage (README-Based)

**Trigger:** `on: issues: opened` or `workflow_dispatch`

**Goal:** Determine "Is this issue worth processing?"

**Checks:**
- Is it a duplicate?
- Is it spam?
- Is it within project scope?
- Is it clear enough?

**Outcomes:**
- Invalid → auto-close, add `ai-issue/triaged` + `ai-issue/invalid`
- Duplicate → link original, close, add `ai-issue/triaged` + `ai-issue/duplicate`
- Unclear → ask clarifying question, add `ai-issue/triaged` + `ai-issue/needs-info`
- Valid → add `ai-issue/triaged` + `ai-issue/valid` → **triggers Stage 2**

---

## Stage 2: Analyze (Code-Based Analysis)

**Trigger:**
- `on: issues: labeled` (when `ai-issue/valid` is added)
- `on: issue_comment: created` (when issue has `ai-issue/needs-info` label)
- `workflow_dispatch`

**Goal:** Analyze the issue deeply and document findings for humans and AI.

**Checks:**
- Analyze codebase to understand the issue
- Identify affected files and root cause
- Determine implementation complexity
- Decide if auto-fix is appropriate

**Build & Test Script:**
- Use `./scripts/build-all.sh` to verify builds pass
- Script builds and tests Java → Python → Node.js in sequence
- Usage: `./scripts/build-all.sh [VERSION]` (default: 0.0.0)

**Outputs:**
- Detailed analysis comment on the issue:
  - Summary of the problem
  - Expected vs current behavior
  - Affected files
  - Root cause (if identifiable)
  - Suggested approach
- Labels: `ai-issue/analyzed`, `type/*`, `priority/*`, `fix/auto-eligible` (if applicable)
- Assignee recommendation

**Outcomes:**
- Add `ai-issue/analyzed` + type/priority labels
- If auto-fixable: add `fix/auto-eligible` (Stage 3 can be triggered manually)
- If not auto-fixable: assigned for manual implementation

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (5 runs)                                     │
│  - Already ai-issue/analyzed?                               │
│  - Has ai-issue/valid or ai-issue/needs-info label?         │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Claude Code - Analysis (15min timeout)                     │
│  - Read skill files for policies                            │
│  - Analyze codebase (Glob, Grep, Read)                      │
│  - Identify affected files and root cause                   │
│  - Determine if auto-fixable (see ai-fix-criteria.md)       │
│  - Select labels, priority, estimate, assignee              │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Post Analysis Comment                                      │
│  - Summary, expected/current behavior                       │
│  - Affected files, root cause, suggested approach           │
│  - Triage decision (auto-fix eligible or manual)            │
│  - Priority, estimate, assignee                             │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Update Labels                                              │
│  - Add type/* labels                                        │
│  - Add priority/* label                                     │
│  - Add fix/auto-eligible if eligible                        │
│  - Add ai-issue/analyzed label                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Stage 3: Fix (Manual Trigger Only)

**Trigger:** `workflow_dispatch` only (requires human approval)

**Goal:** Attempt to automatically fix issues marked as `fix/auto-eligible`.

**Preconditions:**
- Has `fix/auto-eligible` label (from Stage 2)
- Has `ai-issue/analyzed` label
- Does not have `ai-issue/fixed` label
- Daily limit not exceeded (3 runs)

**Process:**
1. Read issue details and AI analysis from Stage 2
2. Use analysis to understand affected files and approach
3. Write test (if applicable)
4. Implement fix
5. Verify tests and build pass using `./scripts/build-all.sh`
6. Create PR

**Build & Test Script:**
- **MUST** run `./scripts/build-all.sh` before creating PR
- Script builds and tests Java → Python → Node.js in sequence
- All builds must pass before PR creation
- Usage: `./scripts/build-all.sh [VERSION]` (default: 0.0.0)

**Outcomes:**
- Success → PR created, add `ai-issue/fixed` label
- Failure → remove `fix/auto-eligible`, add `fix/manual-required`

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (3 runs)                                     │
│  - Has fix/auto-eligible label?                             │
│  - Has ai-issue/analyzed label?                             │
│  - Not already ai-issue/fixed?                              │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Gather Context                                             │
│  - Issue details                                            │
│  - AI analysis comment from Stage 2                         │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Claude Code - Fix (30min timeout)                          │
│  - Use Stage 2 analysis as guide                            │
│  - Locate affected files                                    │
│  - Write test (if applicable)                               │
│  - Implement fix                                            │
│  - Verify tests pass                                        │
│  - Verify build succeeds                                    │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
                 ┌────┴────┐
                 ▼         ▼
            [success]   [fail]
                 │         │
                 ▼         ▼
           [Create PR] [Comment failure]
                 │         │
                 ▼         ▼
           [Add label      [Remove fix/auto-eligible
            ai-issue/fixed] Add fix/manual-required]
```

---

## Complete Flow Diagram

```
New Issue
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 1: Triage (auto on issue open)                     │
│ Labels: ai-issue/triaged + ONE OF:                       │
│   ai-issue/valid | ai-issue/invalid | ai-issue/duplicate │
│   ai-issue/needs-info                                    │
└──────────────────────────────────────────────────────────┘
    │                                     │
    │ (ai-issue/valid)                    │ (ai-issue/needs-info)
    │                                     │
    ▼                                     ▼
┌─────────────────────────────┐    ┌─────────────────────────┐
│ Stage 2 triggered           │    │ Wait for user comment   │
│ automatically               │    │                         │
└─────────────────────────────┘    └───────────┬─────────────┘
    │                                          │ (user comments)
    │                                          ▼
    │                              ┌───────────────────────────┐
    │                              │ Stage 2 triggered         │
    │                              │ by comment                │
    └──────────────┬───────────────┴───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: Analyze (auto triggered)                        │
│ Labels: ai-issue/analyzed + type/* + priority/*          │
│ If auto-fixable: + fix/auto-eligible                     │
└──────────────────────────────────────────────────────────┘
                   │
                   │ (fix/auto-eligible + MANUAL TRIGGER)
                   ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Fix (workflow_dispatch only)                    │
│ Success: ai-issue/fixed + PR created                     │
│ Failure: fix/manual-required                             │
└──────────────────────────────────────────────────────────┘
```
