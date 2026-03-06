# apcore-toolkit

Shared scanner, schema extraction, and output toolkit for apcore Python framework adapters.

Extracts ~1,400 lines of duplicated framework-agnostic logic from `django-apcore` and `flask-apcore` into a standalone Python package.

## Installation

```bash
pip install apcore-toolkit
```

## Usage

```python
from apcore_toolkit import ScannedModule, BaseScanner, YAMLWriter, PythonWriter
from apcore_toolkit import flatten_pydantic_params, resolve_target
from apcore_toolkit.openapi import resolve_ref, extract_input_schema, extract_output_schema
from apcore_toolkit.serializers import module_to_dict, modules_to_dicts
from apcore_toolkit.output import get_writer
```
