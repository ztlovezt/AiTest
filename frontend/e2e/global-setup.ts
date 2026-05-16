import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

const TOKEN_PATH = path.resolve(__dirname, '../../test_tokens_clean.json');
const TOKEN_MAX_AGE_MS = 25 * 60 * 1000; // 25 minutes (token expires in 30 min)

/**
 * Playwright global setup: ensure JWT token is fresh before test run.
 *
 * Reads test_tokens_clean.json; if missing or older than 25 minutes,
 * calls backend/generate_test_token.py to regenerate.
 */
export default async function globalSetup(): Promise<void> {
  let needRefresh = true;

  if (fs.existsSync(TOKEN_PATH)) {
    try {
      const stats = fs.statSync(TOKEN_PATH);
      const ageMs = Date.now() - stats.mtimeMs;
      if (ageMs < TOKEN_MAX_AGE_MS) {
        needRefresh = false;
      } else {
        console.log(`[global-setup] Token age ${Math.round(ageMs / 1000)}s exceeds limit, refreshing...`);
      }
    } catch {
      // corrupted or unreadable — regenerate
    }
  }

  if (!needRefresh) {
    console.log('[global-setup] Token is fresh, skipping regeneration.');
    return;
  }

  console.log('[global-setup] Regenerating JWT token...');
  const backendDir = path.resolve(__dirname, '../../backend');

  const py = spawn('python', ['generate_test_token.py'], {
    cwd: backendDir,
    shell: true,
  });

  let stdout = '';
  let stderr = '';
  py.stdout.on('data', (d: Buffer) => {
    stdout += d.toString();
  });
  py.stderr.on('data', (d: Buffer) => {
    stderr += d.toString();
  });

  await new Promise<void>((resolve, reject) => {
    py.on('close', (code: number | null) => {
      if (code !== 0) {
        reject(new Error(`Token generation failed (code ${code}): ${stderr}`));
      } else {
        resolve();
      }
    });
    py.on('error', (err) => reject(err));
  });

  // Django logging may pollute stdout; extract the JSON line
  const jsonLine = stdout
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('{'))
    .pop();

  if (!jsonLine) {
    throw new Error(`No JSON found in token script output. stdout:\n${stdout}\nstderr:\n${stderr}`);
  }

  // Validate JSON before writing
  JSON.parse(jsonLine);
  fs.writeFileSync(TOKEN_PATH, jsonLine, 'utf-8');
  console.log('[global-setup] Token regenerated successfully.');
}
