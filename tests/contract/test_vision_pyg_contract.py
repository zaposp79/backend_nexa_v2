"""
tests/contract/test_vision_pyg_contract.py
==========================================
Contract tests for VisionPyG structured model (PYG-2/3/4).

Validates:
  - VisionPyG structure: filas count, sections, row types
  - Acumulados in PyGMensual: monotonic, last == KPIs totals
  - ResumenEjecutivoPyG consistency with KPIs
  - Row values consistency (acumulado = sum of valores)
  - Promedio = avg over active months
  - Serializer parity (all fields present in JSON output)

Golden values from bancamia canonical run (26 FTE, 3 channels, 12 months).
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pytest

# WAVE 7: marcado como legacy pre-V2-7 — depende de excel_v24_canonical_bancamia.json
# en ruta inexistente. Ver docs/v27/WAVE7_TRIAGE.md (OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict

CASE_PATH = PROJECT_ROOT / "backend_nexa/test_cases/excel_v24_canonical_bancamia.json"


@pytest.fixture(scope="module")
def resultado():
    ui = UserInputLoader().cargar(CASE_PATH)
    solic = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(solic)


@pytest.fixture(scope="module")
def vp(resultado):
    return resultado.vision_pyg


@pytest.fixture(scope="module")
def pyg_por_mes(resultado):
    return resultado.pyg_por_mes


@pytest.fixture(scope="module")
def kpis(resultado):
    return resultado.kpis


# ── VisionPyG Structure ─────────────────────────────────────

class TestVisionPyGStructure:
    def test_has_28_rows(self, vp):
        assert len(vp.filas) == 29

    def test_meses_contrato(self, vp):
        assert vp.meses_contrato == 12

    def test_meses_activos(self, vp):
        assert vp.meses_activos == 12

    def test_has_resumen(self, vp):
        assert vp.resumen is not None

    def test_sections_present(self, vp):
        secciones = {f.seccion for f in vp.filas}
        assert secciones == {"ingresos", "costos_op", "costos_fin", "resultados", "operativo"}

    def test_row_types(self, vp):
        tipos = {f.tipo for f in vp.filas}
        assert "linea" in tipos
        assert "subtotal" in tipos
        assert "total" in tipos
        assert "porcentaje" in tipos

    def test_each_row_has_12_values(self, vp):
        for f in vp.filas:
            assert len(f.valores) == 12, f"{f.key} has {len(f.valores)} values"

    def test_unique_keys(self, vp):
        keys = [f.key for f in vp.filas]
        assert len(keys) == len(set(keys)), "Duplicate row keys"


# ── Row values consistency ───────────────────────────────────

class TestRowConsistency:
    def test_acumulado_equals_sum_of_valores(self, vp):
        for f in vp.filas:
            if f.tipo == "porcentaje":
                continue  # percentages use avg, not sum
            assert f.acumulado == pytest.approx(sum(f.valores), rel=1e-6), (
                f"{f.key}: acumulado {f.acumulado} != sum {sum(f.valores)}"
            )

    def test_promedio_equals_avg_active_months(self, vp):
        for f in vp.filas:
            if vp.meses_activos == 0:
                continue
            # For non-percentage rows, promedio = sum(active) / n_active
            # All 12 months active in this case, so promedio = acum / 12
            if f.tipo != "porcentaje":
                expected = f.acumulado / vp.meses_activos
                assert f.promedio == pytest.approx(expected, rel=1e-6), (
                    f"{f.key}: promedio mismatch"
                )

    def test_ingreso_neto_row_matches_pyg(self, vp, pyg_por_mes):
        row = next(f for f in vp.filas if f.key == "ingreso_neto")
        for i, m in enumerate(pyg_por_mes):
            assert row.valores[i] == pytest.approx(m.ingreso_neto, rel=1e-6)

    def test_costo_total_row_matches_pyg(self, vp, pyg_por_mes):
        row = next(f for f in vp.filas if f.key == "costo_total")
        for i, m in enumerate(pyg_por_mes):
            assert row.valores[i] == pytest.approx(m.costo_total, rel=1e-6)


# ── ResumenEjecutivoPyG ─────────────────────────────────────

class TestResumenEjecutivo:
    def test_valor_total_deal_matches_kpis(self, vp, kpis):
        assert vp.resumen.valor_total_deal == pytest.approx(kpis.valor_total_deal, rel=1e-6)

    def test_ingreso_neto_total_matches_kpis(self, vp, kpis):
        assert vp.resumen.ingreso_neto_total == pytest.approx(kpis.ingreso_neto_total, rel=1e-6)

    def test_costo_total_contrato_matches_kpis(self, vp, kpis):
        assert vp.resumen.costo_total_contrato == pytest.approx(kpis.costo_total_contrato, rel=1e-6)

    def test_contribucion_total_matches_kpis(self, vp, kpis):
        assert vp.resumen.contribucion_total == pytest.approx(kpis.contribucion_total, rel=1e-6)

    def test_meses(self, vp):
        assert vp.resumen.meses_contrato == 12
        assert vp.resumen.meses_activos == 12


# ── Acumulados in PyGMensual ─────────────────────────────────

class TestAcumulados:
    def test_acumulados_monotonic(self, pyg_por_mes):
        """Acumulados must be non-decreasing (all values positive in this case)."""
        for i in range(1, len(pyg_por_mes)):
            prev, curr = pyg_por_mes[i - 1], pyg_por_mes[i]
            assert curr.acum_ingreso_bruto >= prev.acum_ingreso_bruto
            assert curr.acum_ingreso_neto >= prev.acum_ingreso_neto
            assert curr.acum_costo_total >= prev.acum_costo_total

    def test_last_acum_equals_kpis_totals(self, pyg_por_mes, kpis):
        last = pyg_por_mes[-1]
        assert last.acum_ingreso_neto == pytest.approx(kpis.ingreso_neto_total, rel=1e-6)
        assert last.acum_costo_total == pytest.approx(kpis.costo_total_contrato, rel=1e-6)
        assert last.acum_contribucion == pytest.approx(kpis.contribucion_total, rel=1e-6)

    def test_first_month_acum_equals_value(self, pyg_por_mes):
        m = pyg_por_mes[0]
        assert m.acum_ingreso_bruto == pytest.approx(m.ingreso_bruto, rel=1e-6)
        assert m.acum_costo_total == pytest.approx(m.costo_total, rel=1e-6)


# ── Serializer parity ────────────────────────────────────────

class TestSerializerParity:
    def test_vision_pyg_in_serialized_output(self, resultado):
        data = pricing_result_to_dict(resultado, result_id="test-uuid")
        assert "vision_pyg" in data
        vp = data["vision_pyg"]
        assert vp is not None
        assert "resumen" in vp
        assert "filas" in vp
        assert len(vp["filas"]) == 29

    def test_serialized_row_has_all_fields(self, resultado):
        data = pricing_result_to_dict(resultado, result_id="test-uuid")
        row = data["vision_pyg"]["filas"][0]
        for field in ["key", "label", "seccion", "tipo", "signo", "valores", "acumulado", "promedio"]:
            assert field in row, f"Missing {field} in serialized row"

    def test_pyg_por_mes_has_acumulados(self, resultado):
        data = pricing_result_to_dict(resultado, result_id="test-uuid")
        last = data["pyg_por_mes"][-1]
        assert "acum_ingreso_bruto" in last
        assert "acum_ingreso_neto" in last
        assert "acum_costo_total" in last
        assert "acum_contribucion" in last

    def test_pyg_por_mes_has_computed_properties(self, resultado):
        data = pricing_result_to_dict(resultado, result_id="test-uuid")
        m = data["pyg_por_mes"][0]
        for prop in ["ingreso_bruto", "ingreso_neto", "costo_total",
                     "contribucion", "utilidad_neta", "pct_contribucion"]:
            assert prop in m, f"Missing @property {prop} in serialized PyGMensual"
            assert m[prop] != 0, f"@property {prop} is zero — may not be serialized"

    def test_vision_tarifas_has_decomposition(self, resultado):
        data = pricing_result_to_dict(resultado, result_id="test-uuid")
        vt = data["vision_tarifas"]
        canal = vt["canales"][0]
        for field in ["payroll_ch", "no_payroll_ch", "costo_cadena_a_ch",
                      "cadena_b_atribuible", "financieros_atribuible"]:
            assert field in canal, f"Missing {field} in serialized TarifaCanal"


# ── Golden values ────────────────────────────────────────────

class TestGoldenValues:
    def test_resumen_valor_total_deal(self, vp):
        assert vp.resumen.valor_total_deal == pytest.approx(9_258_666_055, rel=0.001)

    def test_resumen_contribucion(self, vp):
        assert vp.resumen.contribucion_total == pytest.approx(1_096_939_568, rel=0.001)

    def test_last_acum_ingreso_bruto(self, pyg_por_mes):
        assert pyg_por_mes[-1].acum_ingreso_bruto == pytest.approx(9_077_123_584, rel=0.001)

    def test_last_acum_ingreso_neto(self, pyg_por_mes):
        assert pyg_por_mes[-1].acum_ingreso_neto == pytest.approx(9_258_666_055, rel=0.001)
