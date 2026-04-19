# Feature Spec: http_verb_map Module

**Status**: Draft
**Target**: apcore-toolkit-python v0.5.0
**File**: `src/apcore_toolkit/http_verb_map.py`
**Tests**: `tests/test_http_verb_map.py`

---

## 1. Purpose

Provide a single source of truth for HTTP-method-to-semantic-verb mapping used by all Python framework scanners. The module exposes a canonical mapping table, a verb resolver, a path-parameter detector, and an alias generator. All functions are pure (no I/O, no mutable state) and raise no exceptions for any input.

## 2. Module Contents

```python
"""HTTP verb semantic mapping utilities.

Provides the canonical mapping from HTTP methods to semantic verbs used
by scanner implementations when generating user-facing command aliases.
All functions are pure and do not raise exceptions.
"""

from __future__ import annotations

import re

__all__ = [
    "SCANNER_VERB_MAP",
    "generate_suggested_alias",
    "has_path_params",
    "resolve_http_verb",
]
```

## 3. Module-Level Constants

### 3.1 SCANNER_VERB_MAP

```python
SCANNER_VERB_MAP: dict[str, str] = {
    "GET":     "list",
    "GET_ID":  "get",
    "POST":    "create",
    "PUT":     "update",
    "PATCH":   "patch",
    "DELETE":  "delete",
    "HEAD":    "head",
    "OPTIONS": "options",
}
```

**Semantics**:
- Keys are uppercase HTTP methods. `GET_ID` is a synthetic key used when GET routes have path parameters (single-resource access).
- Values are lowercase semantic verbs used by CLI and MCP surfaces.
- The mapping is considered immutable by convention. Downstream code MUST NOT mutate this dict.

### 3.2 _PATH_PARAM_RE

```python
_PATH_PARAM_RE: re.Pattern[str] = re.compile(r"\{[^}]+\}|:[a-zA-Z_]\w*")
```

**Coverage**:

| Syntax | Example | Matched By |
|---|---|---|
| Braces | `{id}`, `{user_id}`, `{task-id}` | `\{[^}]+\}` |
| Colon | `:id`, `:userId`, `:user_id` | `:[a-zA-Z_]\w*` |

**Frameworks**:
- FastAPI / Django / OpenAPI: `{param}`
- Express / NestJS / Gin / Axum: `:param`

The leading underscore marks it as module-private. Consumers call `has_path_params()` instead.

## 4. Functions

### 4.1 has_path_params

```python
def has_path_params(path: str) -> bool:
    """Check if a URL path contains path parameter placeholders.

    Detects both brace-style ({param}) and colon-style (:param) parameters,
    covering all major web frameworks.

    Args:
        path: URL path string (e.g., "/tasks/{id}" or "/users/:userId").

    Returns:
        True if the path contains at least one path parameter, False otherwise.
    """
    return bool(_PATH_PARAM_RE.search(path))
```

**Logic steps**:
1. Call `_PATH_PARAM_RE.search(path)`.
2. Return `bool(...)` on the match result.

**Parameter validation**: None required. The function accepts any string.

**Edge cases**:

| Input | Output | Notes |
|---|---|---|
| `""` | `False` | Empty string contains no placeholders. |
| `"/"` | `False` | Root path has no placeholders. |
| `"/tasks"` | `False` | Static path. |
| `"/tasks/{id}"` | `True` | Brace style. |
| `"/tasks/:id"` | `True` | Colon style. |
| `"/{id}/:name"` | `True` | Mixed styles. |
| `"/a/b/c"` | `False` | No placeholders. |
| `"/tasks/{}"` | `False` | Empty brace does not match `[^}]+`. |

**Verification tests**: T-HVM-HP-01 .. T-HVM-HP-08

---

### 4.2 resolve_http_verb

```python
def resolve_http_verb(method: str, has_path_params: bool) -> str:
    """Map an HTTP method to its semantic verb.

    GET is contextual: collection routes (no path params) map to "list",
    single-resource routes (with path params) map to "get". All other
    methods have a static mapping. Unknown methods fall through to
    the lowercase form of the input.

    Args:
        method: HTTP method string (case-insensitive).
        has_path_params: True if the corresponding route has path parameters.

    Returns:
        Semantic verb string (e.g., "create", "list", "get").
    """
    method_upper = method.upper()
    if method_upper == "GET":
        key = "GET_ID" if has_path_params else "GET"
        return SCANNER_VERB_MAP[key]
    return SCANNER_VERB_MAP.get(method_upper, method.lower())
```

