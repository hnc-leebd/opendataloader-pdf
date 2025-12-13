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

## Stage 2: Deep Triage (Code-Based)

**Goal:** Decide "How should this be handled?"

**Checks:**
- Accurate labels and priority
- Implementation complexity
- Impact scope
- Whether auto-fix is possible

**Outcomes:**
- AI Auto-Fix → create PR
- Comment → respond with guidance
- Assign → assign to expert

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
│  Claude Code - Analysis (10min timeout)                     │
│  - Analyze issue                                            │
│  - Decide action: auto_fix / comment / assign               │
│  - Determine labels, priority, estimated                    │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   [auto_fix]    [comment]     [assign]
        │             │             │
        ▼             │             │
┌───────────────┐     │             │
│ Claude Code   │     │             │
│ Fix (30min)   │     │             │
│ - Write test  │     │             │
│ - Fix code    │     │             │
│ - Verify build│     │             │
└───────┬───────┘     │             │
   ┌────┴────┐        │             │
   ▼         ▼        ▼             ▼
[success] [fail]   [post        [assign +
   │         │     comment]      comment]
   ▼         ▼
[create   [fallback:
 PR]       assign to
   │       Main Engineer]
   ▼
[comment
 PR link]
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Update Labels                                              │
│  - Add analyzed labels                                      │
│  - Add priority label                                       │
│  - Add 'deep-triaged' label                                 │
└─────────────────────────────────────────────────────────────┘
```
