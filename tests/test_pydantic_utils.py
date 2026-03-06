"""Tests for apcore_toolkit.pydantic_utils — Pydantic flattening and target resolution."""

from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel

from apcore_toolkit.pydantic_utils import flatten_pydantic_params, resolve_target


# --- Test models ---


class TaskCreate(BaseModel):
    title: str
    done: bool = False


class UserUpdate(BaseModel):
    name: str
    email: str = "default@example.com"


# --- Test functions ---


def simple_func(x: int, y: str = "hello") -> str:
    return f"{x}-{y}"


def pydantic_func(body: TaskCreate) -> dict:
    return {"title": body.title, "done": body.done}


def mixed_func(name: str, body: TaskCreate) -> dict:
    return {"name": name, "title": body.title}


def multi_pydantic(task: TaskCreate, user: UserUpdate) -> dict:
    return {"title": task.title, "name": user.name}


def no_hints(x, y):
    return x + y


class TestFlattenPydanticParams:
    def test_no_pydantic_returns_same(self) -> None:
        result = flatten_pydantic_params(simple_func)
        assert result is simple_func

    def test_single_pydantic_model(self) -> None:
        wrapped = flatten_pydantic_params(pydantic_func)
        assert wrapped is not pydantic_func
        result = wrapped(title="Test", done=True)
        assert result == {"title": "Test", "done": True}

    def test_single_pydantic_model_default(self) -> None:
        wrapped = flatten_pydantic_params(pydantic_func)
        result = wrapped(title="Test")
        assert result == {"title": "Test", "done": False}

    def test_mixed_simple_and_pydantic(self) -> None:
        wrapped = flatten_pydantic_params(mixed_func)
        result = wrapped(name="Alice", title="Task1")
        assert result == {"name": "Alice", "title": "Task1"}

    def test_multiple_pydantic_models(self) -> None:
        wrapped = flatten_pydantic_params(multi_pydantic)
        result = wrapped(title="Task", done=True, name="Alice", email="a@b.com")
        assert result == {"title": "Task", "name": "Alice"}

    def test_no_type_hints(self) -> None:
        result = flatten_pydantic_params(no_hints)
        assert result is no_hints

    def test_flat_signature(self) -> None:
        wrapped = flatten_pydantic_params(pydantic_func)
        sig = inspect.signature(wrapped)
        param_names = list(sig.parameters.keys())
        assert "title" in param_names
        assert "done" in param_names
        assert "body" not in param_names

    def test_flat_annotations(self) -> None:
        wrapped = flatten_pydantic_params(pydantic_func)
        assert wrapped.__annotations__["title"] is str
        assert wrapped.__annotations__["done"] is bool

    def test_preserves_name(self) -> None:
        wrapped = flatten_pydantic_params(pydantic_func)
        assert wrapped.__name__ == "pydantic_func"


class TestResolveTarget:
    def test_resolve_builtin(self) -> None:
        result = resolve_target("json:loads")
        import json

        assert result is json.loads

    def test_resolve_nested(self) -> None:
        result = resolve_target("os.path:join")
        import os.path

        assert result is os.path.join

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid target format"):
            resolve_target("no_colon_here")

    def test_missing_module(self) -> None:
        with pytest.raises(ImportError):
            resolve_target("nonexistent_module_xyz:func")

    def test_missing_attribute(self) -> None:
        with pytest.raises(AttributeError):
            resolve_target("json:nonexistent_function_xyz")
