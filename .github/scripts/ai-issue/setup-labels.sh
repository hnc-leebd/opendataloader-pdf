#!/bin/bash
# Setup GitHub labels from labels.md definition
# Usage: ./scripts/setup-labels.sh

set -e

echo "Creating/updating GitHub labels..."

# Stage Status Labels
gh label create "ai-issue/triaged" --color "FBCA04" --description "Stage 1 (Triage) completed" --force
gh label create "ai-issue/analyzed" --color "D93F0B" --description "Stage 2 (Analyze) completed" --force
gh label create "ai-issue/fixed" --color "0E8A16" --description "Stage 3 (Fix) completed (PR created)" --force

# Triage Result Labels
gh label create "ai-issue/valid" --color "0E8A16" --description "Valid issue, proceed to Stage 2" --force
gh label create "ai-issue/invalid" --color "666666" --description "Out of scope or spam" --force
gh label create "ai-issue/duplicate" --color "CFD3D7" --description "Duplicate of existing issue" --force
gh label create "ai-issue/needs-info" --color "D876E3" --description "Needs more information" --force

# Action Labels
gh label create "fix/auto-eligible" --color "0E8A16" --description "Eligible for auto-fix" --force
gh label create "fix/manual-required" --color "FBCA04" --description "Requires human implementation" --force
gh label create "respond/comment-only" --color "C5DEF5" --description "No code change needed, respond with comment" --force

# Type Labels
gh label create "type/bug" --color "D73A4A" --description "Bug report" --force
gh label create "type/enhancement" --color "A2EEEF" --description "Feature request or improvement" --force
gh label create "type/docs" --color "0075CA" --description "Documentation" --force
gh label create "type/dependencies" --color "0366D6" --description "Dependency update" --force

# Priority Labels
gh label create "priority/P0" --color "B60205" --description "Critical - production blocking" --force
gh label create "priority/P1" --color "D93F0B" --description "Important - not immediately blocking" --force
gh label create "priority/P2" --color "FBCA04" --description "Normal or low priority" --force

echo "Done! All labels created/updated."
