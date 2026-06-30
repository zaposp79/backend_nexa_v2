"""Default-application methods for InputNormalizer.

Mixin for InputNormalizer — FASE Z.2.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from nexa_engine.modules.calculator_motor.dto.normalized_input import (
    NormalizationLog, NormalizationWarning, NormalizationError,
    NormalizationMode, DefaultApplied, NormalizedInput,
)
logger = logging.getLogger(__name__)


class InputNormalizerDefaultsMixin:
    """Mixin: Default-application methods for InputNormalizer."""

    def _aplicar_defaults_volumetria(
        self, data: Dict, log: NormalizationLog
    ) -> None:
        """
        Aplica defaults explícitos a volumetria.indexacion si faltan campos.
        Todos los defaults están documentados en DEFAULT_REGISTRY.
        """
        if "volumetria" not in data:
            return
        vol = data["volumetria"]
        if "indexacion" not in vol:
            vol["indexacion"] = {}
        idx = vol["indexacion"]

        _defaults_indexacion = {
            "componente_humano":    ("IPC", "Componente humano: IPC estándar contractual BPO"),
            "componente_tecnologico": ("IPC", "Componente tecnológico: IPC por defecto"),
            "frecuencia":           ("Anual", "Frecuencia de indexación anual — estándar BPO Colombia"),
            "mes_aplicacion":       (1, "Mes de aplicación: mes 1 (enero) por defecto"),
        }
        for campo, (default_val, reason) in _defaults_indexacion.items():
            if idx.get(campo) is None:
                idx[campo] = default_val
                log.add_default(f"volumetria.indexacion.{campo}", default_val, reason)


    def _aplicar_defaults_reglas_negocio(
        self, data: Dict, log: NormalizationLog
    ) -> None:
        """
        Aplica defaults explícitos a reglas_negocio para secciones opcionales.
        """
        reg = data.get("reglas_negocio", {})

        # contingencia_operativa
        op_cont = reg.get("contingencia_operativa")
        if op_cont is None:
            reg["contingencia_operativa"] = {"valor": 0.025, "minimo": 0.025, "maximo": 0.12}
            log.add_default(
                "reglas_negocio.contingencia_operativa",
                0.025,
                "Default estándar contingencia operativa BPO; mínimo contractual típico",
            )
        elif isinstance(op_cont, dict) and op_cont.get("valor") is None:
            op_cont["valor"] = 0.025
            log.add_default(
                "reglas_negocio.contingencia_operativa.valor",
                0.025,
                "Default estándar contingencia operativa BPO",
            )

        # contingencia_comercial
        com_cont = reg.get("contingencia_comercial")
        if com_cont is None:
            reg["contingencia_comercial"] = {"valor": 0.0, "minimo": 0.0, "maximo": 0.07}
            log.add_default(
                "reglas_negocio.contingencia_comercial",
                0.0,
                "Sin contingencia comercial por defecto — legítimo si el deal no tiene riesgo adicional",
            )

        # markup
        markup = reg.get("markup")
        if markup is None:
            reg["markup"] = {"valor": 0.0, "minimo": 0.0, "maximo": 0.08}
            log.add_default(
                "reglas_negocio.markup",
                0.0,
                "Sin markup por defecto — solo si el cliente lo negocia",
            )

        # imprevistos
        if reg.get("imprevistos") is None:
            reg["imprevistos"] = 0.0
            log.add_default(
                "reglas_negocio.imprevistos",
                0.0,
                "Sin imprevistos por defecto (GAP-PYG-1)",
            )

        data["reglas_negocio"] = reg

    # ──────────────────────────────────────────────────────────────────────
    # Normalización de Cadena A — flatten capacitacion + preservar estructura
    # ──────────────────────────────────────────────────────────────────────



__all__ = ["InputNormalizerDefaultsMixin"]
