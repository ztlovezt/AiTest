"""Neo4j 图谱健康检查命令。

用法::

    python manage.py verify_graph                    # 只读检查
    python manage.py verify_graph --json             # JSON 输出
    python manage.py verify_graph --fix-orphans      # 删除孤立 Function 节点

检测项：
- 节点 / 关系总量统计
- 孤立节点（无任何入边/出边的 Function/Class）
- 缺失关键属性的节点（id / module / name 任一为空的 Function）
- 重复关系（同一对节点 + 同一类型出现 >1 次）
- TestCase 但无 TESTED_BY 关系（说明用例未关联到代码）
"""
from __future__ import annotations

import json
import sys
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify Neo4j precision-testing graph health and surface inconsistencies"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Emit JSON instead of human-readable output",
        )
        parser.add_argument(
            "--fix-orphans",
            action="store_true",
            dest="fix_orphans",
            help="Delete orphan Function nodes (no incoming/outgoing edges)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Sample size for each issue category (default 20)",
        )

    def handle(self, *args, as_json: bool, fix_orphans: bool, limit: int, **kwargs):
        try:
            from apps.precision_testing.neo4j_client import get_neo4j_client
            from neo4j.exceptions import ServiceUnavailable
        except ImportError as exc:  # pragma: no cover - defensive
            raise CommandError(f"neo4j client unavailable: {exc}") from exc

        client = get_neo4j_client()
        try:
            report = self._collect_report(client, limit=limit)
        except ServiceUnavailable as exc:
            raise CommandError(f"Neo4j unreachable: {exc}") from exc

        if fix_orphans:
            removed = self._delete_orphan_functions(client)
            report["fixed_orphan_functions"] = removed

        if as_json:
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            self._render_human(report)

        if report["issues"]:
            sys.exit(1 if not fix_orphans else 0)

    # ------------------------------------------------------------------
    # 报告采集
    # ------------------------------------------------------------------
    def _collect_report(self, client, *, limit: int) -> dict[str, Any]:
        node_counts = self._count_nodes_by_label(client)
        rel_counts = self._count_rels_by_type(client)
        orphans = self._find_orphan_functions(client, limit=limit)
        missing_props = self._find_missing_props(client, limit=limit)
        duplicate_rels = self._find_duplicate_rels(client, limit=limit)
        unmapped_tcs = self._find_unmapped_testcases(client, limit=limit)

        issues: list[str] = []
        if orphans:
            issues.append(f"orphan_functions={len(orphans)}")
        if missing_props:
            issues.append(f"missing_props={len(missing_props)}")
        if duplicate_rels:
            issues.append(f"duplicate_rels={len(duplicate_rels)}")
        if unmapped_tcs:
            issues.append(f"unmapped_testcases={len(unmapped_tcs)}")

        return {
            "nodes": node_counts,
            "relationships": rel_counts,
            "orphan_functions": orphans,
            "missing_props": missing_props,
            "duplicate_relationships": duplicate_rels,
            "unmapped_testcases": unmapped_tcs,
            "issues": issues,
        }

    def _count_nodes_by_label(self, client) -> dict[str, int]:
        records = client.execute_read(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c"
        )
        return {(r.get("label") or "Unknown"): r["c"] for r in records}

    def _count_rels_by_type(self, client) -> dict[str, int]:
        records = client.execute_read(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c"
        )
        return {r["t"]: r["c"] for r in records}

    def _find_orphan_functions(self, client, *, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (f:Function) "
            "WHERE NOT (f)--() "
            "RETURN f.id AS id, f.module AS module, f.name AS name "
            "LIMIT $limit"
        )
        return client.execute_read(query, {"limit": limit}) or []

    def _find_missing_props(self, client, *, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (f:Function) "
            "WHERE f.id IS NULL OR f.module IS NULL OR f.name IS NULL "
            "RETURN id(f) AS internal_id, f.id AS id, "
            "       f.module AS module, f.name AS name "
            "LIMIT $limit"
        )
        return client.execute_read(query, {"limit": limit}) or []

    def _find_duplicate_rels(self, client, *, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (a)-[r]->(b) "
            "WITH a, b, type(r) AS rel_type, count(*) AS c "
            "WHERE c > 1 "
            "RETURN a.id AS source_id, b.id AS target_id, rel_type, c "
            "LIMIT $limit"
        )
        return client.execute_read(query, {"limit": limit}) or []

    def _find_unmapped_testcases(self, client, *, limit: int) -> list[dict[str, Any]]:
        query = (
            "MATCH (tc:TestCase) "
            "WHERE NOT (:Function)-[:TESTED_BY]->(tc) "
            "RETURN tc.id AS id, tc.title AS title "
            "LIMIT $limit"
        )
        return client.execute_read(query, {"limit": limit}) or []

    def _delete_orphan_functions(self, client) -> int:
        query = (
            "MATCH (f:Function) WHERE NOT (f)--() "
            "WITH f, f.id AS removed_id "
            "DELETE f "
            "RETURN count(removed_id) AS removed"
        )
        records = client.execute_write(query) or []
        return int(records[0]["removed"]) if records else 0

    # ------------------------------------------------------------------
    # 输出
    # ------------------------------------------------------------------
    def _render_human(self, report: dict[str, Any]) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("Node counts:"))
        for label, count in sorted(report["nodes"].items()):
            self.stdout.write(f"  {label:<12} {count}")

        self.stdout.write(self.style.MIGRATE_HEADING("Relationship counts:"))
        for rel_type, count in sorted(report["relationships"].items()):
            self.stdout.write(f"  {rel_type:<12} {count}")

        for category in (
            "orphan_functions",
            "missing_props",
            "duplicate_relationships",
            "unmapped_testcases",
        ):
            items = report.get(category, [])
            if not items:
                continue
            self.stdout.write(
                self.style.WARNING(f"{category} ({len(items)} sampled):")
            )
            for item in items:
                self.stdout.write(f"  {item}")

        if "fixed_orphan_functions" in report:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removed orphan functions: {report['fixed_orphan_functions']}"
                )
            )

        if not report["issues"]:
            self.stdout.write(self.style.SUCCESS("Graph healthy: no issues found"))
        else:
            self.stdout.write(
                self.style.ERROR(f"Issues found: {', '.join(report['issues'])}")
            )
