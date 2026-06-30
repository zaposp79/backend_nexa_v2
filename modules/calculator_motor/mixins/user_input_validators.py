"""Validation and helper methods.

Mixin for UserInputLoader — FASE Z.2.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

_CAMPOS_MAESTROS_PROHIBIDOS = {
    "horas_formacion_mensual",
    "parametros_nomina", "parametros_no_payroll", "parametros_calculo",
}

_CAMPOS_ENTRY_DATA_VALIDOS = {
    "panel_de_control", "condiciones_cadena_a", "condiciones_cadena_b",
    "condiciones_cadena_c", "parametros_nomina", "reglas_negocio",
    "contingencia_operativa", "escenarios_comerciales", "polizas",
}

_CAMPOS_ENTRY_DATA_NUEVO_VALIDOS = {
    "datos_operativos", "polizas", "reglas_negocio", "volumetria",
    "escenarios_comerciales", "condiciones_cadena_a", "condiciones_cadena_b",
    "condiciones_cadena_c",
}


class UserInputValidatorsMixin:
    """Mixin: Validation and helper methods."""

    # ------------------------------------------------------------------

    @staticmethod
    def _requerir(d: Dict, key: str, section: str) -> str:
        """Extrae un campo string requerido. Raise si falta o está vacío."""
        val = d.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise ValueError(
                f"Campo requerido '{key}' falta o está vacío en '{section}'. "
                f"No se permiten fallbacks silenciosos para este campo."
            )
        return str(val)

    @staticmethod
    def _requerir_int(d: Dict, key: str, section: str) -> int:
        """Extrae un campo int requerido. Raise si falta."""
        val = d.get(key)
        if val is None:
            raise ValueError(
                f"Campo requerido '{key}' falta en '{section}'. "
                f"No se permiten fallbacks silenciosos para este campo."
            )
        return int(val)

    @staticmethod
    def _requerir_float(d: Dict, key: str, section: str) -> float:
        """Extrae un campo float requerido. Raise si falta."""
        val = d.get(key)
        if val is None:
            raise ValueError(
                f"Campo requerido '{key}' falta en '{section}'. "
                f"No se permiten fallbacks silenciosos para este campo."
            )
        return float(val)

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def _validar_no_contiene_maestros(self, data: Dict) -> None:
        """Phase 5.5: Validate entry_data contract — no pollution, no legacy fields."""
        # Check for POLLUTION fields (metadata with _ prefix)
        pollution_fields = [k for k in data.keys() if k.startswith("_")]
        if pollution_fields:
            raise ValueError(
                f"❌ PHASE 5.5 CONTRACT VIOLATION: entry_data contiene campos de POLLUTION "
                f"(metadata/debugging) que NO pertenecen al contrato oficial:\n"
                f"  Campos rechazados: {sorted(pollution_fields)}\n"
                f"  Regla: Ningún campo puede comenzar con '_'\n"
                f"  Solución: Usar estructura test_cases/input/ (limpia, sin metadata)"
            )

        # Seleccionar el set de campos válidos según el formato detectado
        campos_validos = (
            _CAMPOS_ENTRY_DATA_NUEVO_VALIDOS
            if "datos_operativos" in data
            else _CAMPOS_ENTRY_DATA_VALIDOS
        )

        # Check for non-contracted entry_data fields
        unknown_fields = set(data.keys()) - campos_validos
        if unknown_fields:
            raise ValueError(
                f"❌ PHASE 5.5 CONTRACT VIOLATION: entry_data contiene campos no contractuales:\n"
                f"  Campos desconocidos: {sorted(unknown_fields)}\n"
                f"  Campos válidos: {sorted(campos_validos)}\n"
                f"  Solución: Remover campos no reconocidos o actualizar schema"
            )

        # Check for legacy maestros fields
        encontrados = set(data.keys()) & _CAMPOS_MAESTROS_PROHIBIDOS
        if encontrados:
            raise ValueError(
                f"❌ El JSON de usuario contiene campos de datos maestros que no debe "
                f"parametrizar el usuario: {sorted(encontrados)}. "
                f"Estos valores se cargan automáticamente desde storage/parametrization/."
            )



__all__ = ["UserInputValidatorsMixin"]
