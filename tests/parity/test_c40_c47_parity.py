"""
Paridad VisionTarifas C40-C47 — CAPEX amortizado + pólizas deal-wide con extensión.

Escenario S1 (fixture: americas_captura_datos.json):
  Contrato con amortización de setup en el mes 1: inversiones_mensual (avg de todos los meses)
  difiere de inversiones_mensual_recurrente (meses 2..N, sin setup). El deal tiene pólizas
  deal-wide (per_canal=False) con aplica_extension=True, por lo que VisionTarifas debe usar
  inversiones_mensual_recurrente como base de la fórmula C45 (extensión post-contrato).
  Sin ese campo, C45 se calcularía sobre el promedio con setup y la póliza de extensión
  quedaría sobreestimada.

Escenarios pendientes de implementar (ver TODOs al final del archivo):
  S2 — inversiones_mensual_recurrente > 0 pero SIN pólizas de extensión → debe ignorarlo.
  S3 — inversiones_mensual_recurrente ausente del input → debe comportarse igual que 0.0.
  S4 — inversiones_mensual_recurrente = 0.0 explícito → base de extensión = último esc_months.

Criterio de certificación: Δ < 0.000001 COP en todos los campos auditados.
"""

import json
import pytest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent.parent / "test_cases" / "input" / "americas_captura_datos.json"

XL_C41 = 1039554872.6578202    # NL SUMPRODUCT × Voz × Inbound
XL_C42 =  289917559.96154934   # No payroll × Voz × Inbound
XL_C43 =   16909711.3293704912 # Pólizas ICA Voz
XL_C44 =    5350268.2742794994 # Pólizas GMF Voz
XL_C45 =   13621325.8068785816 # Pólizas puras Voz (incl. extensión)
XL_C46 =           0.0
XL_C40 = 1365353738.0298982    # = C41+C42+C43+C44+C45+C46
XL_C47 = 1728295870.9239216    # = C40 / (1 - margen)

TOLS = 1e-6  # 0.000001 COP


@pytest.fixture(scope="module")
def vt_result():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
    import backend_nexa  # noqa: F401
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    import logging; logging.disable(logging.CRITICAL)

    data = json.loads(FIXTURE.read_text())
    prov = ParametrizationProvider.build()
    ui = UserInputLoader().cargar_desde_dict(data)
    sol = SimulationContextBuilder(prov).construir(ui)
    res = NexaPricingEngine(parametrizacion=prov).calcular(sol)
    vt = res.vision_tarifas
    pm = res.pyg_por_mes; n = len(pm)
    canales = vt.canales
    voz_pay = sum(ch.payroll_ch * n for ch in canales if (ch.producto or "").lower() == "voz")
    voz_nop = sum(ch.no_payroll_ch * n for ch in canales if (ch.producto or "").lower() == "voz")
    fin = vt.costo_cadena_a_total - voz_pay - voz_nop

    # Per-escenario desglose for Esc1 (Voz) — certified against Excel
    voz_desglose = None
    for esc in vt.escenarios_detalle:
        meta = getattr(esc, "meta", None)
        if meta and (meta.canal or "").lower() == "voz":
            voz_desglose = esc.cadena_a
            break

    return {
        "c40": vt.costo_cadena_a_total,
        "c41": voz_pay,
        "c42": voz_nop,
        "fin": fin,
        "c47": vt.ingreso_cadena_a,
        # Individual C43/C44/C45 — now directly exposed from the certified formula
        "c43": vt.ica_cadena_a,
        "c44": vt.gmf_cadena_a,
        "c45": vt.polizas_cadena_a,
        # Per-escenario desglose (annual values after scope mismatch fix)
        "voz_desglose": voz_desglose,
    }


def test_c41_payroll(vt_result):
    assert abs(vt_result["c41"] - XL_C41) < TOLS, f"C41 Δ={vt_result['c41']-XL_C41}"


