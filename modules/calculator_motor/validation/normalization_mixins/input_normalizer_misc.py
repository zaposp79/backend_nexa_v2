"""Misc normalization and helper methods for InputNormalizer.

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


class InputNormalizerMiscMixin:
    """Mixin: Misc normalization and helper methods for InputNormalizer."""

    def _normalizar_escenarios(
        self,
        escenarios: List[Dict],
        log: NormalizationLog,
    ) -> List[Dict]:
        """
        Normaliza escenarios_comerciales asegurando campos opcionales con defaults.

        El JSON oficial puede omitir componente_variable si el modelo es 100% fijo.
        """
        normalizados = []
        for i, esc in enumerate(escenarios):
            esc_norm = dict(esc)
            prefix = f"escenarios_comerciales[{i}]"

            # componente_variable puede estar vacío en modelo FTE puro
            if not esc_norm.get("componente_variable"):
                esc_norm["componente_variable"] = ""
            if esc_norm.get("proporcion_componente_variable") is None:
                esc_norm["proporcion_componente_variable"] = 0.0
                log.add_default(
                    f"{prefix}.proporcion_componente_variable",
                    0.0,
                    "Proporción variable = 0 cuando el modelo es FTE puro",
                )

            normalizados.append(esc_norm)
        return normalizados

    # ──────────────────────────────────────────────────────────────────────
    # Gestión de errores según modo
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod

    def _registrar_error(
        message: str,
        field_path: str,
        original_value: Any,
        mode: NormalizationMode,
        log: NormalizationLog,
    ) -> None:
        """
        Maneja un error según el modo de normalización:
        - STRICT:     raise inmediatamente
        - VALIDATION: acumular en log (se lanza consolidado al final)
        - AUDIT:      loguear como advertencia y continuar
        """
        if mode in (NormalizationMode.STRICT, NormalizationMode.CONTRACT_STRICT):
            raise ValueError(
                f"[InputNormalizer STRICT] Campo '{field_path}': {message}"
            )
        elif mode == NormalizationMode.VALIDATION:
            log.add_error(field_path, message, original_value)
        else:  # AUDIT
            log.add_warning(
                field_path,
                f"[AUDIT — campo faltante/inválido] {message}",
                original_value,
            )


__all__ = ["InputNormalizerMiscMixin"]
