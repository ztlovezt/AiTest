// ============================================================
// 精准测试模块 — Neo4j 图数据库 Schema
// ============================================================
// 在 Neo4j Browser (http://localhost:7474) 中逐段执行
// 或使用: cat schema.cypher | cypher-shell -u neo4j -p testhub
// ============================================================

// ---------- 1. 创建约束(唯一性) ----------
CREATE CONSTRAINT function_id IF NOT EXISTS
    FOR (f:Function) REQUIRE f.id IS UNIQUE;

CREATE CONSTRAINT class_id IF NOT EXISTS
    FOR (c:Class) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT testcase_id IF NOT EXISTS
    FOR (tc:TestCase) REQUIRE tc.id IS UNIQUE;

CREATE CONSTRAINT api_endpoint_id IF NOT EXISTS
    FOR (ae:APIEndpoint) REQUIRE ae.id IS UNIQUE;

// ---------- 2. 创建索引 ----------
CREATE INDEX function_file_idx IF NOT EXISTS
    FOR (f:Function) ON (f.file_path);

CREATE INDEX testcase_title_idx IF NOT EXISTS
    FOR (tc:TestCase) ON (tc.title);

// ---------- 3. 辅助查询:统计各类节点 ----------
// MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt;

// ---------- 4. 辅助查询:查看所有 TESTED_BY 关系 ----------
// MATCH (f:Function)-[r:TESTED_BY]->(tc:TestCase)
// RETURN f.name, tc.title, r.confidence LIMIT 50;

// ---------- 5. 辅助查询:根据函数查找覆盖用例 ----------
// MATCH (f:Function {id: 'apps.projects.views:ProjectViewSet.list'})-[:TESTED_BY]->(tc:TestCase)
// RETURN tc.id, tc.title;

// ---------- 6. 辅助查询:递归查找受影响函数 ----------
// MATCH (f:Function {id: 'apps.projects.views:ProjectViewSet.list'})-[:CALLS*1..5]->(dep:Function)
// RETURN DISTINCT dep.id, dep.name;
