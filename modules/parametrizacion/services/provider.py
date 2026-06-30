"""
nexa_engine/repositories/parametrization_provider.py
======================================================
ParametrizationProvider — Capa de Aplicación.

Implementa `IParametrizationProvider` usando los repositorios de dominio
que leen desde `storage/parametrization/{hr,gn,op}/`.

Responsabilidad
---------------
Ser la fuente única de verdad para todos los datos de parametrización
que los calculadores del motor necesitan, abstrayendo:

  - Dónde viven los datos (JSON, futuro PostgreSQL/DynamoDB/S3)
  - Qué versión está activa (ParametrizationResolver)
  - Transformaciones de formato (ej: % → decimal)
  - Trazabilidad: log estructurado por cada acceso a datos

Política de errores
-------------------
NO existen defaults silenciosos.  Si un dato falta en la parametrización
activa, se lanza `ParametrizationError` con mensaje descriptivo que indica
qué hoja/clave debe corregirse.  Esto garantiza que los cambios en Excel
se detecten de inmediato en lugar de enmascararse con constantes hardcode.

Arquitectura
------------
    storage/parametrization/      (Infrastructure Layer)
         ↓ ParametrizationResolver
         ↓ ParametrizationLoader
    Domain Repositories            (Application Layer)
         ↓ FinancialParametrizationRepository
         ↓ ProfitabilityParametrizationRepository
         ↓ PayrollParametrizationRepository
         ↓ InfrastructureParametrizationRepository
    ParametrizationProvider        (Application Facade)
         ↓ IParametrizationProvider
    Calculators                    (Domain Layer — puros, sin I/O)

Uso
---
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider

    # Construcción estándar (auto-detecta versión activa)
    provider = ParametrizationProvider.build()

    # Inyección en el motor
    engine = NexaPricingEngine(parametrizacion=provider)

    # Acceso directo
    rampup = provider.get_rampup("Cobranzas", mes=3)   # → 1.0
    tasa   = provider.tasa_mensual_financiacion          # → 0.0088
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.services.resolver import (
    ParametrizationResolver,
    get_resolver,
)
from nexa_engine.modules.parametrizacion.repositories.financial_parametrization_repository import (
    FinancialParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
    InfrastructureParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.repositories.payroll_parametrization_repository import (
    PayrollParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.repositories.profitability_parametrization_repository import (
    ProfitabilityParametrizationRepository,
)
from nexa_engine.modules.shared.exceptions import ParametrizationError
from nexa_engine.modules.parametrizacion.shared.helpers.canonicalization import (
    canonical_channel,
    canonical_complejidad,
    canonical_modalidad,
    canonical_role,
    canonical_service,
)

logger = logging.getLogger(__name__)

from nexa_engine.modules.parametrizacion.mixins.provider_fin_op import ProviderFinOpMixin
from nexa_engine.modules.parametrizacion.mixins.provider_hr import ProviderHrMixin
from nexa_engine.modules.parametrizacion.mixins.provider_business_rules import ProviderBusinessRulesMixin
from nexa_engine.modules.parametrizacion.mixins.provider_snapshot import ProviderSnapshotMixin

# ── Singleton cache ──────────────────────────────────────────────────────────
_PROVIDER_INSTANCE: Optional[ParametrizationProvider] = None



def get_provider() -> "ParametrizationProvider":
    """Return a singleton ParametrizationProvider.

    Uses the singleton ParametrizationResolver internally (see get_resolver()).
    Suitable for production use where a single provider instance serves all requests.
    """
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is None:
        _PROVIDER_INSTANCE = ParametrizationProvider.build(get_resolver())
    return _PROVIDER_INSTANCE


# ── Main class ───────────────────────────────────────────────────────────────


class ParametrizationProvider(
    ProviderFinOpMixin,
    ProviderHrMixin,
    ProviderBusinessRulesMixin,
    ProviderSnapshotMixin,
):
    """
    Facade de parametrización para calculadores del motor NEXA.

    Domain methods organized in mixins (FASE Z.2 decomposition):
      ProviderFinOpMixin         — financial, OP, indexacion, costos
      ProviderHrMixin            — HR, nomina, rotacion, ausentismo
      ProviderBusinessRulesMixin — business rules, riesgo
      ProviderSnapshotMixin      — capture_parametrization_snapshot
    """

    def __init__(
        self,
        financial: FinancialParametrizationRepository,
        profitability: ProfitabilityParametrizationRepository,
        infrastructure: InfrastructureParametrizationRepository,
        payroll: PayrollParametrizationRepository,
    ) -> None:
        self._financial       = financial
        self._profitability   = profitability
        self._infrastructure  = infrastructure
        self._payroll         = payroll

    # ──────────────────────────────────────────────────────────────────────────
    # Factory
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        resolver: Optional[ParametrizationResolver] = None,
    ) -> "ParametrizationProvider":
        """Build a ParametrizationProvider with injected resolver.

        Args:
            resolver: ParametrizationResolver to use. If None, creates a new one.
        """
        if resolver is None:
            resolver = ParametrizationResolver()

        financial      = FinancialParametrizationRepository(resolver)
        profitability  = ProfitabilityParametrizationRepository(resolver)
        infrastructure = InfrastructureParametrizationRepository(resolver)
        payroll        = PayrollParametrizationRepository(resolver)

        instance = cls(financial, profitability, infrastructure, payroll)
        logger.info(
            "[PARAMETRIZATION] ParametrizationProvider initialized "
            "modules=[financial, profitability, infrastructure, payroll]"
        )
        return instance


