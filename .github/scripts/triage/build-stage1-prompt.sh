#!/bin/bash
# Build Stage 1 (Quick Triage) prompt
# Usage: ./build-stage1-prompt.sh <issue_num> <issue_title> <issue_body> [readme_file] [issues_file]
#
# Outputs the complete prompt to stdout
# Can be used in both GitHub Actions and local testing

set -euo pipefail

# Arguments
ISSUE_NUM="${1:-999}"
ISSUE_TITLE="${2:-}"
ISSUE_BODY="${3:-}"
README_FILE="${4:-}"
ISSUES_FILE="${5:-}"

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Default paths
if [ -z "$README_FILE" ]; then
  README_FILE="$ROOT_DIR/README.md"
fi

# Read README (first 50 lines for quick triage)
if [ -f "$README_FILE" ]; then
  README_CONTENT=$(head -50 "$README_FILE" 2>/dev/null || echo "No README")
else
  README_CONTENT="No README"
fi

# Read existing issues
if [ -n "$ISSUES_FILE" ] && [ -f "$ISSUES_FILE" ]; then
  EXISTING_ISSUES=$(cat "$ISSUES_FILE")
else
  EXISTING_ISSUES=""
fi

# Build prompt
cat <<PROMPT_EOF
You are a GitHub issue triage bot. Make a quick decision based on limited information.

## Project (from README)
$README_CONTENT

## Existing Issues
$EXISTING_ISSUES

## New Issue #$ISSUE_NUM
Title: $ISSUE_TITLE
Body: $ISSUE_BODY

## Decision Required
Based ONLY on the README and issue list above, determine:
1. Is this SPAM or OUT OF SCOPE? (ads, gibberish, abuse, unrelated to project) → "triage/invalid"
2. Is this a DUPLICATE? (very similar to existing issue) → "triage/duplicate"
3. Is this UNCLEAR? (missing reproduction steps, environment, or details) → "triage/needs-info"
4. Otherwise → "triage/valid"

Respond with JSON only:
{
  "decision": "triage/invalid" | "triage/duplicate" | "triage/needs-info" | "triage/valid",
  "duplicate_of": <issue number or null>,
  "reason": "one sentence explanation",
  "questions": ["question1", ...] // only if decision is "triage/needs-info"
}
PROMPT_EOF