**Logic steps**:
1. Uppercase the method string.
2. If the method is `GET`, choose the mapping key based on `has_path_params`:
   - `has_path_params=True` -> `SCANNER_VERB_MAP["GET_ID"]` -> `"get"`.
   - `has_path_params=False` -> `SCANNER_VERB_MAP["GET"]` -> `"list"`.
3. Otherwise, look up `method_upper` in the mapping. If absent, return the lowercase form of the input method.

**Parameter validation**:
- `method`: No validation. Any string accepted. Uppercase is applied internally.
- `has_path_params`: Type system enforces `bool`.

**Edge cases**:

| Method | has_path_params | Output |
|---|---|---|
| `"GET"` | `False` | `"list"` |
| `"GET"` | `True` | `"get"` |
| `"get"` | `False` | `"list"` (case-insensitive) |
| `"POST"` | `False` | `"create"` |
| `"POST"` | `True` | `"create"` (POST ignores path param state) |
| `"PUT"` | `True` | `"update"` |
| `"PATCH"` | `True` | `"patch"` |
| `"DELETE"` | `True` | `"delete"` |
| `"HEAD"` | any | `"head"` |
| `"OPTIONS"` | any | `"options"` |
| `"PURGE"` | any | `"purge"` (unknown method fallback) |
| `""` | any | `""` (empty fallback) |

**Verification tests**: T-HVM-RV-01 .. T-HVM-RV-12

---

### 4.3 generate_suggested_alias

```python
def generate_suggested_alias(path: str, method: str) -> str:
    """Generate a dot-separated suggested alias from HTTP route info.

    The alias is built from non-parameter path segments joined with the
    resolved semantic verb. The output uses snake_case preserved from the
    path; surface adapters apply their own naming conventions (e.g., CLI
    converts underscores to hyphens).

    Examples:
        POST   /tasks/user_data         -> "tasks.user_data.create"
        GET    /tasks/user_data         -> "tasks.user_data.list"
        GET    /tasks/user_data/{id}    -> "tasks.user_data.get"
        PUT    /tasks/user_data/{id}    -> "tasks.user_data.update"
        DELETE /tasks/user_data/{id}    -> "tasks.user_data.delete"

    Args:
        path: URL path (e.g., "/tasks/user_data/{id}").
        method: HTTP method (e.g., "POST").

    Returns:
        Dot-separated alias string. If the path has no non-parameter
        segments, returns just the semantic verb (e.g., "list").
    """
    raw_segments = [seg for seg in path.strip("/").split("/") if seg]
    segments = [seg for seg in raw_segments if not _PATH_PARAM_RE.fullmatch(seg)]
    is_single_resource = bool(raw_segments) and bool(_PATH_PARAM_RE.fullmatch(raw_segments[-1]))
    verb = resolve_http_verb(method, is_single_resource)
    return ".".join([*segments, verb])
```

**Logic steps**:
1. Strip leading and trailing `/` from `path`, split on `/`, drop empty strings
   (handles `"/"`, `"//"` and trailing-slash cases).
2. Filter the split segments — keep only segments that do **not** entirely match the
   path parameter regex (full-match, not substring). These are the *non-param* segments.
3. Determine `is_single_resource`: the last segment of the *raw* (unfiltered) list is a
   path parameter placeholder. This correctly classifies nested collection endpoints like
   `GET /orgs/{org_id}/members` as "list" (last segment `members` is not a param),
   while `GET /users/{id}` is "get" (last segment `{id}` is a param).
4. Resolve the semantic verb via `resolve_http_verb(method, is_single_resource)`.
5. Join the non-param segments plus the verb with `"."`.

**Parameter validation**:
- `path`: No validation. Any string accepted.
- `method`: No validation. Delegated to `resolve_http_verb`.

**Edge cases**:

