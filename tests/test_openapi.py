"""Tests for apcore_toolkit.openapi — OpenAPI utilities."""

from __future__ import annotations

from apcore_toolkit.openapi import (
    _deep_resolve_refs,
    extract_input_schema,
    extract_output_schema,
    resolve_ref,
    resolve_schema,
)

OPENAPI_DOC = {
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
                "required": ["id", "name"],
            },
            "UserList": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/User"},
            },
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                },
            },
            "UserWithAddress": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "address": {"$ref": "#/components/schemas/Address"},
                },
            },
            "AdminUser": {
                "allOf": [
                    {"$ref": "#/components/schemas/User"},
                    {
                        "type": "object",
                        "properties": {"role": {"type": "string"}},
                    },
                ],
            },
            "SelfRef": {
                "type": "object",
                "properties": {
                    "child": {"$ref": "#/components/schemas/SelfRef"},
                },
            },
        }
    }
}


class TestResolveRef:
    def test_resolve_existing_ref(self) -> None:
        result = resolve_ref("#/components/schemas/User", OPENAPI_DOC)
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_resolve_nonexistent_ref(self) -> None:
        result = resolve_ref("#/components/schemas/Missing", OPENAPI_DOC)
        assert result == {}

    def test_non_hash_ref(self) -> None:
        result = resolve_ref("external.yaml#/Foo", OPENAPI_DOC)
        assert result == {}

    def test_ref_to_non_dict(self) -> None:
        doc = {"components": {"schemas": {"Leaf": "not-a-dict"}}}
        result = resolve_ref("#/components/schemas/Leaf", doc)
        assert result == {}

    def test_ref_through_missing_path(self) -> None:
        result = resolve_ref("#/a/b/c", OPENAPI_DOC)
        assert result == {}


class TestResolveSchema:
    def test_ref_schema(self) -> None:
        schema = {"$ref": "#/components/schemas/User"}
        result = resolve_schema(schema, OPENAPI_DOC)
        assert result["type"] == "object"

    def test_inline_schema(self) -> None:
        schema = {"type": "string"}
        result = resolve_schema(schema, OPENAPI_DOC)
        assert result == {"type": "string"}

    def test_no_openapi_doc(self) -> None:
        schema = {"$ref": "#/components/schemas/User"}
        result = resolve_schema(schema, None)
        assert result == schema


class TestDeepResolveRefs:
    def test_top_level_ref(self) -> None:
        schema = {"$ref": "#/components/schemas/User"}
        result = _deep_resolve_refs(schema, OPENAPI_DOC)
        assert result["type"] == "object"
        assert "id" in result["properties"]
        assert "name" in result["properties"]

    def test_nested_ref_in_properties(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "address": {"$ref": "#/components/schemas/Address"},
            },
        }
        result = _deep_resolve_refs(schema, OPENAPI_DOC)
        assert result["properties"]["address"]["type"] == "object"
        assert "street" in result["properties"]["address"]["properties"]

    def test_ref_in_allof(self) -> None:
        schema = {
            "allOf": [
                {"$ref": "#/components/schemas/User"},
                {"type": "object", "properties": {"extra": {"type": "boolean"}}},
            ]
        }
        result = _deep_resolve_refs(schema, OPENAPI_DOC)
        assert result["allOf"][0]["type"] == "object"
        assert "id" in result["allOf"][0]["properties"]
        assert result["allOf"][1]["properties"]["extra"]["type"] == "boolean"

    def test_ref_in_anyof(self) -> None:
        schema = {
            "anyOf": [
                {"$ref": "#/components/schemas/User"},
                {"$ref": "#/components/schemas/Address"},
            ]
        }
        result = _deep_resolve_refs(schema, OPENAPI_DOC)
        assert result["anyOf"][0]["type"] == "object"
        assert "name" in result["anyOf"][0]["properties"]
        assert "street" in result["anyOf"][1]["properties"]

    def test_ref_in_array_items(self) -> None:
        schema = {"type": "array", "items": {"$ref": "#/components/schemas/User"}}
        result = _deep_resolve_refs(schema, OPENAPI_DOC)
        assert result["items"]["type"] == "object"
        assert "id" in result["items"]["properties"]

    def test_deeply_nested_ref(self) -> None:
        result = _deep_resolve_refs({"$ref": "#/components/schemas/UserWithAddress"}, OPENAPI_DOC)
        assert result["properties"]["address"]["type"] == "object"
        assert "street" in result["properties"]["address"]["properties"]

    def test_circular_ref_depth_limit(self) -> None:
        result = _deep_resolve_refs({"$ref": "#/components/schemas/SelfRef"}, OPENAPI_DOC)
        # Should not raise — depth limit stops recursion.
        assert result["type"] == "object"
        assert "child" in result["properties"]

    def test_no_mutation_of_original(self) -> None:
        original_address = OPENAPI_DOC["components"]["schemas"]["Address"]
        original_props = dict(original_address.get("properties", {}))
        schema = {"$ref": "#/components/schemas/UserWithAddress"}
        _deep_resolve_refs(schema, OPENAPI_DOC)
        assert OPENAPI_DOC["components"]["schemas"]["Address"]["properties"] == original_props


