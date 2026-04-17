# Feature Spec: DisplayResolver Dual-Source Alias Resolution

**Status**: Draft
**Target**: apcore-toolkit-python v0.5.0
**File**: `src/apcore_toolkit/display/resolver.py`
**Tests**: `tests/test_display_resolver.py`

---

## 1. Purpose

Update `DisplayResolver` to read the scanner-provided `suggested_alias` from two sources in priority order:

1. The new top-level `ScannedModule.suggested_alias` field (primary source).
2. The legacy `metadata["suggested_alias"]` key (fallback for backward compatibility).

This ensures scanners that have already been updated to populate the new field get the preferred path, while older scanners that still write to the metadata dict continue to function without modification.

---

## 2. Current Behavior

Current code at `src/apcore_toolkit/display/resolver.py` line 134 reads only from metadata:

```python
suggested_alias: str | None = (mod.metadata or {}).get("suggested_alias")
```

This is the single-source read used throughout the alias resolve chain:

```
display.cli.alias  ->  display.default.alias  ->  suggested_alias  ->  module_id
```

## 3. Target Behavior

Replace the single-source read with a dual-source read, giving precedence to the new field:

```python
suggested_alias: str | None = (
    getattr(mod, "suggested_alias", None)
    or (mod.metadata or {}).get("suggested_alias")
)
```

### 3.1 Precedence Rules

| `mod.suggested_alias` | `metadata["suggested_alias"]` | Resolved Value |
|---|---|---|
| `"tasks.create"` | not set | `"tasks.create"` (field) |
| `"tasks.create"` | `"tasks.legacy"` | `"tasks.create"` (field wins) |
| `None` | `"tasks.legacy"` | `"tasks.legacy"` (metadata fallback) |
| `""` | `"tasks.legacy"` | `"tasks.legacy"` (empty string is falsy, falls through) |
| `None` | not set | `None` (no alias, resolve chain falls through to `module_id`) |
| `"tasks.create"` | `""` | `"tasks.create"` |

The `or` operator's short-circuit semantics give us this behavior naturally. Empty string is falsy in Python, so we also fall through to metadata if the field is explicitly set to `""`.

### 3.2 Defensive getattr

`getattr(mod, "suggested_alias", None)` is used instead of direct attribute access because:

- `DisplayResolver.resolve()` signature accepts `list[Any]` (not strictly `ScannedModule`). Older callers may pass dict-like or other objects.
- Future `ScannedModule` variants (e.g., from adapters) may not carry the field yet.

---

## 4. Detailed Change

### 4.1 Location

`src/apcore_toolkit/display/resolver.py`, inside `DisplayResolver._resolve_one()`, at the current line 134.

### 4.2 Exact Diff

**Before**:

```python
def _resolve_one(self, mod: Any, binding_map: dict[str, dict[str, Any]]) -> Any:
    """Resolve display fields for a single ScannedModule."""
    entry = binding_map.get(mod.module_id, {})
    display_cfg: dict[str, Any] = entry.get("display") or {}
    binding_desc: str | None = entry.get("description")
    binding_docs: str | None = entry.get("documentation")
    suggested_alias: str | None = (mod.metadata or {}).get("suggested_alias")
```

**After**:

```python
def _resolve_one(self, mod: Any, binding_map: dict[str, dict[str, Any]]) -> Any:
    """Resolve display fields for a single ScannedModule.

    ``suggested_alias`` is read from two sources in priority order:

    1. ``mod.suggested_alias`` (top-level field, preferred)
    2. ``mod.metadata["suggested_alias"]`` (legacy fallback)

    The top-level field takes precedence when set to a truthy value.
    """
    entry = binding_map.get(mod.module_id, {})
    display_cfg: dict[str, Any] = entry.get("display") or {}
    binding_desc: str | None = entry.get("description")
    binding_docs: str | None = entry.get("documentation")
    suggested_alias: str | None = (
        getattr(mod, "suggested_alias", None)
        or (mod.metadata or {}).get("suggested_alias")
    )
```

### 4.3 Logic Steps (After Change)

1. Look up the binding entry for this `mod.module_id`.
2. Extract `display_cfg`, `binding_desc`, `binding_docs` as before.
3. Compute `suggested_alias`:
   a. Read `mod.suggested_alias` via `getattr`, defaulting to `None`.
   b. If that value is truthy, use it.
   c. Otherwise, read `(mod.metadata or {}).get("suggested_alias")`.
4. Continue with the existing resolve chain unchanged (line 137+).

### 4.4 Parameter Validation

No new validation. The existing type guards (`getattr` with default, `(mod.metadata or {})` idiom) already handle missing attributes and `None`-valued metadata.

### 4.5 Error Handling

No new exception paths. `getattr` with a default value never raises.

---

## 5. Verification Tests

Tests live in `tests/test_display_resolver.py`. Add a new test class `TestSuggestedAliasDualSource`.

### 5.1 Test Helpers

```python
from typing import Any

from apcore_toolkit.display.resolver import DisplayResolver
from apcore_toolkit.types import ScannedModule


def _make_module(
    module_id: str = "tasks.user_data.post",
    *,
    suggested_alias: str | None = None,
    metadata_alias: str | None = None,
) -> ScannedModule:
    metadata: dict[str, Any] = {}
    if metadata_alias is not None:
        metadata["suggested_alias"] = metadata_alias
    return ScannedModule(
        module_id=module_id,
        description="x",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {}},
        tags=[],
        target="mod:func",
        suggested_alias=suggested_alias,
        metadata=metadata,
    )
```

