from __future__ import annotations
"""Panel and escenarios builder methods.

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




class UserInputBuildersPanelMixin:
    """Mixin: Panel and escenarios builder methods."""

    def _panel(self, d: Dict) -> PanelDeControlInput:
        return PanelDeControlInput(
            cliente                        = str(d["cliente"]),
            tipo_cliente                   = str(d.get("tipo_cliente", "")),
            linea_negocio                  = str(d["linea_negocio"]),
            # FASE 1 — H3/H6: En formato legacy, ciudad y fecha_inicio tienen defaults
            # documentados para backward compat. FASE 2 (InputNormalizer) los hará requeridos.
            ciudad                         = str(d.get("ciudad", "Bogota")),
            sede                           = str(d.get("sede", "")),
            fecha_inicio                   = str(d.get("fecha_inicio", "2026-01-01")),
            meses_contrato                 = int(d["meses_contrato"]),
            margen                         = float(d["margen"]),
            op_cont                        = float(d["op_cont"]),
            com_cont                       = float(d.get("com_cont", 0.0)),
            markup                         = float(d.get("markup", 0.0)),
            descuento                      = float(d.get("descuento", 0.0)),
            periodo_pago_dias              = int(d.get("periodo_pago_dias", 90)),
            activa_financiacion            = bool(d.get("activa_financiacion", True)),
            antiguedad_cliente             = str(d.get("antiguedad_cliente", "")),
            componente_indexacion_humano   = str(d.get("componente_indexacion_humano", "IPC")),
            componente_indexacion_tecnologico = str(d.get("componente_indexacion_tecnologico", "IPC")),
            tasa_ica            = float(d["tasa_ica"]) if "tasa_ica" in d else None,
            tasa_gmf            = float(d["tasa_gmf"]) if "tasa_gmf" in d else None,
            tasa_mensual_financ = float(d["tasa_mensual_financ"]) if "tasa_mensual_financ" in d else None,
            pct_rotacion        = float(d["pct_rotacion"]) if "pct_rotacion" in d else None,
            pct_ausentismo      = float(d["pct_ausentismo"]) if "pct_ausentismo" in d else None,
            aplica_ley_1819     = bool(d.get("aplica_ley_1819", True)),
            horas_formacion_mensual    = int(d.get("horas_formacion_mensual", 0) or 0),
            tarifa_diaria_capacitacion = float(d.get("tarifa_diaria_capacitacion", 0.0) or 0.0),
            indexacion_frecuencia      = str(d.get("indexacion_frecuencia", "Anual")),
            indexacion_mes_aplicacion  = int(d["indexacion_mes_aplicacion"]) if d.get("indexacion_mes_aplicacion") is not None else None,
            imprevistos                = float(d.get("imprevistos", 0.0) or 0.0),
            complejidad_especialista   = str(d.get("complejidad_especialista", "ALTA") or "ALTA"),
            tarifa_crucero             = float(d.get("tarifa_crucero", 0.0) or 0.0),
            pct_examen_anual           = float(d["pct_examen_anual"]) if d.get("pct_examen_anual") is not None else None,
            # ── WAVE 2 (Excel V2-7) — overrides opcionales ─────────────
            margen_b              = float(d["margen_b"]) if d.get("margen_b") is not None else None,
            margen_c              = float(d["margen_c"]) if d.get("margen_c") is not None else None,
            mes_ajuste_indexacion = int(d["mes_ajuste_indexacion"]) if d.get("mes_ajuste_indexacion") is not None else None,
            tasa_interes_mensual  = float(d["tasa_interes_mensual"]) if d.get("tasa_interes_mensual") is not None else None,
            escenarios                  = self._escenarios(d.get("escenarios_comerciales", [])),
            cadenas_activas             = CadenasActivasInput(**d.get("cadenas_activas", {})),
        )


    def _escenarios(self, raw: list) -> list:
        result = []
        for e in raw or []:
            result.append(EscenarioComercialInput(
                escenario                 = int(e.get("escenario", len(result) + 1)),
                modalidad                 = str(e.get("modalidad", "")),
                canal                     = str(e.get("canal", "")),
                modelo_cobro              = str(e.get("modelo_cobro", "")),
                componente_fijo_tipo      = e.get("componente_fijo"),
                componente_fijo_pct       = float(e.get("proporcion_componente_fijo", 1.0) or 0.0),
                componente_variable_tipo  = e.get("componente_variable") or None,
                componente_variable_pct   = float(e.get("proporcion_componente_variable", 0.0) or 0.0),
            ))
        return result

    # ------------------------------------------------------------------
    # Cadena A
    # ------------------------------------------------------------------



__all__ = ["UserInputBuildersPanelMixin"]
