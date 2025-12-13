import 'dotenv/config';
import Anthropic from '@anthropic-ai/sdk';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { buildStage1Prompt, buildStage2Prompt } from './prompt-builder.js';
import { validateStage1, validateStage2, parseJsonResponse } from './validator.js';
import type {
  Stage1TestCase,
  Stage2TestCase,
  Stage1Response,
  Stage2Response,
  TestResult,
  TestReport,
} from './types.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CASES_DIR = join(__dirname, 'cases');

// Parse command line arguments
const args = process.argv.slice(2);
const stageFilter = args.find(a => a.startsWith('--stage='))?.split('=')[1];
const caseFilter = args.find(a => a.startsWith('--case='))?.split('=')[1];
const verbose = args.includes('--verbose');

// Initialize Anthropic client
const anthropic = new Anthropic();

/**
 * Load test cases from JSON files
 */
function loadTestCases<T>(dir: string): T[] {
  const files = readdirSync(dir).filter(f => f.endsWith('.json'));
  return files
    .filter(f => !caseFilter || f.includes(caseFilter))
    .map(f => {
      const content = readFileSync(join(dir, f), 'utf-8');
      return JSON.parse(content) as T;
    });
}

/**
 * Call Claude API with prompt
 */
async function callClaude(prompt: string, model: string): Promise<string> {
  const response = await anthropic.messages.create({
    model,
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }],
  });

  const textContent = response.content.find(c => c.type === 'text');
  return textContent?.type === 'text' ? textContent.text : '';
}

/**
 * Run Stage 1 test case
 */
async function runStage1Test(testCase: Stage1TestCase): Promise<TestResult> {
  const start = Date.now();
  const errors: string[] = [];

  try {
    const prompt = buildStage1Prompt(testCase.input);

    if (verbose) {
      console.log(`\n--- Prompt for ${testCase.name} ---`);
      console.log(prompt.slice(0, 500) + '...');
    }

    const responseText = await callClaude(prompt, 'claude-sonnet-4-5-20250514');

    if (verbose) {
      console.log(`\n--- Response ---`);
      console.log(responseText);
    }

    const parsed = parseJsonResponse<Stage1Response>(responseText);

    if (!parsed) {
      errors.push('Failed to parse JSON response');
      return {
        name: testCase.name,
        stage: 1,
        passed: false,
        expected: testCase.expected as unknown as Record<string, unknown>,
        actual: { raw: responseText } as Record<string, unknown>,
        errors,
        duration: Date.now() - start,
      };
    }

    const validation = validateStage1(parsed, testCase.expected);

    return {
      name: testCase.name,
      stage: 1,
      passed: validation.passed,
      expected: testCase.expected as unknown as Record<string, unknown>,
      actual: parsed as unknown as Record<string, unknown>,
      errors: validation.errors,
      duration: Date.now() - start,
    };
  } catch (error) {
    errors.push(`Exception: ${error}`);
    return {
      name: testCase.name,
      stage: 1,
      passed: false,
      expected: testCase.expected as unknown as Record<string, unknown>,
      actual: {},
      errors,
      duration: Date.now() - start,
    };
  }
}

/**
 * Run Stage 2 test case
 */
async function runStage2Test(testCase: Stage2TestCase): Promise<TestResult> {
  const start = Date.now();
  const errors: string[] = [];

  try {
    const prompt = buildStage2Prompt(testCase.input);

    if (verbose) {
      console.log(`\n--- Prompt for ${testCase.name} ---`);
      console.log(prompt.slice(0, 500) + '...');
    }

    const responseText = await callClaude(prompt, 'claude-haiku-4-5-20250514');

    if (verbose) {
      console.log(`\n--- Response ---`);
      console.log(responseText);
    }

    const parsed = parseJsonResponse<Stage2Response>(responseText);

    if (!parsed) {
      errors.push('Failed to parse JSON response');
      return {
        name: testCase.name,
        stage: 2,
        passed: false,
        expected: testCase.expected as unknown as Record<string, unknown>,
        actual: { raw: responseText } as Record<string, unknown>,
        errors,
        duration: Date.now() - start,
      };
    }

    const validation = validateStage2(parsed, testCase.expected);

    return {
      name: testCase.name,
      stage: 2,
      passed: validation.passed,
      expected: testCase.expected as unknown as Record<string, unknown>,
      actual: parsed as unknown as Record<string, unknown>,
      errors: validation.errors,
      duration: Date.now() - start,
    };
  } catch (error) {
    errors.push(`Exception: ${error}`);
    return {
      name: testCase.name,
      stage: 2,
      passed: false,
      expected: testCase.expected as unknown as Record<string, unknown>,
      actual: {},
      errors,
      duration: Date.now() - start,
    };
  }
}

