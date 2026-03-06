"""Shared test fixtures for apcore-toolkit."""

from __future__ import annotations

import pytest
from apcore import ModuleAnnotations

from apcore_toolkit.types import ScannedModule


@pytest.fixture
def sample_module() -> ScannedModule:
    """A minimal ScannedModule with all required fields."""
    return ScannedModule(
        module_id="users.get_user",
        description="Get a user by ID",
        input_schema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]},
        output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        tags=["users"],
        target="myapp.views:get_user",
    )


@pytest.fixture
def annotated_module() -> ScannedModule:
    """A ScannedModule with annotations, documentation, and metadata."""
    return ScannedModule(
        module_id="tasks.create_task",
        description="Create a new task",
        input_schema={
            "type": "object",
            "properties": {"title": {"type": "string"}, "done": {"type": "boolean"}},
            "required": ["title"],
        },
        output_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
        tags=["tasks"],
        target="myapp.views:create_task",
        version="2.0.0",
        annotations=ModuleAnnotations(destructive=True),
        documentation="Create a new task with the given title.",
        metadata={"http_method": "POST", "url_rule": "/tasks"},
    )
