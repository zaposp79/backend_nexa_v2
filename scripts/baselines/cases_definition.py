"""
Canonical case definitions for V2-7 certified baseline (WAVE 6).

12 cases covering the matrix of services, modalidades, modelos de cobro
and chain combinations. Each case has a minimal-viable entry_data
request that fully exercises the engine end-to-end.

The case_id is also the directory name under
storage/baselines/v2-7-certified/cases/.
"""
from __future__ import annotations

import copy
from typing import Any


# --- common helpers -----------------------------------------------------------

_BASE_PANEL: dict[str, Any] = {
    "cliente":             "BaselineCert",
    "tipo_cliente":        "No Grupo Aval",
    "linea_negocio":       "Cobranzas",       # overridden per case
    "ciudad":              "Bogotá",
    "sede":                "Bogota - Toberin",
    "fecha_inicio":        "2026-01-01",
    "meses_contrato":      12,
    "margen":              0.21,
    "margen_b":            0.30,
    "margen_c":            0.20,
    "op_cont":             0.05,
    "com_cont":            0.03,
    "markup":              0.0,
    "descuento":           0.0,
    "tasa_ica":            0.01,
    "tasa_gmf":            0.004,
    "activa_financiacion": False,
    "periodo_pago_dias":   30,
    "tasa_mensual_financ": 0.0153,
    "imprevistos":         0.0,
    "pct_rotacion":        0.085,
    "pct_ausentismo":      0.065,
    "cadenas_activas":     {"cadena_a": True, "cadena_b": False, "cadena_c": False},
}


def _perfil_fte(servicio: str, modalidad: str, canal: str = "Voz",
                fte: float = 10.0, salario: float = 1_750_905.0,
                modelo: str = "Fijo FTE", pct_fijo: float = 1.0,
                comision: float = 0.0) -> dict[str, Any]:
    return {
        "nombre":            f"{servicio} {modalidad} {canal}",
        "rol":               "Agente Basico",
        "modalidad":         modalidad,
        "canal":             canal,
        "fte":               fte,
        "pct_presencia":     1.0,
        "salario_base":      salario,
        "comision_pct":      comision,
        "dias_cap_inicial":  0,
        "dias_cap_rotacion": 0,
        "incluye_examenes":  False,
        "incluye_seguridad": False,
        "incluye_crucero":   False,
        "modelo_cobro":      modelo,
        "pct_fijo":          pct_fijo,
        "no_payroll_mensual": 0.0,
    }


def _build(servicio: str, modalidad: str, modelo: str, **panel_overrides) -> dict[str, Any]:
    panel = copy.deepcopy(_BASE_PANEL)
    panel["linea_negocio"] = servicio
    panel.update(panel_overrides)
    pct_fijo = 1.0 if modelo == "Fijo FTE" else (0.0 if modelo == "Volumen" else 0.6)
    perfil = _perfil_fte(servicio, modalidad, modelo=modelo, pct_fijo=pct_fijo)
    return {
        "panel_de_control":     panel,
        "condiciones_cadena_a": {"perfiles": [perfil]},
        "condiciones_cadena_b": {"canales": []},
        "condiciones_cadena_c": {},
    }


# --- case definitions ---------------------------------------------------------

