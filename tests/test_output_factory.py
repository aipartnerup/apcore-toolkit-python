"""Tests for apcore_toolkit.output — get_writer factory."""

from __future__ import annotations

import pytest

from apcore_toolkit.output import get_writer
from apcore_toolkit.output.python_writer import PythonWriter
from apcore_toolkit.output.registry_writer import RegistryWriter
from apcore_toolkit.output.yaml_writer import YAMLWriter


class TestGetWriter:
    def test_yaml(self) -> None:
        writer = get_writer("yaml")
        assert isinstance(writer, YAMLWriter)

    def test_python(self) -> None:
        writer = get_writer("python")
        assert isinstance(writer, PythonWriter)

    def test_registry(self) -> None:
        writer = get_writer("registry")
        assert isinstance(writer, RegistryWriter)

    def test_unknown_format(self) -> None:
        with pytest.raises(ValueError, match="Unknown output format"):
            get_writer("json")

    def test_unknown_format_message(self) -> None:
        with pytest.raises(ValueError, match="'json'"):
            get_writer("json")
