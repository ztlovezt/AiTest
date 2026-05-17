#!/usr/bin/env python3
"""Convert OpenAPI 3.0 YAML/JSON to Swagger 2.0 JSON."""

import json
import sys
import copy
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not found. Install: pip install pyyaml")
    sys.exit(1)


def resolve_schema(schema, components):
    """Resolve $ref in schema."""
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/components/"):
            parts = ref.replace("#/components/", "").split("/")
            current = components
            for p in parts:
                current = current.get(p, {})
            return current
    result = {}
    for k, v in schema.items():
        result[k] = resolve_schema(v, components)
    return result


def convert_schema(schema, components):
    """Convert OAS3 schema object to Swagger 2.0."""
    if not isinstance(schema, dict):
        return schema
    result = {}
    for k, v in schema.items():
        if k == "nullable":
            # Swagger 2.0 does not support nullable; use x-nullable extension
            result["x-nullable"] = v
        elif k == "allOf":
            result[k] = [convert_schema(item, components) for item in v]
        elif k == "anyOf":
            # Swagger 2.0 does not support anyOf; approximate with first option + x-anyOf
            result["x-anyOf"] = [convert_schema(item, components) for item in v]
            if v:
                merged = copy.deepcopy(v[0])
                for item in v[1:]:
                    if isinstance(item, dict) and isinstance(merged, dict):
                        merged.update(item)
                result.update(convert_schema(merged, components))
        elif k == "oneOf":
            result["x-oneOf"] = [convert_schema(item, components) for item in v]
            if v:
                result.update(convert_schema(v[0], components))
        elif k == "discriminator":
            result["discriminator"] = v
        elif k == "xml":
            result[k] = v
        elif k == "example":
            result["example"] = v
        elif k == "deprecated":
            result["x-deprecated"] = v
        elif k == "writeOnly":
            result["x-writeOnly"] = v
        elif k == "readOnly":
            result[k] = v
        elif k == "format":
            result[k] = v
        elif k == "default":
            result[k] = v
        elif k == "description":
            result[k] = v
        elif k == "enum":
            result[k] = v
        elif k == "type":
            result[k] = v
        elif k == "items":
            result[k] = convert_schema(v, components)
        elif k == "properties":
            result[k] = {pk: convert_schema(pv, components) for pk, pv in v.items()}
        elif k == "additionalProperties":
            if isinstance(v, dict):
                result[k] = convert_schema(v, components)
            else:
                result[k] = v
        elif k == "required":
            result[k] = v
        elif k == "minimum":
            result[k] = v
        elif k == "maximum":
            result[k] = v
        elif k == "minLength":
            result[k] = v
        elif k == "maxLength":
            result[k] = v
        elif k == "pattern":
            result[k] = v
        elif k == "minItems":
            result[k] = v
        elif k == "maxItems":
            result[k] = v
        elif k == "uniqueItems":
            result[k] = v
        elif k == "multipleOf":
            result[k] = v
        elif k == "exclusiveMinimum":
            result[k] = v
        elif k == "exclusiveMaximum":
            result[k] = v
        elif k == "minProperties":
            result[k] = v
        elif k == "maxProperties":
            result[k] = v
        elif k == "$ref":
            ref = v
            if ref.startswith("#/components/"):
                ref = ref.replace("#/components/", "#/")
            result["$ref"] = ref
        else:
            # Keep unknown keys as-is (extensions, etc.)
            result[k] = v
    return result


def convert_parameter(param, components):
    """Convert OAS3 parameter to Swagger 2.0."""
    result = {
        "name": param.get("name", ""),
        "in": param.get("in", "query"),
        "required": param.get("required", False),
    }
    if "description" in param:
        result["description"] = param["description"]
    if "deprecated" in param:
        result["x-deprecated"] = param["deprecated"]

    schema = param.get("schema", {})
    if schema:
        schema = convert_schema(schema, components)
        # Inline schema properties into parameter
        for k in ["type", "format", "items", "enum", "default", "minimum", "maximum",
                  "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems",
                  "multipleOf", "exclusiveMinimum", "exclusiveMaximum", "minProperties",
                  "maxProperties", "properties", "additionalProperties", "allOf", "example"]:
            if k in schema:
                result[k] = schema[k]
        if "$ref" in schema:
            result["schema"] = schema
    if result.get("in") == "path":
        result["required"] = True
    return result