| Path | Method | Output | Notes |
|---|---|---|---|
| `"/tasks/user_data"` | `"POST"` | `"tasks.user_data.create"` | Standard collection POST. |
| `"/tasks/user_data"` | `"GET"` | `"tasks.user_data.list"` | Collection GET. |
| `"/tasks/user_data/{id}"` | `"GET"` | `"tasks.user_data.get"` | Single resource GET. |
| `"/tasks/user_data/{id}"` | `"PUT"` | `"tasks.user_data.update"` | Full update. |
| `"/tasks/user_data/{id}"` | `"PATCH"` | `"tasks.user_data.patch"` | Partial update. |
| `"/tasks/user_data/{id}"` | `"DELETE"` | `"tasks.user_data.delete"` | Delete. |
| `"/health"` | `"GET"` | `"health.list"` | Single segment. |
| `"/"` | `"GET"` | `"list"` | Root path. |
| `""` | `"GET"` | `"list"` | Empty path. |
| `"/users/:user_id"` | `"GET"` | `"users.get"` | Colon-style param. |
| `"/api/v2/users"` | `"GET"` | `"api.v2.users.list"` | Version prefix preserved. |
| `"/orgs/{org_id}/teams/{team_id}/members"` | `"GET"` | `"orgs.teams.members.list"` | Nested params stripped. |
| `"//tasks//user_data//"` | `"POST"` | `"tasks.user_data.create"` | Extra slashes collapsed via empty-string filter. |
| `"/{id}"` | `"GET"` | `"get"` | Path with only a param. |
| `"/tasks/{id}/archive"` | `"POST"` | `"tasks.archive.create"` | Non-CRUD routes still append verb (see tech-design 8.2). |

**Verification tests**: T-HVM-SA-01 .. T-HVM-SA-14

---

## 5. Error Handling

None of the functions in this module raise exceptions. Design philosophy matches `BaseScanner.infer_annotations_from_method()`. For any input (including malformed paths, non-HTTP methods, empty strings) the functions return a best-effort string result.

## 6. Type Hints and Style

- `from __future__ import annotations` at the top.
- Full PEP 484 type hints on all functions and constants.
- Module passes `mypy --strict` with zero errors.
- Module passes `ruff check` with the repository's configured rules (py311, line-length 120).
- Docstrings use Google style matching the existing codebase.

## 7. Verification Tests

All tests live in `tests/test_http_verb_map.py`. Test patterns follow the existing `tests/test_scanner.py` structure (class-based grouping, `setup_method` for fixtures, descriptive test method names).

### 7.1 Test Classes and IDs

#### TestHasPathParams

| Test ID | Method | Assertion |
|---|---|---|
| T-HVM-HP-01 | `test_empty_string` | `has_path_params("") is False` |
| T-HVM-HP-02 | `test_root_path` | `has_path_params("/") is False` |
| T-HVM-HP-03 | `test_static_path` | `has_path_params("/tasks") is False` |
| T-HVM-HP-04 | `test_brace_style` | `has_path_params("/tasks/{id}") is True` |
| T-HVM-HP-05 | `test_colon_style` | `has_path_params("/tasks/:id") is True` |
| T-HVM-HP-06 | `test_mixed_styles` | `has_path_params("/{id}/:name") is True` |
| T-HVM-HP-07 | `test_multi_segment_static` | `has_path_params("/a/b/c") is False` |
| T-HVM-HP-08 | `test_empty_brace` | `has_path_params("/tasks/{}") is False` |

#### TestResolveHttpVerb

| Test ID | Method | Assertion |
|---|---|---|
| T-HVM-RV-01 | `test_get_collection` | `resolve_http_verb("GET", False) == "list"` |
| T-HVM-RV-02 | `test_get_single` | `resolve_http_verb("GET", True) == "get"` |
| T-HVM-RV-03 | `test_get_case_insensitive` | `resolve_http_verb("get", False) == "list"` |
| T-HVM-RV-04 | `test_post_no_params` | `resolve_http_verb("POST", False) == "create"` |
| T-HVM-RV-05 | `test_post_with_params` | `resolve_http_verb("POST", True) == "create"` |
| T-HVM-RV-06 | `test_put` | `resolve_http_verb("PUT", True) == "update"` |
| T-HVM-RV-07 | `test_patch` | `resolve_http_verb("PATCH", True) == "patch"` |
| T-HVM-RV-08 | `test_delete` | `resolve_http_verb("DELETE", True) == "delete"` |
| T-HVM-RV-09 | `test_head` | `resolve_http_verb("HEAD", False) == "head"` |
| T-HVM-RV-10 | `test_options` | `resolve_http_verb("OPTIONS", False) == "options"` |
| T-HVM-RV-11 | `test_unknown_method` | `resolve_http_verb("PURGE", False) == "purge"` |
| T-HVM-RV-12 | `test_empty_method` | `resolve_http_verb("", False) == ""` |

#### TestGenerateSuggestedAlias

