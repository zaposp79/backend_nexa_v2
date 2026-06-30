"""
tests/parity/test_servicio_driven_behavior.py
==============================================
GAP-CTS-ACT-1 (re-opened) — service-driven behavior model, derived from Excel V2-7.

Workbook-sourced facts under test:
  - Service catalog = Listas Desplegables!A4:A9 (6 services).
  - CTS!C58/C87 = IF(servicio="SAC", ...) → per-channel header gate, SAC only.
  - The gate does NOT suppress data: channel/desglose computes for every service.
  - Active chains (Panel!M17/M30) and channels (volume>0) are NOT service-driven.
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
from nexa_engine.modules.vision_cost_to_serve.helpers.servicio_catalogo import (
    SERVICIOS_V27,
    canal_detail_habilitado,
    servicio_behavior,
)
from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

REAL_REQUEST = Path(__file__).parent / "fixtures" / "excel_v2_7_real_request.json"


# ── Catalog (single source of truth = Listas Desplegables!A4:A9) ──────────────

class TestServicioCatalogo:
    def test_catalog_matches_workbook_dropdown(self):
        """Exact match to Listas Desplegables!A4:A9 (order-independent)."""
        assert set(SERVICIOS_V27) == {
            "Cobranzas", "SAC", "Ventas multicanal",
            "SACO", "Plataformas", "Captura de Datos",
        }

    @pytest.mark.parametrize("servicio", SERVICIOS_V27)
    def test_known_services_flagged_conocido(self, servicio):
        assert servicio_behavior(servicio).es_servicio_conocido is True

    def test_unknown_service_not_fabricated(self):
        """An unknown service is flagged, not silently defaulted."""
        b = servicio_behavior("NoExiste")
        assert b.es_servicio_conocido is False
        assert b.canal_detail_habilitado is False


# ── Per-channel detail gate (CTS!C58/C87 = ="SAC") ────────────────────────────

class TestCanalDetailGate:
    @pytest.mark.parametrize("servicio", SERVICIOS_V27)
    def test_gate_true_only_for_sac(self, servicio):
        expected = (servicio == "SAC")
        assert canal_detail_habilitado(servicio) is expected, (
            f"{servicio}: gate should be {expected} (Excel C58/C87 == 'SAC')"
        )

    def test_gate_blank_service(self):
        assert canal_detail_habilitado("") is False
        assert canal_detail_habilitado(None) is False


# ── Engine-level: gate exposed, data computes regardless of service ───────────

@pytest.fixture(scope="module", autouse=True)
def v27_param():
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


def _run_with_service(servicio: str):
    import nexa_engine.modules.parametrizacion.services.provider as _prov
    _prov._PROVIDER_INSTANCE = None
    ui = UserInputLoader().cargar(REAL_REQUEST)
    ctx = SimulationContextBuilder().construir(ui)
    ctx.panel.linea_negocio = servicio  # override service (Panel!C5)
    return NexaPricingEngine().calcular(ctx)


class TestServiceDoesNotSuppressData:
    def test_real_service_gate_false_but_data_present(self):
        """Real request service ('Captura de Datos') → gate False, data still computed."""
        r = _run_with_service("Captura de Datos")
        assert r.cost_to_serve.canal_view_habilitado is False
        assert r.cost_to_serve.desglose_a.nomina > 0, "desglose must compute regardless of gate"
        assert r.cost_to_serve.cts_cadena_a > 0

    def test_sac_service_gate_true_and_data_present(self):
        """SAC → gate True; data computed identically (gate is not a data switch)."""
        r = _run_with_service("SAC")
        assert r.cost_to_serve.canal_view_habilitado is True
        assert r.cost_to_serve.desglose_a.nomina > 0

    def test_chains_not_driven_by_service(self):
        """Active chains come from cadenas_activas input, not the service name.
        Switching service must not change which chains are active."""
        r_cap = _run_with_service("Captura de Datos")
        r_sac = _run_with_service("SAC")
        # Cadena B/C presence is identical regardless of service (input-driven).
        assert (r_cap.cost_to_serve.cts_cadena_b > 0) == (r_sac.cost_to_serve.cts_cadena_b > 0)
        assert (r_cap.cost_to_serve.cts_cadena_c > 0) == (r_sac.cost_to_serve.cts_cadena_c > 0)
