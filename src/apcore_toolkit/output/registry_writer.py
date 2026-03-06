"""Registry writer for direct module registration.

Converts ScannedModule instances into apcore FunctionModule instances
and registers them directly into an apcore Registry. This is the default
output mode for framework adapters (no file I/O needed).

Extracted from flask-apcore's registry_writer.py into the shared toolkit.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apcore_toolkit.pydantic_utils import flatten_pydantic_params, resolve_target
from apcore_toolkit.serializers import annotations_to_dict

if TYPE_CHECKING:
    from apcore import Registry

    from apcore_toolkit.types import ScannedModule

logger = logging.getLogger("apcore_toolkit")


class RegistryWriter:
    """Converts ScannedModule to FunctionModule and registers into Registry.

    This is the default writer used when no output_format is specified.
    Instead of writing YAML binding files, it registers modules directly
    into the apcore Registry for immediate use.
    """

    def write(
        self,
        modules: list[ScannedModule],
        registry: Registry,
        *,
        dry_run: bool = False,
    ) -> list[str]:
        """Register scanned modules into the registry.

        Args:
            modules: List of ScannedModule instances to register.
            registry: The apcore Registry to register modules into.
            dry_run: If True, skip registration and return module IDs only.

        Returns:
            List of registered module IDs.
        """
        registered: list[str] = []
        for mod in modules:
            if dry_run:
                registered.append(mod.module_id)
                continue
            fm = self._to_function_module(mod)
            registry.register(mod.module_id, fm)
            registered.append(mod.module_id)
            logger.debug("Registered module: %s", mod.module_id)
        return registered

    def _to_function_module(self, mod: ScannedModule) -> Any:
        """Convert a ScannedModule to an apcore FunctionModule.

        Args:
            mod: The ScannedModule to convert.

        Returns:
            A FunctionModule instance ready for registry insertion.
        """
        from apcore import FunctionModule

        func = flatten_pydantic_params(resolve_target(mod.target))

        return FunctionModule(
            func=func,
            module_id=mod.module_id,
            description=mod.description,
            documentation=mod.documentation,
            tags=mod.tags,
            version=mod.version,
            annotations=annotations_to_dict(mod.annotations),
            metadata=mod.metadata,
            examples=mod.examples or None,
        )
