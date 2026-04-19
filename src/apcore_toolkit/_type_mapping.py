"""Shared Python ↔ JSON Schema type vocabulary.

Single source of truth for the 6-type mapping used by ConventionScanner
(Python→JSON Schema) and PythonWriter (JSON Schema→Python). Adding a new
type here propagates to both automatically.
"""

from __future__ import annotations

PYTHON_TO_JSON_SCHEMA: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}

JSON_SCHEMA_TO_PYTHON: dict[str, str] = {v: k for k, v in PYTHON_TO_JSON_SCHEMA.items()}
