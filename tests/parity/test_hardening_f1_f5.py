"""
Tests for F1–F5 hardening corrections.

Each test corresponds to a confirmed finding from the forensic audit and verifies
that the correction eliminates the risk without breaking AMERICAS parity.
"""
import json
import copy
import logging
import pytest
from pathlib import Path

logging.disable(logging.CRITICAL)

FIXTURE = Path(__file__).resolve().parent.parent.parent / "test_cases" / "input" / "americas_captura_datos.json"
XL_C40 = 1365353738.0298982
XL_C47 = 1728295870.9239216
XL_FIN = 16909711.3293704912 + 5350268.2742794994 + 13621325.8068785816  # C43+C44+C45
TOLS = 1e-6


@pytest.fixture(scope="module")
def engine_runner():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
    import backend_nexa  # noqa
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider

    prov = ParametrizationProvider.build()

    def run(d):
        ui = UserInputLoader().cargar_desde_dict(d)
        sol = SimulationContextBuilder(prov).construir(ui)
        res = NexaPricingEngine(parametrizacion=prov).calcular(sol)
        vt = res.vision_tarifas
        n = len(res.pyg_por_mes)
        canales = vt.canales
        voz_pay = sum(ch.payroll_ch * n for ch in canales if (ch.producto or "").lower() == "voz")
        voz_nop = sum(ch.no_payroll_ch * n for ch in canales if (ch.producto or "").lower() == "voz")
        fin = vt.costo_cadena_a_total - voz_pay - voz_nop
        return {"c40": vt.costo_cadena_a_total, "c47": vt.ingreso_cadena_a, "fin": fin}

    return run


@pytest.fixture(scope="module")
def base_data():
    return json.loads(FIXTURE.read_text())


# ──────────────────────────────────────────────────────────────────────────────
# TEST-1  F1 — Póliza aplica_extension=False con meses_extension>0 NO contribuye
# ──────────────────────────────────────────────────────────────────────────────

