# AI Triage System

## Stage 1: Quick Triage (README-Based)

**Goal:** Determine "Is this issue worth processing?"

**Checks:**
- Is it a duplicate?
- Is it spam?
- Is it within project scope?
- Is it clear enough?

**Outcomes:**
- Invalid → auto-close
- Duplicate → link original, close
- Unclear → ask clarifying question
- Valid → proceed to Stage 2

---

## Stage 2: Deep Triage (Code-Based Analysis)

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
- Labels: priority, category, `auto-fixable` (if applicable)
- Assignee recommendation

**Outcomes:**
- `auto-fixable` label → eligible for Stage 3
- No `auto-fixable` label → assigned for manual implementation

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (5 runs)                                     │
│  - Already deep-triaged?                                    │
│  - Has 'valid' label? (Stage 1 passed)                      │
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
│  - Add category labels                                      │
│  - Add priority label (P0/P1/P2)                            │
│  - Add 'auto-fixable' if eligible                           │
│  - Add 'deep-triaged' label                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Stage 3: Auto Fix (Separate Workflow)

**Goal:** Attempt to automatically fix issues marked as `auto-fixable`.

**Preconditions:**
- Has `auto-fixable` label (from Stage 2)
- Has `deep-triaged` label
- Does not have `ai-fixed` label
- Daily limit not exceeded (3 runs)

**Process:**
1. Read issue details and AI analysis from Stage 2
2. Use analysis to understand affected files and approach
3. Write test (if applicable)
4. Implement fix
5. Verify tests and build pass
6. Create PR

**Outcomes:**
- Success → PR created, `ai-fixed` label added
- Failure → `needs-manual-fix` label, `auto-fixable` removed

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Check Preconditions                                        │
│  - Daily limit (3 runs)                                     │
│  - Has 'auto-fixable' label?                                │
│  - Has 'deep-triaged' label?                                │
│  - Not already 'ai-fixed'?                                  │
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
           [Add label  [Remove 'auto-fixable'
            'ai-fixed'] Add 'needs-manual-fix']
```

---

## Label Reference

| Label | Meaning |
|-------|---------|
| `triaged` | Stage 1 completed |
| `valid` | Passed Stage 1, eligible for Stage 2 |
| `deep-triaged` | Stage 2 completed |
| `auto-fixable` | AI can attempt automatic fix |
| `ai-fixed` | PR created by AI (Stage 3 success) |
| `needs-manual-fix` | Auto-fix failed, needs human |
| `P0` / `P1` / `P2` | Priority level |
