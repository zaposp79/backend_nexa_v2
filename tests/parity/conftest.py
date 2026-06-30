"""Fixtures comunes para tests de paridad Excel V2-7 ↔ backend_nexa."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

import pytest

# Ensure repo root is on sys.path so `backend_nexa` is importable.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401  (registers nexa_engine alias)
from nexa_engine import NexaPricingEngine  # noqa: E402
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder  # noqa: E402
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader  # noqa: E402


BACKEND_ROOT = PROJECT_ROOT / "backend_nexa"
TEST_CASES = BACKEND_ROOT / "test_cases" / "input"
FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# V2-7 parametrization activation helpers.
# Parity tests compare against Excel V2-7 oracle data, so the engine must use
# V2-7 parametrization (not the current production active version).
# ---------------------------------------------------------------------------

_STORAGE = BACKEND_ROOT / "storage" / "parametrization"


def _activate_v27_versions() -> Dict[str, Any]:
    """Switch HR and OP active versions to v2-7. Returns original state."""
    original: Dict[str, Any] = {}
    for module in ("hr", "op"):
        vfile = _STORAGE / module / "versions.json"
        versions: List[dict] = json.loads(vfile.read_text())
        original[module] = json.dumps(versions)  # save original JSON
        changed = False
        for entry in versions:
            if entry.get("is_active"):
                entry["is_active"] = False
                changed = True
        for entry in versions:
            if entry.get("version_id") == "v2-7":
                entry["is_active"] = True
                changed = True
        if changed:
            vfile.write_text(json.dumps(versions, indent=2, ensure_ascii=False))
    return original


def _restore_versions(original: Dict[str, Any]) -> None:
    """Restore HR and OP versions.json from saved state."""
    for module, saved_json in original.items():
        vfile = _STORAGE / module / "versions.json"
        vfile.write_text(saved_json)


def _reset_provider_singleton() -> None:
    """Clear the module-level singleton so next call reloads from disk."""
    import nexa_engine.modules.parametrizacion.services.provider as _prov_mod
    _prov_mod._PROVIDER_INSTANCE = None
    import nexa_engine.modules.parametrizacion.services.resolver as _res_mod
    if hasattr(_res_mod, "_RESOLVER_INSTANCE"):
        _res_mod._RESOLVER_INSTANCE = None


# ----------------------------------------------------------------------------
# Canonical case builder — a single, minimal, deterministic input shape that
# every dimensional test can mutate to flip one knob at a time.
# ----------------------------------------------------------------------------

CANONICAL_INPUT = {
    "panel_de_control": {
        "cliente": "ParityTest",
        "tipo_cliente": "No Grupo Aval",
        "linea_negocio": "Cobranzas",
        "ciudad": "Bogotá",
        "sede": "Bogota - Toberin",
        "fecha_inicio": "2026-01-01",
        "meses_contrato": 12,
        "margen": 0.21,
        "margen_b": 0.30,
        "margen_c": 0.20,
        "op_cont": 0.05,
        "com_cont": 0.03,
        "markup": 0.0,
        "descuento": 0.0,
        "tasa_ica": 0.01,
        "tasa_gmf": 0.004,
        "activa_financiacion": False,
        "periodo_pago_dias": 30,
        "tasa_mensual_financ": 0.0153,
        "imprevistos": 0.0,
        "pct_rotacion": 0.085,
        "pct_ausentismo": 0.065,
        "cadenas_activas": {"cadena_a": True, "cadena_b": False, "cadena_c": False},
    },
    "condiciones_cadena_a": {
        "perfiles": [{
            "nombre": "Agente Cobranzas",
            "rol": "Agente Basico",
            "modalidad": "Inbound",
            "canal": "Voz",
            "fte": 10.0,
            "pct_presencia": 1.0,
            "salario_base": 1_750_905.0,
            "comision_pct": 0.0,
            "dias_cap_inicial": 0,
            "dias_cap_rotacion": 0,
            "incluye_examenes": False,
            "incluye_seguridad": False,
            "incluye_crucero": False,
            "modelo_cobro": "Fijo FTE",
            "pct_fijo": 1.0,
            "no_payroll_mensual": 0.0,
        }],
    },
    "condiciones_cadena_b": {"canales": []},
    "condiciones_cadena_c": {},
}


def _patch(d, **kw):
    """Deep-merge kw into a copy of d (panel-level only — simple)."""
    out = copy.deepcopy(d)
    panel_patch = kw.pop("panel", None) or {}
    for k, v in panel_patch.items():
        out["panel_de_control"][k] = v
    cadenas_patch = kw.pop("cadenas", None) or {}
    out["panel_de_control"].setdefault("cadenas_activas", {}).update(cadenas_patch)
    return out


@pytest.fixture(scope="session")
def v27_parametrization():
    """Session-scoped fixture that activates V2-7 parametrization and restores on teardown."""
    original = _activate_v27_versions()
    _reset_provider_singleton()
    yield
    _restore_versions(original)
    _reset_provider_singleton()


@pytest.fixture(scope="session")
def engine(v27_parametrization) -> NexaPricingEngine:
    return NexaPricingEngine()


@pytest.fixture(scope="session")
def builder(v27_parametrization) -> SimulationContextBuilder:
    return SimulationContextBuilder()


@pytest.fixture(scope="session")
def loader() -> UserInputLoader:
    return UserInputLoader()


@pytest.fixture
def canonical_input() -> dict:
    return copy.deepcopy(CANONICAL_INPUT)


@pytest.fixture
def run_engine(engine, builder, loader, tmp_path):
    """Factory that takes a dict input, writes it to a tmp file, runs the engine."""
    def _run(input_dict: dict):
        p = tmp_path / f"parity_case_{abs(hash(json.dumps(input_dict, sort_keys=True, default=str))) & 0xFFFF}.json"
        p.write_text(json.dumps(input_dict, default=str))
        ui = loader.cargar(p)
        req = builder.construir(ui)
        return engine.calcular(req)
    return _run


@pytest.fixture
def patch_input():
    """Returns the `_patch` helper for use in tests."""
    return _patch


# ---------------------------------------------------------------------------
# WAVE 17 — Marcar tests circulares (pre-WAVE-17) como legacy_circular para
# visibilidad y excluirlos del default run sin eliminarlos.
# Los archivos test_excel_oracle_v2_7_real.py y test_mutation_detection.py
# (WAVE 17) NO se marcan — esos son los tests reales.
# ---------------------------------------------------------------------------

_CIRCULAR_FILES = {
    "test_parity_anomalia_margen_c.py",
    "test_parity_bancamia_golden.py",
    "test_parity_cadenas.py",
    "test_parity_canales.py",
    "test_parity_complejidad.py",
    "test_parity_excel_oracle.py",
    "test_parity_modalidades.py",
    "test_parity_modelos.py",
    "test_parity_panel_propagation.py",
    "test_parity_servicios.py",
    "test_parity_smoke.py",
}


def pytest_collection_modifyitems(config, items):
    legacy_circular = pytest.mark.legacy_circular
    for item in items:
        fname = Path(str(item.fspath)).name
        if fname in _CIRCULAR_FILES:
            item.add_marker(legacy_circular)
