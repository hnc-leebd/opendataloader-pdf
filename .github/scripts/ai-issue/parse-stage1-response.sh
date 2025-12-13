#!/bin/bash
# Parse Stage 1 response and output GitHub Actions outputs
# Usage: ./parse-stage1-response.sh <response_text>
#
# Outputs (for GitHub Actions):
#   decision=ai-issue/invalid|ai-issue/duplicate|ai-issue/needs-info|ai-issue/valid
#   duplicate_of=<number or empty>
#   reason=<string>
#   questions=<json array>

set -euo pipefail

RESPONSE_TEXT="${1:-}"

if [ -z "$RESPONSE_TEXT" ]; then
  # Read from stdin if no argument
  RESPONSE_TEXT=$(cat)
fi

# Parse JSON from text (handle multiline JSON)
RESULT=$(echo "$RESPONSE_TEXT" | jq -c '.' 2>/dev/null || \
         echo "$RESPONSE_TEXT" | sed -n '/{/,/}/p' | jq -c '.' 2>/dev/null || \
         echo '{}')

# Extract fields
DECISION=$(echo "$RESULT" | jq -r '.decision // "ai-issue/valid"')
DUPLICATE_OF=$(echo "$RESULT" | jq -r '.duplicate_of // empty')
REASON=$(echo "$RESULT" | jq -r '.reason // "Could not parse response"')
QUESTIONS=$(echo "$RESULT" | jq -c '.questions // []')

# Normalize decision to label format (for backwards compatibility)
case "$DECISION" in
  "invalid"|"triage/invalid"|"ai-issue/invalid")
    DECISION="ai-issue/invalid"
    ;;
  "duplicate"|"triage/duplicate"|"ai-issue/duplicate")
    DECISION="ai-issue/duplicate"
    ;;
  "question"|"needs-info"|"triage/question"|"triage/needs-info"|"ai-issue/needs-info")
    DECISION="ai-issue/needs-info"
    ;;
  "valid"|"triage/valid"|"ai-issue/valid")
    DECISION="ai-issue/valid"
    ;;
  *)
    DECISION="ai-issue/valid"
    ;;
esac

# Output for GitHub Actions
echo "decision=$DECISION"
echo "duplicate_of=$DUPLICATE_OF"
echo "reason=$REASON"
echo "questions=$QUESTIONS"
