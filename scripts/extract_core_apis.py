"""提取核心模块接口元数据 (Step 1: Input Understanding)

从 testhub_api_swagger2.json 中抽取 auth/users/projects 模块的接口元数据,
解析路径参数、请求体 schema、响应 schema 与认证要求,输出结构化 JSON 文件。
"""
import json
import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parent
SWAGGER = ROOT / "testhub_api_swagger2.json"
OUTPUT = ROOT / "core_apis_metadata.json"
TARGET_MODULES = ["auth", "users", "projects"]


def resolve_ref(ref: str, definitions: dict, seen: set | None = None) -> dict:
    """递归解析 $ref 引用,避免循环引用。"""
    seen = seen or set()
    if ref in seen:
        return {"_circular": ref}
    seen = seen | {ref}
    name = ref.rsplit("/", 1)[-1]
    schema = definitions.get(name, {})
    return inline_schema(deepcopy(schema), definitions, seen)


def inline_schema(schema: dict, definitions: dict, seen: set | None = None) -> dict:
    """把 schema 内的 $ref 全部就地展开。"""
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        return resolve_ref(schema["$ref"], definitions, seen)
    for k, v in list(schema.items()):
        if isinstance(v, dict):
            schema[k] = inline_schema(v, definitions, seen)
        elif isinstance(v, list):
            schema[k] = [inline_schema(it, definitions, seen) if isinstance(it, dict) else it for it in v]
    return schema


def extract_core(swagger: dict) -> list[dict]:
    definitions = swagger.get("definitions", {})
    apis = []
    for path, ops in swagger.get("paths", {}).items():
        segs = path.strip("/").split("/")
        if len(segs) < 2:
            continue
        module = segs[1]
        if module not in TARGET_MODULES:
            continue
        for method, op in ops.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            params = []
            body_schema = None
            for p in op.get("parameters", []):
                p = deepcopy(p)
                if "schema" in p:
                    p["schema"] = inline_schema(p["schema"], definitions)
                if p.get("in") == "body":
                    body_schema = p.get("schema")
                else:
                    params.append({
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": p.get("required", False),
                        "type": p.get("type"),
                        "description": p.get("description", ""),
                    })
            responses = {}
            for code, resp in op.get("responses", {}).items():
                resp = deepcopy(resp)
                if "schema" in resp:
                    resp["schema"] = inline_schema(resp["schema"], definitions)
                responses[code] = resp
            apis.append({
                "module": module,
                "path": path,
                "method": method.upper(),
                "operationId": op.get("operationId"),
                "summary": op.get("summary", ""),
                "description": op.get("description", ""),
                "tags": op.get("tags", []),
                "parameters": params,
                "body_schema": body_schema,
                "responses": responses,
                "security": op.get("security", []),
            })
    return apis


def main():
    if not SWAGGER.exists():
        sys.exit(f"swagger file not found: {SWAGGER}")
    swagger = json.loads(SWAGGER.read_text(encoding="utf-8"))
    apis = extract_core(swagger)
    OUTPUT.write_text(json.dumps(apis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"extracted {len(apis)} operations -> {OUTPUT}")
    from collections import Counter
    cnt = Counter((a["module"], a["method"]) for a in apis)
    for (mod, mth), c in sorted(cnt.items()):
        print(f"  {mod:10s} {mth:6s} {c}")


if __name__ == "__main__":
    main()
