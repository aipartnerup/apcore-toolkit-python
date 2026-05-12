"""Conformance harness: assert Python reference impl matches the shared
fixture corpus at ``apcore-toolkit/conformance/fixtures/``.

The TypeScript and Rust SDKs run the same fixture files through their own
implementations and assert byte-equivalent output. This is the cross-SDK
byte-identity contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apcore_toolkit.formatting.tabular import format_csv, format_jsonl

_CONFORMANCE_DIR = Path(__file__).resolve().parent.parent.parent / "apcore-toolkit" / "conformance" / "fixtures"


def _load_fixture(name: str) -> list[dict]:
    path = _CONFORMANCE_DIR / name
    if not path.exists():
        pytest.skip(f"conformance fixture not found at {path}", allow_module_level=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["test_cases"]


@pytest.mark.parametrize("case", _load_fixture("format_csv.json"), ids=lambda c: c["id"])
def test_format_csv_conformance(case: dict) -> None:
    inp = case["input"]
    actual = format_csv(inp["rows"], bom=inp.get("bom", False))
    assert actual == case["expected"], (
        f"\nCase {case['id']}: {case['description']}\n" f"Expected: {case['expected']!r}\n" f"Actual:   {actual!r}"
    )


@pytest.mark.parametrize("case", _load_fixture("format_jsonl.json"), ids=lambda c: c["id"])
def test_format_jsonl_conformance(case: dict) -> None:
    actual = format_jsonl(case["input"]["rows"])
    assert actual == case["expected"], (
        f"\nCase {case['id']}: {case['description']}\n" f"Expected: {case['expected']!r}\n" f"Actual:   {actual!r}"
    )
