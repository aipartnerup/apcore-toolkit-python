"""Generic dict-to-Markdown conversion with depth control and table heuristics.

Provides ``to_markdown()`` — a best-effort converter for arbitrary dicts.
For complex domain-specific structures, modules should implement their own
``format_output()`` method instead of relying on this generic converter.
"""

from __future__ import annotations

from typing import Any


def to_markdown(
    data: dict[str, Any],
    *,
    fields: list[str] | None = None,
    exclude: list[str] | None = None,
    max_depth: int = 3,
    table_threshold: int = 5,
    title: str | None = None,
) -> str:
    """Convert a dict to a Markdown string.

    Args:
        data: The dictionary to convert.
        fields: If provided, only include these top-level keys (order preserved).
        exclude: Keys to exclude at every nesting level.
        max_depth: Maximum nesting depth to render. Beyond this, values are
            shown as inline JSON-like repr.
        table_threshold: When a dict at the current level has at least this
            many keys **and** all values are scalars, render as a Markdown table
            instead of a bullet list.
        title: Optional Markdown heading (``# title``) prepended to output.

    Returns:
        A Markdown-formatted string.
    """
    if not isinstance(data, dict):
        raise TypeError(f"to_markdown() expects a dict, got {type(data).__name__}")
    filtered = _filter_keys(data, fields=fields, exclude=exclude)
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    _render_dict(
        filtered, lines, depth=0, abs_depth=0, max_depth=max_depth, table_threshold=table_threshold, exclude=exclude
    )
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _filter_keys(
    data: dict[str, Any],
    *,
    fields: list[str] | None,
    exclude: list[str] | None,
) -> dict[str, Any]:
    if fields is not None:
        data = {k: data[k] for k in fields if k in data}
    if exclude:
        ex = set(exclude)
        data = {k: v for k, v in data.items() if k not in ex}
    return data


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _format_scalar(value: Any) -> str:
    if value is None:
        return "*N/A*"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _render_dict(
    data: dict[str, Any],
    lines: list[str],
    *,
    depth: int,
    abs_depth: int,
    max_depth: int,
    table_threshold: int,
    exclude: list[str] | None,
) -> None:
    """Render a dict as Markdown.

    ``depth`` controls indentation (resets under headings).
    ``abs_depth`` tracks true nesting level for max_depth enforcement.
    """
    if not data:
        return

    # Apply exclude at every level
    if exclude:
        ex = set(exclude)
        data = {k: v for k, v in data.items() if k not in ex}

    # Decide: table vs structured rendering
    all_scalar = all(_is_scalar(v) for v in data.values())

    if all_scalar and len(data) >= table_threshold:
        _render_table(data, lines)
        return

    for key, value in data.items():
        if _is_scalar(value):
            lines.append(f"{'  ' * depth}- **{key}**: {_format_scalar(value)}")

        elif isinstance(value, dict):
            if abs_depth + 1 >= max_depth:
                lines.append(f"{'  ' * depth}- **{key}**: {_compact_repr(value)}")
            else:
                # Use heading for top-level dict children, bullets for deeper
                if depth == 0:
                    heading_level = min(abs_depth + 2, 6)  # ## at top, ### deeper
                    lines.append("")
                    lines.append(f"{'#' * heading_level} {key}")
                    lines.append("")
                    _render_dict(
                        value,
                        lines,
                        depth=0,
                        abs_depth=abs_depth + 1,
                        max_depth=max_depth,
                        table_threshold=table_threshold,
                        exclude=exclude,
                    )
                else:
                    lines.append(f"{'  ' * depth}- **{key}**:")
                    _render_dict(
                        value,
                        lines,
                        depth=depth + 1,
                        abs_depth=abs_depth + 1,
                        max_depth=max_depth,
                        table_threshold=table_threshold,
                        exclude=exclude,
                    )

        elif isinstance(value, list):
            if abs_depth + 1 >= max_depth:
                lines.append(f"{'  ' * depth}- **{key}**: {_compact_repr(value)}")
            else:
                lines.append(f"{'  ' * depth}- **{key}**:")
                _render_list(
                    value,
                    lines,
                    depth=depth + 1,
                    abs_depth=abs_depth + 1,
                    max_depth=max_depth,
                    exclude=exclude,
                )
        else:
            lines.append(f"{'  ' * depth}- **{key}**: {_format_scalar(value)}")


