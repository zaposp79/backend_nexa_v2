"""
tests/golden/test_pyg_v28_ingreso_indexado.py
=============================================
Golden test — PYG-001: P&G annual indexed revenue (V2-8).

PURPOSE
-------
Validate that PyGCalculator.calcular_mes applies the annual IPC/SMMLV factor
per Visión P&G!C19-C21 from Excel V2-8:

  ingreso_cadena_X *= (1 + Tasas[componente][YEAR(mes_date)])

  Cadena A → Panel!L7 = indexacion.componente_humano  (typically "IPC")
  Cadena B/C → Panel!L8 = indexacion.componente_tecnologico (typically "20% SMMLV 80% IPC")

DEAL (request/request.json — V2-8 canonical deal)
--------------------------------------------------
  servicio  : SAC
  cliente   : METROCUADRADO COM SAS (Grupo Aval)
  inicio    : 2026-07-01 (24 months)
  componente_humano : IPC
  componente_tecnologico : "20% SMMLV 80% IPC" (Panel!L8 V2-8; rate=0.06616 per year)

V2-7 OP-Componente rates used (storage/parametrization/v2-7/op.json):
  IPC[2025] = 0.0, IPC[2026] = 0.0, IPC[2027] = 0.05547729, IPC[2028] = 0.05840094

CALENDAR YEAR MAPPING (start=2026-07-01):
  Months  1-6  → 2026 → IPC=0.0    (no indexation)
  Months  7-18 → 2027 → IPC=0.05547729
  Months 19-24 → 2028 → IPC=0.05840094

EXCEL REFERENCE VALUES (Visión P&G sheet, V2-8 simulator)
-----------------------------------------------------------
  Month 1  (Jul 2026, ramp=0.90, IPC=0):
    Excel ingreso_a = 1,639,941,976.12  → backend base differs (dynamic vs HME fixed)
    Excel ingreso_b = 20,491,163.97
    Excel ingreso_c = 1,055,864,482.24  → backend ingreso_c=0 (separate CADENA_C_NULL bug)

  Month 7  (Jan 2027, ramp=1.0, IPC=0.05547729):
    Excel ingreso_a = 1,923,246,125.24
    Excel ingreso_b = 24,274,288.19

  Month 19 (Jan 2028, ramp=1.0, IPC=0.05840094):
    Excel ingreso_a = 1,928,573,482.55

  Known delta vs Excel: base ingreso_a differs ~24% (backend uses dynamic cost model
  vs Excel HME!C296 fixed base). Full base-parity is a separate blocker.

GOLDEN LOCKS
------------
  1. Mechanism ratio: ingreso_a[M7] / ingreso_a[M6] == 1 + IPC[2027] (exact)
  2. Mechanism ratio: ingreso_a[M19] / ingreso_a[M18] == (1+IPC[2028]) / (1+IPC[2027])
  3. No indexation in 2026 months: ingreso_a[M3..M6] are equal
  4. Absolute ingreso values (backend anchors, NOT Excel values)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401 — registers nexa_engine alias
from backend_nexa.tests.refactor._v27_provider import build_v27_provider
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REQUEST_PATH = _BACKEND_ROOT / "request" / "request.json"

# V2-8 OP-Componente IPC rates (storage/parametrization/v2-7/op.json)
# EXCEL V2-8: Tasas, TRM, Polizas!J7:O16 — IPC row
_IPC_2026 = 0.0
_IPC_2027 = 0.05547729
_IPC_2028 = 0.05840094


@pytest.fixture(scope="module")
def pyg_v28():
    """Engine output using V2-8 deal with V2-7 parametrization (indexed IPC rates)."""
    payload = json.loads(_REQUEST_PATH.read_text(encoding="utf-8"))
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=build_v27_provider()).calcular(solicitud)
    return resultado.pyg_por_mes


class TestPYGIndexacionMechanism:
    """
    Validate the annual IPC indexation mechanism in PyGCalculator.

    These tests validate the RATIO correctness (mechanism), not Excel parity.
    Excel absolute parity is blocked by base computation mismatch (see module docstring).
    """

    def test_no_indexation_in_2026(self, pyg_v28):
        """Months 3-6 (all 2026, IPC=0) must have identical ingreso_a (no indexation)."""
        m3, m4, m5, m6 = pyg_v28[2], pyg_v28[3], pyg_v28[4], pyg_v28[5]
        # All have rampup=1.0 and same base costs → must be equal
        assert math.isclose(m3.ingreso_bruto_a, m4.ingreso_bruto_a, rel_tol=1e-12)
        assert math.isclose(m4.ingreso_bruto_a, m5.ingreso_bruto_a, rel_tol=1e-12)
        assert math.isclose(m5.ingreso_bruto_a, m6.ingreso_bruto_a, rel_tol=1e-12)

    def test_ipc_2027_ratio_cadena_a(self, pyg_v28):
        """
        M7/M6 ingreso_a ratio must equal exactly (1 + IPC[2027]).

        EXCEL V2-8: Visión P&G!C19 row 19 — factor = (1 + Tasas[IPC][YEAR=2027])
        """
        m6 = pyg_v28[5]   # Dec 2026, IPC[2026]=0
        m7 = pyg_v28[6]   # Jan 2027, IPC[2027]=0.05547729
        ratio = m7.ingreso_bruto_a / m6.ingreso_bruto_a
        expected = 1.0 + _IPC_2027
        assert math.isclose(ratio, expected, rel_tol=1e-9), (
            f"IPC 2027 ratio wrong: {ratio:.10f} vs expected {expected:.10f}"
        )

    def test_ipc_2028_ratio_cadena_a(self, pyg_v28):
        """
        M19/M18 ingreso_a ratio must equal (1+IPC[2028]) / (1+IPC[2027]).

        EXCEL V2-8: Visión P&G!C19 — 2028 factor replaces 2027 factor
        """
        m18 = pyg_v28[17]  # Dec 2027, IPC[2027]=0.05547729
        m19 = pyg_v28[18]  # Jan 2028, IPC[2028]=0.05840094
        ratio = m19.ingreso_bruto_a / m18.ingreso_bruto_a
        expected = (1.0 + _IPC_2028) / (1.0 + _IPC_2027)
        assert math.isclose(ratio, expected, rel_tol=1e-9), (
            f"IPC 2028 ratio wrong: {ratio:.10f} vs expected {expected:.10f}"
        )

    def test_uniform_within_2027(self, pyg_v28):
        """Months 7-18 (all 2027, same steady-state costs) must have identical ingreso_a."""
        m7, m8, m13, m18 = pyg_v28[6], pyg_v28[7], pyg_v28[12], pyg_v28[17]
        assert math.isclose(m7.ingreso_bruto_a, m8.ingreso_bruto_a, rel_tol=1e-12)
        assert math.isclose(m7.ingreso_bruto_a, m13.ingreso_bruto_a, rel_tol=1e-12)
        assert math.isclose(m7.ingreso_bruto_a, m18.ingreso_bruto_a, rel_tol=1e-12)


class TestPYGAbsoluteAnchorsV28:
    """
    Backend absolute anchors for V2-8 indexed ingreso.

    Values are backend-computed (not Excel values — see base mismatch note in module docstring).
    These anchors freeze the post-PYG-001 behavior and detect future regressions.

    EXCEL V2-8 reference values are in module docstring for traceability.
    """

    # ---- Ingreso anchors (backend-computed, with IPC indexation applied) ----
    # CADENA_C_NULL fix: ingreso_c is now non-zero (tarifa_proveedor correctly mapped)
    # EXCEL V2-8: HME C296 avg = 1,822,157,751.25 (deal mismatch: backend=SAC/METROCUADRADO, Excel has different deal)
    # ANCHOR VALUES updated post BASE_INGRESO_MISMATCH fix (ingreso base now includes financial costs per cadena).
    # Formula: ingreso_cadena = (costo_opex + ica + gmf + polizas + comadm + fin) / factor_billing * rampup
    # Updated 2026-06-11: Excel inputs reconciled — Cadena B OPEX cantidad 1→10000,
    # CAPEX valor_mes 6250000→6345625, volumetria Voz2 cadena_b 1→100000, HITL deactivated.
    # Updated 2026-06-11 (OPEX_REQUEST_ALIGNMENT): no_payroll_mensual override applied to 3 Cadena A
    # profiles. OPEX TI now matches Excel exactly (308.14 COP/tx). Ingreso A increases because
    # tarifa = cost_plus(costo_total_a, margen), and costo_total_a now reflects full deal OPEX.
    # Updated 2026-06-12 (DIAS_CAPACITACION_REQUEST_ALIGNMENT): CCA!E139=F139=G139=11 → dias 10→11.
    # Ingreso A shifts +741,800 (M1) / +869,947 (M7) / +872,358 (M19) via cost→tarifa propagation.
    # Updated 2026-06-12 (CARGOS_ADICIONALES, V2-8 CCA!E26=12/G26=7.3846): el numerador del FTE de
    # soporte regular ahora es (fte+cargos_adicionales)/ratio. El costo de Cadena A sube → ingreso_a
    # (= costo/(1-margen)) sube +14.85M (M1) / +17.41M (M7) / +17.46M (M19). B/C SIN cambio (Cadena A only).
    # Updated 2026-06-12 (OP_CONFIG_P4 + REQUEST_FIX_P3): tasa_ica 0.01→0.00966 (Tasas!B37 Bogota);
    # request cargos_adicionales typed array; detalles_recursos_humanos added; fte_soporte_overrides removed.
    # All four fields shift: ingreso_a (costo_a via ICA change), ingreso_b/c (request cadena B/C alignment),
    # ingreso_total (sum). IPC ratios M7/M6 and M19/M18 remain exact (mechanism tests PASS unchanged).
    # Updated 2026-06-12 (E95_WIP_RESTORE): fte_soporte_overrides.Supervisor=9.5 restored per
    # Excel V2-8 'Condiciones Cadena A'!E95 = 9.5 (literal manual). Supervisor FTE 7.1→9.5 (+2.4).
    # Cadena A support cost increases → ingreso_a rises +12.94M (M1) / +15.18M (M7/M19). B/C unchanged.
    # Updated 2026-06-12 (CTS-001_SUPPORT_FTE): roles_operativos[].incluye_en_deal=False exclusions wired
    # (JCR/AFAC/GTR excluded from support FTE) + Director de Performance/WhatsApp=1.0 (CCA!G78).
    # Cost-plus propagation: ingreso_a shifts +3.64M (M1) / +4.27M (M7/M19). B/C unchanged.
    _M1_INGRESO_A = 1588091619.5543475
    _M1_INGRESO_B = 30391251.084335886
    # Updated 2026-06-12 (CTS-002/OPEX_FIJO_C): opex_fijo_integ now mapped from
    # costo_variable.opex_items (tipo='Fijo', 22,230,000/mo) per Excel V2-8 'Costo Cadena C'!D136.
    # Updated 2026-06-12 (CTS-002/INVERSIONES_C): inversion_anual=0 per Excel K34=SUM(K35,K36,K40)
    # — K38 (inversiones) NOT included; K38=0 (#REF!). Removes 76.32 COP/tx from cost base.
    # Updated 2026-06-12 (CTS-002/EQUIPO_C): opex_herramientas_transversal=1,159,602.60/mo from
    # recurso_humano_transversal.opex; salario_cargado=4,284,360.05/FTE per v27 parity fixture.
    # ingreso_c increases slightly: cost-plus propagation of equipo fix (2,873,347/mo net).
    _M1_INGRESO_C = 1022474865.8452781
    _M1_INGRESO_TOTAL = 2640957736.4839616

    # Updated 2026-06-11: V2-8 Panel!L8 = "20% SMMLV 80% IPC" (rate=0.06616/yr via v2-7 OP).
    # Cadena B/C now use 20% SMMLV 80% IPC indexation instead of IPC.
    # Updated 2026-06-12 (CTS-002/OPEX_FIJO_C + INVERSIONES_C + EQUIPO_C): net cost-plus propagation.
    # Updated 2026-06-12 (E95_WIP_RESTORE): Supervisor 7.1→9.5, Cadena A cost increases propagate.
    # Updated 2026-06-12 (CTS-001_SUPPORT_FTE): JCR/AFAC/GTR exclusion + Director/WhatsApp=1.0.
    _M7_INGRESO_A = 1862438487.6432598
    _M7_INGRESO_B = 36002151.395639494
    _M7_INGRESO_C = 1211246447.7440019
    _M7_INGRESO_TOTAL = 3109687086.782901

    # Updated 2026-06-12 (CTS-001_SUPPORT_FTE): JCR/AFAC/GTR exclusion + Director/WhatsApp=1.0.
    _M19_INGRESO_A = 1867597403.269382
    _M19_INGRESO_B = 36002151.395639494
    # Updated 2026-06-12 (CTS-002/CADENA_C_INDEXATION): pct_aumento_tecnologico set to 0.0 per
    # Excel V2-8 'Tasas, TRM, Polizas'!C15:G15 ('20% SMMLV 80% IPC' cumulative) = 1.0 ALL years.
    # M19 Cadena C revenue is now flat (= M7), no longer inflated by 6.62% annual technology rate.
    # Updated 2026-06-12 (CTS-002/OPEX_FIJO_C + INVERSIONES_C + EQUIPO_C): net cost-plus propagation same as M7.
    # Updated 2026-06-12 (E95_WIP_RESTORE): Supervisor 7.1→9.5, Cadena A cost increases propagate.
    _M19_INGRESO_C = 1211246447.7440019
    _M19_INGRESO_TOTAL = 3114846002.4090233

    def test_month1_ingreso_anchors(self, pyg_v28):
        """Month 1 (Jul 2026, ramp=0.90, IPC[2026]=0): no indexation applied."""
        m1 = pyg_v28[0]
        assert math.isclose(m1.rampup, 0.90, abs_tol=1e-9)
        assert math.isclose(m1.ingreso_bruto_a, self._M1_INGRESO_A, rel_tol=1e-9)
        assert math.isclose(m1.ingreso_bruto_b, self._M1_INGRESO_B, rel_tol=1e-9)
        assert math.isclose(m1.ingreso_bruto_c, self._M1_INGRESO_C, rel_tol=1e-9)
        assert math.isclose(m1.ingreso_bruto, self._M1_INGRESO_TOTAL, rel_tol=1e-9)

    def test_month7_ingreso_anchors(self, pyg_v28):
        """Month 7 (Jan 2027, ramp=1.0): IPC[2027]=0.05547729 applied to ingreso."""
        m7 = pyg_v28[6]
        assert math.isclose(m7.rampup, 1.0, abs_tol=1e-9)
        assert math.isclose(m7.ingreso_bruto_a, self._M7_INGRESO_A, rel_tol=1e-9)
        assert math.isclose(m7.ingreso_bruto_b, self._M7_INGRESO_B, rel_tol=1e-9)
        assert math.isclose(m7.ingreso_bruto_c, self._M7_INGRESO_C, rel_tol=1e-9)
        assert math.isclose(m7.ingreso_bruto, self._M7_INGRESO_TOTAL, rel_tol=1e-9)

    def test_month19_ingreso_anchors(self, pyg_v28):
        """Month 19 (Jan 2028, ramp=1.0): IPC[2028]=0.05840094 applied to ingreso."""
        m19 = pyg_v28[18]
        assert math.isclose(m19.rampup, 1.0, abs_tol=1e-9)
        assert math.isclose(m19.ingreso_bruto_a, self._M19_INGRESO_A, rel_tol=1e-9)
        assert math.isclose(m19.ingreso_bruto_b, self._M19_INGRESO_B, rel_tol=1e-9)
        assert math.isclose(m19.ingreso_bruto_c, self._M19_INGRESO_C, rel_tol=1e-9)
        assert math.isclose(m19.ingreso_bruto, self._M19_INGRESO_TOTAL, rel_tol=1e-9)
