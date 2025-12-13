# AI Triage System

## Stage 1: Quick Triage (README-Based)

**Trigger:** `on: issues: opened` or `workflow_dispatch`

**Goal:** Determine "Is this issue worth processing?"

**Checks:**
- Is it a duplicate?
- Is it spam?
- Is it within project scope?
- Is it clear enough?

**Outcomes:**
- Invalid → auto-close, add `triage/quick` + `triage/invalid`
- Duplicate → link original, close, add `triage/quick` + `triage/duplicate`
- Unclear → ask clarifying question, add `triage/quick` + `triage/question`
- Valid → add `triage/quick` + `triage/valid` → **triggers Stage 2**

---

## Stage 2: Deep Triage (Code-Based Analysis)

**Trigger:**
- `on: issues: labeled` (when `triage/valid` is added)
- `on: issue_comment: created` (when issue has `triage/question` label)
- `workflow_dispatch`

**Goal:** Analyze the issue deeply and document findings for humans and AI.

**Checks:**
- Analyze codebase to understand the issue
- Identify affected files and root cause
- Determine implementation complexity
- Decide if auto-fix is appropriate

**Outputs:**
- Detailed analysis comment on the issue:
  - Summary of the problem
  - Expected vs current behavior
  - Affected files
  - Root cause (if identifiable)
  - Suggested approach
- Labels: `type/*`, `priority/*`, `fix/auto-eligible` (if applicable)
- Assignee recommendation

**Outcomes:**
- Add `triage/deep` + type/priority labels
- If auto-fixable: add `fix/auto-eligible` (Stage 3 can be triggered manually)
- If not auto-fixable: assigned for manual implementation

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (5 runs)                                     │
│  - Already triage/deep?                                     │
│  - Has triage/valid or triage/question label?               │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Claude Code - Deep Analysis (15min timeout)                │
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
│  - Add triage/deep label                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Stage 3: Auto Fix (Manual Trigger Only)

**Trigger:** `workflow_dispatch` only (requires human approval)

**Goal:** Attempt to automatically fix issues marked as `fix/auto-eligible`.

**Preconditions:**
- Has `fix/auto-eligible` label (from Stage 2)
- Has `triage/deep` label
- Does not have `triage/fixed` label
- Daily limit not exceeded (3 runs)

**Process:**
1. Read issue details and AI analysis from Stage 2
2. Use analysis to understand affected files and approach
3. Write test (if applicable)
4. Implement fix
5. Verify tests and build pass
6. Create PR

**Outcomes:**
- Success → PR created, add `triage/fixed` label
- Failure → remove `fix/auto-eligible`, add `fix/manual-required`

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (3 runs)                                     │
│  - Has fix/auto-eligible label?                             │
│  - Has triage/deep label?                                   │
│  - Not already triage/fixed?                                │
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
           [Add label  [Remove fix/auto-eligible
            triage/fixed] Add fix/manual-required]
```

---

## Complete Flow Diagram

```
New Issue
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 1: Quick Triage (auto on issue open)               │
│ Labels: triage/quick + ONE OF:                           │
│   triage/valid | triage/invalid | triage/duplicate |     │
│   triage/question                                        │
└──────────────────────────────────────────────────────────┘
    │                                     │
    │ (triage/valid)                      │ (triage/question)
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
│ Stage 2: Deep Triage (auto triggered)                    │
│ Labels: triage/deep + type/* + priority/*                │
│ If auto-fixable: + fix/auto-eligible                     │
└──────────────────────────────────────────────────────────┘
                   │
                   │ (fix/auto-eligible + MANUAL TRIGGER)
                   ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Auto Fix (workflow_dispatch only)               │
│ Success: triage/fixed + PR created                       │
│ Failure: fix/manual-required                             │
└──────────────────────────────────────────────────────────┘
```