def convert_request_body(request_body, components):
    """Convert OAS3 requestBody to Swagger 2.0 body parameter."""
    if not request_body:
        return None
    if "$ref" in request_body:
        ref = request_body["$ref"]
        if ref.startswith("#/components/"):
            parts = ref.replace("#/components/", "").split("/")
            current = components
            for p in parts:
                current = current.get(p, {})
            request_body = current

    content = request_body.get("content", {})
    if not content:
        return None

    # Pick the first content type, or application/json if available
    content_type = None
    if "application/json" in content:
        content_type = "application/json"
    else:
        content_type = list(content.keys())[0]

    media = content.get(content_type, {})
    schema = media.get("schema", {})
    result = {
        "name": "body",
        "in": "body",
        "required": request_body.get("required", False),
    }
    if schema:
        schema = convert_schema(schema, components)
        result["schema"] = schema
    if "description" in request_body:
        result["description"] = request_body["description"]
    return result, content_type


def convert_response(response, components):
    """Convert OAS3 response to Swagger 2.0."""
    if not isinstance(response, dict):
        return response
    if "$ref" in response:
        ref = response["$ref"]
        if ref.startswith("#/components/"):
            parts = ref.replace("#/components/", "").split("/")
            current = components
            for p in parts:
                current = current.get(p, {})
            response = current

    result = {}
    if "description" in response:
        result["description"] = response["description"]
    if "headers" in response:
        result["headers"] = response["headers"]
    if "content" in response:
        content = response["content"]
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            if schema:
                result["schema"] = convert_schema(schema, components)
        elif content:
            first = list(content.keys())[0]
            schema = content[first].get("schema", {})
            if schema:
                result["schema"] = convert_schema(schema, components)
    if "links" in response:
        result["x-links"] = response["links"]
    return result


def convert_security_scheme(scheme):
    """Convert OAS3 security scheme to Swagger 2.0."""
    stype = scheme.get("type", "")
    if stype == "http" and scheme.get("scheme") == "bearer":
        return {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": scheme.get("description", "JWT Bearer token")
        }
    elif stype == "http" and scheme.get("scheme") == "basic":
        return {
            "type": "basic",
            "description": scheme.get("description", "")
        }
    elif stype == "apiKey":
        return {
            "type": "apiKey",
            "name": scheme.get("name", ""),
            "in": scheme.get("in", "header"),
            "description": scheme.get("description", "")
        }
    elif stype == "oauth2":
        result = {
            "type": "oauth2",
            "description": scheme.get("description", "")
        }
        flows = scheme.get("flows", {})
        if "implicit" in flows:
            result["flow"] = "implicit"
            result["authorizationUrl"] = flows["implicit"].get("authorizationUrl", "")
            result["scopes"] = flows["implicit"].get("scopes", {})
        elif "password" in flows:
            result["flow"] = "password"
            result["tokenUrl"] = flows["password"].get("tokenUrl", "")
            result["scopes"] = flows["password"].get("scopes", {})
        elif "clientCredentials" in flows:
            result["flow"] = "application"
            result["tokenUrl"] = flows["clientCredentials"].get("tokenUrl", "")
            result["scopes"] = flows["clientCredentials"].get("scopes", {})
        elif "authorizationCode" in flows:
            result["flow"] = "accessCode"
            result["authorizationUrl"] = flows["authorizationCode"].get("authorizationUrl", "")
            result["tokenUrl"] = flows["authorizationCode"].get("tokenUrl", "")
            result["scopes"] = flows["authorizationCode"].get("scopes", {})
        return result
    else:
        return scheme


def convert_servers(servers):
    """Extract host, basePath, schemes from servers."""
    if not servers:
        return {}, {}, {}
    first = servers[0]
    url = first.get("url", "")
    # Remove protocol
    scheme = "https"
    if "://" in url:
        scheme, rest = url.split("://", 1)
        url = rest
    else:
        scheme = "https"
    # Split host and path
    parts = url.split("/", 1)
    host = parts[0]
    base_path = "/" + parts[1] if len(parts) > 1 else "/"
    # Remove variable placeholders like {port}
    host = host.replace("{", "").replace("}", "")
    base_path = base_path.replace("{", "").replace("}", "")
    return {"host": host}, {"basePath": base_path}, {"schemes": [scheme]}


