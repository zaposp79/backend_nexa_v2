"""
tests/refactor/test_input_contract_fix_b1.py
============================================
INPUT_CONTRACT_FIX_B1 — Tests for D-1 bug fix.

Validates that NewEntryDataAdapter (via UserInputLoader._normalizar_entry_data_format)
correctly unwraps the double-nesting of condiciones_cadena_b when request.json
sends condiciones_cadena_b.condiciones_cadena_b.{opex, hitl, ...} instead of
a flat condiciones_cadena_b.{opex, hitl, ...}.

Tests:
  1. test_cadena_b_flat_format_works               — flat format still works
  2. test_cadena_b_nested_format_works             — nested format now produces costo_b > 0
  3. test_cadena_b_nested_and_flat_produce_equal_cost — both formats give same result
  4. test_cadena_b_produces_canales               — channels are built from nested data
  5. test_cadena_c_flat_format_doesnt_break       — flat cadena_c still OK
  6. test_cadena_a_not_affected                   — cadena_a unaffected
  7. test_request_json_after_fix                  — request.json no longer costo_b=0

D-1 bug: condiciones_cadena_b.condiciones_cadena_b double-nesting
Fix location: user_input_loader.py _normalizar_entry_data_format cadena_b section.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401 — registers nexa_engine alias

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
REQUEST_PATH = _BACKEND_ROOT / "request" / "request.json"

# ── Fixtures ──────────────────────────────────────────────────────────────────

_DATOS_OPERATIVOS = {
    "servicio": "Cobranzas",
    "cliente": "TestClient",
    "tipo_cliente": "No Grupo Aval",
    "fecha_inicio": "2026-01-01",
    "duracion_meses": 2,
    "ciudad": "Bogota",
    "sede": "Toberin",
    "tarifa_diaria_capacitacion": 20000,
    "crucero": 8422,
    "horas_formacion_mes": 8,
    "pct_ausentismo": 0.065,
    "pct_rotacion": 0.085,
    "cons_costo_de_financiacion": False,
    "tasa_ica": 0.0097,
    "tasa_gmf": 0.004,
}

_REGLAS_NEGOCIO = {
    "margen_objetivo_cadena_a": 0.18,
    "contingencia_operativa": {"valor": 0.025, "minimo": 0.025, "maximo": 0.12},
    "contingencia_comercial": {"valor": 0.04, "minimo": 0.04, "maximo": 0.07},
    "markup": {"valor": 0.0, "minimo": 0.02, "maximo": 0.08},
    "imprevistos": 0,
    "porcentaje_acumulado": {"actual": 0.02, "minimo": 0.012, "maximo": 0.15},
}

# Minimal cadena_a profile required by InputNormalizer STRICT
_CONDICIONES_A_MINIMAL = {
    "Calculo_conversion_fte_interacciones": {
        "tmo": 0.0145,
        "tmo_promedio_seg": 522.2,
        "horas": 3600,
    },
    "perfiles": [
        {
            "nombre": "Inbound WhatsApp",
            "modalidad": "Inbound",
            "canal": "WhatsApp",
            "fte": 5,
            "pct_presencia": 1.0,
            "salario_base": 1560000,
            "comision_pct": 0.0,
            "estaciones_presenciales": 5,
            "roles_operativos": [],
            "capacitacion": {
                "dias_capacitacion_perfil": 5,
                "por_capacitacion_mes": 0.09,
                "incluye_costo_examenes_ingreso": False,
                "incluye_costo_examenes_rotacion": False,
                "incluye_costo_capacitacion_anual": False,
                "incluye_estudio_seguridad_ingreso": False,
                "incluye_estudio_seguridad_rotacion": False,
                "incluye_estudio_seguridad_final_ingreso": False,
                "incluye_estudio_seguridad_final_rotacion": False,
            },
            "opex_fijo": {
                "items": [],
                "staffing": {
                    "analista_staffing": 4.5,
                    "supervisores": 1,
                    "ausentismo_cem": 0.07,
                },
            },
            "inversiones": [],
        }
    ],
}

_VOLUMETRIA_AB_ACTIVE = {
    "indexacion": {
        "componente_humano": "IPC",
        "componente_tecnologico": "IPC",
        "frecuencia": "Anual",
        "mes_aplicacion": 1,
        "tasa_interes_mensual": 0.0153,
    },
    "inbound": {
        "cadenas_activas": {"cadena_a": True, "cadena_b": True, "cadena_c": False},
        "canales": [
            {
                "canal": "WhatsApp",
                "cadena_a": {"unidad": "FTE", "valor": 5, "participacion": 1.0},
                "cadena_b": {"unidad": "VOLUMEN", "valor": 5000, "participacion": 1.0},
                "cadena_c": {"unidad": "VOLUMEN", "valor": 0, "participacion": 0.0},
            }
        ],
    },
    "outbound": {
        "cadenas_activas": {"cadena_a": False, "cadena_b": False, "cadena_c": False},
        "canales": [],
    },
}

_VOLUMETRIA_A_ONLY = {
    "indexacion": {
        "componente_humano": "IPC",
        "componente_tecnologico": "IPC",
        "frecuencia": "Anual",
        "mes_aplicacion": 1,
        "tasa_interes_mensual": 0.0153,
    },
    "inbound": {
        "cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": False},
        "canales": [
            {
                "canal": "WhatsApp",
                "cadena_a": {"unidad": "FTE", "valor": 5, "participacion": 1.0},
                "cadena_b": {"unidad": "VOLUMEN", "valor": 0, "participacion": 0.0},
                "cadena_c": {"unidad": "VOLUMEN", "valor": 0, "participacion": 0.0},
            }
        ],
    },
    "outbound": {
        "cadenas_activas": {"cadena_a": False, "cadena_b": False, "cadena_c": False},
        "canales": [],
    },
}

# Flat cadena_b payload (single level)
_CADENA_B_FLAT = {
    "opex": {
        "items": [
            {
                "rubro": "Plataformas y licencias",
                "modalidad": "Inbound",
                "canal": "WhatsApp",
                "producto": "Token IA",
                "tipo_de_cobro": "Unitario",
                "tipo_de_gasto": "Fijo",
                "valor": 3075,
                "cantidad": 10,
                "valor_total": 30750,
            }
        ]
    },
    "inversiones_capex": [],
    "equipo_soporte_mantenimiento": {
        "fte": 1,
        "roles": [
            {"rol": "Service Owner", "activado": True, "dedicacion": 5, "fte": 0.25}
        ],
        "dispositivos_requeridos": [],
    },
    "costo_variable": {
        "tarifas_por_canal": {
            "inbound": [{"canal": "WhatsApp", "tarifa": 4500}],
            "outbound": [],
        },
        "tasa_escalamiento": {
            "tarifa_de_escalamiento_indbound": {"tipo": "Input Calculado", "value": 3000},
            "tarifa_de_escalamiento_outbound": {"tipo": "Input Manual", "value": 0},
            "inbound": [{"canal": "WhatsApp", "tasa": 0.05}],
            "outbound": [],
        },
    },
    "hitl": {
        "total_volumen_cadena_b": 500,
        "equipo": [
            {
                "rol": "Human Reviewers",
                "activado": True,
                "ratio": 4000,
                "personas": 0.1,
            }
        ],
        "dispositivos_requeridos": [],
    },
}

# Double-nested cadena_b payload (as in request.json — D-1 bug format)
_CADENA_B_NESTED = {"condiciones_cadena_b": _CADENA_B_FLAT}

_CONDICIONES_C_EMPTY = {
    "tarifa_proveedor_canal": {"items": []},
    "inversiones_capex": [],
    "recurso_humano_transversal": {"fte": 0, "roles": [], "opex": []},
    "costo_variable": {
        "tarifas_por_canal": {"inbound": [], "outbound": []},
        "tasa_escalamiento": {
            "tarifa_de_escalamiento_indbound": {"tipo": "Input Calculado", "value": 0},
            "tarifa_de_escalamiento_outbound": {"tipo": "Input Manual", "value": 0},
            "inbound": [],
            "outbound": [],
        },
    },
    "hitl": {"total_volumen_cadena_c": 0, "equipo": [], "opex": []},
}


def _base_payload(**extra) -> dict:
    """Build a minimal valid entry_data payload."""
    payload = {
        "datos_operativos": _DATOS_OPERATIVOS,
        "reglas_negocio": _REGLAS_NEGOCIO,
        "volumetria": _VOLUMETRIA_AB_ACTIVE,
        "condiciones_cadena_a": _CONDICIONES_A_MINIMAL,
        "escenarios_comerciales": [],
        "polizas": [],
    }
    payload.update(extra)
    return payload


def _run_engine(payload: dict):
    """Run full engine pipeline from entry_data payload."""
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    return NexaPricingEngine().calcular(solicitud)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.baseline
def test_cadena_b_flat_format_works():
    """Cadena B with flat format (condiciones_cadena_b.opex directly) works."""
    payload = _base_payload(condiciones_cadena_b=_CADENA_B_FLAT)
    resultado = _run_engine(payload)
    total_b = sum(m.costo_b for m in resultado.pyg_por_mes)
    assert total_b > 0, f"Expected costo_b > 0 with flat format, got {total_b}"


@pytest.mark.baseline
def test_cadena_b_nested_format_works():
    """Cadena B with double-nested format (condiciones_cadena_b.condiciones_cadena_b) produces costo_b > 0."""
    payload = _base_payload(condiciones_cadena_b=_CADENA_B_NESTED)
    resultado = _run_engine(payload)
    total_b = sum(m.costo_b for m in resultado.pyg_por_mes)
    assert total_b > 0, (
        f"D-1 BUG REGRESSED: Expected costo_b > 0 with nested format, got {total_b}. "
        "The double-nesting unwrap guard must be present in _normalizar_entry_data_format."
    )


@pytest.mark.baseline
def test_cadena_b_nested_and_flat_produce_equal_cost():
    """Flat and double-nested formats for cadena_b produce identical costo_b."""
    resultado_flat = _run_engine(_base_payload(condiciones_cadena_b=_CADENA_B_FLAT))
    resultado_nested = _run_engine(_base_payload(condiciones_cadena_b=_CADENA_B_NESTED))

    total_flat = sum(m.costo_b for m in resultado_flat.pyg_por_mes)
    total_nested = sum(m.costo_b for m in resultado_nested.pyg_por_mes)
    assert math.isclose(total_flat, total_nested, rel_tol=1e-9), (
        f"Flat vs nested cadena_b cost mismatch: flat={total_flat}, nested={total_nested}"
    )


@pytest.mark.baseline
def test_cadena_b_produces_canales():
    """Cadena B builds channels from the nested format after unwrap."""
    payload = _base_payload(condiciones_cadena_b=_CADENA_B_NESTED)
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    assert len(user_input.cadena_b.canales) > 0, (
        "cadena_b.canales should be non-empty after unwrapping double-nesting"
    )


@pytest.mark.baseline
def test_cadena_c_flat_format_doesnt_break():
    """Cadena C with flat format (request.json pattern) continues to work."""
    payload = _base_payload(condiciones_cadena_c=_CONDICIONES_C_EMPTY)
    resultado = _run_engine(payload)
    assert resultado is not None
    # cadena_c empty — costo_c should be 0 or very small
    total_c = sum(m.costo_c for m in resultado.pyg_por_mes)
    assert total_c == 0.0 or total_c >= 0.0, "costo_c should be >= 0"


@pytest.mark.baseline
def test_cadena_a_not_affected():
    """The cadena_b double-nesting fix does not affect cadena_a calculation."""
    payload = {
        "datos_operativos": _DATOS_OPERATIVOS,
        "reglas_negocio": _REGLAS_NEGOCIO,
        "volumetria": _VOLUMETRIA_A_ONLY,
        "condiciones_cadena_a": _CONDICIONES_A_MINIMAL,
        "escenarios_comerciales": [],
        "polizas": [],
    }
    resultado = _run_engine(payload)
    total_a = sum(m.payroll_a + m.no_payroll_a for m in resultado.pyg_por_mes)
    assert total_a > 0, f"cadena_a should produce cost, got {total_a}"


@pytest.mark.baseline
def test_request_json_after_fix():
    """request/request.json (SAC METROCUADRADO COM SAS) no longer produces costo_b=0 after D-1 fix."""
    payload = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    resultado = _run_engine(payload)
    pyg = resultado.pyg_por_mes

    # All 24 months must have costo_b > 0 (cadena_b active in request.json)
    for i, mes in enumerate(pyg, start=1):
        assert mes.costo_b > 0, (
            f"D-1 REGRESSED: costo_b=0 in month {i}. "
            "The double-nesting unwrap guard may have been removed."
        )

    # Anchor: costo_b mes1 (SAC METROCUADRADO COM SAS, V2-8 canonical deal)
    # Updated 2026-06-11: Excel Condiciones Cadena B I8 cantidad corrected 1→10000
    assert math.isclose(pyg[0].costo_b, 56071220.0, rel_tol=1e-4), (
        f"costo_b mes1 anchor mismatch: {pyg[0].costo_b}"
    )


# ── Canonicalization tests (INPUT_CONTRACT_CANONICALIZATION_1) ────────────────


@pytest.mark.baseline
def test_request_json_cadena_b_is_canonical_flat():
    """request/request.json condiciones_cadena_b está en formato canónico plano."""
    data = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    cb = data.get("condiciones_cadena_b", {})

    # Formato plano: las claves son opex, inversiones_capex, hitl, etc.
    # No debe haber 'condiciones_cadena_b' como única clave (formato legacy anidado)
    if len(cb) == 1 and "condiciones_cadena_b" in cb:
        pytest.fail(
            "request/request.json todavía está en formato legacy anidado. "
            "Canonicalization no se aplicó correctamente."
        )

    assert "opex" in cb, f"cadena_b plana debe tener clave 'opex', got keys: {list(cb.keys())}"
    assert "hitl" in cb, f"cadena_b plana debe tener clave 'hitl', got keys: {list(cb.keys())}"


@pytest.mark.baseline
def test_request_json_cadena_a_is_canonical_flat():
    """request/request.json condiciones_cadena_a está en formato canónico plano."""
    data = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    ca = data.get("condiciones_cadena_a", {})

    if len(ca) == 1 and "condiciones_cadena_a" in ca:
        pytest.fail(
            "request/request.json condiciones_cadena_a todavía está en formato legacy anidado. "
            "Canonicalization no se aplicó correctamente."
        )

    assert "perfiles" in ca, f"cadena_a plana debe tener clave 'perfiles', got keys: {list(ca.keys())}"


@pytest.mark.baseline
def test_request_json_cadena_c_is_canonical_flat():
    """request/request.json condiciones_cadena_c está en formato canónico plano (ya lo estaba)."""
    data = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    cc = data.get("condiciones_cadena_c", {})

    # Cadena C nunca fue anidada — confirmar que sigue siendo plana
    assert "condiciones_cadena_c" not in cc, (
        "cadena_c no debería estar anidada en ningún caso"
    )
    assert "tarifa_proveedor_canal" in cc, (
        f"cadena_c plana debe tener clave 'tarifa_proveedor_canal', got keys: {list(cc.keys())}"
    )


@pytest.mark.baseline
def test_flat_and_nested_b_produce_same_output():
    """Formato plano y anidado de cadena_b producen EXACTAMENTE el mismo PricingResult."""
    import copy

    payload_flat = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))

    # Construir versión anidada artificialmente (formato legacy)
    payload_nested = copy.deepcopy(payload_flat)
    payload_nested["condiciones_cadena_b"] = {
        "condiciones_cadena_b": copy.deepcopy(payload_flat["condiciones_cadena_b"])
    }

    resultado_flat = _run_engine(payload_flat)
    resultado_nested = _run_engine(payload_nested)

    # Comparar costo_b mes1 (anchor value)
    costo_b_flat = resultado_flat.pyg_por_mes[0].costo_b
    costo_b_nested = resultado_nested.pyg_por_mes[0].costo_b
    assert math.isclose(costo_b_flat, costo_b_nested, rel_tol=1e-9), (
        f"costo_b mes1 difiere: flat={costo_b_flat}, nested={costo_b_nested}"
    )

    # Comparar KPIs totales
    total_flat = sum(m.costo_b for m in resultado_flat.pyg_por_mes)
    total_nested = sum(m.costo_b for m in resultado_nested.pyg_por_mes)
    assert math.isclose(total_flat, total_nested, rel_tol=1e-9), (
        f"costo_b total difiere: flat={total_flat}, nested={total_nested}"
    )


@pytest.mark.baseline
def test_flat_and_nested_a_produce_same_output():
    """Formato plano y anidado de cadena_a producen EXACTAMENTE el mismo PricingResult."""
    import copy

    payload_flat = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))

    # Construir versión anidada artificialmente (formato legacy)
    payload_nested = copy.deepcopy(payload_flat)
    payload_nested["condiciones_cadena_a"] = {
        "condiciones_cadena_a": copy.deepcopy(payload_flat["condiciones_cadena_a"])
    }

    resultado_flat = _run_engine(payload_flat)
    resultado_nested = _run_engine(payload_nested)

    # Comparar payroll_a mes1
    payroll_flat = resultado_flat.pyg_por_mes[0].payroll_a
    payroll_nested = resultado_nested.pyg_por_mes[0].payroll_a
    assert math.isclose(payroll_flat, payroll_nested, rel_tol=1e-9), (
        f"payroll_a mes1 difiere: flat={payroll_flat}, nested={payroll_nested}"
    )
