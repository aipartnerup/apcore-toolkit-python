"""Tests for apcore_toolkit.ai_enhancer — AIEnhancer."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from apcore import ModuleAnnotations

from apcore_toolkit.ai_enhancer import AIEnhancer
from apcore_toolkit.types import ScannedModule


@pytest.fixture
def enhancer() -> AIEnhancer:
    return AIEnhancer(endpoint="http://localhost:11434/v1", model="test-model", threshold=0.7, timeout=10)


@pytest.fixture
def sparse_module() -> ScannedModule:
    """A module with missing metadata (gaps to fill)."""
    return ScannedModule(
        module_id="legacy.handler",
        description="",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        tags=["legacy"],
        target="legacy.views:handler",
    )


@pytest.fixture
def complete_module() -> ScannedModule:
    """A module with all metadata filled (no gaps)."""
    return ScannedModule(
        module_id="users.get_user",
        description="Get a user by ID",
        input_schema={"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
        output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        tags=["users"],
        target="myapp.views:get_user",
        documentation="Returns a user object given an ID.",
        annotations=ModuleAnnotations(readonly=True),
    )


class TestIsEnabled:
    def test_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert AIEnhancer.is_enabled() is False

    def test_enabled_true(self) -> None:
        with patch.dict(os.environ, {"APCORE_AI_ENABLED": "true"}):
            assert AIEnhancer.is_enabled() is True

    def test_enabled_1(self) -> None:
        with patch.dict(os.environ, {"APCORE_AI_ENABLED": "1"}):
            assert AIEnhancer.is_enabled() is True

    def test_enabled_yes(self) -> None:
        with patch.dict(os.environ, {"APCORE_AI_ENABLED": "yes"}):
            assert AIEnhancer.is_enabled() is True

    def test_disabled_false(self) -> None:
        with patch.dict(os.environ, {"APCORE_AI_ENABLED": "false"}):
            assert AIEnhancer.is_enabled() is False


class TestIdentifyGaps:
    def test_no_gaps_for_complete_module(self, enhancer: AIEnhancer, complete_module: ScannedModule) -> None:
        gaps = enhancer._identify_gaps(complete_module)
        assert gaps == []

    def test_empty_description(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        gaps = enhancer._identify_gaps(sparse_module)
        assert "description" in gaps

    def test_description_equals_module_id(self, enhancer: AIEnhancer) -> None:
        module = ScannedModule(
            module_id="test.func",
            description="test.func",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
            output_schema={},
            tags=[],
            target="m:f",
            documentation="Some docs",
            annotations=ModuleAnnotations(readonly=True),
        )
        gaps = enhancer._identify_gaps(module)
        assert "description" in gaps

    def test_missing_documentation(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        gaps = enhancer._identify_gaps(sparse_module)
        assert "documentation" in gaps

    def test_default_annotations(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        gaps = enhancer._identify_gaps(sparse_module)
        assert "annotations" in gaps

    def test_empty_input_schema(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        gaps = enhancer._identify_gaps(sparse_module)
        assert "input_schema" in gaps


class TestParseResponse:
    def test_valid_json(self) -> None:
        response = '{"description": "Hello", "confidence": {"description": 0.9}}'
        result = AIEnhancer._parse_response(response)
        assert result["description"] == "Hello"

    def test_json_with_markdown_fences(self) -> None:
        response = '```json\n{"description": "Hello"}\n```'
        result = AIEnhancer._parse_response(response)
        assert result["description"] == "Hello"

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="SLM returned invalid JSON"):
            AIEnhancer._parse_response("not json at all")


class TestBuildPrompt:
    def test_prompt_contains_module_id(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        prompt = enhancer._build_prompt(sparse_module, ["description"])
        assert "legacy.handler" in prompt

    def test_prompt_requests_description(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        prompt = enhancer._build_prompt(sparse_module, ["description"])
        assert '"description"' in prompt

    def test_prompt_requests_annotations(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        prompt = enhancer._build_prompt(sparse_module, ["annotations"])
        assert '"readonly"' in prompt
        assert '"destructive"' in prompt

    def test_prompt_requests_input_schema(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        prompt = enhancer._build_prompt(sparse_module, ["input_schema"])
        assert '"input_schema"' in prompt


class TestEnhanceModule:
    def test_applies_description_above_threshold(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps(
            {
                "description": "Handle legacy requests",
                "confidence": {"description": 0.92},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["description"])

        assert result.description == "Handle legacy requests"
        assert result.metadata["x-generated-by"] == "slm"
        assert result.metadata["x-ai-confidence"]["description"] == 0.92

    def test_skips_description_below_threshold(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps(
            {
                "description": "Maybe this?",
                "confidence": {"description": 0.3},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["description"])

        assert result.description == ""  # unchanged
        assert any("Low confidence" in w for w in result.warnings)

    def test_applies_annotations_selectively(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps(
            {
                "annotations": {
                    "readonly": True,
                    "destructive": False,
                    "open_world": True,
                },
                "confidence": {
                    "annotations.readonly": 0.85,
                    "annotations.destructive": 0.40,  # below threshold
                    "annotations.open_world": 0.90,
                },
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["annotations"])

        assert result.annotations is not None
        assert result.annotations.readonly is True
        assert result.annotations.open_world is True
        # destructive was below threshold, should remain at default (False)
        assert result.annotations.destructive is False
        assert any("annotations.destructive" in w for w in result.warnings)

    def test_applies_input_schema(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        new_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
            "required": ["name"],
        }
        llm_response = json.dumps(
            {
                "input_schema": new_schema,
                "confidence": {"input_schema": 0.88},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["input_schema"])

        assert result.input_schema == new_schema

    def test_ignores_non_dict_annotations(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps(
            {
                "annotations": "readonly",  # string instead of dict
                "confidence": {},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["annotations"])

        # Should not crash, annotations unchanged
        assert result.annotations is None or result.annotations == sparse_module.annotations

    def test_no_updates_returns_original(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps({"confidence": {}})
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer._enhance_module(sparse_module, ["description"])

        assert result.description == sparse_module.description


class TestEnhance:
    def test_skips_complete_modules(self, enhancer: AIEnhancer, complete_module: ScannedModule) -> None:
        result = enhancer.enhance([complete_module])
        assert len(result) == 1
        assert result[0] is complete_module  # no copy needed

    def test_enhances_sparse_modules(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        llm_response = json.dumps(
            {
                "description": "Handle legacy requests",
                "confidence": {"description": 0.92},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer.enhance([sparse_module])

        assert len(result) == 1
        assert result[0].description == "Handle legacy requests"

    def test_handles_llm_failure_gracefully(self, enhancer: AIEnhancer, sparse_module: ScannedModule) -> None:
        with patch.object(enhancer, "_call_llm", side_effect=ConnectionError("Offline")):
            result = enhancer.enhance([sparse_module])

        assert len(result) == 1
        assert result[0] is sparse_module  # original returned on failure

    def test_mixed_modules(
        self, enhancer: AIEnhancer, complete_module: ScannedModule, sparse_module: ScannedModule
    ) -> None:
        llm_response = json.dumps(
            {
                "description": "Enhanced desc",
                "confidence": {"description": 0.95},
            }
        )
        with patch.object(enhancer, "_call_llm", return_value=llm_response):
            result = enhancer.enhance([complete_module, sparse_module])

        assert len(result) == 2
        assert result[0] is complete_module  # untouched
        assert result[1].description == "Enhanced desc"


class TestConfiguration:
    def test_defaults_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APCORE_AI_ENDPOINT": "http://custom:8080/v1",
                "APCORE_AI_MODEL": "custom-model",
                "APCORE_AI_THRESHOLD": "0.5",
                "APCORE_AI_TIMEOUT": "60",
            },
        ):
            e = AIEnhancer()
            assert e.endpoint == "http://custom:8080/v1"
            assert e.model == "custom-model"
            assert e.threshold == 0.5
            assert e.timeout == 60

    def test_constructor_overrides_env(self) -> None:
        with patch.dict(os.environ, {"APCORE_AI_ENDPOINT": "http://env:8080/v1"}):
            e = AIEnhancer(endpoint="http://override:9090/v1")
            assert e.endpoint == "http://override:9090/v1"
