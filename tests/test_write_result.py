"""Tests for apcore_toolkit.output.types — WriteResult."""

from __future__ import annotations

from apcore_toolkit.output.types import WriteResult


class TestWriteResult:
    def test_defaults(self) -> None:
        r = WriteResult(module_id="test.mod")
        assert r.module_id == "test.mod"
        assert r.path is None
        assert r.verified is True
        assert r.verification_error is None

    def test_with_path(self) -> None:
        r = WriteResult(module_id="test.mod", path="/tmp/test.yaml")
        assert r.path == "/tmp/test.yaml"

    def test_failed_verification(self) -> None:
        r = WriteResult(
            module_id="test.mod",
            path="/tmp/test.yaml",
            verified=False,
            verification_error="Missing field",
        )
        assert r.verified is False
        assert r.verification_error == "Missing field"

    def test_equality(self) -> None:
        a = WriteResult(module_id="test.mod")
        b = WriteResult(module_id="test.mod")
        assert a == b
