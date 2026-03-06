"""Tests for apcore_toolkit.types — ScannedModule dataclass."""

from __future__ import annotations

from dataclasses import fields, replace

from apcore import ModuleAnnotations, ModuleExample

from apcore_toolkit.types import ScannedModule


class TestScannedModuleDefaults:
    def test_required_fields_only(self, sample_module: ScannedModule) -> None:
        assert sample_module.module_id == "users.get_user"
        assert sample_module.version == "1.0.0"
        assert sample_module.annotations is None
        assert sample_module.documentation is None
        assert sample_module.metadata == {}
        assert sample_module.warnings == []

    def test_all_fields(self, annotated_module: ScannedModule) -> None:
        assert annotated_module.version == "2.0.0"
        assert annotated_module.annotations is not None
        assert annotated_module.annotations.destructive is True
        assert annotated_module.documentation == "Create a new task with the given title."
        assert annotated_module.metadata["http_method"] == "POST"

    def test_field_count(self) -> None:
        """ScannedModule has exactly 12 fields."""
        assert len(fields(ScannedModule)) == 12

    def test_mutable_defaults_are_independent(self) -> None:
        a = ScannedModule(
            module_id="a",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
        )
        b = ScannedModule(
            module_id="b",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
        )
        a.warnings.append("warn")
        a.metadata["key"] = "val"
        assert b.warnings == []
        assert b.metadata == {}


class TestScannedModuleReplace:
    def test_replace_module_id(self, sample_module: ScannedModule) -> None:
        new = replace(sample_module, module_id="users.get_user_2")
        assert new.module_id == "users.get_user_2"
        assert sample_module.module_id == "users.get_user"

    def test_replace_preserves_other_fields(self, annotated_module: ScannedModule) -> None:
        new = replace(annotated_module, description="Updated")
        assert new.description == "Updated"
        assert new.annotations == annotated_module.annotations
        assert new.metadata == annotated_module.metadata


class TestAnnotationsType:
    def test_accepts_module_annotations(self) -> None:
        ann = ModuleAnnotations(readonly=True, idempotent=True)
        m = ScannedModule(
            module_id="x",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
            annotations=ann,
        )
        assert m.annotations is not None
        assert m.annotations.readonly is True
        assert m.annotations.idempotent is True

    def test_none_annotations(self, sample_module: ScannedModule) -> None:
        assert sample_module.annotations is None


class TestExamplesField:
    def test_default_empty(self, sample_module: ScannedModule) -> None:
        assert sample_module.examples == []

    def test_with_examples(self) -> None:
        ex = ModuleExample(title="Get user", inputs={"user_id": 1}, output={"name": "Alice"})
        m = ScannedModule(
            module_id="x",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
            examples=[ex],
        )
        assert len(m.examples) == 1
        assert m.examples[0].title == "Get user"

    def test_mutable_default_independent(self) -> None:
        a = ScannedModule(
            module_id="a",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
        )
        b = ScannedModule(
            module_id="b",
            description="",
            input_schema={},
            output_schema={},
            tags=[],
            target="m:f",
        )
        a.examples.append(ModuleExample(title="test", inputs={}, output={}))
        assert b.examples == []
