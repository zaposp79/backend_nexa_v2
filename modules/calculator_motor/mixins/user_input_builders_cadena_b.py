from __future__ import annotations
"""Cadena B builder methods.

Mixin for UserInputLoader — FASE Z.2.
"""
"""
nexa_engine/adapters/user_input_loader.py
==========================================
Carga un UserInput desde un archivo JSON.
Solo lee los campos que el usuario puede configurar (Panel, Cadena A/B/C).
Rechaza cualquier campo que pertenezca a datos maestros.
"""


import json
from pathlib import Path
from typing import Any, Dict, List

from nexa_engine.modules.calculator_motor.adapters.entry_data_adapter import NewEntryDataAdapter
from nexa_engine.modules.calculator_motor.validation.input_normalizer import InputNormalizer
from nexa_engine.modules.calculator_motor.adapters.volume_resolution import VolumeResolutionService
from nexa_engine.modules.calculator_motor.dto.normalized_input import NormalizationMode
from nexa_engine.modules.calculator_motor.dto.user_inputs import (
    CanalCadenaBInput,
    CanalCadenaCInput,
    CadenasActivasInput,
    CondicionesCadenaAInput,
    CondicionesCadenaBInput,
    CondicionesCadenaCInput,
    DispositivoSMInput,
    EquipoHITLItemInput,
    EscenarioComercialInput,
    ItemOpexConsumoInput,
    MiembroEquipoSMInput,
    MiembroEquipoTransversalInput,
    PanelDeControlInput,
    PerfilCadenaAInput,
    PolizaInput,
    UserInput,
)

# Campos que NO deben aparecer en el JSON del usuario — son datos maestros puros.
# Nota: tasa_ica, tasa_gmf, tasa_mensual_financ, pct_rotacion, pct_ausentismo
# SÍ pueden aparecer en panel_de_control como overrides opcionales del usuario.
_CAMPOS_MAESTROS_PROHIBIDOS = {
    "horas_formacion_mensual",
    "parametros_nomina", "parametros_no_payroll", "parametros_calculo",
}

# Campos legítimos del contrato entry_data (Phase 5.5: Contract Enforcement)
# Formato legacy (test_cases)
_CAMPOS_ENTRY_DATA_VALIDOS = {
    "panel_de_control",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
    "parametros_nomina",
    "reglas_negocio",
    "contingencia_operativa",
    "escenarios_comerciales",
    # FASE D / Gap C3: polizas preservadas por el normalizer
    "polizas",
}

# Campos válidos del formato entry_data (datos_operativos, polizas, etc.)
_CAMPOS_ENTRY_DATA_NUEVO_VALIDOS = {
    "datos_operativos",
    "polizas",
    "reglas_negocio",
    "volumetria",
    "escenarios_comerciales",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
}


def _aplicar_escenarios_a_perfiles(
    condiciones_a: dict,
    escenarios: list,
) -> dict:
    """
    FASE C — Gap C4: Enriquecer perfiles de cadena_a con modelo_cobro y pct_fijo
    según los escenarios_comerciales.

    Matching por (modalidad, canal) — case-insensitive.
    Si un perfil no tiene escenario correspondiente, conserva sus defaults.

    Mapeo:
      escenario.modelo_cobro              → perfil.modelo_cobro
      escenario.proporcion_componente_fijo → perfil.pct_fijo
    """
    # Indexar escenarios por (modalidad_lower, canal_lower)
    idx: dict = {}
    for esc in escenarios:
        mod  = str(esc.get("modalidad", "")).lower().strip()
        canal = str(esc.get("canal", "")).lower().strip()
        idx[(mod, canal)] = esc

    perfiles_enriquecidos = []
    for perfil in condiciones_a.get("perfiles", []):
        clave = (
            str(perfil.get("modalidad", "")).lower().strip(),
            str(perfil.get("canal", "")).lower().strip(),
        )
        esc = idx.get(clave)
        if esc is not None:
            modelo_cobro = str(esc.get("modelo_cobro", perfil.get("modelo_cobro", "Fijo FTE")))
            pct_fijo     = float(esc.get("proporcion_componente_fijo",
                                         perfil.get("pct_fijo", 1.0)))
            perfil = {**perfil, "modelo_cobro": modelo_cobro, "pct_fijo": pct_fijo}
        perfiles_enriquecidos.append(perfil)

    return {**condiciones_a, "perfiles": perfiles_enriquecidos}




class UserInputBuildersCadenaBMixin:
    """Mixin: Cadena B builder methods."""

    def _cadena_b(self, d: Dict) -> CondicionesCadenaBInput:
        return CondicionesCadenaBInput(
            canales               = [self._canal_b(c) for c in d.get("canales", [])],
            opex_consumo_variable = [self._opex_consumo(i) for i in d.get("opex_consumo_variable", [])],
            equipo_sm             = [self._miembro_sm(m) for m in d.get("equipo_sm", [])],
            dispositivos_sm       = [self._dispositivo(dev) for dev in d.get("dispositivos_sm", [])],
            inversion_plataforma  = float(d.get("inversion_plataforma", 0.0)),
            fte_equipo_sm         = float(d.get("fte_equipo_sm", 1.0)),
            amortizar_dispositivos_sm = bool(d.get("amortizar_dispositivos_sm", True)),
        )


    def _canal_b(self, d: Dict) -> CanalCadenaBInput:
        return CanalCadenaBInput(
            nombre             = str(d["nombre"]),
            modalidad          = str(d["modalidad"]),
            producto           = str(d.get("producto", "")),
            volumen_mensual    = float(d.get("volumen_mensual", 0.0)),
            activo             = bool(d.get("activo", True)),
            opex_fijo          = float(d.get("opex_fijo", 0.0)),
            tarifa_unitaria    = float(d.get("tarifa_unitaria", 0.0)),
            pct_escalamiento   = float(d.get("pct_escalamiento", 0.0)),
            costo_escalamiento = float(d.get("costo_escalamiento", 0.0)),
            vol_escalamiento   = float(d.get("vol_escalamiento", 0.0)),
        )


    def _opex_consumo(self, d: Dict) -> ItemOpexConsumoInput:
        return ItemOpexConsumoInput(
            nombre         = str(d["nombre"]),
            producto       = str(d["producto"]),
            modalidad      = str(d["modalidad"]),
            canal          = str(d["canal"]),
            valor_unitario = float(d["valor_unitario"]),
            cantidad       = float(d["cantidad"]),
            tipo_cobro     = str(d.get("tipo_cobro", "Unitario")),
        )


    def _miembro_sm(self, d: Dict) -> MiembroEquipoSMInput:
        return MiembroEquipoSMInput(
            rol            = str(d["rol"]),
            activo         = bool(d["activo"]),
            pct_dedicacion = float(d["pct_dedicacion"]),
        )


    def _dispositivo(self, d: Dict) -> DispositivoSMInput:
        return DispositivoSMInput(
            tipo               = str(d["tipo"]),
            costo_unitario     = float(d["costo_unitario"]),
            cantidad           = float(d["cantidad"]),
            meses_amortizacion = int(d.get("meses_amortizacion", 1)),
        )

    # ------------------------------------------------------------------
    # Cadena C
    # ------------------------------------------------------------------



__all__ = ["UserInputBuildersCadenaBMixin"]
