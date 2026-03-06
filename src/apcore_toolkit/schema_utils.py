"""JSON Schema enrichment utilities.

Helpers for merging docstring-extracted parameter descriptions into
JSON Schema ``properties``. Designed to be called by concrete scanner
implementations when their schema source lacks parameter descriptions
(e.g., schemas generated from bare type hints).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def enrich_schema_descriptions(
    schema: dict[str, Any],
    param_descriptions: dict[str, str],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Merge parameter descriptions into JSON Schema properties.

    By default, only fills in *missing* descriptions — existing ones are
    preserved. Set ``overwrite=True`` to replace existing descriptions.

    Args:
        schema: A JSON Schema dict with a ``properties`` key.
        param_descriptions: Mapping of parameter names to description strings,
            typically from ``parse_docstring()``.
        overwrite: If True, overwrite existing ``description`` fields.

    Returns:
        A **new** schema dict with descriptions merged in when changes are
        needed. Returns the original schema as-is when ``param_descriptions``
        is empty or the schema has no ``properties``. The original schema is
        not mutated when a new dict is returned.
    """
    if not param_descriptions:
        return schema

    properties = schema.get("properties")
    if not properties:
        return schema

    result = deepcopy(schema)
    for name, desc in param_descriptions.items():
        if name in result["properties"]:
            prop = result["properties"][name]
            if overwrite or "description" not in prop:
                prop["description"] = desc

    return result
