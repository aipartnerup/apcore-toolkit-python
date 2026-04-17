"""ScannedModule dataclass — canonical representation of a scanned endpoint.

Unified superset of django-apcore and flask-apcore ScannedModule definitions.
Web-specific fields (http_method, url_rule) are stored in the ``metadata`` dict
rather than as top-level fields, keeping the dataclass domain-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apcore import ModuleAnnotations, ModuleExample


@dataclass
class ScannedModule:
    """Result of scanning a single endpoint.

    Attributes:
        module_id: Unique module identifier (e.g., 'users.get_user.get').
        description: Human-readable description for MCP tool listing.
        input_schema: JSON Schema dict for module input.
        output_schema: JSON Schema dict for module output.
        tags: Categorization tags.
        target: Callable reference in 'module.path:callable' format.
        version: Module version string.
        annotations: Behavioral annotations (readonly, destructive, etc.).
        documentation: Full docstring text for rich descriptions.
        suggested_alias: Scanner-generated human-friendly alias used by
            surface adapters in the resolve chain before falling back to
            module_id. Scanners SHOULD set this using
            ``BaseScanner.generate_suggested_alias()`` when the source
            endpoint has HTTP route information. Defaults to ``None``.
        examples: Example invocations for documentation and testing.
        metadata: Arbitrary key-value data (e.g., http_method, url_rule).
        warnings: Non-fatal issues encountered during scanning.
    """

    module_id: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tags: list[str]
    target: str
    version: str = "1.0.0"
    annotations: ModuleAnnotations | None = None
    documentation: str | None = None
    suggested_alias: str | None = None
    examples: list[ModuleExample] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