class TestExtractInputSchema:
    def test_query_and_path_params(self) -> None:
        operation = {
            "parameters": [
                {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                {"name": "q", "in": "query", "schema": {"type": "string"}},
            ]
        }
        result = extract_input_schema(operation)
        assert result["properties"]["user_id"] == {"type": "integer"}
        assert result["properties"]["q"] == {"type": "string"}
        assert "user_id" in result["required"]
        assert "q" not in result["required"]

    def test_request_body(self) -> None:
        operation = {
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        }
                    }
                }
            }
        }
        result = extract_input_schema(operation)
        assert "name" in result["properties"]
        assert "name" in result["required"]

    def test_ref_in_request_body(self) -> None:
        operation = {
            "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}}
        }
        result = extract_input_schema(operation, OPENAPI_DOC)
        assert "name" in result["properties"]

    def test_ref_in_param_schema(self) -> None:
        operation = {
            "parameters": [
                {"name": "user", "in": "query", "required": True, "schema": {"$ref": "#/components/schemas/User"}},
            ]
        }
        result = extract_input_schema(operation, OPENAPI_DOC)
        assert result["properties"]["user"]["type"] == "object"

    def test_nested_ref_in_body_properties(self) -> None:
        operation = {
            "requestBody": {
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserWithAddress"}}}
            }
        }
        result = extract_input_schema(operation, OPENAPI_DOC)
        assert result["properties"]["address"]["type"] == "object"
        assert "street" in result["properties"]["address"]["properties"]

    def test_empty_operation(self) -> None:
        result = extract_input_schema({})
        assert result["type"] == "object"
        assert result["properties"] == {}
        assert result["required"] == []


class TestExtractOutputSchema:
    def test_200_response(self) -> None:
        operation = {
            "responses": {
                "200": {
                    "content": {
                        "application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}
                    }
                }
            }
        }
        result = extract_output_schema(operation)
        assert result["properties"]["ok"]["type"] == "boolean"

    def test_201_response(self) -> None:
        operation = {
            "responses": {
                "201": {
                    "content": {
                        "application/json": {"schema": {"type": "object", "properties": {"id": {"type": "integer"}}}}
                    }
                }
            }
        }
        result = extract_output_schema(operation)
        assert "id" in result["properties"]

    def test_200_preferred_over_201(self) -> None:
        operation = {
            "responses": {
                "200": {"content": {"application/json": {"schema": {"type": "string"}}}},
                "201": {"content": {"application/json": {"schema": {"type": "integer"}}}},
            }
        }
        result = extract_output_schema(operation)
        assert result["type"] == "string"

    def test_ref_in_response(self) -> None:
        operation = {
            "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}}}
        }
        result = extract_output_schema(operation, OPENAPI_DOC)
        assert result["type"] == "object"

    def test_array_with_ref_items(self) -> None:
        operation = {
            "responses": {
                "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserList"}}}}
            }
        }
        result = extract_output_schema(operation, OPENAPI_DOC)
        assert result["type"] == "array"
        assert result["items"]["type"] == "object"

    def test_no_matching_response(self) -> None:
        operation = {"responses": {"404": {}}}
        result = extract_output_schema(operation)
        assert result == {"type": "object", "properties": {}}

    def test_nested_ref_in_response_properties(self) -> None:
        operation = {
            "responses": {
                "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserWithAddress"}}}}
            }
        }
        result = extract_output_schema(operation, OPENAPI_DOC)
        assert result["type"] == "object"
        assert result["properties"]["address"]["type"] == "object"
        assert "street" in result["properties"]["address"]["properties"]

    def test_allof_composition_in_response(self) -> None:
        operation = {
            "responses": {
                "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminUser"}}}}
            }
        }
        result = extract_output_schema(operation, OPENAPI_DOC)
        assert result["allOf"][0]["type"] == "object"
        assert "id" in result["allOf"][0]["properties"]
        assert result["allOf"][1]["properties"]["role"]["type"] == "string"

    def test_empty_responses(self) -> None:
        result = extract_output_schema({})
        assert result == {"type": "object", "properties": {}}
