"""Tests for DisplayResolver (§5.13 display overlay)."""

from __future__ import annotations

import pytest

from apcore_toolkit.display import DisplayResolver
from apcore_toolkit.types import ScannedModule


def _mod(
    module_id: str = "image.resize",
    description: str = "Resize an image",
    tags: list[str] | None = None,
    documentation: str | None = None,
    metadata: dict | None = None,
) -> ScannedModule:
    return ScannedModule(
        module_id=module_id,
        description=description,
        input_schema={},
        output_schema={},
        tags=tags or [],
        target="myapp:func",
        documentation=documentation,
        metadata=metadata or {},
    )


@pytest.fixture
def resolver() -> DisplayResolver:
    return DisplayResolver()


# ---------------------------------------------------------------------------
# No binding — fields fall through to scanner values
# ---------------------------------------------------------------------------


def test_no_binding_alias_is_module_id(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod("image.resize")])
    d = result[0].metadata["display"]
    assert d["alias"] == "image.resize"


def test_no_binding_description_is_scanner(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod(description="Resize an image")])
    d = result[0].metadata["display"]
    assert d["description"] == "Resize an image"


def test_no_binding_tags_from_scanner(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod(tags=["image", "transform"])])
    d = result[0].metadata["display"]
    assert d["tags"] == ["image", "transform"]


def test_no_binding_guidance_is_none(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod()])
    d = result[0].metadata["display"]
    assert d["guidance"] is None


def test_no_binding_documentation_from_scanner(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod(documentation="Full docs here.")])
    d = result[0].metadata["display"]
    assert d["documentation"] == "Full docs here."


# ---------------------------------------------------------------------------
# display.alias only — all surfaces inherit it
# ---------------------------------------------------------------------------


def test_display_alias_propagates_to_all_surfaces(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod("product.get")],
        binding_data={"bindings": [{"module_id": "product.get", "display": {"alias": "product-get"}}]},
    )
    d = result[0].metadata["display"]
    assert d["alias"] == "product-get"
    assert d["cli"]["alias"] == "product-get"
    assert d["a2a"]["alias"] == "product-get"


def test_display_alias_sanitized_for_mcp(resolver: DisplayResolver) -> None:
    """display.alias may contain hyphens — MCP alias must only have [a-zA-Z0-9_-]."""
    result = resolver.resolve(
        [_mod("payment.status")],
        binding_data={"bindings": [{"module_id": "payment.status", "display": {"alias": "pay-status"}}]},
    )
    d = result[0].metadata["display"]
    assert d["mcp"]["alias"] == "pay-status"  # hyphens are allowed in MCP pattern


# ---------------------------------------------------------------------------
# Surface-specific overrides
# ---------------------------------------------------------------------------


def test_cli_alias_override_only_affects_cli(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod("order.list")],
        binding_data={
            "bindings": [{"module_id": "order.list", "display": {"alias": "order-list", "cli": {"alias": "orders"}}}]
        },
    )
    d = result[0].metadata["display"]
    assert d["cli"]["alias"] == "orders"
    assert d["mcp"]["alias"] == "order-list"  # hyphens are valid in MCP pattern, no change
    assert d["a2a"]["alias"] == "order-list"


def test_mcp_alias_override_only_affects_mcp(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod("order.list")],
        binding_data={
            "bindings": [
                {
                    "module_id": "order.list",
                    "display": {"alias": "order-list", "mcp": {"alias": "list_orders"}},
                }
            ]
        },
    )
    d = result[0].metadata["display"]
    assert d["mcp"]["alias"] == "list_orders"
    assert d["cli"]["alias"] == "order-list"
    assert d["a2a"]["alias"] == "order-list"


def test_surface_description_override(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod("my.mod", description="Generic description")],
        binding_data={
            "bindings": [
                {
                    "module_id": "my.mod",
                    "display": {
                        "description": "Default override",
                        "cli": {"description": "CLI-specific description"},
                    },
                }
            ]
        },
    )
    d = result[0].metadata["display"]
    assert d["cli"]["description"] == "CLI-specific description"
    assert d["mcp"]["description"] == "Default override"
    assert d["a2a"]["description"] == "Default override"


# ---------------------------------------------------------------------------
# MCP alias validation
# ---------------------------------------------------------------------------


def test_mcp_alias_exceeds_64_chars_raises(resolver: DisplayResolver) -> None:
    with pytest.raises(ValueError, match="exceeds.*64"):
        resolver.resolve(
            [_mod("my.mod")],
            binding_data={"bindings": [{"module_id": "my.mod", "display": {"mcp": {"alias": "a" * 65}}}]},
        )


