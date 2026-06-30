"""WAVE 15 certified-mode test fixtures."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

import backend_nexa  # noqa: F401


@pytest.fixture(scope="session")
def baseline_root() -> Path:
    return PROJECT_ROOT / "storage" / "baselines" / "v2-7-certified"


@pytest.fixture(scope="session")
def bancamia_request(baseline_root) -> dict:
    path = baseline_root / "cases" / "bancamia_sac_inbound_fte" / "request.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def tmp_cert_repo(tmp_path):
    from nexa_engine.modules.certification.certificate_repository import (
        CertificateRepository,
    )
    return CertificateRepository(root=tmp_path)


@pytest.fixture
def real_engine():
    from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    registry = VersionRegistry()
    return NexaPricingEngine(version_registry=registry), registry


@pytest.fixture
def use_case(real_engine, tmp_cert_repo, baseline_root):
    from nexa_engine.modules.calculator.use_cases.certified_calculation import (
        CertifiedCalculationUseCase,
    )
    engine, registry = real_engine
    return CertifiedCalculationUseCase(
        engine=engine,
        version_registry=registry,
        baseline_root=baseline_root,
        cert_repo=tmp_cert_repo,
    )


@pytest.fixture
def build_solicitud():
    """Factory: dict → PricingRequest."""
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

    def _build(raw: dict):
        ui = UserInputLoader().cargar_desde_dict(raw)
        return SimulationContextBuilder().construir(ui)

    return _build


@pytest.fixture
def client():
    """FastAPI TestClient — builds a fresh app instance per test."""
    from fastapi.testclient import TestClient
    from nexa_engine.app import create_app
    with TestClient(create_app()) as c:
        yield c
