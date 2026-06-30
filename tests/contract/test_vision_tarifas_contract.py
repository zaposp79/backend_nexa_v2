"""
tests/contract/test_vision_tarifas_contract.py
===============================================
Contract tests for VisionTarifas decomposition (VT-1/2/3).

Validates:
  - Per-channel cost decomposition (payroll + no_payroll sub-components)
  - Channel totals consistency (costo_cadena_a_ch = payroll_ch + no_payroll_ch)
  - ResultadoVisionTarifas totals (sum of channels = totals)
  - Factor billing formula: (1-margen) * (1-op_cont) [* (1-com_cont)]
  - Ingreso = costo / factor_billing
  - Tarifa FTE = facturacion / FTE
  - All 17 decomposition fields populated for each channel

Golden values from bancamia canonical run (26 FTE, 3 channels, 12 months).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# WAVE 7: marcado como legacy pre-V2-7 — depende de fixtures Excel V2-4 obsoletas.
# Ver docs/v27/WAVE7_TRIAGE.md (categoría OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.models.snapshot import (
    PanelSummary,
    ParametrizationSnapshot,
    SimulationSnapshot,
)
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
    configuracion_comercial_to_dict,
)
from nexa_engine.modules.shared.models import ResultadoVisionTarifas, TarifaCanal

CASE_PATH = PROJECT_ROOT / "backend_nexa/test_cases/excel_v24_canonical_bancamia.json"


@pytest.fixture(scope="module")
def resultado():
    ui = UserInputLoader().cargar(CASE_PATH)
    solic = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(solic)


@pytest.fixture(scope="module")
def vt(resultado) -> ResultadoVisionTarifas:
    return resultado.vision_tarifas


@pytest.fixture(scope="module")
def canales(vt) -> list:
    return vt.canales


# ── Structure ────────────────────────────────────────────────

class TestVisionTarifasStructure:
    def test_has_canales(self, vt):
        assert vt.canales is not None
        assert len(vt.canales) == 3

    def test_canal_names(self, canales):
        names = [c.nombre_canal for c in canales]
        assert "Inbound 10" in names
        assert "Inbound 15 personas" in names
        assert "Inbound 20 personas" in names

    def test_all_decomposition_fields_present(self, canales):
        """Every TarifaCanal must have all 17 decomposition fields."""
        decomp_fields = [
            "payroll_ch", "no_payroll_ch", "costo_cadena_a_ch",
            "nomina_loaded_ch", "salario_fijo_ch", "salario_variable_ch",
            "capacitacion_inicial_ch", "capacitacion_rotacion_ch", "examenes_ch",
            "estudios_seguridad_ch",
            "opex_it_ch", "inversiones_ch", "costos_fijos_ch",
            "cadena_b_atribuible", "financieros_atribuible",
            "nomina_agente_basico",
        ]
        for canal in canales:
            for field in decomp_fields:
                assert hasattr(canal, field), f"{canal.nombre_canal} missing {field}"

    def test_totals_fields_present(self, vt):
        for field in ["costo_cadena_a_total", "costo_cadena_b_total",
                      "costo_cadena_c_total", "costo_total", "ingreso_mensual"]:
            assert hasattr(vt, field)


# ── Per-channel consistency ──────────────────────────────────

class TestChannelConsistency:
    def test_costo_a_equals_payroll_plus_no_payroll(self, canales):
        for c in canales:
            assert c.costo_cadena_a_ch == pytest.approx(
                c.payroll_ch + c.no_payroll_ch, rel=1e-6
            ), f"{c.nombre_canal}: costo_a != payroll + no_payroll"

    def test_payroll_sub_components_sum(self, canales):
        """Payroll sub-components should roughly sum to payroll_ch."""
        for c in canales:
            if c.payroll_ch == 0:
                continue
            sub = (c.nomina_loaded_ch + c.capacitacion_inicial_ch + c.capacitacion_rotacion_ch
                   + c.examenes_ch + c.estudios_seguridad_ch)
            # Allow some tolerance — nomina_loaded includes salario_fijo + variable
            assert sub == pytest.approx(c.payroll_ch, rel=0.02), (
                f"{c.nombre_canal}: payroll subs {sub:.0f} != payroll {c.payroll_ch:.0f}"
            )

    def test_costo_atribuible_equals_op_plus_fin_plus_b(self, canales):
        for c in canales:
            expected = c.costo_cadena_a_ch + c.financieros_atribuible + c.cadena_b_atribuible
            assert c.costo_atribuible == pytest.approx(expected, rel=1e-6), (
                f"{c.nombre_canal}: costo_atribuible mismatch"
            )

    def test_ingreso_positive(self, canales):
        for c in canales:
            assert c.ingreso_bruto > 0, f"{c.nombre_canal} has zero ingreso"

    def test_tarifa_fte_equals_facturacion_over_fte(self, canales):
        for c in canales:
            if c.fte > 0:
                expected = c.facturacion / c.fte
                assert c.tarifa_fijo_fte == pytest.approx(expected, rel=1e-6)

    def test_facturacion_equals_ingreso_times_pct_fijo(self, canales):
        for c in canales:
            expected = c.ingreso_bruto * c.pct_fijo
            assert c.facturacion == pytest.approx(expected, rel=1e-6)

    def test_pct_fijo_plus_variable_equals_one(self, canales):
        for c in canales:
            assert c.pct_fijo + c.pct_variable == pytest.approx(1.0, abs=1e-9)

    def test_nomina_agente_positive(self, canales):
        """Each channel should have a non-zero agent payroll."""
        for c in canales:
            assert c.nomina_agente_basico > 0, f"{c.nombre_canal} missing nomina_agente"


# ── Totals consistency ───────────────────────────────────────

class TestTotalsConsistency:
    def test_costo_a_total_is_sum_of_channels(self, vt, canales):
        expected = sum(c.costo_cadena_a_ch for c in canales)
        assert vt.costo_cadena_a_total == pytest.approx(expected, rel=1e-6)

    def test_costo_total_is_sum_of_chains(self, vt):
        expected = vt.costo_cadena_a_total + vt.costo_cadena_b_total + vt.costo_cadena_c_total
        assert vt.costo_total == pytest.approx(expected, rel=1e-6)

    def test_ingreso_from_factor_billing(self, vt, resultado):
        """ingreso_mensual = costo_total / factor_billing."""
        panel = resultado.panel
        factor = (1 - panel.margen) * (1 - panel.op_cont)
        if panel.com_cont > 0:
            factor *= (1 - panel.com_cont)
        expected = vt.costo_total / factor if factor > 0 else 0
        assert vt.ingreso_mensual == pytest.approx(expected, rel=1e-6)


# ── Golden values (bancamia canonical) ───────────────────────

class TestGoldenValues:
    """Snapshot values from current engine run — guards against regressions."""

    def test_channel_count(self, canales):
        assert len(canales) == 3

    def test_total_costo_a(self, vt):
        assert vt.costo_cadena_a_total == pytest.approx(319_621_918, rel=0.001)

    def test_total_costo_b(self, vt):
        assert vt.costo_cadena_b_total == pytest.approx(350_863_435, rel=0.001)

    def test_total_ingreso(self, vt):
        assert vt.ingreso_mensual == pytest.approx(789_941_955, rel=0.001)

    def test_inbound10_tarifa_fte(self, canales):
        c = next(c for c in canales if "10" in c.nombre_canal)
        assert c.tarifa_fijo_fte == pytest.approx(31_233_114, rel=0.001)

    def test_inbound10_payroll(self, canales):
        c = next(c for c in canales if "10" in c.nombre_canal)
        assert c.payroll_ch == pytest.approx(30_017_217, rel=0.001)


class TestSerializationGuardrails:
    def test_pricing_result_serialization_preserves_vision_tarifas_canales(self, resultado):
        serialized = pricing_result_to_dict(resultado, result_id="sim-vt-contract")

        assert "vision_tarifas" in serialized
        assert serialized["vision_tarifas"] is not None
        assert len(serialized["vision_tarifas"]["canales"]) == len(resultado.vision_tarifas.canales)

        canal = serialized["vision_tarifas"]["canales"][0]
        for field in (
            "nombre_canal",
            "modelo_cobro",
            "pct_fijo",
            "pct_variable",
            "tarifa_fijo_fte",
            "tarifa_variable",
        ):
            assert field in canal, f"Falta campo '{field}' en vision_tarifas.canales[0]"

    def test_simulation_snapshot_round_trip_preserves_vision_tarifas(self, resultado):
        serialized = pricing_result_to_dict(resultado, result_id="sim-vt-contract")
        expected = serialized["vision_tarifas"]

        snapshot = SimulationSnapshot(
            simulation_id="sim-vt-contract",
            created_at="2026-06-15T00:00:00+00:00",
            raw_input={"source": "unit-test"},
            normalized_input={"source": "unit-test"},
            normalization_log={"defaults_applied": [], "warnings": [], "errors": []},
            parametrization=ParametrizationSnapshot(
                parametrization_id="param-001",
                captured_at="2026-06-15T00:00:00+00:00",
                smmlv=1.0,
                auxilio_transporte=1.0,
                linea_negocio=resultado.panel.linea_negocio,
                ciudad=resultado.panel.ciudad,
            ),
            data_provenance={},
            pricing_result=serialized,
            panel_summary=PanelSummary(
                simulation_id="sim-vt-contract",
                cliente=resultado.panel.cliente,
                linea_negocio=resultado.panel.linea_negocio,
                ciudad=resultado.panel.ciudad,
                meses_contrato=resultado.panel.meses_contrato,
            ),
        )

        restored = SimulationSnapshot.from_dict(json.loads(json.dumps(snapshot.as_dict())))

        assert restored.pricing_result["vision_tarifas"] == expected

    def test_configuracion_comercial_reads_persisted_tarifa_fijo_fte(self, resultado):
        canal_principal = max(resultado.vision_tarifas.canales, key=lambda c: c.facturacion)
        sentinel = canal_principal.tarifa_fijo_fte + 123.45
        canal_principal.tarifa_fijo_fte = sentinel

        config = configuracion_comercial_to_dict(resultado)

        assert config["tarifa_fija"] == pytest.approx(sentinel)
        assert config["tarifa_fija"] == pytest.approx(canal_principal.tarifa_fijo_fte)