def _render_list(
    items: list[Any],
    lines: list[str],
    *,
    depth: int,
    abs_depth: int,
    max_depth: int,
    exclude: list[str] | None,
) -> None:
    if not items:
        lines.append(f"{'  ' * depth}- *(empty)*")
        return

    # Homogeneous list of scalar-only dicts → render as table
    if (
        len(items) >= 2
        and all(isinstance(item, dict) for item in items)
        and _uniform_keys(items)
        and all(_is_scalar(v) for item in items for v in item.values())
    ):
        _render_list_table(items, lines, exclude=exclude)
        return

    ex = set(exclude) if exclude else None
    for item in items:
        if _is_scalar(item):
            lines.append(f"{'  ' * depth}- {_format_scalar(item)}")
        elif isinstance(item, dict):
            if abs_depth >= max_depth:
                lines.append(f"{'  ' * depth}- {_compact_repr(item)}")
            else:
                # Render each dict item inline under a bullet
                first = True
                for k, v in item.items():
                    if ex and k in ex:
                        continue
                    prefix = f"{'  ' * depth}- " if first else f"{'  ' * (depth + 1)}"
                    first = False
                    if _is_scalar(v):
                        lines.append(f"{prefix}**{k}**: {_format_scalar(v)}")
                    else:
                        lines.append(f"{prefix}**{k}**: {_compact_repr(v)}")
        elif isinstance(item, list):
            lines.append(f"{'  ' * depth}- {_compact_repr(item)}")
        else:
            lines.append(f"{'  ' * depth}- {_format_scalar(item)}")


def _escape_pipe(text: str) -> str:
    """Escape pipe characters for Markdown table cells."""
    return text.replace("|", "\\|")


def _render_table(data: dict[str, Any], lines: list[str]) -> None:
    """Render a flat dict as a two-column Markdown table."""
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    for key, value in data.items():
        lines.append(f"| {_escape_pipe(str(key))} | {_escape_pipe(_format_scalar(value))} |")
    lines.append("")


def _render_list_table(
    items: list[dict[str, Any]],
    lines: list[str],
    *,
    exclude: list[str] | None,
) -> None:
    """Render a list of uniform dicts as a Markdown table."""
    if not items:
        return
    keys = list(items[0].keys())
    if exclude:
        ex = set(exclude)
        keys = [k for k in keys if k not in ex]
    lines.append("| " + " | ".join(_escape_pipe(k) for k in keys) + " |")
    lines.append("| " + " | ".join("---" for _ in keys) + " |")
    for item in items:
        row = " | ".join(_escape_pipe(_format_scalar(item.get(k))) for k in keys)
        lines.append(f"| {row} |")
    lines.append("")


def _uniform_keys(items: list[dict[str, Any]]) -> bool:
    """Check if all dicts in a list share the same keys."""
    if not items:
        return True
    ref = set(items[0].keys())
    return all(set(item.keys()) == ref for item in items)


def _compact_repr(value: Any, max_len: int = 80) -> str:
    """Produce a compact string representation, truncated if needed."""
    if isinstance(value, dict):
        parts = ", ".join(f"{k}: {_compact_repr(v, max_len=30)}" for k, v in value.items())
        text = f"{{{parts}}}"
    elif isinstance(value, list):
        parts = ", ".join(_compact_repr(v, max_len=30) for v in value)
        text = f"[{parts}]"
    elif _is_scalar(value):
        text = _format_scalar(value)
    else:
        text = repr(value)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text