| Test ID | Method | Assertion |
|---|---|---|
| T-HVM-SA-01 | `test_post_collection` | `generate_suggested_alias("/tasks/user_data", "POST") == "tasks.user_data.create"` |
| T-HVM-SA-02 | `test_get_collection` | `generate_suggested_alias("/tasks/user_data", "GET") == "tasks.user_data.list"` |
| T-HVM-SA-03 | `test_get_single` | `generate_suggested_alias("/tasks/user_data/{id}", "GET") == "tasks.user_data.get"` |
| T-HVM-SA-04 | `test_put_single` | `generate_suggested_alias("/tasks/user_data/{id}", "PUT") == "tasks.user_data.update"` |
| T-HVM-SA-05 | `test_patch_single` | `generate_suggested_alias("/tasks/user_data/{id}", "PATCH") == "tasks.user_data.patch"` |
| T-HVM-SA-06 | `test_delete_single` | `generate_suggested_alias("/tasks/user_data/{id}", "DELETE") == "tasks.user_data.delete"` |
| T-HVM-SA-07 | `test_single_segment` | `generate_suggested_alias("/health", "GET") == "health.list"` |
| T-HVM-SA-08 | `test_root_path` | `generate_suggested_alias("/", "GET") == "list"` |
| T-HVM-SA-09 | `test_empty_path` | `generate_suggested_alias("", "GET") == "list"` |
| T-HVM-SA-10 | `test_colon_param` | `generate_suggested_alias("/users/:user_id", "GET") == "users.get"` |
| T-HVM-SA-11 | `test_version_prefix` | `generate_suggested_alias("/api/v2/users", "GET") == "api.v2.users.list"` |
| T-HVM-SA-12 | `test_nested_params` | `generate_suggested_alias("/orgs/{org_id}/teams/{team_id}/members", "GET") == "orgs.teams.members.list"` |
| T-HVM-SA-13 | `test_double_slashes` | `generate_suggested_alias("//tasks//user_data//", "POST") == "tasks.user_data.create"` |
| T-HVM-SA-14 | `test_param_only_path` | `generate_suggested_alias("/{id}", "GET") == "get"` |

#### TestConformanceFixture

Loads `tests/fixtures/scanner_verb_map.json` and runs a parameterized test for each entry:

```python
import json
from pathlib import Path

import pytest

from apcore_toolkit.http_verb_map import generate_suggested_alias

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scanner_verb_map.json"


def _load_fixture() -> list[dict[str, str]]:
    with _FIXTURE_PATH.open() as fh:
        data: list[dict[str, str]] = json.load(fh)
    return data


class TestConformanceFixture:
    @pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: f"{c['method']} {c['path']}")
    def test_case(self, case: dict[str, str]) -> None:
        result = generate_suggested_alias(case["path"], case["method"])
        assert result == case["expected_alias"], (
            f"Fixture mismatch for {case['method']} {case['path']}: "
            f"got {result!r}, expected {case['expected_alias']!r}"
        )
```

| Test ID | Description |
|---|---|
| T-HVM-CF-01 | Fixture parametrized test — runs once per fixture entry |

## 8. Example Usage

```python
from apcore_toolkit.http_verb_map import (
    SCANNER_VERB_MAP,
    generate_suggested_alias,
    has_path_params,
    resolve_http_verb,
)

# Direct verb lookup
resolve_http_verb("POST", False)              # "create"
resolve_http_verb("GET", has_path_params=True)  # "get"

# Path analysis
has_path_params("/users/{id}")                # True

# End-to-end alias generation (typical scanner usage)
alias = generate_suggested_alias("/tasks/user_data/{id}", "DELETE")
# "tasks.user_data.delete"
```

## 9. Acceptance Criteria

- [ ] `src/apcore_toolkit/http_verb_map.py` implements the full module as specified.
- [ ] All symbols in `__all__` are importable at module level.
- [ ] `tests/test_http_verb_map.py` covers every test ID in section 7.1.
- [ ] `tests/fixtures/scanner_verb_map.json` exists and is loaded by `TestConformanceFixture`.
- [ ] `pytest tests/test_http_verb_map.py` reports zero failures.
- [ ] `ruff check src/apcore_toolkit/http_verb_map.py tests/test_http_verb_map.py` passes.
- [ ] `mypy --strict src/apcore_toolkit/http_verb_map.py` passes.
- [ ] Symbols are re-exported from `apcore_toolkit/__init__.py` and listed in `__all__`.
