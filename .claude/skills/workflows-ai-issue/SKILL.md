---
name: workflows-ai-issue
description: Automatically process GitHub issues using AI analysis. Validates issues, determines priority, assigns labels, routes to assignees, and decides auto-fix eligibility. Use when processing, categorizing, or routing GitHub issues.
---

# AI Issue Skill

Three-stage AI system for automatic GitHub issue classification and processing.

## Purpose

- **Stage 1 (Triage)**: Validate issues (duplicate, spam, scope check)
- **Stage 2 (Analyze)**: Analyze code and decide action (auto_fix, comment, assign)
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
| `auto_fix` | Meets criteria in ai-fix-criteria.md, creates PR |
| `comment` | Guidance or clarification needed |
| `assign` | Expert review required (see members.md) |
