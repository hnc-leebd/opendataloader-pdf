import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import type { Stage1Input, Stage2Input } from './types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..', '..');
const FIXTURES_DIR = join(__dirname, 'fixtures');

/**
 * Build Stage 1 (Quick Triage) prompt - matches ai-triage-1-quick.yml
 */
export function buildStage1Prompt(input: Stage1Input, issueNum: number = 999): string {
  const readmeContent = readFileSync(join(FIXTURES_DIR, 'readme-excerpt.txt'), 'utf-8');
  const existingIssues = readFileSync(join(FIXTURES_DIR, 'existing-issues.txt'), 'utf-8');

  const prompt = `You are a GitHub issue triage bot. Make a quick decision based on limited information.

## Project (from README)
${readmeContent}

## Existing Issues
${existingIssues}

## New Issue #${issueNum}
Title: ${input.title}
Body: ${input.body}

## Decision Required
Based ONLY on the README and issue list above, determine:
1. Is this SPAM or OUT OF SCOPE? (ads, gibberish, abuse, unrelated to project) → "invalid"
2. Is this a DUPLICATE? (very similar to existing issue) → "duplicate"
3. Is this UNCLEAR? (missing reproduction steps, environment, or details) → "question"
4. Otherwise → "valid"

Respond with JSON only:
{
  "decision": "invalid" | "duplicate" | "question" | "valid",
  "duplicate_of": <issue number or null>,
  "reason": "one sentence explanation",
  "questions": ["question1", ...] // only if decision is "question"
}`;

  return prompt;
}

/**
 * Build Stage 2 (Deep Triage) prompt - matches ai-triage-2-deep.yml
 */
export function buildStage2Prompt(input: Stage2Input, issueNum: number = 999): string {
  // Load skill files for context
  const skillDir = join(ROOT_DIR, '.claude', 'skills', 'workflows-ai-triage');

  let aiFixCriteria = '';
  let issuePolicy = '';
  let members = '';

  try {
    aiFixCriteria = readFileSync(join(skillDir, 'ai-fix-criteria.md'), 'utf-8');
    issuePolicy = readFileSync(join(skillDir, 'issue-policy.md'), 'utf-8');
    members = readFileSync(join(skillDir, 'members.md'), 'utf-8');
  } catch {
    // Skills files not found - use defaults
  }

  const issueJson = JSON.stringify({
    title: input.title,
    body: input.body,
    labels: input.labels.map(name => ({ name })),
    comments: input.comments.map(c => ({ author: { login: c.author }, body: c.body }))
  }, null, 2);

  const prompt = `Perform deep triage for GitHub issue #${issueNum}.

## Issue Details
${issueJson}

## AI Fix Criteria
${aiFixCriteria || 'Use standard criteria: simple bugs, typos, type errors are auto-fixable. Architecture changes, security issues require manual review.'}

## Issue Policy
${issuePolicy || 'Priority: P0 (critical), P1 (important), P2 (normal). Story points: 1, 2, 3, 5, 8.'}

## Team Members
${members || 'Available: benedict (available)'}

## Instructions
1. Analyze the issue to understand what it's about
2. Decide action: "auto_fix" or "assign"
   - auto_fix: Simple, localized changes (typos, type errors, simple bugs)
   - assign: Architecture changes, security issues, UX decisions, wide impact
3. Select appropriate labels, priority, and estimate
4. Recommend the best available team member

## Required Output
Respond with JSON only (no markdown code blocks):
{
  "action": "auto_fix" | "assign",
  "labels": ["label1", "label2"],
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
  "auto_fix_rationale": "Why this is/isn't suitable for auto-fix"
}`;

  return prompt;
}
