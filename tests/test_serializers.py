"""Tests for apcore_toolkit.serializers — dict conversion utilities."""

from __future__ import annotations

import logging

import pytest
from apcore import ModuleAnnotations, ModuleExample

from apcore_toolkit.serializers import annotations_to_dict, module_to_dict, modules_to_dicts
from apcore_toolkit.types import ScannedModule


class TestAnnotationsToDict:
    def test_none(self) -> None:
        assert annotations_to_dict(None) is None

    def test_dict_passthrough(self) -> None:
        d = {"readonly": True, "destructive": False}
        assert annotations_to_dict(d) is d

    def test_dataclass_instance(self) -> None:
        ann = ModuleAnnotations(readonly=True)
        result = annotations_to_dict(ann)
        assert isinstance(result, dict)
        assert result["readonly"] is True

    def test_unrecognised_type(self) -> None:
        assert annotations_to_dict("not-valid") is None
        assert annotations_to_dict(42) is None

    def test_unrecognised_type_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="apcore_toolkit"):
            annotations_to_dict("not-valid")
        assert any("not-valid" in r.message for r in caplog.records)


class TestModuleToDict:
    def test_basic_module(self, sample_module: ScannedModule) -> None:
        result = module_to_dict(sample_module)
        assert result["module_id"] == "users.get_user"
        assert result["target"] == "myapp.views:get_user"
        assert result["tags"] == ["users"]
        assert result["version"] == "1.0.0"
        assert result["annotations"] is None
        assert result["documentation"] is None
        assert result["metadata"] == {}

    def test_annotated_module(self, annotated_module: ScannedModule) -> None:
        result = module_to_dict(annotated_module)
        assert result["annotations"]["destructive"] is True
        assert result["documentation"] == "Create a new task with the given title."
        assert result["metadata"]["http_method"] == "POST"

    def test_all_expected_keys(self, sample_module: ScannedModule) -> None:
        result = module_to_dict(sample_module)
        expected_keys = {
            "module_id", "description", "documentation", "tags", "version",
            "target", "annotations", "examples", "metadata", "input_schema",
            "output_schema", "warnings",
        }
        assert set(result.keys()) == expected_keys

    def test_warnings_included(self) -> None:
        m = ScannedModule(
            module_id="x", description="", input_schema={}, output_schema={},
            tags=[], target="m:f", warnings=["warn1", "warn2"],
        )
        result = module_to_dict(m)
        assert result["warnings"] == ["warn1", "warn2"]

    def test_warnings_empty_by_default(self, sample_module: ScannedModule) -> None:
        result = module_to_dict(sample_module)
        assert result["warnings"] == []

    def test_examples_empty_by_default(self, sample_module: ScannedModule) -> None:
        result = module_to_dict(sample_module)
        assert result["examples"] == []

    def test_examples_serialized(self) -> None:
        ex = ModuleExample(title="Demo", inputs={"x": 1}, output={"y": 2})
        m = ScannedModule(
            module_id="x", description="", input_schema={}, output_schema={},
            tags=[], target="m:f", examples=[ex],
        )
        result = module_to_dict(m)
        assert len(result["examples"]) == 1
        assert result["examples"][0]["title"] == "Demo"
        assert result["examples"][0]["inputs"] == {"x": 1}
        assert isinstance(result["examples"][0], dict)


class TestModulesToDicts:
    def test_empty_list(self) -> None:
        assert modules_to_dicts([]) == []

    def test_multiple_modules(self, sample_module: ScannedModule, annotated_module: ScannedModule) -> None:
        result = modules_to_dicts([sample_module, annotated_module])
        assert len(result) == 2
        assert result[0]["module_id"] == "users.get_user"
        assert result[1]["module_id"] == "tasks.create_task"
