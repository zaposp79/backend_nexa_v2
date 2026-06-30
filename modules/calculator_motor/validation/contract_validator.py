"""Validación contractual fail-fast para entry_data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContractValidationResult:
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class ContractValidator:
    """Valida estructura y coherencia mínima del contrato JSON oficial."""

    def validate(self, payload: Dict[str, Any]) -> ContractValidationResult:
        result = ContractValidationResult()
        if "datos_operativos" not in payload:
            result.errors.append("datos_operativos is required")
        if "reglas_negocio" not in payload:
            result.errors.append("reglas_negocio is required")
        if "volumetria" not in payload:
            result.errors.append("volumetria is required")
        if result.errors:
            return result

        self._validate_datos_operativos(payload["datos_operativos"], result)
        self._validate_reglas(payload["reglas_negocio"], result)
        self._validate_volumetria(payload["volumetria"], result)
        self._validate_polizas(payload.get("polizas"), result)
        self._validate_escenarios(payload.get("escenarios_comerciales", []), payload, result)
        return result

    def raise_if_invalid(self, payload: Dict[str, Any]) -> None:
        result = self.validate(payload)
        if not result.is_valid:
            raise ValueError("CONTRACT_VALIDATION_ERROR: " + "; ".join(result.errors))

    @staticmethod
    def _validate_datos_operativos(ops: Dict[str, Any], result: ContractValidationResult) -> None:
        for field in ("cliente", "servicio", "ciudad", "fecha_inicio", "duracion_meses"):
            if ops.get(field) in (None, ""):
                result.errors.append(f"datos_operativos.{field} is required")
        if ops.get("duracion_meses") is not None and int(ops.get("duracion_meses")) <= 0:
            result.errors.append("datos_operativos.duracion_meses must be > 0")

    @staticmethod
    def _validate_reglas(reg: Dict[str, Any], result: ContractValidationResult) -> None:
        if reg.get("margen_objetivo") is None:
            result.errors.append("reglas_negocio.margen_objetivo is required")
        for name in ("contingencia_operativa", "contingencia_comercial", "markup"):
            block = reg.get(name)
            if not isinstance(block, dict) or block.get("valor") is None:
                result.errors.append(f"reglas_negocio.{name}.valor is required")

    @staticmethod
    def _validate_volumetria(vol: Dict[str, Any], result: ContractValidationResult) -> None:
        idx = vol.get("indexacion")
        if not isinstance(idx, dict):
            result.errors.append("volumetria.indexacion is required")
        else:
            for field in ("componente_humano", "componente_tecnologico", "frecuencia", "mes_aplicacion", "tasa_interes_mensual"):
                if idx.get(field) is None:
                    result.errors.append(f"volumetria.indexacion.{field} is required")

        active_any = False
        for modalidad in ("inbound", "outbound"):
            block = vol.get(modalidad, {}) or {}
            activas = block.get("cadenas_activas", {}) or {}
            active_any = active_any or any(bool(activas.get(c)) for c in ("cadena_a", "cadena_b", "cadena_c"))
        if not active_any:
            result.errors.append("volumetria must activate at least one cadena")

    @staticmethod
    def _validate_polizas(polizas: Any, result: ContractValidationResult) -> None:
        if polizas is None:
            return
        if not isinstance(polizas, list):
            result.errors.append("polizas must be null or an array")
            return
        for i, pol in enumerate(polizas):
            if pol.get("pct_poliza") is None or pol.get("pct_atribuible") is None:
                result.errors.append(f"polizas[{i}] pct_poliza and pct_atribuible are required")

    @staticmethod
    def _validate_escenarios(escenarios: List[Dict[str, Any]], payload: Dict[str, Any], result: ContractValidationResult) -> None:
        # Build valid keys from explicit condiciones_cadena_a.perfiles (if provided)
        perfiles = payload.get("condiciones_cadena_a", {}).get("perfiles", []) or []
        perfil_keys = {
            (str(p.get("modalidad", "")).lower(), str(p.get("canal", "")).lower())
            for p in perfiles
        }
        # Also accept volumetria-derived canales as valid escenario targets.
        # The engine resolves outbound cadena_a from volumetria.outbound.canales even
        # when condiciones_cadena_a is provided explicitly (profiles without volumetria
        # still match if cadena_a is active for that canal).
        vol = payload.get("volumetria", {})
        for modalidad in ("inbound", "outbound"):
            block = vol.get(modalidad, {}) or {}
            activas = block.get("cadenas_activas", {}) or {}
            if activas.get("cadena_a"):
                for canal_entry in block.get("canales", []) or []:
                    canal = str(canal_entry.get("canal", "")).lower()
                    if canal:
                        perfil_keys.add((modalidad, canal))
        for i, escenario in enumerate(escenarios or []):
            for field in ("escenario", "modalidad", "canal", "modelo_cobro"):
                if escenario.get(field) in (None, ""):
                    result.errors.append(f"escenarios_comerciales[{i}].{field} is required")
            key = (str(escenario.get("modalidad", "")).lower(), str(escenario.get("canal", "")).lower())
            if perfil_keys and key not in perfil_keys:
                result.errors.append(
                    f"escenarios_comerciales[{i}] references orphan canal/modalidad: {key}"
                )
