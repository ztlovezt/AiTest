"""
Extract every module/operation from swagger 2.0 to a structured JSON,
keyed by tag (module). Produces module-level summary + per-operation list
for downstream test plan & test case generation.
"""
import json
from collections import defaultdict
from pathlib import Path

SWAGGER = Path(__file__).parent / "testhub_api_swagger2.json"
OUT_FULL = Path(__file__).parent / "modules_full.json"
OUT_SUMMARY = Path(__file__).parent / "modules_summary.json"

DONE = {"auth", "users", "projects"}


def main():
    spec = json.loads(SWAGGER.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})

    by_tag: dict[str, list] = defaultdict(list)
    for path, ops in paths.items():
        for method, op in ops.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            tags = op.get("tags") or ["_untagged"]
            tag = tags[0]
            params = op.get("parameters", [])
            has_body = any(p.get("in") == "body" for p in params)
            path_params = [p["name"] for p in params if p.get("in") == "path"]
            query_params = [p["name"] for p in params if p.get("in") == "query"]
            entry = {
                "method": method.upper(),
                "path": path,
                "operationId": op.get("operationId", ""),
                "summary": op.get("summary", ""),
                "has_body": has_body,
                "path_params": path_params,
                "query_params": query_params,
                "responses": list(op.get("responses", {}).keys()),
            }
            by_tag[tag].append(entry)

    summary = []
    for tag, items in sorted(by_tag.items(), key=lambda x: -len(x[1])):
        summary.append({
            "module": tag,
            "operations": len(items),
            "paths": len({i["path"] for i in items}),
            "status": "DONE" if tag in DONE else "TODO",
        })

    OUT_FULL.write_text(json.dumps(by_tag, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    total_ops = sum(len(v) for v in by_tag.values())
    print(f"Total tags: {len(by_tag)} | Total operations: {total_ops}")
    print(f"\n{'Module':<30}{'Ops':>6}{'Paths':>8}  Status")
    print("-" * 60)
    for s in summary:
        print(f"{s['module']:<30}{s['operations']:>6}{s['paths']:>8}  {s['status']}")


if __name__ == "__main__":
    main()
