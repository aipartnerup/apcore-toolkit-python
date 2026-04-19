"""Tests for apcore_toolkit.http_verb_map — HTTP verb semantic mapping utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apcore_toolkit.http_verb_map import (
    SCANNER_VERB_MAP,
    generate_suggested_alias,
    has_path_params,
    resolve_http_verb,
)

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scanner_verb_map.json"


def _load_fixture() -> list[dict[str, str]]:
    with _FIXTURE_PATH.open() as fh:
        data: list[dict[str, str]] = json.load(fh)
    return data


class TestPublicApiReexports:
    def test_import_scanner_verb_map(self) -> None:
        from apcore_toolkit import SCANNER_VERB_MAP as reexported

        assert isinstance(reexported, dict)
        assert reexported["POST"] == "create"

    def test_import_resolve_http_verb(self) -> None:
        from apcore_toolkit import resolve_http_verb as reexported

        assert reexported("POST", False) == "create"

    def test_import_has_path_params(self) -> None:
        from apcore_toolkit import has_path_params as reexported

        assert reexported("/tasks/{id}") is True

    def test_import_generate_suggested_alias(self) -> None:
        from apcore_toolkit import generate_suggested_alias as reexported

        assert reexported("/tasks", "POST") == "tasks.create"


class TestHasPathParams:
    def test_empty_string(self) -> None:
        assert has_path_params("") is False

    def test_root_path(self) -> None:
        assert has_path_params("/") is False

    def test_static_path(self) -> None:
        assert has_path_params("/tasks") is False

    def test_brace_style(self) -> None:
        assert has_path_params("/tasks/{id}") is True

    def test_colon_style(self) -> None:
        assert has_path_params("/tasks/:id") is True

    def test_mixed_styles(self) -> None:
        assert has_path_params("/{id}/:name") is True

    def test_multi_segment_static(self) -> None:
        assert has_path_params("/a/b/c") is False

    def test_empty_brace(self) -> None:
        assert has_path_params("/tasks/{}") is False


class TestResolveHttpVerb:
    def test_get_collection(self) -> None:
        assert resolve_http_verb("GET", False) == "list"

    def test_get_single(self) -> None:
        assert resolve_http_verb("GET", True) == "get"

    def test_get_case_insensitive(self) -> None:
        assert resolve_http_verb("get", False) == "list"

    def test_post_no_params(self) -> None:
        assert resolve_http_verb("POST", False) == "create"

    def test_post_with_params(self) -> None:
        assert resolve_http_verb("POST", True) == "create"

    def test_put(self) -> None:
        assert resolve_http_verb("PUT", True) == "update"

    def test_patch(self) -> None:
        assert resolve_http_verb("PATCH", True) == "patch"

    def test_delete(self) -> None:
        assert resolve_http_verb("DELETE", True) == "delete"

    def test_head(self) -> None:
        assert resolve_http_verb("HEAD", False) == "head"

    def test_options(self) -> None:
        assert resolve_http_verb("OPTIONS", False) == "options"

    def test_unknown_method(self) -> None:
        assert resolve_http_verb("PURGE", False) == "purge"

    def test_empty_method(self) -> None:
        assert resolve_http_verb("", False) == ""


class TestGenerateSuggestedAlias:
    def test_post_collection(self) -> None:
        assert generate_suggested_alias("/tasks/user_data", "POST") == "tasks.user_data.create"

    def test_get_collection(self) -> None:
        assert generate_suggested_alias("/tasks/user_data", "GET") == "tasks.user_data.list"

    def test_get_single(self) -> None:
        assert generate_suggested_alias("/tasks/user_data/{id}", "GET") == "tasks.user_data.get"

    def test_put_single(self) -> None:
        assert generate_suggested_alias("/tasks/user_data/{id}", "PUT") == "tasks.user_data.update"

    def test_patch_single(self) -> None:
        assert generate_suggested_alias("/tasks/user_data/{id}", "PATCH") == "tasks.user_data.patch"

    def test_delete_single(self) -> None:
        assert generate_suggested_alias("/tasks/user_data/{id}", "DELETE") == "tasks.user_data.delete"

    def test_single_segment(self) -> None:
        assert generate_suggested_alias("/health", "GET") == "health.list"

    def test_root_path(self) -> None:
        assert generate_suggested_alias("/", "GET") == "list"

    def test_empty_path(self) -> None:
        assert generate_suggested_alias("", "GET") == "list"

    def test_colon_param(self) -> None:
        assert generate_suggested_alias("/users/:user_id", "GET") == "users.get"

    def test_version_prefix(self) -> None:
        assert generate_suggested_alias("/api/v2/users", "GET") == "api.v2.users.list"

    def test_nested_params(self) -> None:
        assert generate_suggested_alias("/orgs/{org_id}/teams/{team_id}/members", "GET") == "orgs.teams.members.list"

    def test_double_slashes(self) -> None:
        assert generate_suggested_alias("//tasks//user_data//", "POST") == "tasks.user_data.create"

    def test_param_only_path(self) -> None:
        assert generate_suggested_alias("/{id}", "GET") == "get"


class TestScannerVerbMapConstant:
    def test_contains_standard_http_methods(self) -> None:
        assert set(SCANNER_VERB_MAP.keys()) >= {
            "GET",
            "GET_ID",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        }

    def test_values_are_lowercase(self) -> None:
        for value in SCANNER_VERB_MAP.values():
            assert value == value.lower()


class TestConformanceFixture:
    @pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: f"{c['method']} {c['path']}")
    def test_case(self, case: dict[str, str]) -> None:
        result = generate_suggested_alias(case["path"], case["method"])
        assert result == case["expected_alias"], (
            f"Fixture mismatch for {case['method']} {case['path']}: "
            f"got {result!r}, expected {case['expected_alias']!r}"
        )
