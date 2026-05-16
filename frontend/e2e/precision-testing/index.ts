// Precision Testing E2E Tests
// This file re-exports all test modules

export { test, expect } from './auth';
export { default as repoBindingsTests } from './repo-bindings.spec';
export { default as changeAnalysesTests } from './change-analyses.spec';
export { default as mappingManagerTests } from './mapping-manager.spec';
export { default as impactGraphTests } from './impact-graph.spec';
export { default as riskDashboardTests } from './risk-dashboard.spec';
export { default as precisionRunHistoryTests } from './precision-run-history.spec';