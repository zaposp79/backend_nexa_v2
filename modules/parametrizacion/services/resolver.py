"""ParametrizationResolver — facade sobre repositories de datos maestros.

Responsabilidad actual (FASE DB.4 facade):
  - Delegar lecturas de HR, GN y OP a sus repositories conectados a DocumentStore.
  - Mantener caché en memoria por session.
  - Preservar métodos públicos existentes para compatibilidad con ParametrizationProvider
    y SimulationContextBuilder sin cambios en esos consumidores.

Lo que el resolver YA NO hace:
  - Leer archivos JSON directamente.
  - Procesar versions.json.
  - Resolver rutas físicas.
  - Llamar a RepositoryFactory.

El resolver se inicializa con repositorios inyectados. El singleton ``get_resolver()``
los construye internamente desde ``get_parametrization_store()``. El container construye
el resolver con los mismos repos que construye para los Query Services (instancia compartida).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from nexa_engine.modules.shared.exceptions import ParametrizationError, ParametrizationNotFoundError

logger = logging.getLogger(__name__)


class ParametrizationResolver:
    """Facade de lectura de parametrización. Delega a repositories; no accede al filesystem."""

    def __init__(
        self,
        hr_repo=None,
        gn_repo=None,
        op_repo=None,
    ) -> None:
        from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
            HRActiveParametrizationRepository,
        )
        from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
            GNActiveParametrizationRepository,
        )
        from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
            OPActiveParametrizationRepository,
        )

        if hr_repo is None or gn_repo is None or op_repo is None:
            from nexa_engine.db.factory import get_parametrization_store
            ps = get_parametrization_store()
            hr_repo = hr_repo or HRActiveParametrizationRepository(ps)
            gn_repo = gn_repo or GNActiveParametrizationRepository(ps)
            op_repo = op_repo or OPActiveParametrizationRepository(ps)

        self._hr_repo = hr_repo
        self._gn_repo = gn_repo
        self._op_repo = op_repo
        self._cache: Dict[str, Dict[str, Any]] = {}

    # -----------------------------------------------------------------------
    # Public API (preserved for ParametrizationProvider compatibility)
    # -----------------------------------------------------------------------

    def get_active_hr(self) -> Dict[str, Any]:
        """Return active HR parametrization, cached."""
        return self._get_cached("hr", self._hr_repo)

    def get_active_gn(self) -> Dict[str, Any]:
        """Return active GN parametrization, cached."""
        return self._get_cached("gn", self._gn_repo)

    def get_active_op(self) -> Dict[str, Any]:
        """Return active OP parametrization, cached."""
        return self._get_cached("op", self._op_repo)

    def get_module(self, module: str) -> Dict[str, Any]:
        """Return active parametrization for 'hr', 'gn' or 'op'."""
        if module == "hr":
            return self.get_active_hr()
        if module == "gn":
            return self.get_active_gn()
        if module == "op":
            return self.get_active_op()
        raise ValueError(f"Invalid module: {module!r}. Must be one of ('hr', 'gn', 'op')")

    def invalidate_cache(self, module: Optional[str] = None) -> None:
        """Invalidate in-memory cache for *module*, or all modules if None."""
        if module is None:
            self._cache.clear()
            logger.info("[PARAMETRIZATION] Cache invalidated (all modules)")
        else:
            self._cache.pop(module, None)
            logger.info("[PARAMETRIZATION] Cache invalidated (%s)", module)

    # -----------------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------------

    def _get_cached(self, module: str, repo) -> Dict[str, Any]:
        if module not in self._cache:
            try:
                data = repo.get_active_data()
            except ParametrizationNotFoundError:
                raise
            except Exception as exc:
                raise ParametrizationError(
                    f"Failed to load parametrization for {module}: {exc}",
                    module=module,
                ) from exc
            self._validate(module, data)
            self._cache[module] = data
            logger.debug("[PARAMETRIZATION] Loaded and cached %s", module)
        return self._cache[module]

    def _validate(self, module: str, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ParametrizationError(
                f"Parametrization data must be a dict, got {type(data).__name__}",
                module=module,
            )
        if "version_id" not in data:
            raise ParametrizationError(
                "Parametrization missing required field: version_id",
                module=module,
            )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_resolver_instance: Optional[ParametrizationResolver] = None


def get_resolver() -> ParametrizationResolver:
    """Return the process-wide ParametrizationResolver, building it on first use."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = ParametrizationResolver()
    return _resolver_instance


def reset_resolver() -> None:
    """Drop the cached singleton. Call in tests that change parametrization state."""
    global _resolver_instance
    _resolver_instance = None
