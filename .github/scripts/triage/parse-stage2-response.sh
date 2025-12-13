#!/bin/bash
# Parse Stage 2 (Deep Triage) response from Claude Code CLI
# Usage: ./parse-stage2-response.sh [output_dir]
#
# Reads Claude Code CLI output from stdin and extracts JSON fields
# Outputs key=value pairs for GitHub Actions to stdout
# Also writes analysis fields to files in output_dir (default: /tmp)
#
# Outputs to stdout:
#   action=auto_fix|assign
#   labels=["label1", "label2"]
#   priority=P0|P1|P2
#   estimated=1|2|3|5|8
#   assignee=github_id
#
# Outputs to files (in output_dir):
#   analysis_summary.txt
#   expected_behavior.txt
#   current_behavior.txt
#   affected_files.txt
#   root_cause.txt
#   suggested_approach.txt
#   auto_fix_rationale.txt

set -euo pipefail

OUTPUT_DIR="${1:-/tmp}"

# Read from stdin
RESPONSE_TEXT=$(cat)

# Extract JSON from result (handle ```json wrapper if present)
PARSED_JSON=$(echo "$RESPONSE_TEXT" | sed -n '/```json/,/```/p' | sed '1d;$d')

if [ -z "$PARSED_JSON" ]; then
  # Try to extract raw JSON object (multiline)
  PARSED_JSON=$(echo "$RESPONSE_TEXT" | awk '/^{/,/^}/' | head -100)
fi

if [ -z "$PARSED_JSON" ]; then
  PARSED_JSON='{}'
fi

# Parse JSON fields
ACTION=$(echo "$PARSED_JSON" | jq -r '.action // "assign"')
LABELS=$(echo "$PARSED_JSON" | jq -c '.labels // []')
PRIORITY=$(echo "$PARSED_JSON" | jq -r '.priority // "P2"')
ESTIMATED=$(echo "$PARSED_JSON" | jq -r '.estimated // 3')
ASSIGNEE=$(echo "$PARSED_JSON" | jq -r '.assignee // ""' | tr -d '@')

# Output for GitHub Actions (single-line values)
echo "action=$ACTION"
echo "labels=$LABELS"
echo "priority=$PRIORITY"
echo "estimated=$ESTIMATED"
echo "assignee=$ASSIGNEE"

# Write analysis fields to files (for multi-line content)
echo "$PARSED_JSON" | jq -r '.analysis.summary // "Unable to analyze"' > "$OUTPUT_DIR/analysis_summary.txt"
echo "$PARSED_JSON" | jq -r '.analysis.expected_behavior // ""' > "$OUTPUT_DIR/expected_behavior.txt"
echo "$PARSED_JSON" | jq -r '.analysis.current_behavior // ""' > "$OUTPUT_DIR/current_behavior.txt"
echo "$PARSED_JSON" | jq -r '.analysis.affected_files // [] | join(", ")' > "$OUTPUT_DIR/affected_files.txt"
echo "$PARSED_JSON" | jq -r '.analysis.root_cause // ""' > "$OUTPUT_DIR/root_cause.txt"
echo "$PARSED_JSON" | jq -r '.analysis.suggested_approach // ""' > "$OUTPUT_DIR/suggested_approach.txt"
echo "$PARSED_JSON" | jq -r '.auto_fix_rationale // ""' > "$OUTPUT_DIR/auto_fix_rationale.txt"
