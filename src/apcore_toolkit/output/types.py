"""Shared types for output writers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WriteResult:
    """Result of writing a single module.

    Attributes:
        module_id: The module that was written.
        path: Output file path (None for RegistryWriter).
        verified: Whether verification passed (always True if verify=False).
        verification_error: Error message if verification failed.
    """

    module_id: str
    path: str | None = None
    verified: bool = True
    verification_error: str | None = None
