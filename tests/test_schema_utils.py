"""Tests for apcore_toolkit.schema_utils — enrich_schema_descriptions()."""

from __future__ import annotations

from typing import Any

from apcore_toolkit.schema_utils import enrich_schema_descriptions


def _make_schema(**props: Any) -> dict[str, Any]:
    return {"type": "object", "properties": props}


class TestEnrichSchemaDescriptions:
    def test_adds_missing_descriptions(self) -> None:
        schema = _make_schema(
            user_id={"type": "integer"},
            name={"type": "string"},
        )
        result = enrich_schema_descriptions(schema, {"user_id": "The user ID", "name": "User name"})
        assert result["properties"]["user_id"]["description"] == "The user ID"
        assert result["properties"]["name"]["description"] == "User name"

    def test_does_not_overwrite_existing(self) -> None:
        schema = _make_schema(
            user_id={"type": "integer", "description": "Original desc"},
        )
        result = enrich_schema_descriptions(schema, {"user_id": "New desc"})
        assert result["properties"]["user_id"]["description"] == "Original desc"

    def test_overwrite_flag(self) -> None:
        schema = _make_schema(
            user_id={"type": "integer", "description": "Original desc"},
        )
        result = enrich_schema_descriptions(schema, {"user_id": "New desc"}, overwrite=True)
        assert result["properties"]["user_id"]["description"] == "New desc"

    def test_ignores_unknown_params(self) -> None:
        schema = _make_schema(user_id={"type": "integer"})
        result = enrich_schema_descriptions(schema, {"nonexistent": "desc"})
        assert "nonexistent" not in result["properties"]
        assert "description" not in result["properties"]["user_id"]

    def test_empty_param_descriptions(self) -> None:
        schema = _make_schema(user_id={"type": "integer"})
        result = enrich_schema_descriptions(schema, {})
        assert result is schema  # no copy needed

    def test_no_properties_key(self) -> None:
        schema = {"type": "object"}
        result = enrich_schema_descriptions(schema, {"x": "desc"})
        assert result is schema

    def test_does_not_mutate_original(self) -> None:
        schema = _make_schema(user_id={"type": "integer"})
        result = enrich_schema_descriptions(schema, {"user_id": "The ID"})
        assert "description" not in schema["properties"]["user_id"]
        assert result["properties"]["user_id"]["description"] == "The ID"

    def test_partial_match(self) -> None:
        schema = _make_schema(
            a={"type": "string"},
            b={"type": "integer", "description": "Existing"},
        )
        result = enrich_schema_descriptions(schema, {"a": "Desc A", "b": "Desc B"})
        assert result["properties"]["a"]["description"] == "Desc A"
        assert result["properties"]["b"]["description"] == "Existing"


class TestTopLevelImport:
    def test_import_from_package(self) -> None:
        from apcore_toolkit import enrich_schema_descriptions as esd

        assert esd is enrich_schema_descriptions
