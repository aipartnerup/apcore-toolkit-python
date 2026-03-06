"""Tests for apcore_toolkit.output.registry_writer — RegistryWriter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apcore_toolkit.output.registry_writer import RegistryWriter
from apcore_toolkit.types import ScannedModule


@pytest.fixture
def writer() -> RegistryWriter:
    return RegistryWriter()


@pytest.fixture
def mock_registry() -> MagicMock:
    return MagicMock()


class TestRegistryWriter:
    def test_write_registers_modules(
        self, writer: RegistryWriter, mock_registry: MagicMock, sample_module: ScannedModule
    ) -> None:
        with patch.object(writer, "_to_function_module", return_value=MagicMock()) as mock_to_fm:
            result = writer.write([sample_module], mock_registry)

        assert result == ["users.get_user"]
        mock_to_fm.assert_called_once_with(sample_module)
        mock_registry.register.assert_called_once()

    def test_write_dry_run(
        self, writer: RegistryWriter, mock_registry: MagicMock, sample_module: ScannedModule
    ) -> None:
        result = writer.write([sample_module], mock_registry, dry_run=True)

        assert result == ["users.get_user"]
        mock_registry.register.assert_not_called()

    def test_write_empty_list(self, writer: RegistryWriter, mock_registry: MagicMock) -> None:
        result = writer.write([], mock_registry)
        assert result == []

    def test_write_multiple_modules(
        self, writer: RegistryWriter, mock_registry: MagicMock, sample_module: ScannedModule, annotated_module: ScannedModule
    ) -> None:
        with patch.object(writer, "_to_function_module", return_value=MagicMock()):
            result = writer.write([sample_module, annotated_module], mock_registry)

        assert result == ["users.get_user", "tasks.create_task"]
        assert mock_registry.register.call_count == 2


class TestGetWriterRegistry:
    def test_get_writer_registry(self) -> None:
        from apcore_toolkit.output import get_writer

        writer = get_writer("registry")
        assert isinstance(writer, RegistryWriter)
