"""pytest fixtures comunes para tests de integración del motor NEXA."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root on sys.path so `backend_nexa` is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Trigger nexa_engine alias registration
import backend_nexa  # noqa: E402, F401


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def backend_root() -> Path:
    return PROJECT_ROOT / "backend_nexa"


@pytest.fixture(scope="session")
def test_cases_dir(backend_root) -> Path:
    return backend_root / "test_cases"


@pytest.fixture(scope="session")
def reports_dir(backend_root) -> Path:
    return backend_root / "reports"


@pytest.fixture
def whatsapp_only_case(test_cases_dir) -> Path:
    return test_cases_dir / "input" / "bancamia_whatsapp_only.json"


@pytest.fixture
def three_profiles_case(test_cases_dir) -> Path:
    return test_cases_dir / "input" / "bancamia_excel_match.json"


@pytest.fixture
def baseline_data(reports_dir) -> dict:
    """Load the official baseline JSON."""
    import json
    path = reports_dir / "baseline_oficial.json"
    if not path.exists():
        pytest.skip("baseline_oficial.json not yet generated. Run scripts/generate_baseline.py first.")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def run_engine():
    """Returns a callable: case_path → PricingResult."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    def _run(case_path: Path):
        ui = UserInputLoader().cargar(case_path)
        solic = SimulationContextBuilder().construir(ui)
        return NexaPricingEngine().calcular(solic)

    return _run
