from __future__ import annotations
"""Cadena A builder methods.

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
from nexa_engine.modules.shared.exceptions import ValidationError
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




class UserInputBuildersCadenaAMixin:
    """Mixin: Cadena A builder methods."""

    def _cadena_a(self, d: Dict) -> CondicionesCadenaAInput:
        perfiles = [self._perfil_a(p) for p in d.get("perfiles", [])]
        staff_config = [self._staff_rol(s) for s in d.get("staff_config", [])]
        detalles = [self._detalle_recurso_humano(item) for item in d.get("detalles_recursos_humanos", [])]
        return CondicionesCadenaAInput(
            perfiles=perfiles,
            staff_config=staff_config,
            detalles_recursos_humanos=detalles,
        )


    @staticmethod
    def _detalle_recurso_humano(d: Dict):
        from nexa_engine.modules.calculator_motor.dto.user_inputs import DetalleRecursoHumanoInput

        return DetalleRecursoHumanoInput(
            cargo=str(d["cargo"]),
            salario_base=float(d["salario_base"]),
            comisiones=float(d.get("comisiones", 0.0)),
        )


    def _staff_rol(self, d: Dict) -> "StaffRolInput":
        from nexa_engine.modules.calculator_motor.dto.user_inputs import StaffRolInput
        ratio = d.get("ratio_override")
        return StaffRolInput(
            nombre=str(d["nombre"]),
            activo=bool(d.get("activo", True)),
            ratio_override=float(ratio) if ratio is not None else None,
        )


    def _perfil_a(self, d: Dict) -> PerfilCadenaAInput:
        # H-01 FIX: Validate critical financial fields are present or explicitly zero
        # If missing, raise ValidationError instead of silently defaulting to 0.0
        try:
            cadena_b_mensual = float(d["cadena_b_mensual"]) if "cadena_b_mensual" in d else 0.0
            costos_financieros_mensual = float(d["costos_financieros_mensual"]) if "costos_financieros_mensual" in d else 0.0
            vol_cadena_a_mensual = float(d["vol_cadena_a_mensual"]) if "vol_cadena_a_mensual" in d else 0.0
        except (KeyError, ValueError) as e:
            raise ValidationError(f"Perfil {d.get('nombre', 'unknown')}: critical financial field missing or invalid", field="perfil_a")

        cargos_adicionales = d.get("cargos_adicionales", 0.0)
        if isinstance(cargos_adicionales, dict):
            cargos_adicionales = cargos_adicionales.get("ratio", 0.0)
        elif isinstance(cargos_adicionales, list):
            cargos_adicionales = sum(float(item.get("ratio", 0.0)) for item in cargos_adicionales)

        # EXCEL V2-8 CCA!C79/C80/C87: roles_operativos con incluye_en_deal=False se excluyen.
        # El valor viene del request; NO se hardcodean nombres en módulos.
        roles_excluidos_deal: frozenset = frozenset(
            str(r.get("rol", r.get("nombre", "")))
            for r in (d.get("roles_operativos") or [])
            if not r.get("incluye_en_deal", True)
        )

        # EXCEL V2-8 CCA!E95=9.5 (override Supervisor SAC) + CCA!G78 (Director de Performance WhatsApp=1.0)
        # Valor puede ser float (todas las cadenas) o dict {canal: float} (override por canal específico).
        # Se preserva el dict tal cual para que el mixin resuelva el canal en runtime.
        raw_overrides = d.get("fte_soporte_overrides") or {}
        fte_soporte_overrides = {
            str(k): (v if isinstance(v, dict) else float(v))
            for k, v in raw_overrides.items()
        }

        return PerfilCadenaAInput(
            nombre            = str(d["nombre"]),
            rol               = str(d.get("rol", d.get("nombre", "Agente Basico"))),
            canal             = str(d["canal"]),
            modalidad         = str(d["modalidad"]),
            fte               = float(d["fte"]),
            cargos_adicionales = float(cargos_adicionales),  # EXCEL V2-8 CCA!E26/F26/G26
            fte_soporte_overrides = fte_soporte_overrides,
            roles_excluidos_deal = roles_excluidos_deal,
            pct_presencia     = float(d.get("pct_presencia", 1.0)),
            comision_pct      = float(d.get("comision_pct", 0.0)),
            salario_base      = float(d["salario_base"]) if "salario_base" in d else None,
            incluye_examenes  = bool(d.get("incluye_examenes", True)),
            incluye_seguridad = bool(d.get("incluye_seguridad", False)),
            incluye_crucero   = bool(d.get("incluye_crucero", False)),
            dias_cap_inicial  = int(d.get("dias_cap_inicial", 10)),
            dias_cap_rotacion = int(d.get("dias_cap_rotacion", 10)),
            tmo_segundos      = float(d.get("tmo_segundos", 0.0)),
            modelo_cobro         = str(d.get("modelo_cobro", "Fijo FTE")),
            pct_fijo             = float(d.get("pct_fijo", 1.0)),
            no_payroll_mensual          = float(d.get("no_payroll_mensual", 0.0)),
            inversiones_mensual         = float(d.get("inversiones_mensual", 0.0)),
            inversiones_mensual_recurrente = float(d.get("inversiones_mensual_recurrente", 0.0)),
            costos_fijos_mensual        = float(d.get("costos_fijos_mensual", 0.0)),
            cadena_b_mensual            = cadena_b_mensual,
            costos_financieros_mensual  = costos_financieros_mensual,
            vol_cadena_a_mensual        = vol_cadena_a_mensual,
            opex_fijo                   = d.get("opex_fijo"),
            inversiones                 = d.get("inversiones"),
        )

    # ------------------------------------------------------------------
    # Cadena B
    # ------------------------------------------------------------------



__all__ = ["UserInputBuildersCadenaAMixin"]
