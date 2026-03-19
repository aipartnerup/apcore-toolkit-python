"""OpenAPI $ref resolution and schema extraction utilities.

Standalone functions extracted from django-apcore's BaseScanner so any
scanner can use them without subclassing.
"""

from __future__ import annotations

from typing import Any


def resolve_ref(ref_string: str, openapi_doc: dict[str, Any]) -> dict[str, Any]:
    """Resolve a JSON $ref pointer like ``#/components/schemas/Foo``.

    Args:
        ref_string: The ``$ref`` value (e.g., ``#/components/schemas/Foo``).
        openapi_doc: The full OpenAPI document dict.

    Returns:
        The resolved schema dict, or empty dict on failure.
    """
    if not ref_string.startswith("#/"):
        return {}
    parts = ref_string[2:].split("/")
    current: Any = openapi_doc
    for part in parts:
        if not isinstance(current, dict):
            return {}
        current = current.get(part, {})
    return current if isinstance(current, dict) else {}


def resolve_schema(
    schema: dict[str, Any],
    openapi_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    """If *schema* contains a ``$ref``, resolve it; otherwise return as-is.

    Args:
        schema: A JSON Schema dict (possibly containing ``$ref``).
        openapi_doc: The full OpenAPI document (needed for ref resolution).

    Returns:
        The resolved or original schema dict.
    """
    if openapi_doc and "$ref" in schema:
        return resolve_ref(schema["$ref"], openapi_doc)
    return schema


def _deep_resolve_refs(
    schema: dict[str, Any],
    openapi_doc: dict[str, Any],
    _depth: int = 0,
) -> dict[str, Any]:
    """Recursively resolve all ``$ref`` pointers in a schema.

    Handles nested ``$ref``, ``allOf``, ``anyOf``, ``oneOf``, and ``items``.
    Depth-limited to 16 levels to prevent infinite recursion.
    """
    if _depth > 16:
        return schema

    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], openapi_doc)
        return _deep_resolve_refs(resolved, openapi_doc, _depth + 1)

    result = dict(schema)

    # Resolve inside allOf/anyOf/oneOf
    for key in ("allOf", "anyOf", "oneOf"):
        if key in result and isinstance(result[key], list):
            result[key] = [_deep_resolve_refs(item, openapi_doc, _depth + 1) for item in result[key]]

    # Resolve array items
    if "items" in result and isinstance(result["items"], dict):
        result["items"] = _deep_resolve_refs(result["items"], openapi_doc, _depth + 1)

    # Resolve nested properties
    if "properties" in result and isinstance(result["properties"], dict):
        result["properties"] = {
            k: _deep_resolve_refs(v, openapi_doc, _depth + 1) for k, v in result["properties"].items()
        }

    return result


def extract_input_schema(
    operation: dict[str, Any],
    openapi_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract input schema from an OpenAPI operation.

    Combines query/path parameters and request body properties into a
    single ``{"type": "object", "properties": ..., "required": ...}`` schema.

    Args:
        operation: An OpenAPI operation dict (e.g., from paths["/users"]["get"]).
        openapi_doc: The full OpenAPI document (for $ref resolution).

    Returns:
        A merged JSON Schema dict for all input parameters.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    # Query/path parameters
    for param in operation.get("parameters", []):
        if param.get("in") in ("query", "path"):
            name = param["name"]
            param_schema = param.get("schema", {"type": "string"})
            param_schema = resolve_schema(param_schema, openapi_doc)
            schema["properties"][name] = param_schema
            if param.get("required", False):
                schema["required"].append(name)

    # Request body
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    body_schema = json_content.get("schema", {})
    if body_schema:
        body_schema = resolve_schema(body_schema, openapi_doc)
        schema["properties"].update(body_schema.get("properties", {}))
        schema["required"].extend(body_schema.get("required", []))

    # Recursively resolve $ref inside individual properties
    if openapi_doc:
        for prop_name, prop_schema in list(schema["properties"].items()):
            schema["properties"][prop_name] = _deep_resolve_refs(prop_schema, openapi_doc)

    return schema


def extract_output_schema(
    operation: dict[str, Any],
    openapi_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract output schema from OpenAPI operation responses (200/201).

    Args:
        operation: An OpenAPI operation dict.
        openapi_doc: The full OpenAPI document (for $ref resolution).

    Returns:
        The output JSON Schema dict, or a default empty object schema.
    """
    responses = operation.get("responses", {})
    for status_code in ("200", "201"):
        response = responses.get(status_code, {})
        content = response.get("content", {})
        json_content = content.get("application/json", {})
        if "schema" in json_content:
            schema: dict[str, Any] = json_content["schema"]
            schema = resolve_schema(schema, openapi_doc)
            # Recursively resolve all nested $ref pointers
            if openapi_doc:
                schema = _deep_resolve_refs(schema, openapi_doc)
            return schema

    return {"type": "object", "properties": {}}
