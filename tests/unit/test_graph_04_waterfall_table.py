"""
Unit tests for Graph 4 — Waterfall Table (Graficos!P65:S81).
"""

from __future__ import annotations

import pytest

from nexa_engine.modules.calculator_motor.formulas.graphics.graph_04_waterfall_table import (
    build_waterfall_table,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoWaterfallTableResult,
    WaterfallItem,
)
from nexa_engine.modules.calculator_motor.models.results import PyGMensual


def _mes(
    mes: int,
    ingreso_bruto_a: float = 1000.0,
    ingreso_bruto_b: float = 500.0,
    ingreso_bruto_c: float = 200.0,
    payroll_a: float = 300.0,
    no_payroll_a: float = 50.0,
    costo_b: float = 100.0,
    costo_c: float = 80.0,
    ica: float = 10.0,
    gmf: float = 5.0,
    polizas: float = 8.0,
    financiacion: float = 7.0,
    comision_administracion: float = 4.0,
) -> PyGMensual:
    return PyGMensual(
        mes=mes,
        ingreso_bruto_a=ingreso_bruto_a,
        ingreso_bruto_b=ingreso_bruto_b,
        ingreso_bruto_c=ingreso_bruto_c,
        payroll_a=payroll_a,
        no_payroll_a=no_payroll_a,
        costo_b=costo_b,
        costo_c=costo_c,
        ica=ica,
        gmf=gmf,
        polizas=polizas,
        financiacion=financiacion,
        comision_administracion=comision_administracion,
    )


class TestWaterfallTableOrdering:
    def test_items_are_ordered(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1), _mes(2)],
            pct_utilidad_neta_total=0.15,
        )
        ordenes = [it.orden for it in result.items]
        assert ordenes == sorted(ordenes)

    def test_items_count(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.10,
        )
        assert len(result.items) == 8


class TestWaterfallTableTypes:
    def test_tipos_correctos(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.10,
        )
        tipos = {it.concepto: it.tipo for it in result.items}
        assert tipos["Ingreso Bruto"] == "ingreso"
        assert tipos["Ingreso Neto"] == "subtotal"
        assert tipos["Costos Cadena A"] == "costo"
        assert tipos["Costos Cadena B"] == "costo"
        assert tipos["Costos Cadena C"] == "costo"
        assert tipos["Costo Total"] == "subtotal"
        assert tipos["Contribución"] == "subtotal"
        assert tipos["Utilidad Neta"] == "utilidad"


class TestWaterfallTableValues:
    def test_ingreso_bruto_sum_from_pyg(self):
        mes1 = _mes(1, ingreso_bruto_a=1000, ingreso_bruto_b=500, ingreso_bruto_c=200)
        mes2 = _mes(2, ingreso_bruto_a=2000, ingreso_bruto_b=600, ingreso_bruto_c=300)
        result = build_waterfall_table(
            pyg_por_mes=[mes1, mes2],
            pct_utilidad_neta_total=0.0,
        )
        ingreso_bruto = next(it for it in result.items if it.concepto == "Ingreso Bruto")
        expected = (1000 + 500 + 200) + (2000 + 600 + 300)
        assert ingreso_bruto.total == pytest.approx(expected)

    def test_promedio_is_total_divided_by_months(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1), _mes(2)],
            pct_utilidad_neta_total=0.0,
        )
        for item in result.items:
            assert item.promedio == pytest.approx(item.total / 2)

    def test_pct_utilidad_neta_uses_kpis_value(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.234,
        )
        utilidad = next(it for it in result.items if it.concepto == "Utilidad Neta")
        assert utilidad.pct_ingreso_neto == pytest.approx(0.234)

    def test_pct_ingreso_neto_zero_when_ingreso_neto_zero(self):
        mes_zero = PyGMensual(
            mes=1,
            ingreso_bruto_a=0.0,
            ingreso_bruto_b=0.0,
            ingreso_bruto_c=0.0,
        )
        result = build_waterfall_table(
            pyg_por_mes=[mes_zero],
            pct_utilidad_neta_total=0.0,
        )
        for item in result.items:
            if item.concepto != "Utilidad Neta":
                assert item.pct_ingreso_neto == 0.0

    def test_contribucion_equals_ingreso_neto_minus_costo_total(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.0,
        )
        totals = {it.concepto: it.total for it in result.items}
        assert totals["Contribución"] == pytest.approx(
            totals["Ingreso Neto"] - totals["Costo Total"]
        )


class TestWaterfallTableMetadata:
    def test_excel_trace(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.0,
        )
        assert result.excel_trace == "Graficos!P65:S81"

    def test_meses_contrato(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(i) for i in range(1, 13)],
            pct_utilidad_neta_total=0.0,
        )
        assert result.meses_contrato == 12

    def test_as_dict_has_expected_keys(self):
        result = build_waterfall_table(
            pyg_por_mes=[_mes(1)],
            pct_utilidad_neta_total=0.10,
        )
        d = result.as_dict()
        assert "items" in d
        assert "meses_contrato" in d
        assert "excel_trace" in d
        item = d["items"][0]
        assert all(k in item for k in ("concepto", "total", "promedio", "pct_ingreso_neto", "tipo", "orden"))
