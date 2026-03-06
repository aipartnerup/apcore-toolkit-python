"""Tests for apcore_toolkit.output.python_writer — PythonWriter."""

from __future__ import annotations

from pathlib import Path

import pytest

from apcore_toolkit.output.python_writer import PythonWriter
from apcore_toolkit.types import ScannedModule


class TestPythonWriterDryRun:
    def setup_method(self) -> None:
        self.writer = PythonWriter()

    def test_empty_modules(self) -> None:
        result = self.writer.write([], "/tmp/out", dry_run=True)
        assert result == []

    def test_single_module(self, sample_module: ScannedModule) -> None:
        result = self.writer.write([sample_module], "/tmp/out", dry_run=True)
        assert len(result) == 1
        code = result[0]
        assert "from apcore import module" in code
        assert "@module(" in code
        assert "id='users.get_user'" in code
        assert "from myapp.views import get_user as _original" in code

    def test_function_name_sanitized(self) -> None:
        module = ScannedModule(
            module_id="api.v1.123-bad-name",
            description="test",
            input_schema={"type": "object", "properties": {}},
            output_schema={},
            tags=[],
            target="mod.path:func",
        )
        result = self.writer.write([module], "/tmp/out", dry_run=True)
        code = result[0]
        # Function name derived from last segment, sanitized
        assert "def _123_bad_name" in code

    def test_parameters_from_schema(self, sample_module: ScannedModule) -> None:
        result = self.writer.write([sample_module], "/tmp/out", dry_run=True)
        code = result[0]
        assert "user_id: int" in code

    def test_optional_parameters(self) -> None:
        module = ScannedModule(
            module_id="test.func",
            description="test",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name"],
            },
            output_schema={},
            tags=[],
            target="mod:func",
        )
        result = self.writer.write([module], "/tmp/out", dry_run=True)
        code = result[0]
        assert "name: str" in code
        assert "age: int | None = None" in code

    def test_annotations_in_decorator(self, annotated_module: ScannedModule) -> None:
        result = self.writer.write([annotated_module], "/tmp/out", dry_run=True)
        code = result[0]
        assert "annotations=" in code

    def test_no_annotations_omitted(self, sample_module: ScannedModule) -> None:
        result = self.writer.write([sample_module], "/tmp/out", dry_run=True)
        code = result[0]
        assert "annotations=" not in code

    def test_multiple_modules(self, sample_module: ScannedModule, annotated_module: ScannedModule) -> None:
        result = self.writer.write([sample_module, annotated_module], "/tmp/out", dry_run=True)
        assert len(result) == 2


class TestPythonWriterValidation:
    def setup_method(self) -> None:
        self.writer = PythonWriter()

    def test_invalid_target_no_colon(self) -> None:
        module = ScannedModule(
            module_id="test.func",
            description="test",
            input_schema={"type": "object", "properties": {}},
            output_schema={},
            tags=[],
            target="no_colon_here",
        )
        with pytest.raises(ValueError, match="Invalid target format"):
            self.writer.write([module], "/tmp/out", dry_run=True)

    def test_invalid_module_path(self) -> None:
        module = ScannedModule(
            module_id="test.func",
            description="test",
            input_schema={"type": "object", "properties": {}},
            output_schema={},
            tags=[],
            target="123invalid:func",
        )
        with pytest.raises(ValueError, match="Invalid module path"):
            self.writer.write([module], "/tmp/out", dry_run=True)


class TestPythonWriterFileOutput:
    def setup_method(self) -> None:
        self.writer = PythonWriter()

    def test_writes_files(self, tmp_path: Path, sample_module: ScannedModule) -> None:
        self.writer.write([sample_module], str(tmp_path))
        files = list(tmp_path.glob("*.py"))
        assert len(files) == 1
        code = files[0].read_text()
        assert "Auto-generated apcore module" in code

    def test_creates_output_dir(self, tmp_path: Path, sample_module: ScannedModule) -> None:
        out_dir = tmp_path / "nested" / "output"
        self.writer.write([sample_module], str(out_dir))
        assert out_dir.exists()
        assert len(list(out_dir.glob("*.py"))) == 1

    def test_overwrite_existing(self, tmp_path: Path, sample_module: ScannedModule) -> None:
        self.writer.write([sample_module], str(tmp_path))
        self.writer.write([sample_module], str(tmp_path))
        files = list(tmp_path.glob("*.py"))
        assert len(files) == 1