def test_mcp_module_id_with_dots_auto_sanitized(resolver: DisplayResolver) -> None:
    """module_id fallback must be sanitized — dots become underscores."""
    result = resolver.resolve([_mod("image.resize")])
    assert result[0].metadata["display"]["mcp"]["alias"] == "image_resize"


def test_mcp_module_id_nested_dots_sanitized(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod("product.catalog.get")])
    assert result[0].metadata["display"]["mcp"]["alias"] == "product_catalog_get"


# ---------------------------------------------------------------------------
# suggested_alias fallback (from simplify_ids=True scanner)
# ---------------------------------------------------------------------------


def test_suggested_alias_used_when_no_display_alias(resolver: DisplayResolver) -> None:
    mod = _mod(
        "product.get_product_product__product_id_.get",
        metadata={"suggested_alias": "product.get_product.get"},
    )
    result = resolver.resolve([mod])
    d = result[0].metadata["display"]
    assert d["alias"] == "product.get_product.get"


def test_display_alias_takes_priority_over_suggested_alias(resolver: DisplayResolver) -> None:
    mod = _mod(
        "product.get_product_product__product_id_.get",
        metadata={"suggested_alias": "product.get_product.get"},
    )
    result = resolver.resolve(
        [mod],
        binding_data={
            "bindings": [
                {
                    "module_id": "product.get_product_product__product_id_.get",
                    "display": {"alias": "product-detail"},
                }
            ]
        },
    )
    d = result[0].metadata["display"]
    assert d["alias"] == "product-detail"


# ---------------------------------------------------------------------------
# Sparse overlay — unmentioned modules get scanner values
# ---------------------------------------------------------------------------


def test_sparse_overlay_unmentioned_module_unchanged(resolver: DisplayResolver) -> None:
    """10 modules, 1 in binding.yaml → 10 modules returned, 9 with scanner values."""
    mods = [_mod(f"mod.func{i}", f"Description {i}", tags=[f"tag{i}"]) for i in range(10)]
    result = resolver.resolve(
        mods,
        binding_data={"bindings": [{"module_id": "mod.func3", "display": {"alias": "special-func"}}]},
    )
    assert len(result) == 10
    assert result[3].metadata["display"]["alias"] == "special-func"
    assert result[3].metadata["display"]["cli"]["alias"] == "special-func"
    for i in [0, 1, 2, 4, 5, 6, 7, 8, 9]:
        assert result[i].metadata["display"]["alias"] == f"mod.func{i}"


# ---------------------------------------------------------------------------
# Tags resolution
# ---------------------------------------------------------------------------


def test_display_tags_override_scanner_tags(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod(tags=["old"])],
        binding_data={"bindings": [{"module_id": "image.resize", "display": {"tags": ["image", "v2"]}}]},
    )
    assert result[0].metadata["display"]["tags"] == ["image", "v2"]


def test_tags_only_binding_entry_not_dropped(resolver: DisplayResolver) -> None:
    """Binding entries with only tags (no display/description) must not be silently dropped."""
    result = resolver.resolve(
        [_mod(tags=["old"])],
        binding_data={"bindings": [{"module_id": "image.resize", "tags": ["payment", "v2"]}]},
    )
    assert result[0].metadata["display"]["tags"] == ["payment", "v2"]


def test_scanner_tags_used_when_no_display_tags(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod(tags=["scanner-tag"])],
        binding_data={"bindings": [{"module_id": "image.resize", "description": "override"}]},
    )
    assert result[0].metadata["display"]["tags"] == ["scanner-tag"]


# ---------------------------------------------------------------------------
# binding_data dict format (module_id → entry map)
# ---------------------------------------------------------------------------


def test_binding_data_as_direct_map(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod("image.resize")],
        binding_data={"image.resize": {"display": {"alias": "img-resize"}}},
    )
    assert result[0].metadata["display"]["alias"] == "img-resize"


# ---------------------------------------------------------------------------
# binding_path file loading
# ---------------------------------------------------------------------------


def test_binding_path_missing_logs_warning(resolver: DisplayResolver, tmp_path, caplog) -> None:
    import logging

    with caplog.at_level(logging.WARNING, logger="apcore_toolkit"):
        result = resolver.resolve([_mod()], binding_path=tmp_path / "nonexistent.binding.yaml")
    # Should not raise, just warn; module falls through to scanner values
    assert len(result) == 1
    assert result[0].metadata["display"]["alias"] == "image.resize"


