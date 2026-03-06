"""Tests for apcore_toolkit.formatting.markdown — to_markdown()."""

from __future__ import annotations

import pytest

from apcore_toolkit.formatting.markdown import to_markdown


class TestScalarDict:
    def test_simple_flat_dict(self) -> None:
        data = {"task_id": "abc", "status": "completed", "score": 86.5}
        result = to_markdown(data)
        assert "**task_id**: abc" in result
        assert "**status**: completed" in result
        assert "**score**: 86.5" in result

    def test_flat_dict_as_table(self) -> None:
        data = {f"key_{i}": f"val_{i}" for i in range(6)}
        result = to_markdown(data, table_threshold=5)
        assert "| Field | Value |" in result
        assert "| key_0 | val_0 |" in result

    def test_below_table_threshold_uses_bullets(self) -> None:
        data = {"a": 1, "b": 2}
        result = to_markdown(data, table_threshold=5)
        assert "| Field |" not in result
        assert "**a**: 1" in result


class TestFieldsAndExclude:
    def test_fields_filter(self) -> None:
        data = {"a": 1, "b": 2, "c": 3}
        result = to_markdown(data, fields=["a", "c"])
        assert "**a**: 1" in result
        assert "**c**: 3" in result
        assert "**b**" not in result

    def test_exclude_filter(self) -> None:
        data = {"a": 1, "token_usage": 999, "c": 3}
        result = to_markdown(data, exclude=["token_usage"])
        assert "**a**: 1" in result
        assert "token_usage" not in result

    def test_exclude_applies_to_nested(self) -> None:
        data = {"outer": {"keep": 1, "secret": 2}}
        result = to_markdown(data, exclude=["secret"])
        assert "**keep**: 1" in result
        assert "secret" not in result


class TestNestedDict:
    def test_depth_1_heading(self) -> None:
        data = {"summary": {"total": 10, "passed": 8}}
        result = to_markdown(data)
        assert "## summary" in result
        assert "**total**: 10" in result

    def test_nested_heading_levels(self) -> None:
        data = {"l1": {"l2": {"l3": {"l4": "val"}}}}
        result = to_markdown(data, max_depth=4)
        assert "## l1" in result
        assert "### l2" in result
        assert "#### l3" in result

    def test_max_depth_truncates(self) -> None:
        data = {"a": {"b": {"c": {"d": "deep"}}}}
        result = to_markdown(data, max_depth=2)
        # a at abs_depth 0 → heading, b at abs_depth 1 → compact (abs_depth+1=2 >= max_depth)
        assert "## a" in result
        assert "**b**: {c:" in result

    def test_deeply_nested_compact(self) -> None:
        data = {"l1": {"l2": {"l3": {"l4": "val"}}}}
        result = to_markdown(data, max_depth=3)
        assert "## l1" in result
        assert "### l2" in result
        assert "**l3**: {l4: val}" in result


class TestListRendering:
    def test_scalar_list(self) -> None:
        data = {"tags": ["alpha", "beta"]}
        result = to_markdown(data)
        assert "- alpha" in result
        assert "- beta" in result

    def test_empty_list(self) -> None:
        data = {"items": []}
        result = to_markdown(data)
        assert "*(empty)*" in result

    def test_uniform_dict_list_as_table(self) -> None:
        data = {
            "results": [
                {"name": "Alice", "score": 95},
                {"name": "Bob", "score": 88},
                {"name": "Charlie", "score": 72},
            ]
        }
        result = to_markdown(data)
        assert "| name | score |" in result
        assert "| Alice | 95 |" in result

    def test_non_uniform_dict_list_as_bullets(self) -> None:
        data = {
            "items": [
                {"name": "x", "value": 1},
                {"name": "y", "extra": 2},
            ]
        }
        result = to_markdown(data)
        assert "| name |" not in result


class TestSpecialValues:
    def test_none_renders_na(self) -> None:
        data = {"value": None}
        result = to_markdown(data)
        assert "*N/A*" in result

    def test_bool_renders_yes_no(self) -> None:
        data = {"active": True, "deleted": False}
        result = to_markdown(data)
        assert "Yes" in result
        assert "No" in result

    def test_float_precision(self) -> None:
        data = {"score": 86.85909090909091}
        result = to_markdown(data)
        assert "86.86" in result


class TestTitle:
    def test_title_prepended(self) -> None:
        data = {"x": 1}
        result = to_markdown(data, title="Report")
        assert result.startswith("# Report\n")


class TestEdgeCases:
    def test_empty_dict(self) -> None:
        result = to_markdown({})
        assert result == "\n"

    def test_non_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="expects a dict"):
            to_markdown([1, 2, 3])  # type: ignore[arg-type]

    def test_pipe_in_table_values(self) -> None:
        data = {f"k{i}": f"v{i}" for i in range(5)}
        data["k0"] = "a|b"
        result = to_markdown(data, table_threshold=5)
        assert "a\\|b" in result
        assert "| Field | Value |" in result

    def test_pipe_in_list_table(self) -> None:
        data = {
            "items": [
                {"name": "x|y", "val": 1},
                {"name": "a", "val": 2},
            ]
        }
        result = to_markdown(data)
        assert "x\\|y" in result

    def test_single_item_dict_list_no_table(self) -> None:
        data = {"items": [{"name": "only", "score": 1}]}
        result = to_markdown(data)
        # Single item list should NOT render as table (requires >= 2)
        assert "| name |" not in result
        assert "**name**: only" in result

    def test_max_depth_1(self) -> None:
        data = {"a": 1, "nested": {"b": 2}}
        result = to_markdown(data, max_depth=1)
        assert "**a**: 1" in result
        assert "**nested**: {b: 2}" in result


class TestAEOLikeStructure:
    def test_complex_nested_with_max_depth(self) -> None:
        data = {
            "total_score": 86.86,
            "children_scores": {
                "analyzer_a": {"score": 71.96, "details": {"brand": {"score": 25}}},
                "analyzer_b": {"score": 100, "details": {"brand": {"score": 50}}},
            },
        }
        result = to_markdown(data, max_depth=3)
        assert "**total_score**: 86.86" in result
        assert "## children_scores" in result
        assert "### analyzer_a" in result
        assert "### analyzer_b" in result
        # details at abs_depth 3 → compact
        assert "{brand:" in result
