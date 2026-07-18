"""Validation methods for InputNormalizer.

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


class InputNormalizerValidationMixin:
    """Mixin: Validation methods for InputNormalizer."""

    def _validar_secciones_requeridas(
        self, data: Dict, mode: NormalizationMode, log: NormalizationLog
    ) -> None:
        """Verifica que las secciones de primer nivel requeridas existan."""
        requeridas = ["datos_operativos", "reglas_negocio", "condiciones_cadena_a"]
        for sec in requeridas:
            if sec not in data:
                msg = (
                    f"Sección requerida '{sec}' falta en el JSON de entrada. "
                    f"El contrato oficial requiere: {requeridas}"
                )
                self._registrar_error(msg, sec, None, mode, log)


    def _validar_datos_operativos(
        self, data: Dict, mode: NormalizationMode, log: NormalizationLog
    ) -> None:
        """
        Valida los campos requeridos en datos_operativos.

        Campos requeridos (FASE 1 — H2/H6/H8):
          ciudad, fecha_inicio, duracion_meses
        """
        ops = data.get("datos_operativos", {})

        # ciudad — FASE 1 H2: requerido, no fallback silencioso
        ciudad = ops.get("ciudad")
        if not ciudad or (isinstance(ciudad, str) and not ciudad.strip()):
            self._registrar_error(
                "Campo 'ciudad' es requerido en datos_operativos. "
                "Afecta tasa ICA y costos de infraestructura (FASE 1 — H2).",
                "datos_operativos.ciudad",
                ciudad,
                mode,
                log,
            )

        # fecha_inicio — FASE 1 H6: requerido, formato YYYY-MM-DD
        fecha = ops.get("fecha_inicio")
        if not fecha or (isinstance(fecha, str) and not fecha.strip()):
            self._registrar_error(
                "Campo 'fecha_inicio' es requerido en datos_operativos. "
                "Afecta indexación y toda la estructura temporal del contrato (FASE 1 — H6).",
                "datos_operativos.fecha_inicio",
                fecha,
                mode,
                log,
            )
        elif isinstance(fecha, str) and len(fecha) >= 4:
            try:
                year = int(fecha[:4])
                if year < 2000 or year > 2100:
                    self._registrar_error(
                        f"'fecha_inicio' tiene año fuera de rango: {year}. "
                        f"Se requiere año entre 2000 y 2100.",
                        "datos_operativos.fecha_inicio",
                        fecha,
                        mode,
                        log,
                    )
                    return  # no seguir validando si el año es inválido
            except ValueError:
                self._registrar_error(
                    f"'fecha_inicio' no tiene formato YYYY-MM-DD válido: '{fecha}'.",
                    "datos_operativos.fecha_inicio",
                    fecha,
                    mode,
                    log,
                )

        # duracion_meses — FASE 1 H8: requerido
        duracion = ops.get("duracion_meses")
        if duracion is None:
            self._registrar_error(
                "Campo 'duracion_meses' es requerido en datos_operativos. "
                "Afecta indexación, pólizas y estructura temporal (FASE 1 — H8).",
                "datos_operativos.duracion_meses",
                duracion,
                mode,
                log,
            )
        elif not isinstance(duracion, (int, float)) or int(duracion) <= 0:
            self._registrar_error(
                f"'duracion_meses' debe ser un entero positivo, se recibió: {duracion!r}.",
                "datos_operativos.duracion_meses",
                duracion,
                mode,
                log,
            )


    def _validar_reglas_negocio(
        self, data: Dict, mode: NormalizationMode, log: NormalizationLog
    ) -> None:
        """
        Valida campos requeridos en reglas_negocio.

        Campos requeridos (FASE 1 — H9):
          margen_objetivo_cadena_a
        """
        reg = data.get("reglas_negocio", {})
        margen = reg.get("margen_objetivo_cadena_a")
        if margen is None:
            self._registrar_error(
                "Campo 'margen_objetivo_cadena_a' es requerido en reglas_negocio. "
                "Afecta todos los cálculos de pricing (FASE 1 — H9).",
                "reglas_negocio.margen_objetivo_cadena_a",
                margen,
                mode,
                log,
            )
        elif not isinstance(margen, (int, float)) or float(margen) < 0:
            self._registrar_error(
                f"'margen_objetivo_cadena_a' debe ser un número >= 0, se recibió: {margen!r}.",
                "reglas_negocio.margen_objetivo_cadena_a",
                margen,
                mode,
                log,
            )

    # ──────────────────────────────────────────────────────────────────────
    # Aplicación de defaults explícitos
    # ──────────────────────────────────────────────────────────────────────



__all__ = ["InputNormalizerValidationMixin"]
