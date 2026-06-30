"""
tests/parity/test_vision_gap_closure.py
========================================
Validation of the V2-7 GAP closures (Phase 2). Each test ties a backend value
to a workbook source. No fabricated data — values either match Excel or the
field is sourced from an existing calculator output.

Closed gaps:
  GAP-PYG-HIER-1  payroll / no-payroll sub-components (Cadena A) in VisionPyG
  GAP-PYG-HIER-2  Cadena B sub-components (partial — OPEX Variable UNDETERMINED)
  GAP-PYG-HIER-3  Cadena C sub-components
  GAP-PYG-HIER-4  "Contribución por Puesto" (= Contribución / Estaciones)
  GAP-CTS-HIER-1  "Crucero" in DesgloseCTSCadenaA  (premise "always 0" corrected)
  GAP-CTS-ACT-1   canal_view_habilitado flag (service == "SAC")
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401
from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

FIXTURES = Path(__file__).parent / "fixtures"
REAL_REQUEST = FIXTURES / "excel_v2_7_real_request.json"


@pytest.fixture(scope="module", autouse=True)
def v27_parametrization_gap():
    import nexa_engine.modules.parametrizacion.services.provider as _prov
    _prov._PROVIDER_INSTANCE = None
    storage = PROJECT_ROOT / "backend_nexa" / "storage" / "parametrization"
    originals = {}
    for mod in ("hr", "op"):
        vf = storage / mod / "versions.json"
        originals[mod] = vf.read_text()
        v = json.loads(originals[mod])
        for e in v:
            e["is_active"] = False
        for e in v:
            if e.get("version_id") == "v2-7":
                e["is_active"] = True
        vf.write_text(json.dumps(v, indent=2))
    _prov._PROVIDER_INSTANCE = None
    yield
    for mod, saved in originals.items():
        (storage / mod / "versions.json").write_text(saved)
    _prov._PROVIDER_INSTANCE = None


@pytest.fixture(scope="module")
def result():
    import nexa_engine.modules.parametrizacion.services.provider as _prov
    _prov._PROVIDER_INSTANCE = None
    ui = UserInputLoader().cargar(REAL_REQUEST)
    ctx = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(ctx)


def _row(vp, key):
    return next((f for f in vp.filas if f.key == key), None)


# ── GAP-PYG-HIER-1: Cadena A payroll/no-payroll sub-components ─────────────────

class TestGapPygHier1:
    def test_payroll_detail_rows_present(self, result):
        det = result.vision_pyg.filas_detalle
        keys = {d.key for d in det if d.parent == "payroll_a"}
        assert keys == {
            "salario_fijo", "salario_variable", "cap_inicial", "cap_rotacion",
            "examenes", "estudios_seguridad", "crucero",
        }

    def test_no_payroll_detail_rows_present(self, result):
        det = result.vision_pyg.filas_detalle
        keys = {d.key for d in det if d.parent == "no_payroll_a"}
        assert keys == {"opex_fijo_a", "inversiones_a", "costos_fijos_a"}

    def test_payroll_detail_sums_to_parent(self, result):
        """Sub-components must reconcile exactly to the payroll_a summary row, per month."""
        vp = result.vision_pyg
        parent = _row(vp, "payroll_a")
        det = [d for d in vp.filas_detalle if d.parent == "payroll_a"]
        for i in range(vp.meses_contrato):
            s = sum(d.valores[i] for d in det)
            assert abs(parent.valores[i] - s) < 1.0, f"mes {i+1}: {parent.valores[i]} != {s}"

    def test_no_payroll_detail_sums_to_parent(self, result):
        vp = result.vision_pyg
        parent = _row(vp, "no_payroll_a")
        det = [d for d in vp.filas_detalle if d.parent == "no_payroll_a"]
        for i in range(vp.meses_contrato):
            s = sum(d.valores[i] for d in det)
            assert abs(parent.valores[i] - s) < 1.0


# ── GAP-PYG-HIER-2: Cadena B sub-components ───────────────────────────────────

class TestGapPygHier2:
    def test_cadena_b_detail_rows(self, result):
        det = result.vision_pyg.filas_detalle
        keys = {d.key for d in det if d.parent == "costo_b"}
        # 6 derivable; OPEX Variable (Excel row 52) intentionally omitted (UNDETERMINED)
        assert keys == {
            "opex_fijo_b", "inversiones_b", "sm_b",
            "tarifa_canal_b", "tasa_escalamiento_b", "hitl_b",
        }

    def test_opex_variable_b_not_fabricated(self, result):
        """ResultadoCadenaB has no opex_variable field → must NOT emit a fake row."""
        det = result.vision_pyg.filas_detalle
        assert not any(d.key == "opex_variable_b" for d in det)


# ── GAP-PYG-HIER-3: Cadena C sub-components ───────────────────────────────────

class TestGapPygHier3:
    def test_cadena_c_detail_rows(self, result):
        det = result.vision_pyg.filas_detalle
        keys = {d.key for d in det if d.parent == "costo_c"}
        assert keys == {
            "tarifa_proveedor_c", "opex_fijo_integ_c", "inversiones_integ_c",
            "equipo_integ_c", "tasa_escalamiento_c", "opex_var_integ_c", "hitl_c",
        }


# ── GAP-PYG-HIER-4: Contribución por Puesto ───────────────────────────────────

class TestGapPygHier4:
    def test_row_present(self, result):
        assert _row(result.vision_pyg, "contribucion_por_puesto") is not None

    def test_estaciones_matches_workbook(self, result):
        """Workbook C14 (Estaciones de Trabajo) = 24 for the real V2-7 request.
        estaciones = Σ(fte × pct_presencia) over non-soporte profiles."""
        vp = result.vision_pyg
        cpp = _row(vp, "contribucion_por_puesto")
        contrib = _row(vp, "contribucion")
        idx = next((i for i, v in enumerate(cpp.valores) if v > 0), None)
        assert idx is not None, "no active month with contribución > 0"
        estaciones = contrib.valores[idx] / cpp.valores[idx]
        assert abs(estaciones - 24.0) < 0.01, f"estaciones={estaciones} != 24 (workbook C14)"


# ── GAP-CTS-HIER-1: Crucero in DesgloseCTSCadenaA ─────────────────────────────

class TestGapCtsHier1:
    def test_crucero_field_present_and_nonzero(self, result):
        """Phase-1 doc claimed 'always 0' — workbook service-level row 43 = 11.17."""
        da = result.cost_to_serve.desglose_a
        assert hasattr(da, "crucero")
        assert abs(da.crucero - 11.1687) < 0.5, f"crucero={da.crucero} != ~11.17 (workbook)"

    def test_payroll_subcomponents_reconcile_with_crucero(self, result):
        """With crucero included, payroll sub-fields sum to the nomina aggregate."""
        da = result.cost_to_serve.desglose_a
        s = (da.salario_fijo + da.salario_variable + da.capacitacion_inicial + da.capacitacion_rotacion
             + da.examenes + da.estudios_seguridad + da.crucero)
        assert abs(da.nomina - s) < 0.5, f"nomina={da.nomina} != sum(sub)={s}"


# ── GAP-CTS-ACT-1: canal_view_habilitado flag ────────────────────────────────

class TestGapCtsAct1:
    def test_flag_false_for_non_sac(self, result):
        """Real request service = 'Captura de Datos' ≠ SAC → flag False."""
        assert result.cost_to_serve.canal_view_habilitado is False

    def test_flag_true_for_sac(self, tmp_path):
        """When service == 'SAC', flag is True (Excel C58/C87 condition)."""
        import nexa_engine.modules.parametrizacion.services.provider as _prov
        _prov._PROVIDER_INSTANCE = None
        req = json.loads(REAL_REQUEST.read_text())
        # Locate and override the service/linea_negocio field
        req = copy.deepcopy(req)
        _set_service_sac(req)
        p = tmp_path / "sac.json"
        p.write_text(json.dumps(req, default=str))
        ui = UserInputLoader().cargar(p)
        ctx = SimulationContextBuilder().construir(ui)
        ctx.panel.linea_negocio = "SAC"  # ensure panel reflects SAC
        r = NexaPricingEngine().calcular(ctx)
        assert r.cost_to_serve.canal_view_habilitado is True

    def test_flag_does_not_suppress_data(self, result):
        """Excel computes channel data regardless of the flag — backend must still
        emit the desglose (no node-hiding). desglose_a is always populated."""
        assert result.cost_to_serve.desglose_a.nomina > 0


def _set_service_sac(req: dict) -> None:
    """Best-effort: set the service field to 'SAC' wherever it lives in the request."""
    for path in (("panel_de_control", "linea_negocio"),
                 ("user_input", "datos_operativos", "servicio"),
                 ("datos_operativos", "servicio")):
        node = req
        ok = True
        for k in path[:-1]:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok and isinstance(node, dict) and path[-1] in node:
            node[path[-1]] = "SAC"
