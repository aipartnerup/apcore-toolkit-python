# Feature Overview: HTTP Verb Semantic Mapping

**Package**: apcore-toolkit-python v0.5.0
**Date**: 2026-04-16
**Tech Design**: `docs/http-verb-mapping/tech-design.md`

---

## Summary

The HTTP Verb Semantic Mapping feature adds shared utilities for converting raw HTTP methods (GET, POST, PUT, DELETE, etc.) into human-friendly semantic verbs (list, create, update, delete, etc.) and generating `suggested_alias` values for scanned endpoints. This enables downstream CLI and surface adapters to present user-facing command names that follow industry conventions.

## Component Map

```
src/apcore_toolkit/
    http_verb_map.py          <-- NEW: standalone module (spec: http-verb-map.md)
    scanner.py                <-- UPDATE: add generate_suggested_alias() staticmethod
                                   (spec: scanner-integration.md)
    types.py                  <-- UPDATE: add suggested_alias field to ScannedModule
                                   (spec: scanner-integration.md)
    display/
        resolver.py           <-- UPDATE: dual-source alias resolution
                                   (spec: display-resolver-update.md)
    __init__.py               <-- UPDATE: re-export new public symbols

tests/
    fixtures/
        scanner_verb_map.json <-- NEW: cross-language conformance fixture
    test_http_verb_map.py     <-- NEW: unit + conformance tests
    test_scanner.py           <-- UPDATE: tests for new staticmethod
    test_types.py             <-- UPDATE: tests for new field
    test_display_resolver.py  <-- UPDATE: tests for dual-source resolution
```

## Feature Specs

| Spec Document | Component | Change Type |
|---|---|---|
| [http-verb-map.md](http-verb-map.md) | `http_verb_map.py` | New module |
| [scanner-integration.md](scanner-integration.md) | `scanner.py`, `types.py` | Additive update |
| [display-resolver-update.md](display-resolver-update.md) | `display/resolver.py` | Backward-compatible update |

## Dependency Flow

```
http_verb_map.py  (standalone, no internal deps)
       |
       v
scanner.py  (delegates to http_verb_map.py)
       |
       v
types.py  (ScannedModule carries suggested_alias)
       |
       v
display/resolver.py  (reads suggested_alias from field + metadata)
```

## Public API Additions

All new symbols are re-exported from `apcore_toolkit.__init__`:

| Symbol | Type | Import Path |
|---|---|---|
| `SCANNER_VERB_MAP` | `dict[str, str]` | `apcore_toolkit.http_verb_map` |
| `resolve_http_verb` | `function` | `apcore_toolkit.http_verb_map` |
| `has_path_params` | `function` | `apcore_toolkit.http_verb_map` |
| `generate_suggested_alias` | `function` | `apcore_toolkit.http_verb_map` |

Existing symbols with additions:

| Symbol | Change |
|---|---|
| `BaseScanner` | New `@staticmethod generate_suggested_alias(path, method)` |
| `ScannedModule` | New field `suggested_alias: str \| None = None` |
| `DisplayResolver` | Reads `suggested_alias` from field first, then metadata fallback |

## Versioning

This release is `v0.5.0` (minor bump) because it adds new public API surface. All changes are backward compatible. Existing code that constructs `ScannedModule` without `suggested_alias` continues to work due to the `None` default. Existing scanners that set `metadata["suggested_alias"]` continue to work via the `DisplayResolver` fallback.

## Cross-Language Conformance

A JSON fixture at `tests/fixtures/scanner_verb_map.json` defines input/output pairs. The identical fixture is maintained in:

- `apcore-toolkit-python` (this package)
- `apcore-toolkit-typescript`
- `apcore-toolkit-rust`

CI in each language validates that `generate_suggested_alias()` produces identical output for every fixture entry.
