---
name: ai-issue
description: Automatically process GitHub issues using AI analysis. Validates issues, determines priority, assigns labels, routes to assignees, and decides auto-fix eligibility. Use when processing, categorizing, or routing GitHub issues.
---

# AI Issue Skill

Three-stage AI system for automatic GitHub issue classification and processing.

## Purpose

- **Stage 1 (Triage)**: Validate issues (duplicate, spam, scope check)
- **Stage 2 (Analyze)**: Analyze code and decide action (fix/auto-eligible, fix/manual-required, respond/comment-only)
- **Stage 3 (Fix)**: Automatically fix eligible issues and create PRs

## When to Use

- Processing new GitHub issues
- Determining issue priority and complexity
- Deciding AI fix eligibility
- Assigning to appropriate team members

## Reference

| File | Description |
|------|-------------|
| [workflow.md](workflow.md) | Detailed workflow (Stage 1/2/3 process, flowchart) |
| [issue-policy.md](issue-policy.md) | Labels, priority (P0-P2), story points policy |
| [ai-fix-criteria.md](ai-fix-criteria.md) | Criteria for AI auto-fix eligibility |
| [members.md](members.md) | Team member list and availability |
| [labels.md](labels.md) | Label naming conventions and definitions |
| [testing.md](testing.md) | Test framework for validating decisions |

## Key Decisions

### Actions

| Action | Condition |
|--------|-----------|
| `fix/auto-eligible` | Meets criteria in ai-fix-criteria.md, creates PR |
| `fix/manual-required` | Expert review required (see members.md) |
| `respond/comment-only` | No code change needed, respond with comment (existing feature guidance, docs reference, roadmap review needed, external dependency, needs more info, duplicate, won't fix) |