def test_c42_nopayroll(vt_result):
    assert abs(vt_result["c42"] - XL_C42) < TOLS, f"C42 Δ={vt_result['c42']-XL_C42}"


def test_c43_ica(vt_result):
    """C43: ICA anual Voz — valor individual directo desde vt.ica_cadena_a."""
    assert abs(vt_result["c43"] - XL_C43) < TOLS, f"C43 ICA Δ={vt_result['c43']-XL_C43}"


def test_c44_gmf(vt_result):
    """C44: GMF anual Voz — valor individual directo desde vt.gmf_cadena_a."""
    assert abs(vt_result["c44"] - XL_C44) < TOLS, f"C44 GMF Δ={vt_result['c44']-XL_C44}"


def test_c45_polizas(vt_result):
    """C45: Pólizas puras Voz incl. extensión — valor individual desde vt.polizas_cadena_a."""
    assert abs(vt_result["c45"] - XL_C45) < TOLS, f"C45 Pólizas Δ={vt_result['c45']-XL_C45}"


def test_c43_c44_c45_sum(vt_result):
    """C43+C44+C45 sum via residual — verifies algebraic consistency."""
    xl_fin = XL_C43 + XL_C44 + XL_C45
    assert abs(vt_result["fin"] - xl_fin) < TOLS, f"C43+44+45 Δ={vt_result['fin']-xl_fin}"
    # Also verify that individual sum equals residual (internal consistency)
    individual_sum = vt_result["c43"] + vt_result["c44"] + vt_result["c45"]
    assert abs(individual_sum - vt_result["fin"]) < TOLS, (
        f"INTERNAL: sum(c43+c44+c45)={individual_sum} ≠ fin_a_sum={vt_result['fin']}"
    )


def test_c40(vt_result):
    assert abs(vt_result["c40"] - XL_C40) < TOLS, f"C40 Δ={vt_result['c40']-XL_C40}"


def test_c47(vt_result):
    assert abs(vt_result["c47"] - XL_C47) < TOLS, f"C47 Δ={vt_result['c47']-XL_C47}"


# ---------------------------------------------------------------------------
# Desglose per-escenario — scope mismatch fix validation
# ---------------------------------------------------------------------------

def test_desglose_esc1_voz_ica_equals_c43(vt_result):
    """
    escenarios_detalle[Voz].cadena_a.ica must equal XL_C43 (annual).
    Before the fix: used avg(m.ica_a) deal-wide = 26,219,672 → Δ=+9.3M
    After the fix:  uses c43_sim from certified formula = 16,909,711 → Δ=0
    """
    d = vt_result["voz_desglose"]
    assert d is not None, "No Voz escenario found in escenarios_detalle"
    assert abs(d.ica - XL_C43) < TOLS, (
        f"Desglose Esc1 Voz: ica={d.ica:.4f} ≠ XL_C43={XL_C43:.4f} Δ={d.ica-XL_C43:+.4f}"
    )


def test_desglose_esc1_voz_gmf_equals_c44(vt_result):
    """escenarios_detalle[Voz].cadena_a.gmf must equal XL_C44."""
    d = vt_result["voz_desglose"]
    assert d is not None
    assert abs(d.gmf - XL_C44) < TOLS, (
        f"Desglose Esc1 Voz: gmf={d.gmf:.4f} ≠ XL_C44={XL_C44:.4f} Δ={d.gmf-XL_C44:+.4f}"
    )


def test_desglose_esc1_voz_polizas_equals_c45(vt_result):
    """
    escenarios_detalle[Voz].cadena_a.polizas must equal XL_C45.
    Before the fix: avg(m.polizas_a) = 0 (extension polizas absent from PyG) → Δ=100%
    After the fix:  uses c45_sim = 13,621,325 → Δ=0
    """
    d = vt_result["voz_desglose"]
    assert d is not None
    assert abs(d.polizas - XL_C45) < TOLS, (
        f"Desglose Esc1 Voz: polizas={d.polizas:.4f} ≠ XL_C45={XL_C45:.4f} Δ={d.polizas-XL_C45:+.4f}"
    )


