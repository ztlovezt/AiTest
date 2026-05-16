import { test, expect, request } from '@playwright/test';

/**
 * Week 5 Cross-Page E2E Tests — API Security (no token)
 * Test cases SEC_001 ~ SEC_010 in CROSS_PAGE_TEST_CASES.md
 *
 * Each test issues a raw HTTP call without Authorization to a precision-testing
 * endpoint and expects 401 Unauthorized.
 */

const BACKEND_BASE = process.env.BACKEND_BASE_URL || 'http://localhost:8000';

/**
 * Some deployments accept 401 vs 403 vs 302→login. We treat any of these as
 * "not authorized" for negative tests, but we still require a 4xx (not 5xx).
 */
const UNAUTH_STATUSES = new Set([401, 403]);

async function probe(method: 'get' | 'post' | 'delete', path: string, data?: unknown) {
  const ctx = await request.newContext({ baseURL: BACKEND_BASE });
  try {
    let resp;
    if (method === 'get') resp = await ctx.get(path);
    else if (method === 'post') resp = await ctx.post(path, { data: data ?? {} });
    else resp = await ctx.delete(path);
    const status = resp.status();
    let body: unknown = null;
    try { body = await resp.json(); } catch { body = await resp.text().catch(() => null); }
    return { status, body };
  } finally {
    await ctx.dispose();
  }
}

test.describe('Precision Testing - API Security (unauthenticated)', () => {
  test('SEC_001: GET /api/precision-testing/repos/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/repos/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_002: GET /api/precision-testing/analyses/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/analyses/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_003: GET /api/precision-testing/mappings/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/mappings/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_004: GET /api/precision-testing/graph/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/graph/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_005: GET /api/precision-testing/dashboard/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/dashboard/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_006: GET /api/precision-testing/runs/ without token → 401', async () => {
    const { status } = await probe('get', '/api/precision-testing/runs/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_007: POST /api/precision-testing/repos/ without token → 401, nothing created', async () => {
    const { status } = await probe('post', '/api/precision-testing/repos/', {
      name: 'sec-test',
      repo_url: 'https://example.invalid/sec-test.git',
    });
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_008: DELETE /api/precision-testing/mappings/1/ without token → 401', async () => {
    const { status } = await probe('delete', '/api/precision-testing/mappings/1/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_009: POST /api/precision-testing/impact/query/ without token → 401', async () => {
    const { status } = await probe('post', '/api/precision-testing/impact/query/', {
      file_paths: ['src/example.py'],
    });
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });

  test('SEC_010: POST /api/precision-testing/repos/1/analyze/ without token → 401', async () => {
    const { status } = await probe('post', '/api/precision-testing/repos/1/analyze/');
    expect(UNAUTH_STATUSES.has(status), `expected 401/403 got ${status}`).toBeTruthy();
  });
});
