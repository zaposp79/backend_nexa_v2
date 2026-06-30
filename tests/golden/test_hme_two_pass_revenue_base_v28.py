"""
tests/golden/test_hme_two_pass_revenue_base_v28.py
===================================================
Golden test — BASE_INGRESO_MISMATCH fix (V2-8).

PURPOSE
-------
Validate that PyGCalculator now uses costo_total_cadena (opex + financieros)
as the ingreso base, replicating the HME computation chain:

  HME!C258 = Payroll + NoPayroll + ICA + GMF + ComAdm + Pólizas + Financiación
  HME!C296 = C258 / (1 - margen_a)

FORMULA CHAIN
-------------
  costo_total_cadena_a = costo_opex_a + ica_a + gmf_a + polizas_a + comadm_a + fin_a
  ingreso_cadena_a     = costo_total_cadena_a / factor_billing_a * rampup

KNOWN DEAL MISMATCH
-------------------
Absolute values still differ from Excel HME because the Excel workbook has
a different deal cached (different FTE/volumes). INPUT_DEAL_MISMATCH is a
separate blocker. This test validates:
  1. The structural formula change is in place
  2. The IPC indexation mechanism still holds (ratio-based)
  3. The per-cadena financial cost breakdown is correctly propagated

GOLDEN LOCKS
------------
  1. costo_total_cadena_a > costos_operativos.costo_a (financial items included)
  2. IPC ratio M7/M3 == 1 + IPC_2027 (mechanism unchanged)
  3. ingreso_a = costo_total_a / (1-margen) when op_cont=com_cont=markup=descuento=0
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401
from backend_nexa.tests.refactor._v27_provider import build_v27_provider
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REQUEST_PATH = _BACKEND_ROOT / "request" / "request.json"

_IPC_2027 = 0.05547729
_MARGEN_A = 0.21  # Panel!C63 for SAC/METROCUADRADO deal


@pytest.fixture(scope="module")
def pyg_result():
    """Engine output using V2-8 deal with V2-7 parametrization."""
    payload = json.loads(_REQUEST_PATH.read_text(encoding="utf-8"))
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=build_v27_provider()).calcular(solicitud)
    return resultado


class TestHMETwoPassRevenueBaseV28:
    """
    Validate the HME two-pass ingreso computation: ingreso = costo_total / factor_billing.

    EXCEL V2-8: HME!C258 = SUM(payroll, nopayroll, ICA, GMF, ComAdm, Pólizas, Fin)
                HME!C296 = C258 / (1 - margen_a)
    """

    def test_ingreso_a_includes_financial_costs(self, pyg_result):
        """
        Validate structural change: ingreso_a now uses costo_total_cadena
        (opex + financieros) as base, not just costo_opex.

        With the fix, ingreso_a > (payroll_a + no_payroll_a) / (1 - margen_a).
        The difference = contribution of financial items to the ingreso base.
        """
        m3 = pyg_result.pyg_por_mes[2]  # ramp=1, IPC=0 → clean baseline month
        costo_opex_a = m3.payroll_a + m3.no_payroll_a

        # ingreso without financial items (V2-7 formula)
        ingreso_opex_only = costo_opex_a / (1 - _MARGEN_A)

        # ingreso with financial items (V2-8 formula)
        ingreso_actual = m3.ingreso_bruto_a

        # The actual ingreso should be larger than the opex-only ingreso
        # because financial items (ICA, GMF) are included in the base
        assert ingreso_actual > ingreso_opex_only, (
            f"ingreso_a should include financial items: "
            f"ingreso_actual={ingreso_actual:,.2f} <= ingreso_opex_only={ingreso_opex_only:,.2f}"
        )

    def test_ipc_ratio_mechanism_unchanged(self, pyg_result):
        """
        IPC indexation ratio M7/M3 == 1 + IPC_2027 still holds after the fix.
        This is the MATCH verified in the parity runner.
        """
        pyg = pyg_result.pyg_por_mes
        m3 = pyg[2]
        m7 = pyg[6]
        ratio = m7.ingreso_bruto_a / m3.ingreso_bruto_a
        expected = 1.0 + _IPC_2027
        assert math.isclose(ratio, expected, rel_tol=1e-9), (
            f"IPC 2027 ratio wrong: {ratio:.10f} vs {expected:.10f}"
        )

    def test_m3_m6_no_indexation(self, pyg_result):
        """M3 through M6 (year 2026) have no IPC indexation → same ingreso_a."""
        pyg = pyg_result.pyg_por_mes
        m3 = pyg[2]
        for i in [3, 4, 5]:  # M4, M5, M6
            assert math.isclose(
                pyg[i].ingreso_bruto_a, m3.ingreso_bruto_a, rel_tol=1e-12
            ), f"M{i+1} ingreso_a differs from M3 (expected no IPC in 2026)"

    def test_ingreso_b_and_c_positive(self, pyg_result):
        """Ingreso B and C are non-zero when cadenas are active."""
        m3 = pyg_result.pyg_por_mes[2]
        assert m3.ingreso_bruto_b > 0, "ingreso_b should be positive"
        assert m3.ingreso_bruto_c > 0, "ingreso_c should be positive"

    def test_financial_costs_contribute_to_ingreso(self, pyg_result):
        """
        Validate that per-cadena financial costs (ica_a, gmf_a) contribute
        to ingreso_a. At M3 (ramp=1, IPC=0):
          ingreso_a ≈ (costo_opex_a + ica_a + gmf_a) / (1-margen_a)
        """
        m3 = pyg_result.pyg_por_mes[2]
        costo_opex_a = m3.payroll_a + m3.no_payroll_a

        # Reconstruct approximate costo_total including only ICA+GMF (most significant)
        approx_costo_total = costo_opex_a + m3.ica_a + m3.gmf_a
        approx_ingreso = approx_costo_total / (1 - _MARGEN_A)

        # ingreso_actual should be close to this approximation (within polizas+comadm margin)
        rel_diff = abs(m3.ingreso_bruto_a - approx_ingreso) / m3.ingreso_bruto_a
        assert rel_diff < 0.05, (
            f"ingreso_a deviates more than 5% from (opex+ica+gmf)/(1-margen): "
            f"rel_diff={rel_diff:.4f}"
        )
