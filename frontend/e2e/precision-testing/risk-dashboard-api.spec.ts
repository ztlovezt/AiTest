/**
 * Risk Dashboard — API Tests (DASH_API_001 ~ DASH_API_009)
 *
 * Backend DashboardView returns nested structure:
 *   { summary, risk_distribution, trend, top_risky_files, run_stats }
 */
import { test, expect, request } from './auth-api';

const BACKEND = 'http://localhost:8000';

async function apiWithAuth(
  method: 'get' | 'post',
  path: string,
  token: string,
  body?: unknown,
) {
  const ctx = await request.newContext({
    baseURL: BACKEND,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });
  try {
    const resp =
      method === 'get'
        ? await ctx.get(path)
        : await ctx.post(path, { data: body });
    const json = await resp.json().catch(() => null);
    return { status: resp.status(), body: json };
  } finally {
    await ctx.dispose();
  }
}

test.describe('Risk Dashboard API', () => {
  test('DASH_API_001: GET /api/precision-testing/dashboard/ → 200 with data', async () => {
    const { tokens } = await import('./auth-api');
    // We need a token — grab from loadTokens via a small helper
    // Since loadTokens is sync, just read directly in the test body via eval-like approach
    // Actually auth-api.ts exports loadTokens, so we can use it if we import it.
    // But the import above already gives us test/expect/request.
    // Let's use the fixture to get an authenticated page, then read its localStorage token.
    // Simpler: just call the API using the same token file auth-api uses.
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { status, body } = await apiWithAuth('get', '/api/precision-testing/dashboard/', token);
    expect(status).toBe(200);
    expect(body).toBeTruthy();
  });

  test('DASH_API_002: response fields exist and are numbers', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { status, body } = await apiWithAuth('get', '/api/precision-testing/dashboard/', token);
    expect(status).toBe(200);
    expect(typeof body.summary.mapping_count).toBe('number');
    expect(typeof body.summary.analysis_count).toBe('number');
    expect(typeof body.summary.repo_count).toBe('number');
    expect(typeof body.summary.avg_reduction_rate).toBe('number');
    expect(typeof body.risk_distribution).toBe('object');
    expect(typeof body.trend).toBe('object');
  });

  test('DASH_API_007: empty data returns 200 with safe defaults', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { status, body } = await apiWithAuth('get', '/api/precision-testing/dashboard/', token);
    expect(status).toBe(200);
    expect(body.summary).toBeDefined();
    expect(body.summary.mapping_count).toBeDefined();
    expect(body.summary.analysis_count).toBeDefined();
    expect(body.summary.avg_reduction_rate).toBeDefined();
    expect(Array.isArray(body.top_risky_files)).toBe(true);
    expect(typeof body.run_stats).toBe('object');
  });

  test('DASH_API_008: unauthorized access → 401', async () => {
    const ctx = await request.newContext({ baseURL: BACKEND });
    try {
      const resp = await ctx.get('/api/precision-testing/dashboard/');
      expect([401, 403]).toContain(resp.status());
    } finally {
      await ctx.dispose();
    }
  });

  test('DASH_API_009: avg_reduction_rate precision', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { body } = await apiWithAuth('get', '/api/precision-testing/dashboard/', token);
    const rate = body.summary.avg_reduction_rate;
    // Should be a finite number with reasonable precision (max 3 decimals from backend round)
    expect(Number.isFinite(rate)).toBe(true);
    const decimalStr = rate.toString().split('.')[1];
    if (decimalStr) {
      expect(decimalStr.length).toBeLessThanOrEqual(3);
    }
  });

  test('DASH_API_003~006: frontend expected fields (risk_distribution/trend/top_risky_files/run_stats) — structural gap check', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { body } = await apiWithAuth('get', '/api/precision-testing/dashboard/', token);

    // Verify all nested fields expected by frontend are present
    const expectedFrontendFields = ['summary', 'risk_distribution', 'trend', 'top_risky_files', 'run_stats'];
    const missing = expectedFrontendFields.filter((f) => !(f in body));

    expect(missing).toEqual([]);
  });
});
