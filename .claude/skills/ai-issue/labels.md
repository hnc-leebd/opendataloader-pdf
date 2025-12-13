# Label System

All labels use `/` prefix for grouping in GitHub UI.

## Stage Status Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `ai-issue/triaged` | `#FBCA04` (yellow) | Stage 1 (Triage) completed | Stage 1 |
| `ai-issue/analyzed` | `#D93F0B` (orange) | Stage 2 (Analyze) completed | Stage 2 |
| `ai-issue/fixed` | `#0E8A16` (green) | Stage 3 (Fix) completed (PR created) | Stage 3 |

## Triage Result Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `ai-issue/valid` | `#0E8A16` (green) | Valid issue, proceed to Stage 2 | Stage 1 |
| `ai-issue/invalid` | `#666666` (gray) | Out of scope or spam | Stage 1 |
| `ai-issue/duplicate` | `#CFD3D7` (light gray) | Duplicate of existing issue | Stage 1 |
| `ai-issue/needs-info` | `#D876E3` (purple) | Needs more information | Stage 1 |

## Action Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `fix/auto-eligible` | `#0E8A16` (green) | Eligible for auto-fix | Stage 2 |
| `fix/manual-required` | `#FBCA04` (yellow) | Requires human implementation | Stage 2/3 |
| `respond/comment-only` | `#C5DEF5` (light blue) | No code change needed, respond with comment | Stage 2 |

## Type Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `type/bug` | `#D73A4A` (red) | Bug report | Stage 2 |
| `type/enhancement` | `#A2EEEF` (cyan) | Feature request or improvement | Stage 2 |
| `type/docs` | `#0075CA` (blue) | Documentation | Stage 2 |
| `type/dependencies` | `#0366D6` (blue) | Dependency update | Stage 2 |

## Priority Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `priority/P0` | `#B60205` (dark red) | Critical - production blocking | Stage 2 |
| `priority/P1` | `#D93F0B` (orange) | Important - not immediately blocking | Stage 2 |
| `priority/P2` | `#FBCA04` (yellow) | Normal or low priority | Stage 2 |

## Workflow Flow

```
New Issue
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 1: Triage                                          │
│ Adds: ai-issue/triaged + ONE OF:                         │
│   - ai-issue/valid     → triggers Stage 2                │
│   - ai-issue/invalid   → closes issue                    │
│   - ai-issue/duplicate → closes issue                    │
│   - ai-issue/needs-info → waits for user response        │
└──────────────────────────────────────────────────────────┘
    │ (ai-issue/valid)          │ (ai-issue/needs-info + user comment)
    ▼                           ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: Analyze                                         │
│ Adds: ai-issue/analyzed + type/* + priority/* +          │
│   - fix/auto-eligible (if auto-fixable)                  │
│   - fix/manual-required (if needs human)                 │
│   - respond/comment-only (if no code change needed)      │
└──────────────────────────────────────────────────────────┘
    │ (fix/auto-eligible + manual trigger)
    ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Fix (workflow_dispatch only)                    │
│ On success: ai-issue/fixed + PR created                  │
│ On failure: removes fix/auto-eligible,                   │
│             adds fix/manual-required                     │
└──────────────────────────────────────────────────────────┘
```

## Trigger Conditions

| Stage | Trigger |
|-------|---------|
| Stage 1 | `on: issues: opened` or `workflow_dispatch` |
| Stage 2 | `on: issues: labeled` (ai-issue/valid) or `on: issue_comment: created` (has ai-issue/needs-info) or `workflow_dispatch` |
| Stage 3 | `workflow_dispatch` only (manual trigger required) |