def test_desglose_esc1_voz_total_equals_c40(vt_result):
    """
    escenarios_detalle[Voz].cadena_a.total_costo must equal XL_C40.
    After the fix with annual values: total = C41+C42+C43+C44+C45+C46 = C40.
    """
    d = vt_result["voz_desglose"]
    assert d is not None
    assert abs(d.total_costo - XL_C40) < TOLS, (
        f"Desglose Esc1 Voz: total_costo={d.total_costo:.4f} ≠ XL_C40={XL_C40:.4f}"
    )


def test_desglose_esc1_voz_ingreso_equals_c47(vt_result):
    """escenarios_detalle[Voz].cadena_a.ingreso_bruto must equal XL_C47."""
    d = vt_result["voz_desglose"]
    assert d is not None
    assert abs(d.ingreso_bruto - XL_C47) < TOLS, (
        f"Desglose Esc1 Voz: ingreso={d.ingreso_bruto:.4f} ≠ XL_C47={XL_C47:.4f}"
    )


# ---------------------------------------------------------------------------
# Esqueletos de paridad para comportamientos adicionales de
# inversiones_mensual_recurrente (pendiente de fixture + valores Excel).
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="TODO S2: crear fixture con inv_rec>0 y SIN pólizas de extensión")
def test_s2_inv_rec_sin_polizas_extension():
    """
    S2 — inversiones_mensual_recurrente > 0, pero ninguna póliza tiene aplica_extension=True.

    Condición esperada: VisionTarifas ignora inv_rec (has_deal_wide_polizas=False) y calcula
    la base de extensión como el último mes de esc_months, igual que si inv_rec fuera 0.0.
    C45 debe ser idéntico al obtenido con inv_rec=0.0 para el mismo input.

    TODO:
      1. Crear fixture derivado de americas_captura_datos.json con aplica_extension=False
         en todas las pólizas (o sin pólizas) y con inv_rec=500_000.0 en ambos perfiles.
      2. Obtener valores de referencia de Excel (o del motor con inv_rec=0.0 como oráculo).
      3. Añadir las aserciones correspondientes.
    """
    raise NotImplementedError("fixture S2 pendiente")


@pytest.mark.skip(reason="TODO S3: verificar comportamiento cuando inv_rec está ausente del JSON")
def test_s3_inv_rec_ausente():
    """
    S3 — el campo inversiones_mensual_recurrente no aparece en el JSON de entrada.

    Condición esperada: el loader lo inicializa a 0.0 (default del dataclass).
    VisionTarifas usa el último mes de esc_months como base de extensión.
    El resultado debe ser idéntico al de inv_rec=0.0 explícito (S4).

    TODO:
      1. Usar americas_captura_datos.json sin el campo inv_rec en los perfiles.
      2. Comparar C40/C45/C47 con los mismos valores que produciría inv_rec=0.0.
      3. Asegurar que no se lanza KeyError ni AttributeError.
    """
    raise NotImplementedError("fixture S3 pendiente")


@pytest.mark.skip(reason="TODO S4: verificar comportamiento con inv_rec=0.0 explícito")
def test_s4_inv_rec_cero_explicito():
    """
    S4 — inversiones_mensual_recurrente = 0.0 declarado explícitamente en el JSON.

    Condición esperada: VisionTarifas usa el último mes de esc_months como base de extensión
    (rama `else` del guard `if recurrent_inv > 0`). C45 debe coincidir con el valor que
    produce el fallback histórico (sin campo inv_rec).

    TODO:
      1. Crear variante del fixture con inv_rec=0.0 en todos los perfiles.
      2. Calcular el C45 esperado con la rama fallback.
      3. Añadir las aserciones correspondientes.
    """
    raise NotImplementedError("fixture S4 pendiente")
