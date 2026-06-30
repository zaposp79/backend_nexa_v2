"""
nexa_engine/repositories/frozen_parametrization_adapter.py
============================================================
H-04 — Adapter que inyecta la parametrización frozen (versionada) en el motor.

Implementa IParametrizationProvider delegando al ParametrizationProvider base
para los métodos no afectados por la versión frozen, y overrideando los métodos
clave (SMMLV, GMF, ICA, indexación) con valores frozen.

Uso en engine.py:
    engine = NexaPricingEngine(parametrization_version="v2-6")

Uso directo:
    provider = FrozenParametrizationAdapter.from_version("v2-6")
    engine   = NexaPricingEngine(parametrizacion=provider)

Métodos overrideados (usan frozen):
    - get_nomina_laboral_params()  → SMMLV + auxilio_transporte frozen
    - get_gmf()                    → GMF frozen
    - get_ica()                    → ICA por ciudad frozen
    - get_factor_indexacion()      → factores frozen por componente/año

Todos los demás métodos delegan al ParametrizationProvider base.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from nexa_engine.modules.parametrizacion.shared.models.frozen_parametrization import FrozenParametrizationV26
from nexa_engine.modules.parametrizacion.repositories.frozen_parametrization_repository import FrozenParametrizationRepository
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider

logger = logging.getLogger("nexa.frozen_adapter")

# Mapa componente → atributo en FrozenParametrizationV26
_COMPONENTE_TO_ATTR: Dict[str, str] = {
    # Nombres canónicos del código
    "IPC":           "factor_ipc",
    "SMLV":          "factor_smmlv",
    "SMMLV":         "factor_smmlv",
    "70SMMLV_30IPC": "factor_mix_70_30",
    "80SMMLV_20IPC": "factor_mix_80_20",
    "20SMMLV_80IPC": "factor_mix_20_80",
    "IPC_mas_1pt":   "factor_ipc_plus_1",
    "Fijo":          "factor_fixed",
    # Nombres literales del Excel OP
    "70% SMMLV - 30% IPC": "factor_mix_70_30",
    "80% SMMLV - 20% IPC": "factor_mix_80_20",
    "20% SMMLV - 80% IPC": "factor_mix_20_80",
    "IPC + 1 PUNTO":        "factor_ipc_plus_1",
    "IPC, previa negociación con AVAL": "factor_ipc",
}


class FrozenParametrizationAdapter(IParametrizationProvider):
    """
    IParametrizationProvider que combina:
      - Valores frozen (SMMLV, GMF, ICA, indexación) del snapshot V2-x
      - Todos los demás valores del ParametrizationProvider activo (storage)

    Patrón: composición con un _base provider.
    """

    def __init__(self, frozen: FrozenParametrizationV26, base: Optional[ParametrizationProvider] = None) -> None:
        self._frozen = frozen
        self._base   = base or ParametrizationProvider.build()
        logger.info(
            "[frozen_adapter] Inicializado version=%s SMMLV=%.0f auxilio=%.0f gmf=%.4f",
            frozen.version, frozen.smmlv, frozen.auxilio_transporte, frozen.gmf,
        )

    @classmethod
    def from_version(cls, version: str) -> "FrozenParametrizationAdapter":
        """
        Carga la versión frozen desde storage y retorna el adapter.

        Raises:
            FileNotFoundError: si el JSON de esa versión no existe.
        """
        frozen = FrozenParametrizationRepository.load(version)
        if frozen is None:
            raise FileNotFoundError(
                f"Frozen parametrization '{version}' not found in "
                f"storage/parametrization/frozen/{version}.json"
            )
        return cls(frozen)

    # ──────────────────────────────────────────────────────────────────────────
    # Override: Nómina Laboral
    # ──────────────────────────────────────────────────────────────────────────

    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        """
        Parámetros de nómina con SMMLV y auxilio_transporte frozen.
        Aportes y prestaciones vienen del provider base.
        """
        base = self._base.get_nomina_laboral_params()
        base["salario_minimo"]     = self._frozen.smmlv
        base["auxilio_transporte"] = self._frozen.auxilio_transporte
        if self._frozen.dotacion_mensual:
            base["dotaciones_mensual"] = self._frozen.dotacion_mensual
        logger.debug(
            "[frozen_adapter] get_nomina_laboral_params SMMLV=%.0f auxilio=%.0f (frozen %s)",
            self._frozen.smmlv, self._frozen.auxilio_transporte, self._frozen.version,
        )
        return base

    # ──────────────────────────────────────────────────────────────────────────
    # Override: GMF
    # ──────────────────────────────────────────────────────────────────────────

    def get_gmf(self) -> float:
        value = self._frozen.gmf
        logger.debug("[frozen_adapter] get_gmf=%.4f (frozen %s)", value, self._frozen.version)
        return value

    # ──────────────────────────────────────────────────────────────────────────
    # Override: ICA por ciudad
    # ──────────────────────────────────────────────────────────────────────────

    def get_ica(self, ciudad: str) -> float:
        ciudad_norm = ciudad.strip().title() if ciudad else ""
        frozen_ica = self._frozen.ica_por_ciudad or {}
        if ciudad_norm in frozen_ica:
            value = frozen_ica[ciudad_norm]
            logger.debug("[frozen_adapter] get_ica %s=%.5f (frozen)", ciudad_norm, value)
            return value
        logger.debug("[frozen_adapter] get_ica %s → base (no en frozen)", ciudad_norm)
        return self._base.get_ica(ciudad)

    # ──────────────────────────────────────────────────────────────────────────
    # Override: Factor de indexación
    # ──────────────────────────────────────────────────────────────────────────

    def get_factor_indexacion(self, componente: str, anio: int) -> float:
        attr = _COMPONENTE_TO_ATTR.get(componente)
        if attr:
            factors: List[float] = getattr(self._frozen, attr, [])
            if factors:
                idx = max(0, min(anio - 1, len(factors) - 1))
                value = factors[idx]
                logger.debug(
                    "[frozen_adapter] get_factor_indexacion %s año%d=%.6f (frozen)",
                    componente, anio, value,
                )
                return value
        logger.debug("[frozen_adapter] get_factor_indexacion %s → base", componente)
        return self._base.get_factor_indexacion(componente, anio)

    # ──────────────────────────────────────────────────────────────────────────
    # Delegación al base provider (todos los demás métodos)
    # ──────────────────────────────────────────────────────────────────────────

    def tasa_mensual_financiacion(self) -> float:
        return self._base.tasa_mensual_financiacion()

    def get_rampup(self, linea_negocio: str, mes: int) -> float:
        return self._base.get_rampup(linea_negocio, mes)

    def get_tasa_polizas_efectiva(self, mes: int) -> float:
        return self._base.get_tasa_polizas_efectiva(mes)

    def get_factor_periodo(self, dias: int) -> int:
        return self._base.get_factor_periodo(dias)

    def get_margen_minimo(self, linea_negocio: str) -> float:
        return self._base.get_margen_minimo(linea_negocio)

    def get_salario_rol(self, rol: str) -> float:
        return self._base.get_salario_rol(rol)

    def get_costo_no_payroll(self, sede: str) -> Dict[str, Any]:
        return self._base.get_costo_no_payroll(sede)

    def get_examen_medico(self, ciudad: str) -> float:
        return self._base.get_examen_medico(ciudad)

    def get_pct_rotacion(self, linea: str) -> float:
        return self._base.get_pct_rotacion(linea)

    def get_pct_ausentismo(self, linea: str) -> float:
        return self._base.get_pct_ausentismo(linea)

    def get_pct_examen_anual(self, linea: str) -> float:
        return self._base.get_pct_examen_anual(linea)

    def get_costo_operativo(self, clave: str) -> float:
        return self._base.get_costo_operativo(clave)

    def get_reglas_staff(self) -> Dict[str, Any]:
        return self._base.get_reglas_staff()

    def get_ratios_staff(self, linea: str) -> Dict[str, float]:
        return self._base.get_ratios_staff(linea)

    def get_politicas_comerciales(self) -> list:
        return self._base.get_politicas_comerciales()

    def get_riesgo_config(self) -> Dict[str, Any]:
        return self._base.get_riesgo_config()

    def get_portfolio_clientes(self):
        return self._base.get_portfolio_clientes()

    def get_smmlv(self) -> float:
        """SMMLV del snapshot frozen. Fuente: FrozenParametrizationV26.smmlv."""
        return float(self._frozen.smmlv)

    # ──────────────────────────────────────────────────────────────────────────
    # Acceso a la frozen para auditoría
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def frozen(self) -> FrozenParametrizationV26:
        """Retorna la parametrización frozen (para auditoría/snapshot)."""
        return self._frozen

    def get_frozen_version(self) -> str:
        """Retorna la versión frozen activa."""
        return self._frozen.version
