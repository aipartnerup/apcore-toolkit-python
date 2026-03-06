# apcore-toolkit

Shared scanner, schema extraction, and output toolkit for [apcore](https://github.com/aipartnerup/apcore-python) Python framework adapters.

Extracts ~1,400 lines of duplicated framework-agnostic logic from `django-apcore` and `flask-apcore` into a standalone Python package.

## Installation

```bash
pip install apcore-toolkit
```

## Core Modules

| Module | Description |
|--------|-------------|
| `ScannedModule` | Canonical dataclass representing a scanned endpoint |
| `BaseScanner` | Abstract base class for framework scanners with filtering and deduplication |
| `YAMLWriter` | Generates `.binding.yaml` files for `apcore.BindingLoader` |
| `PythonWriter` | Generates `@module`-decorated Python wrapper files |
| `RegistryWriter` | Registers modules directly into an `apcore.Registry` |
| `to_markdown` | Converts arbitrary dicts to Markdown with depth control and table heuristics |

## Usage

### Scanning and Writing

```python
from apcore_toolkit import BaseScanner, ScannedModule, YAMLWriter

class MyScanner(BaseScanner):
    def scan(self, **kwargs):
        # Scan your framework endpoints and return ScannedModule instances
        return [
            ScannedModule(
                module_id="users.get_user",
                description="Get a user by ID",
                input_schema={"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
                output_schema={"type": "object", "properties": {"name": {"type": "string"}}},
                tags=["users"],
                target="myapp.views:get_user",
            )
        ]

    def get_source_name(self):
        return "my-framework"

scanner = MyScanner()
modules = scanner.scan()

# Filter and deduplicate
modules = scanner.filter_modules(modules, include=r"^users\.")
modules = scanner.deduplicate_ids(modules)

# Write YAML binding files
writer = YAMLWriter()
writer.write(modules, output_dir="./bindings")
```

### Direct Registry Registration

```python
from apcore import Registry
from apcore_toolkit import RegistryWriter

registry = Registry()
writer = RegistryWriter()
writer.write(modules, registry)
```

### Output Format Factory

```python
from apcore_toolkit.output import get_writer

writer = get_writer("yaml")    # YAMLWriter
writer = get_writer("python")  # PythonWriter
writer = get_writer("registry")  # RegistryWriter
```

### Pydantic Model Flattening

```python
from apcore_toolkit import flatten_pydantic_params, resolve_target

# Resolve a target string to a callable
func = resolve_target("myapp.views:create_task")

# Flatten Pydantic model params into scalar kwargs for MCP tools
wrapped = flatten_pydantic_params(func)
```

### OpenAPI Schema Extraction

```python
from apcore_toolkit.openapi import extract_input_schema, extract_output_schema

input_schema = extract_input_schema(operation, openapi_doc)
output_schema = extract_output_schema(operation, openapi_doc)
```

### Schema Enrichment

```python
from apcore_toolkit import enrich_schema_descriptions

enriched = enrich_schema_descriptions(schema, {"user_id": "The user ID"})
```

### Markdown Formatting

```python
from apcore_toolkit import to_markdown

md = to_markdown({"name": "Alice", "role": "admin"}, title="User Info")
```

## Requirements

- Python >= 3.11
- apcore >= 0.9.0
- pydantic >= 2.0
- PyYAML >= 6.0

## License

Apache-2.0
