from __future__ import annotations
"""Cadena C builder methods.

Mixin for UserInputLoader — FASE Z.2.
"""
from typing import Any, Dict, List
from nexa_engine.modules.calculator_motor.dto.user_inputs import (
    CondicionesCadenaCInput, CanalCadenaCInput, EquipoHITLItemInput,
    MiembroEquipoTransversalInput,
)


class UserInputBuildersCadenaCMixin:
    """Mixin: Cadena C builder methods."""

    def _cadena_c(self, d: Dict) -> CondicionesCadenaCInput:
        return CondicionesCadenaCInput(
            canales            = [self._canal_c(c) for c in d.get("canales", [])],
            equipo_transversal = [
                MiembroEquipoTransversalInput(
                    rol             = str(m["rol"]),
                    activo          = bool(m["activo"]),
                    pct_dedicacion  = float(m["pct_dedicacion"]),
                    salario_cargado = float(m["salario_cargado"]) if m.get("salario_cargado") is not None else None,
                )
                for m in d.get("equipo_transversal", [])
            ],
            equipo_hitl = [self._equipo_hitl_item(m) for m in d.get("equipo_hitl", [])],
            opex_dispositivos_por_persona = float(d.get("opex_dispositivos_por_persona", 0.0)),
            inversion_anual = float(d.get("inversion_anual", 0.0)),
            opex_herramientas_transversal = float(d.get("opex_herramientas_transversal", 0.0)),
        )

    def _equipo_hitl_item(self, d: Dict) -> EquipoHITLItemInput:
        return EquipoHITLItemInput(
            rol             = str(d["rol"]),
            activado        = bool(d["activado"]),
            ratio           = float(d["ratio"]),
            salario_cargado = float(d["salario_cargado"]),
        )

    def _canal_c(self, d: Dict) -> CanalCadenaCInput:
        return CanalCadenaCInput(
            nombre             = str(d["nombre"]),
            modalidad          = str(d["modalidad"]),
            volumen_mensual    = float(d.get("volumen_mensual", 0.0)),
            activo             = bool(d.get("activo", True)),
            tarifa_unitaria    = float(d.get("tarifa_unitaria", 0.0)),
            opex_fijo_integ    = float(d.get("opex_fijo_integ", 0.0)),
            opex_var_integ     = float(d.get("opex_var_integ", 0.0)),
            pct_escalamiento   = float(d.get("pct_escalamiento", 0.0)),
            costo_escalamiento = float(d.get("costo_escalamiento", 0.0)),
        )

    # ------------------------------------------------------------------


__all__ = ["UserInputBuildersCadenaCMixin"]