CASES: list[dict[str, Any]] = [
    {
        "case_id": "bancamia_sac_inbound_fte",
        "description": "Golden master heredado: SAC inbound FTE (configuración Bancamia básica).",
        "dimensions": {"servicio": "Sac", "modalidad": "Inbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Sac", "Inbound", "Fijo FTE"),
    },
    {
        "case_id": "sac_outbound_volumen",
        "description": "SAC outbound con modelo Volumen (variable puro).",
        "dimensions": {"servicio": "Sac", "modalidad": "Outbound", "modelo": "Volumen",
                        "cadenas": ["A"]},
        "request": _build("Sac", "Outbound", "Volumen"),
    },
    {
        "case_id": "sac_blended_hibrido",
        "description": "SAC blended con modelo Híbrido (60% fijo / 40% variable).",
        "dimensions": {"servicio": "Sac", "modalidad": "Blended", "modelo": "Híbrido",
                        "cadenas": ["A"]},
        "request": _build("Sac", "Blended", "Híbrido"),
    },
    {
        "case_id": "cobranzas_outbound_fte",
        "description": "Cobranzas outbound FTE — caso clásico cobranzas.",
        "dimensions": {"servicio": "Cobranzas", "modalidad": "Outbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Cobranzas", "Outbound", "Fijo FTE"),
    },
    {
        "case_id": "cobranzas_outbound_volumen",
        "description": "Cobranzas outbound modelo Volumen — pricing por unidad gestionada.",
        "dimensions": {"servicio": "Cobranzas", "modalidad": "Outbound", "modelo": "Volumen",
                        "cadenas": ["A"]},
        "request": _build("Cobranzas", "Outbound", "Volumen"),
    },
    {
        "case_id": "ventas_outbound_fte",
        "description": "Ventas multicanal outbound FTE.",
        "dimensions": {"servicio": "Ventas multicanal", "modalidad": "Outbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Ventas multicanal", "Outbound", "Fijo FTE"),
    },
    {
        "case_id": "ventas_blended_hibrido",
        "description": "Ventas multicanal blended con modelo Híbrido.",
        "dimensions": {"servicio": "Ventas multicanal", "modalidad": "Blended", "modelo": "Híbrido",
                        "cadenas": ["A"]},
        "request": _build("Ventas multicanal", "Blended", "Híbrido"),
    },
    {
        "case_id": "backoffice_inbound_fte",
        "description": "Backoffice inbound FTE (canonicaliza a Captura de Datos).",
        "dimensions": {"servicio": "Backoffice", "modalidad": "Inbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Backoffice", "Inbound", "Fijo FTE"),
    },
    {
        "case_id": "es_sac_inbound_fte",
        "description": "ES SAC (SACO) inbound FTE — servicio especializado.",
        "dimensions": {"servicio": "SACO", "modalidad": "Inbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("SACO", "Inbound", "Fijo FTE"),
    },
    {
        "case_id": "captura_datos_inbound_fte",
        "description": "Captura de Datos inbound FTE — edge case ramp-up=0.",
        "dimensions": {"servicio": "Captura de Datos", "modalidad": "Inbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Captura de Datos", "Inbound", "Fijo FTE"),
    },
    {
        "case_id": "plataformas_inbound_fte",
        "description": "Plataformas inbound FTE — edge case ramp-up=0.",
        "dimensions": {"servicio": "Plataformas", "modalidad": "Inbound", "modelo": "Fijo FTE",
                        "cadenas": ["A"]},
        "request": _build("Plataformas", "Inbound", "Fijo FTE"),
    },
    {
        "case_id": "bancamia_full_chains_abc",
        "description": "Bancamia con cadenas A+B+C activas — caso completo de cobertura.",
        "dimensions": {"servicio": "Cobranzas", "modalidad": "Blended", "modelo": "Híbrido",
                        "cadenas": ["A", "B", "C"]},
        "request": {
            "panel_de_control": {
                **_BASE_PANEL,
                "cliente":         "Bancamia",
                "linea_negocio":   "Cobranzas",
                "meses_contrato":  24,
                "margen":          0.18,
                "margen_b":        0.30,
                "margen_c":        0.20,
                "op_cont":         0.025,
                "com_cont":        0.0,
                "activa_financiacion": True,
                "periodo_pago_dias": 90,
                "cadenas_activas": {"cadena_a": True, "cadena_b": True, "cadena_c": True},
            },
            "condiciones_cadena_a": {
                "perfiles": [_perfil_fte("Cobranzas", "Blended", canal="Voz",
                                           fte=5.0, salario=1_750_905.0,
                                           modelo="Híbrido", pct_fijo=0.6)]
            },
            "condiciones_cadena_b": {
                "canales": [{
                    "nombre":           "WhatsApp Inbound",
                    "modalidad":        "Inbound",
                    "tarifa_unitaria":  4500.0,
                    "volumen_mensual":  0,
                    "opex_fijo":        50_000_000.0,
                    "pct_escalamiento": 0.03,
                    "costo_escalamiento": 0.0,
                }],
                "fte_equipo_sm":            1.0,
                "amortizar_dispositivos_sm": True,
            },
            "condiciones_cadena_c": {
                "canales": [{
                    "nombre":           "IA Voz",
                    "modalidad":        "Outbound",
                    "volumen_mensual":  10000.0,
                    "opex_fijo_integ":  5_000_000.0,
                    "opex_var_integ":   200.0,
                    "pct_escalamiento": 0.05,
                    "costo_escalamiento": 0.0,
                }],
                "inversion_anual": 10_000_000.0,
            },
        },
    },
]


assert len(CASES) == 12, f"Expected 12 canonical cases, found {len(CASES)}"