/**
 * Print test report
 */
function printReport(report: TestReport): void {
  console.log('\n' + '='.repeat(60));
  console.log('AI Triage Test Results');
  console.log('='.repeat(60));

  // Group by stage
  const stage1Results = report.results.filter(r => r.stage === 1);
  const stage2Results = report.results.filter(r => r.stage === 2);

  if (stage1Results.length > 0) {
    console.log('\nStage 1: Quick Triage');
    for (const result of stage1Results) {
      const icon = result.passed ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
      const actualDecision = (result.actual as { decision?: string }).decision || 'unknown';
      console.log(`  ${icon} ${result.name} (decision: ${actualDecision}) [${result.duration}ms]`);
      if (!result.passed) {
        for (const error of result.errors) {
          console.log(`    \x1b[31m→ ${error}\x1b[0m`);
        }
      }
    }
  }

  if (stage2Results.length > 0) {
    console.log('\nStage 2: Deep Triage');
    for (const result of stage2Results) {
      const icon = result.passed ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
      const actualAction = (result.actual as { action?: string }).action || 'unknown';
      console.log(`  ${icon} ${result.name} (action: ${actualAction}) [${result.duration}ms]`);
      if (!result.passed) {
        for (const error of result.errors) {
          console.log(`    \x1b[31m→ ${error}\x1b[0m`);
        }
      }
    }
  }

  console.log('\n' + '-'.repeat(60));
  const passRate = report.total > 0 ? ((report.passed / report.total) * 100).toFixed(1) : '0';
  const color = report.passed === report.total ? '\x1b[32m' : '\x1b[33m';
  console.log(
    `Summary: ${color}${report.passed}/${report.total} passed (${passRate}%)\x1b[0m`
  );
  console.log(`Total duration: ${report.duration}ms`);
  console.log('='.repeat(60) + '\n');
}

/**
 * Main runner
 */
async function main(): Promise<void> {
  const start = Date.now();
  const results: TestResult[] = [];

  console.log('AI Triage Test Runner');
  console.log('=====================\n');

  // Check API key
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('\x1b[31mError: ANTHROPIC_API_KEY environment variable is required\x1b[0m');
    process.exit(1);
  }

  // Run Stage 1 tests
  if (!stageFilter || stageFilter === '1') {
    const stage1Cases = loadTestCases<Stage1TestCase>(join(CASES_DIR, 'stage1-quick'));
    console.log(`Running ${stage1Cases.length} Stage 1 tests...`);

    for (const testCase of stage1Cases) {
      process.stdout.write(`  Testing: ${testCase.name}...`);
      const result = await runStage1Test(testCase);
      results.push(result);
      console.log(result.passed ? ' \x1b[32mPASS\x1b[0m' : ' \x1b[31mFAIL\x1b[0m');
    }
  }

  // Run Stage 2 tests
  if (!stageFilter || stageFilter === '2') {
    const stage2Cases = loadTestCases<Stage2TestCase>(join(CASES_DIR, 'stage2-deep'));
    console.log(`Running ${stage2Cases.length} Stage 2 tests...`);

    for (const testCase of stage2Cases) {
      process.stdout.write(`  Testing: ${testCase.name}...`);
      const result = await runStage2Test(testCase);
      results.push(result);
      console.log(result.passed ? ' \x1b[32mPASS\x1b[0m' : ' \x1b[31mFAIL\x1b[0m');
    }
  }

  // Generate report
  const report: TestReport = {
    total: results.length,
    passed: results.filter(r => r.passed).length,
    failed: results.filter(r => !r.passed).length,
    results,
    duration: Date.now() - start,
  };

  printReport(report);

  // Exit with error code if any tests failed
  if (report.failed > 0) {
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