def test_binding_data_takes_precedence_over_binding_path(resolver: DisplayResolver, tmp_path) -> None:
    """When both binding_data and binding_path are provided, binding_data wins."""
    # Write a file that would override to "from-file"
    (tmp_path / "test.binding.yaml").write_text(
        "bindings:\n  - module_id: image.resize\n    display:\n      alias: from-file\n"
    )
    # binding_data overrides with "from-data"
    result = resolver.resolve(
        [_mod("image.resize")],
        binding_path=tmp_path,
        binding_data={"bindings": [{"module_id": "image.resize", "display": {"alias": "from-data"}}]},
    )
    assert result[0].metadata["display"]["alias"] == "from-data"


def test_binding_path_yaml_file(resolver: DisplayResolver, tmp_path) -> None:
    yaml_content = """
bindings:
  - module_id: image.resize
    display:
      alias: img-resize
"""
    f = tmp_path / "test.binding.yaml"
    f.write_text(yaml_content)
    result = resolver.resolve([_mod("image.resize")], binding_path=f)
    assert result[0].metadata["display"]["alias"] == "img-resize"


def test_binding_path_directory_loads_all_yaml_files(resolver: DisplayResolver, tmp_path) -> None:
    (tmp_path / "a.binding.yaml").write_text(
        "bindings:\n  - module_id: image.resize\n    display:\n      alias: img-resize\n"
    )
    (tmp_path / "b.binding.yaml").write_text(
        "bindings:\n  - module_id: text.summarize\n    display:\n      alias: summarize\n"
    )
    mods = [_mod("image.resize"), _mod("text.summarize", "Summarize text")]
    result = resolver.resolve(mods, binding_path=tmp_path)
    assert result[0].metadata["display"]["alias"] == "img-resize"
    assert result[1].metadata["display"]["alias"] == "summarize"


# ---------------------------------------------------------------------------
# guidance resolution
# ---------------------------------------------------------------------------


def test_guidance_from_display(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod()],
        binding_data={
            "bindings": [
                {
                    "module_id": "image.resize",
                    "display": {"guidance": "Use width/height in pixels."},
                }
            ]
        },
    )
    d = result[0].metadata["display"]
    assert d["guidance"] == "Use width/height in pixels."
    assert d["cli"]["guidance"] == "Use width/height in pixels."
    assert d["mcp"]["guidance"] == "Use width/height in pixels."
    assert d["a2a"]["guidance"] == "Use width/height in pixels."


def test_surface_guidance_overrides_default(resolver: DisplayResolver) -> None:
    result = resolver.resolve(
        [_mod()],
        binding_data={
            "bindings": [
                {
                    "module_id": "image.resize",
                    "display": {
                        "guidance": "Default guidance.",
                        "mcp": {"guidance": "MCP-specific guidance."},
                    },
                }
            ]
        },
    )
    d = result[0].metadata["display"]
    assert d["mcp"]["guidance"] == "MCP-specific guidance."
    assert d["cli"]["guidance"] == "Default guidance."


def test_no_guidance_is_none(resolver: DisplayResolver) -> None:
    result = resolver.resolve([_mod()])
    d = result[0].metadata["display"]
    assert d["guidance"] is None
    assert d["cli"]["guidance"] is None


# ---------------------------------------------------------------------------
# existing metadata is preserved (non-display keys untouched)
# ---------------------------------------------------------------------------


def test_existing_metadata_preserved(resolver: DisplayResolver) -> None:
    mod = _mod(metadata={"source": "openapi", "operation_id": "get_user_get"})
    result = resolver.resolve([mod])
    m = result[0].metadata
    assert m["source"] == "openapi"
    assert m["operation_id"] == "get_user_get"
    assert "display" in m


# ---------------------------------------------------------------------------
# CLI alias: invalid explicit alias warns + falls back
# ---------------------------------------------------------------------------


def test_cli_explicit_invalid_alias_falls_back(resolver: DisplayResolver, caplog) -> None:
    import logging

    with caplog.at_level(logging.WARNING, logger="apcore_toolkit"):
        result = resolver.resolve(
            [_mod("my.mod")],
            binding_data={"bindings": [{"module_id": "my.mod", "display": {"cli": {"alias": "MyAlias"}}}]},
        )
    assert "MyAlias" in caplog.text
    # Falls back to display.alias → module_id
    assert result[0].metadata["display"]["cli"]["alias"] == "my.mod"


