"""
tests/unit/test_graph_05_cts_bargaining_zone.py
------------------------------------------------
Unit tests for Graph 5 — CTS Deal Bargaining Zone.

Excel V2-8 · Graficos!P84:Q93
"""

import pytest

from nexa_engine.modules.calculator_motor.formulas.graphics.graph_05_cts_bargaining_zone import (
    build_cts_bargaining_zone,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoCtsBargainingZoneResult,
    GraficosResult,
)

# ─── controlled fixture values ───────────────────────────────────────────────
COSTO_MENSUAL = 100_000.0       # Q84
INGRESO_NETO_TOTAL = 240_000.0  # sum over contract
MESES = 12
MARGEN = 0.20                   # 20%

# Expected derived values
INGRESO_DEAL = INGRESO_NETO_TOTAL / MESES          # Q85 = 20_000.0
META_INGRESO = COSTO_MENSUAL / (1 - MARGEN)         # Q87 = 125_000.0
EJE_MAX = max(INGRESO_DEAL, META_INGRESO) * 1.05    # Q88 = 131_250.0
PIERDE_PLATA = COSTO_MENSUAL                         # Q90 = 100_000.0
NO_CUMPLE_META = EJE_MAX - COSTO_MENSUAL            # Q91 = 31_250.0
ZONA_SEGURA = EJE_MAX - META_INGRESO                # Q92 = 6_250.0
MARCADOR = INGRESO_DEAL                              # Q93 = 20_000.0


def _build() -> GraficoCtsBargainingZoneResult:
    result = build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=MESES,
        margen_objetivo=MARGEN,
    )
    assert result is not None
    return result


# ─── 1. all 9 Excel values computed correctly ────────────────────────────────

def test_cts_deal():
    assert _build().cts_deal == pytest.approx(COSTO_MENSUAL)


def test_ingreso_deal():
    assert _build().ingreso_deal == pytest.approx(INGRESO_DEAL)


def test_margen_objetivo_stored():
    assert _build().margen_objetivo == pytest.approx(MARGEN)


def test_meta_ingreso():
    assert _build().meta_ingreso == pytest.approx(META_INGRESO)


def test_eje_max():
    assert _build().eje_max == pytest.approx(EJE_MAX)


def test_pierde_plata():
    assert _build().pierde_plata == pytest.approx(PIERDE_PLATA)


def test_no_cumple_meta():
    assert _build().no_cumple_meta == pytest.approx(NO_CUMPLE_META)


def test_zona_segura():
    assert _build().zona_segura == pytest.approx(ZONA_SEGURA)


def test_marcador():
    assert _build().marcador == pytest.approx(MARCADOR)


# ─── 2. meta_ingreso formula ─────────────────────────────────────────────────

def test_meta_ingreso_formula():
    r = _build()
    assert r.meta_ingreso == pytest.approx(r.cts_deal / (1 - r.margen_objetivo))


# ─── 3. eje_max formula ──────────────────────────────────────────────────────

def test_eje_max_formula():
    r = _build()
    assert r.eje_max == pytest.approx(max(r.ingreso_deal, r.meta_ingreso) * 1.05)


# ─── 4. pierde_plata = cts_deal ──────────────────────────────────────────────

def test_pierde_plata_equals_cts_deal():
    r = _build()
    assert r.pierde_plata == pytest.approx(r.cts_deal)


# ─── 5. no_cumple_meta = eje_max - cts_deal ──────────────────────────────────

def test_no_cumple_meta_formula():
    r = _build()
    assert r.no_cumple_meta == pytest.approx(r.eje_max - r.cts_deal)


# ─── 6. zona_segura = eje_max - meta_ingreso ─────────────────────────────────

def test_zona_segura_formula():
    r = _build()
    assert r.zona_segura == pytest.approx(r.eje_max - r.meta_ingreso)


# ─── 7. marcador = ingreso_deal ──────────────────────────────────────────────

def test_marcador_equals_ingreso_deal():
    r = _build()
    assert r.marcador == pytest.approx(r.ingreso_deal)


# ─── 8. division-by-zero guard: margen >= 1 ──────────────────────────────────

def test_guard_margen_exactly_1():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=MESES,
        margen_objetivo=1.0,
    ) is None


def test_guard_margen_greater_than_1():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=MESES,
        margen_objetivo=1.5,
    ) is None


# ─── 9. zero-month guard ─────────────────────────────────────────────────────

def test_guard_zero_meses():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=0,
        margen_objetivo=MARGEN,
    ) is None


def test_guard_negative_meses():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=-1,
        margen_objetivo=MARGEN,
    ) is None


# ─── 10. missing kpis / input guards ─────────────────────────────────────────

def test_guard_none_costo():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=None,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=MESES,
        margen_objetivo=MARGEN,
    ) is None


def test_guard_none_ingreso_neto():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=None,
        meses_contrato=MESES,
        margen_objetivo=MARGEN,
    ) is None


def test_guard_none_margen():
    assert build_cts_bargaining_zone(
        costo_mensual_promedio=COSTO_MENSUAL,
        ingreso_neto_total=INGRESO_NETO_TOTAL,
        meses_contrato=MESES,
        margen_objetivo=None,
    ) is None


# ─── 11. as_dict serialization ───────────────────────────────────────────────

def test_as_dict_keys():
    d = _build().as_dict()
    expected_keys = {
        "cts_deal", "ingreso_deal", "margen_objetivo", "meta_ingreso",
        "eje_max", "pierde_plata", "no_cumple_meta", "zona_segura",
        "marcador", "excel_trace",
    }
    assert set(d.keys()) == expected_keys


def test_as_dict_excel_trace():
    assert _build().as_dict()["excel_trace"] == "Graficos!P84:Q93"


def test_as_dict_values_match():
    r = _build()
    d = r.as_dict()
    assert d["cts_deal"] == pytest.approx(r.cts_deal)
    assert d["eje_max"] == pytest.approx(r.eje_max)
    assert d["marcador"] == pytest.approx(r.marcador)


# ─── 12. GraficosResult still carries Graph 1–4 fields ───────────────────────

def test_graficos_result_graph1_to_4_fields_present():
    g = GraficosResult()
    assert hasattr(g, "bandas_vision_final")
    assert hasattr(g, "ratios_cost_to_serve")
    assert hasattr(g, "ingresos_mensuales")
    assert hasattr(g, "waterfall_table")
    assert hasattr(g, "cts_bargaining_zone")


def test_graficos_result_defaults_none():
    g = GraficosResult()
    assert g.bandas_vision_final is None
    assert g.ratios_cost_to_serve is None
    assert g.ingresos_mensuales is None
    assert g.waterfall_table is None
    assert g.cts_bargaining_zone is None


def test_graficos_result_as_dict_includes_all_keys():
    g = GraficosResult()
    d = g.as_dict()
    assert "bandas_vision_final" in d
    assert "ratios_cost_to_serve" in d
    assert "ingresos_mensuales" in d
    assert "waterfall_table" in d
    assert "cts_bargaining_zone" in d


def test_graficos_result_cts_zone_wired():
    r = _build()
    g = GraficosResult(cts_bargaining_zone=r)
    d = g.as_dict()
    assert d["cts_bargaining_zone"] is not None
    assert d["cts_bargaining_zone"]["excel_trace"] == "Graficos!P84:Q93"
