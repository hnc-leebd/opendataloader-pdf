#!/bin/bash
# Build Stage 2 (Deep Triage) prompt
# Usage: ./build-stage2-prompt.sh <issue_num> <issue_json_file>
#
# Outputs the complete prompt to stdout
# Can be used in both GitHub Actions and local testing

set -euo pipefail

# Arguments
ISSUE_NUM="${1:-999}"
ISSUE_JSON_FILE="${2:-}"

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SKILL_DIR="$ROOT_DIR/.claude/skills/ai-issue"

# Read issue JSON
if [ -n "$ISSUE_JSON_FILE" ] && [ -f "$ISSUE_JSON_FILE" ]; then
  ISSUE_JSON=$(cat "$ISSUE_JSON_FILE")
else
  ISSUE_JSON="{}"
fi

# Read skill files (optional)
AI_FIX_CRITERIA=""
ISSUE_POLICY=""
MEMBERS=""

if [ -f "$SKILL_DIR/ai-fix-criteria.md" ]; then
  AI_FIX_CRITERIA=$(cat "$SKILL_DIR/ai-fix-criteria.md")
fi

if [ -f "$SKILL_DIR/issue-policy.md" ]; then
  ISSUE_POLICY=$(cat "$SKILL_DIR/issue-policy.md")
fi

if [ -f "$SKILL_DIR/members.md" ]; then
  MEMBERS=$(cat "$SKILL_DIR/members.md")
fi

# Build prompt
cat <<PROMPT_EOF
Perform deep analysis for GitHub issue #$ISSUE_NUM using the ai-issue skill.

## Issue Details
$ISSUE_JSON

## Instructions
Use the ai-issue skill to:
1. Read the skill files in .claude/skills/ai-issue/ for policies and criteria
2. **Analyze the codebase** to understand:
   - What the issue is about
   - Which files/components are involved
   - How the current implementation works
3. Decide action: "fix/auto-eligible" or "fix/manual-required"
   - Use ai-fix-criteria.md to determine if auto-fix is appropriate
4. Select appropriate labels, priority, and estimate based on issue-policy.md
5. Recommend the best available team member from members.md

## AI Fix Criteria
${AI_FIX_CRITERIA:-Use standard criteria: simple bugs, typos, type errors are auto-fixable. Architecture changes, security issues require manual review.}

## Issue Policy
${ISSUE_POLICY:-Priority: P0 (critical), P1 (important), P2 (normal). Story points: 1, 2, 3, 5, 8.}

## Team Members
${MEMBERS:-Available: benedict (available)}

## Required Output
Respond with JSON only (no markdown code blocks):
{
  "action": "fix/auto-eligible" | "fix/manual-required",
  "labels": ["type/bug", "type/enhancement", ...],
  "priority": "P0" | "P1" | "P2",
  "estimated": 1 | 2 | 3 | 5 | 8,
  "assignee": "github_id",
  "analysis": {
    "summary": "One paragraph summary of what this issue is about",
    "expected_behavior": "What the user expects to happen",
    "current_behavior": "What currently happens (if applicable)",
    "affected_files": ["path/to/file1.ts", "path/to/file2.ts"],
    "root_cause": "Technical explanation of why the issue occurs (if identifiable)",
    "suggested_approach": "How to fix or implement this"
  },
  "auto_fix_rationale": "Why this is/isn't suitable for auto-fix (reference ai-fix-criteria.md)"
}
PROMPT_EOF
