---
name: workflows-ai-triage
description: Automatically triage GitHub issues using AI analysis. Validates issues, determines priority, assigns labels, routes to assignees, and decides auto-fix eligibility. Use when processing, categorizing, or routing GitHub issues.
---

# AI Triage Skill

Two-stage AI system for automatic GitHub issue classification and processing.

## Purpose

- **Stage 1 (Quick Triage)**: Validate issues (duplicate, spam, scope check)
- **Stage 2 (Deep Triage)**: Analyze code and decide action (auto_fix, comment, assign)

## When to Use

- Processing new GitHub issues
- Determining issue priority and complexity
- Deciding AI fix eligibility
- Assigning to appropriate team members

## Reference

| File | Description |
|------|-------------|
| [workflow.md](workflow.md) | Detailed triage workflow (Stage 1/2 process, flowchart) |
| [issue-policy.md](issue-policy.md) | Labels, priority (P0-P2), story points policy |
| [ai-fix-criteria.md](ai-auto-fix-criteria.md) | Criteria for AI auto-fix eligibility |
| [members.md](members.md) | Team member list and availability |

## Key Decisions

### Actions

| Action | Condition |
|--------|-----------|
| `auto_fix` | Meets criteria in ai-auto-fix-criteria.md, creates PR |
| `comment` | Guidance or clarification needed |
| `assign` | Expert review required (see members.md) |