def test_f1_poliza_aplica_ext_false_no_contribuye(engine_runner, base_data):
    """
    Una póliza con aplica_extension=False y meses_extension=30 NO debe modificar C40.
    Con la corrección F1 (predicado unificado), pol_cfg_fin excluye esta póliza.
    """
    d = copy.deepcopy(base_data)
    d["polizas"].append({
        "nombre": "Poliza Fantasma",
        "activa": True,
        "pct_poliza": 0.05,
        "pct_atribuible": 1.0,
        "aplica_extension": False,
        "meses_extension": 30,
    })
    r_phantom = engine_runner(d)
    r_base = engine_runner(base_data)

    delta = abs(r_phantom["c40"] - r_base["c40"])
    assert delta < TOLS, (
        f"F1 FAIL: póliza con aplica_extension=False modificó C40 en {delta:+.4f} COP. "
        f"pol_cfg_fin no debe incluir pólizas sin aplica_extension."
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST-2  F2 — Comisión de Administración nunca doble-cuenta en C45
# ──────────────────────────────────────────────────────────────────────────────

def test_f2_comision_con_flag_y_aplica_ext_false_no_doble_cuenta(engine_runner, base_data):
    """
    Caso normal: Comisión con is_comision_administracion=True y aplica_extension=False.
    El fixture AMERICAS ya incluye el flag. Cualquier combinación de meses_extension
    no debe modificar C40 porque is_comision_administracion=True la excluye del predicado.
    """
    d = copy.deepcopy(base_data)
    assert d["polizas"][-1].get("is_comision_administracion") is True, (
        "Fixture debe declarar is_comision_administracion=True en la Comisión"
    )
    d["polizas"][-1]["meses_extension"] = 20  # arbitrary positive value

    r = engine_runner(d)
    r_base = engine_runner(base_data)
    delta = abs(r["c40"] - r_base["c40"])
    assert delta < TOLS, (
        f"F2 FAIL: Comisión con flag modificó C40 en {delta:+.4f} COP."
    )


def test_f2_comision_con_flag_y_aplica_ext_true_no_doble_cuenta(engine_runner, base_data):
    """
    Caso adverso F2B: Comisión con is_comision_administracion=True pero aplica_extension=True.
    El flag is_comision_administracion=True es la defensa estructural que bloquea la póliza
    independientemente de aplica_extension. ΔC40 debe ser 0.
    """
    d = copy.deepcopy(base_data)
    assert d["polizas"][-1].get("is_comision_administracion") is True
    # Simulate data entry error: aplica_extension=True on Comisión
    d["polizas"][-1]["aplica_extension"] = True
    d["polizas"][-1]["meses_extension"] = 20

    r = engine_runner(d)
    r_base = engine_runner(base_data)
    delta = abs(r["c40"] - r_base["c40"])
    assert delta < TOLS, (
        f"F2B FAIL: is_comision_administracion=True no protegió contra aplica_extension=True. "
        f"ΔC40={delta:+.4f} COP — doble conteo detectado."
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST-3  F3 — Canal base de C45 depende del primer escenario con perfiles
# ──────────────────────────────────────────────────────────────────────────────

def test_f3_canal_base_es_primer_escenario_certificado(engine_runner, base_data):
    """
    El canal base para C45 es el canal del primer escenario que tenga perfiles agente.
    Para AMERICAS: escenario 1 = Voz → esc_canal = 'voz'. Resultado certificado Δ=0
    contra Excel V2-7.

    LIMITACIÓN DOCUMENTADA: no existe evidencia de Excel V2-7 que certifique cuál
    debe ser el canal base en un deal con orden de escenarios distinto al de AMERICAS.
    Un criterio alternativo (ej. FTE-máximo) fue evaluado y rechazado por falta de
    certificación. El criterio actual (primer escenario) es dependiente del orden y
    debe declararse explícitamente en los deals futuros con pólizas de extensión.
    """
    # The certified scenario: Voz is escenario 1 → matches Excel C45 base
    r = engine_runner(base_data)
    assert abs(r["c40"] - XL_C40) < TOLS, f"Parity broken: C40 Δ={r['c40']-XL_C40}"
    assert abs(r["fin"] - XL_FIN) < TOLS, f"Parity broken: fin Δ={r['fin']-XL_FIN}"


def test_f3_orden_afecta_c45_cuando_canales_distintos(engine_runner, base_data):
    """
    Documenta el comportamiento order-dependent: invertir escenarios 1↔2 cambia
    esc_canal de Voz a WA y produce un C40 diferente (Δ ≠ 0).
    Este es el comportamiento esperado del algoritmo actual — NO un fallo.
    El test verifica que el comportamiento sea predecible, no que sea estable.
    """
    d_swapped = copy.deepcopy(base_data)
    esc = d_swapped["escenarios_comerciales"]
    esc[0], esc[1] = esc[1], esc[0]
    esc[0]["escenario"] = 1
    esc[1]["escenario"] = 2

    r_original = engine_runner(base_data)
    r_swapped = engine_runner(d_swapped)

    delta_c40 = r_swapped["c40"] - r_original["c40"]
    # Delta is expected to be non-zero: different base channel produces different C45
    # This test documents the magnitude of the order-dependency, not asserts zero
    assert abs(delta_c40) > 1.0, (
        f"F3-ORDER: expected non-zero delta when swapping channel order, got {delta_c40:+.4f}. "
        f"If zero, either channels have identical costs or the algorithm became order-independent."
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST-4  F4 — inv_rec>0 con inv_avg=0 normaliza a inv_rec=0
# ──────────────────────────────────────────────────────────────────────────────

def test_f4_inv_rec_sin_inv_avg_normalizado_a_cero(engine_runner, base_data, caplog):
    """
    Cuando inv_rec>0 pero inv_avg=0, el motor debe:
    1. Emitir un warning con el motivo.
    2. Normalizar inv_rec=0 internamente.
    3. Producir el mismo resultado que inv_rec=0 explícito (usando esc_months[-1] como base).

    Verifica la equivalencia numérica entre:
    - inv_avg=0 + inv_rec=500k → normalizado a inv_rec=0
    - inv_avg=0 + inv_rec=0   → base directa esc_months[-1]
    """
    import logging as _logging

    # Case A: inv_avg=0, inv_rec=500k (triggers normalization)
    d_a = copy.deepcopy(base_data)
    for p in d_a["condiciones_cadena_a"]["condiciones_cadena_a"]["perfiles"]:
        p["inversiones_mensual"] = 0.0
        p["inversiones_mensual_recurrente"] = 500000.0

    # Case B: inv_avg=0, inv_rec=0 (explicit zero — should be identical after normalization)
    d_b = copy.deepcopy(base_data)
    for p in d_b["condiciones_cadena_a"]["condiciones_cadena_a"]["perfiles"]:
        p["inversiones_mensual"] = 0.0
        p["inversiones_mensual_recurrente"] = 0.0

    _logging.disable(_logging.NOTSET)
    try:
        with caplog.at_level(_logging.WARNING, logger="nexa_engine.vision_tarifas"):
            r_a = engine_runner(d_a)
        r_b = engine_runner(d_b)
    finally:
        _logging.disable(_logging.CRITICAL)

    # 1. Warning must be emitted
    assert any(
        "inversiones_mensual" in rec.message.lower() or "inv_rec" in rec.message.lower()
        for rec in caplog.records
    ), (
        "F4 FAIL: warning no emitido para inv_rec>0 sin inv_avg. "
        f"Records: {[r.message for r in caplog.records]}"
    )

    # 2. Normalization: result with inv_rec=500k (no inv_avg) must equal result with inv_rec=0
    delta = abs(r_a["c40"] - r_b["c40"])
    assert delta < TOLS, (
        f"F4 FAIL: inv_rec con inv_avg=0 no fue normalizado a 0. "
        f"C40(inv_rec=500k, no avg)={r_a['c40']:.4f} ≠ C40(inv_rec=0)={r_b['c40']:.4f} "
        f"Δ={delta:.4f} — inconsistencia de bases persiste."
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST-5  F5 — fecha_inicio sin zero-padding lanza ValueError claro
# ──────────────────────────────────────────────────────────────────────────────

def test_f5_fecha_sin_padding_lanza_error(engine_runner, base_data):
    """
    fecha_inicio='2026-6-01' debe lanzar ValueError con mensaje explicativo,
    no un ValueError críptico de int() ni un resultado silenciosamente incorrecto.
    """
    d = copy.deepcopy(base_data)
    d["datos_operativos"]["fecha_inicio"] = "2026-6-01"

    with pytest.raises(ValueError) as exc_info:
        engine_runner(d)

    msg = str(exc_info.value).lower()
    assert "fecha_inicio" in msg or "mm" in msg or "formato" in msg, (
        f"F5 FAIL: ValueError lanzado pero sin mensaje descriptivo. Got: '{exc_info.value}'"
    )


def test_f5_fecha_slash_format_lanza_error(engine_runner, base_data):
    """fecha_inicio='2026/06/01' debe lanzar ValueError."""
    d = copy.deepcopy(base_data)
    d["datos_operativos"]["fecha_inicio"] = "2026/06/01"
    with pytest.raises(ValueError):
        engine_runner(d)


# ──────────────────────────────────────────────────────────────────────────────
# PARIDAD EXCEL — AMERICAS no debe verse afectada por ninguna corrección
# ──────────────────────────────────────────────────────────────────────────────

def test_paridad_excel_amercias_intacta(engine_runner, base_data):
    """
    La paridad certificada contra Excel V2-7 debe permanecer intacta
    después de todas las correcciones F1–F5.
    """
    r = engine_runner(base_data)
    assert abs(r["c40"] - XL_C40) < TOLS, f"C40 Δ={r['c40'] - XL_C40}"
    assert abs(r["c47"] - XL_C47) < TOLS, f"C47 Δ={r['c47'] - XL_C47}"
    assert abs(r["fin"] - XL_FIN) < TOLS, f"fin(C43+C44+C45) Δ={r['fin'] - XL_FIN}"