def convert_openapi3_to_swagger2(data):
    """Main conversion function."""
    swagger = {
        "swagger": "2.0",
        "info": copy.deepcopy(data.get("info", {})),
    }

    # Servers → host, basePath, schemes
    servers = data.get("servers", [])
    host_dict, base_dict, schemes_dict = convert_servers(servers)
    swagger.update(host_dict)
    swagger.update(base_dict)
    swagger.update(schemes_dict)

    # Tags
    if "tags" in data:
        swagger["tags"] = copy.deepcopy(data["tags"])

    # External docs
    if "externalDocs" in data:
        swagger["externalDocs"] = copy.deepcopy(data["externalDocs"])

    components = data.get("components", {})

    # Paths
    paths = {}
    swagger["paths"] = paths
    for path, path_item in data.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        new_path_item = {}
        for method, operation in path_item.items():
            if method.startswith("x-") or method == "parameters":
                new_path_item[method] = copy.deepcopy(operation)
                continue
            if not isinstance(operation, dict):
                continue
            new_op = {}
            # Copy simple fields
            for k in ["tags", "summary", "description", "operationId", "deprecated",
                      "callbacks", "security"]:
                if k in operation:
                    new_op[k] = copy.deepcopy(operation[k])
            # Parameters
            parameters = []
            if "parameters" in operation:
                for param in operation["parameters"]:
                    parameters.append(convert_parameter(param, components))
            # Request body → body parameter
            if "requestBody" in operation:
                body_param, content_type = convert_request_body(operation["requestBody"], components)
                if body_param:
                    parameters.append(body_param)
                    # Also add Consumes for this operation
                    new_op.setdefault("consumes", []).append(content_type)
            if parameters:
                new_op["parameters"] = parameters
            # Responses
            if "responses" in operation:
                new_op["responses"] = {}
                for code, response in operation["responses"].items():
                    new_op["responses"][code] = convert_response(response, components)
            # Servers at operation level → host override (not supported in Swagger 2.0)
            if "servers" in operation:
                new_op["x-servers"] = copy.deepcopy(operation["servers"])
            new_path_item[method] = new_op
        paths[path] = new_path_item

    # Definitions (from components/schemas)
    schemas = components.get("schemas", {})
    if schemas:
        swagger["definitions"] = {}
        for name, schema in schemas.items():
            swagger["definitions"][name] = convert_schema(schema, components)

    # Security definitions
    security_schemes = components.get("securitySchemes", {})
    if security_schemes:
        swagger["securityDefinitions"] = {}
        for name, scheme in security_schemes.items():
            swagger["securityDefinitions"][name] = convert_security_scheme(scheme)

    # Global security
    if "security" in data:
        swagger["security"] = copy.deepcopy(data["security"])

    # Components/responses → x-responses (not native in Swagger 2.0)
    responses = components.get("responses", {})
    if responses:
        swagger["x-responses"] = {}
        for name, response in responses.items():
            swagger["x-responses"][name] = convert_response(response, components)

    # Components/parameters → x-parameters (not native in Swagger 2.0)
    params = components.get("parameters", {})
    if params:
        swagger["x-parameters"] = {}
        for name, param in params.items():
            swagger["x-parameters"][name] = convert_parameter(param, components)

    # Components/examples → x-examples
    examples = components.get("examples", {})
    if examples:
        swagger["x-examples"] = copy.deepcopy(examples)

    # Components/requestBodies → x-requestBodies
    request_bodies = components.get("requestBodies", {})
    if request_bodies:
        swagger["x-requestBodies"] = copy.deepcopy(request_bodies)

    # Components/headers → x-headers
    headers = components.get("headers", {})
    if headers:
        swagger["x-headers"] = copy.deepcopy(headers)

    # Components/links → x-links
    links = components.get("links", {})
    if links:
        swagger["x-links"] = copy.deepcopy(links)

    # Remove empty arrays/objects
    for key in list(swagger.keys()):
        if swagger[key] in ([], {}, None):
            del swagger[key]

    return swagger


def main():
    if len(sys.argv) < 2:
        input_file = "/tmp/testhub_openapi3.yaml"
    else:
        input_file = sys.argv[1]

    output_file = str(Path(input_file).with_suffix("")) + "_swagger2.json"

    print(f"Reading: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    print("Converting OpenAPI 3.0 → Swagger 2.0...")
    swagger = convert_openapi3_to_swagger2(data)

    print(f"Writing: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(swagger, f, ensure_ascii=False, indent=2)

    print(f"Done! Output: {output_file}")
    # Print summary
    paths_count = len(swagger.get("paths", {}))
    defs_count = len(swagger.get("definitions", {}))
    print(f"  Paths: {paths_count}")
    print(f"  Definitions: {defs_count}")


if __name__ == "__main__":
    main()