def test_cli_implicit_module_id_no_warning(resolver: DisplayResolver, caplog) -> None:
    """No warning when CLI alias is implicitly from module_id (dots ok in CLI cmd names)."""
    import logging

    with caplog.at_level(logging.WARNING, logger="apcore_toolkit"):
        resolver.resolve([_mod("image.resize")])
    assert "image.resize" not in caplog.text or "CLI alias" not in caplog.text


# ---------------------------------------------------------------------------
# Dual-source suggested_alias resolution (field + metadata compat)
# ---------------------------------------------------------------------------


def _make_module(
    module_id: str = "tasks.user_data.post",
    *,
    suggested_alias: str | None = None,
    metadata_alias: str | None = None,
) -> ScannedModule:
    from typing import Any

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
        # display.alias from binding.yaml overrides suggested_alias.
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
        # Defensive: dataclass-like object without the suggested_alias attribute.
        # The resolver's getattr(mod, "suggested_alias", None) must not raise.
        from dataclasses import dataclass, field
        from typing import Any

        @dataclass
        class FakeMod:
            module_id: str = "foo.bar"
            description: str = "x"
            documentation: str | None = None
            tags: list[str] = field(default_factory=list)
            metadata: dict[str, Any] = field(default_factory=lambda: {"suggested_alias": "foo.bar.list"})

        [resolved] = self.resolver.resolve([FakeMod()])
        # Falls through to metadata since getattr defaults to None.
        assert resolved.metadata["display"]["alias"] == "foo.bar.list"


class TestMalformedBindingYAML:
    """display.{cli,mcp,a2a} supplied as a non-dict value (common YAML typo) must not crash."""

    def setup_method(self) -> None:
        self.resolver = DisplayResolver()

    def _make_module(self, module_id: str = "tasks.create") -> ScannedModule:
        return ScannedModule(
            module_id=module_id,
            description="Create a task",
            input_schema={},
            output_schema={},
            tags=[],
            target="mod:func",
        )

    def test_display_cli_as_string_is_coerced_to_empty_dict(self) -> None:
        """display.cli: "tasks-create" (string typo) must not raise AttributeError."""
        mod = self._make_module()
        binding_data = {
            "bindings": [
                {
                    "module_id": "tasks.create",
                    "display": {
                        "alias": "tasks.create",
                        "cli": "tasks-create",  # should be a dict
                    },
                }
            ]
        }
        result = self.resolver.resolve([mod], binding_data=binding_data)
        d = result[0].metadata["display"]
        assert d["cli"]["alias"] == "tasks.create"

    def test_display_mcp_as_string_is_coerced_to_empty_dict(self) -> None:
        """display.mcp: "tasks_create" (string typo) must not raise AttributeError."""
        mod = self._make_module()
        binding_data = {
            "bindings": [
                {
                    "module_id": "tasks.create",
                    "display": {
                        "alias": "tasks.create",
                        "mcp": "tasks_create",  # should be a dict
                    },
                }
            ]
        }
        result = self.resolver.resolve([mod], binding_data=binding_data)
        d = result[0].metadata["display"]
        assert d["mcp"]["alias"] == "tasks_create"

    def test_display_a2a_as_string_is_coerced_to_empty_dict(self) -> None:
        """display.a2a as a non-dict must not raise AttributeError."""
        mod = self._make_module()
        binding_data = {
            "bindings": [
                {
                    "module_id": "tasks.create",
                    "display": {
                        "alias": "tasks.create",
                        "a2a": 42,  # should be a dict
                    },
                }
            ]
        }
        result = self.resolver.resolve([mod], binding_data=binding_data)
        d = result[0].metadata["display"]
        assert d["a2a"]["alias"] == "tasks.create"

    def test_all_surfaces_as_non_dict_fall_through_to_defaults(self) -> None:
        """All three surfaces malformed: all fall through to display-level defaults."""
        mod = self._make_module("img.resize")
        binding_data = {
            "bindings": [
                {
                    "module_id": "img.resize",
                    "display": {
                        "alias": "img.resize",
                        "cli": "bad",
                        "mcp": "bad",
                        "a2a": "bad",
                    },
                }
            ]
        }
        result = self.resolver.resolve([mod], binding_data=binding_data)
        d = result[0].metadata["display"]
        assert d["alias"] == "img.resize"
        assert d["cli"]["alias"] == "img.resize"
        assert d["mcp"]["alias"] == "img_resize"  # dot replaced by sanitizer
