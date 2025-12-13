# Label System

All labels use `/` prefix for grouping in GitHub UI.

## Triage Status Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `triage/quick` | `#FBCA04` (yellow) | Stage 1 completed | Stage 1 |
| `triage/deep` | `#D93F0B` (orange) | Stage 2 completed | Stage 2 |
| `triage/fixed` | `#0E8A16` (green) | Stage 3 completed (PR created) | Stage 3 |

## Triage Result Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `triage/valid` | `#0E8A16` (green) | Valid issue, proceed to Stage 2 | Stage 1 |
| `triage/invalid` | `#666666` (gray) | Out of scope or spam | Stage 1 |
| `triage/duplicate` | `#CFD3D7` (light gray) | Duplicate of existing issue | Stage 1 |
| `triage/question` | `#D876E3` (purple) | Needs more information | Stage 1 |

## Fix Status Labels

| Label | Color | Description | Set By |
|-------|-------|-------------|--------|
| `fix/auto-eligible` | `#0E8A16` (green) | Eligible for auto-fix | Stage 2 |
| `fix/manual-required` | `#FBCA04` (yellow) | Requires human implementation | Stage 3 (on failure) |

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
│ Stage 1: Quick Triage                                    │
│ Adds: triage/quick + ONE OF:                             │
│   - triage/valid    → triggers Stage 2                   │
│   - triage/invalid  → closes issue                       │
│   - triage/duplicate → closes issue                      │
│   - triage/question → waits for user response            │
└──────────────────────────────────────────────────────────┘
    │ (triage/valid)              │ (triage/question + user comment)
    ▼                             ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: Deep Triage                                     │
│ Adds: triage/deep + type/* + priority/* +                │
│   - fix/auto-eligible (if auto-fixable)                  │
└──────────────────────────────────────────────────────────┘
    │ (fix/auto-eligible + manual trigger)
    ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 3: Auto Fix (workflow_dispatch only)               │
│ On success: triage/fixed + PR created                    │
│ On failure: removes fix/auto-eligible,                   │
│             adds fix/manual-required                     │
└──────────────────────────────────────────────────────────┘
```

## Trigger Conditions

| Stage | Trigger |
|-------|---------|
| Stage 1 | `on: issues: opened` or `workflow_dispatch` |
| Stage 2 | `on: issues: labeled` (triage/valid) or `on: issue_comment: created` (has triage/question) or `workflow_dispatch` |
| Stage 3 | `workflow_dispatch` only (manual trigger required) |