### 5.2 Test Cases

```python
class TestSuggestedAliasDualSource:
    def setup_method(self) -> None:
        self.resolver = DisplayResolver()

    def test_field_only(self) -> None:
        mod = _make_module(suggested_alias="tasks.user_data.create")
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.create"

    def test_metadata_only(self) -> None:
        mod = _make_module(metadata_alias="tasks.user_data.legacy")
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.legacy"

    def test_field_precedence_over_metadata(self) -> None:
        mod = _make_module(
            suggested_alias="tasks.user_data.create",
            metadata_alias="tasks.user_data.legacy",
        )
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.create"

    def test_neither_source_falls_through_to_module_id(self) -> None:
        mod = _make_module(module_id="tasks.user_data.post")
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.post"

    def test_empty_string_field_falls_through_to_metadata(self) -> None:
        mod = _make_module(
            suggested_alias="",
            metadata_alias="tasks.user_data.legacy",
        )
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.legacy"

    def test_none_field_falls_through_to_metadata(self) -> None:
        mod = _make_module(
            suggested_alias=None,
            metadata_alias="tasks.user_data.legacy",
        )
        [resolved] = self.resolver.resolve([mod])
        assert resolved.metadata["display"]["alias"] == "tasks.user_data.legacy"

    def test_binding_alias_still_wins(self) -> None:
        # display.cli.alias from binding.yaml overrides suggested_alias.
        mod = _make_module(suggested_alias="tasks.user_data.create")
        binding_data = {
            "bindings": [
                {
                    "module_id": "tasks.user_data.post",
                    "display": {
                        "alias": "tasks.user-data.search",
                        "cli": {"alias": "tasks.user-data.search"},
                    },
                }
            ]
        }
        [resolved] = self.resolver.resolve([mod], binding_data=binding_data)
        # Cross-surface default alias comes from display.alias.
        assert resolved.metadata["display"]["alias"] == "tasks.user-data.search"
        # CLI surface-specific alias is the same.
        assert resolved.metadata["display"]["cli"]["alias"] == "tasks.user-data.search"

    def test_getattr_handles_missing_attribute(self) -> None:
        # Defensive: non-ScannedModule objects without the attribute.
        class FakeMod:
            module_id = "foo.bar"
            description = "x"
            documentation = None
            tags: list[str] = []
            metadata: dict[str, Any] = {"suggested_alias": "foo.bar.list"}

        [resolved] = self.resolver.resolve([FakeMod()])  # type: ignore[list-item]
        # Falls through to metadata since getattr defaults to None.
        assert resolved.metadata["display"]["alias"] == "foo.bar.list"
```

### 5.3 Test IDs

| Test ID | Method | Coverage |
|---|---|---|
| T-DRV-SA-01 | `test_field_only` | Field-only path |
| T-DRV-SA-02 | `test_metadata_only` | Legacy metadata-only path |
| T-DRV-SA-03 | `test_field_precedence_over_metadata` | Precedence rule |
| T-DRV-SA-04 | `test_neither_source_falls_through_to_module_id` | Fall through to canonical |
| T-DRV-SA-05 | `test_empty_string_field_falls_through_to_metadata` | Empty field is falsy |
| T-DRV-SA-06 | `test_none_field_falls_through_to_metadata` | `None` field falls through |
| T-DRV-SA-07 | `test_binding_alias_still_wins` | `display.cli.alias` override still has priority |
| T-DRV-SA-08 | `test_getattr_handles_missing_attribute` | Defensive `getattr` on non-`ScannedModule` |

---

## 6. Backward Compatibility

### 6.1 Scanners Emitting Metadata Only

Works unchanged. The fallback path hits `(mod.metadata or {}).get("suggested_alias")`.

### 6.2 Scanners Emitting Field Only

Works correctly. The field is read first and is truthy.

### 6.3 Scanners Emitting Both (Transitional)

The new field wins. This can be used during migration: a scanner upgrade can set both the field and the metadata key simultaneously so that consumers on old toolkit versions still see the metadata, and consumers on the new toolkit see the field.

### 6.4 Callers Not Using ScannedModule

The existing signature is `list[Any]`. The `getattr` defensive read ensures that duck-typed inputs without the attribute still resolve via the metadata path.

---

## 7. Interaction With Other Resolve-Chain Layers

The dual-source read only affects how `suggested_alias` is **acquired**. It does not change:

- The existing `display.cli.alias` > `display.default.alias` > `suggested_alias` > `module_id` priority.
- The MCP alias auto-sanitization (lines 164-175 of `resolver.py`).
- The CLI alias validation (lines 217-227 of `resolver.py`).

These continue to consume the resolved `suggested_alias` in the same way.

---

## 8. Acceptance Criteria

- [ ] The exact two-line read replaces line 134 of `resolver.py` with the dual-source expression.
- [ ] The `_resolve_one` docstring is updated to describe the dual-source behavior.
- [ ] All tests in section 5.3 pass.
- [ ] All existing tests in `test_display_resolver.py` continue to pass without modification.
- [ ] `ruff check src/apcore_toolkit/display/resolver.py` passes.
- [ ] `mypy --strict src/apcore_toolkit/display/resolver.py` passes.

---

## 9. Out of Scope

- Changes to the overall resolve chain priority.
- Changes to MCP or CLI alias validation.
- Migration of existing scanner code (covered in downstream scanner work items).
- Deprecation of `metadata["suggested_alias"]`. The legacy path remains supported indefinitely for backward compatibility.
