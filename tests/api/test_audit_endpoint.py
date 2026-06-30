"""WAVE 13 — tests for the /audit/* endpoints.

These tests exercise the audit router both via the FastAPI TestClient
(end-to-end) and via the `AuditSimulationUseCase` directly (unit).

A shared module-scoped fixture pre-runs Bancamia with `with_lineage=True`
so we have a real, persisted graph to query.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from nexa_engine.app import create_app
from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageNode,
    LineageRef,
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_PARAMETRIZATION,
    SOURCE_TYPE_REQUEST,
)
from nexa_engine.modules.audit.use_cases.audit_simulation import (
    AuditNotAvailableError,
    AuditSimulationUseCase,
    ValueNotFoundError,
)
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)
from tests.refactor._v27_provider import build_v27_provider


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


THIS_DIR     = Path(__file__).resolve().parent
BACKEND_ROOT = THIS_DIR.parent.parent
BANCAMIA_FIXTURE = BACKEND_ROOT / "tests" / "parity" / "fixtures" / "bancamia_v2_7.json"


@pytest.fixture(scope="module")
def isolated_storage(tmp_path_factory) -> Path:
    """Per-module isolated lineage storage so tests don't depend on prod data."""
    return tmp_path_factory.mktemp("audit_lineage_storage")


@pytest.fixture(scope="module")
def bancamia_sim_id(isolated_storage: Path) -> str:
    """Run Bancamia with lineage and persist to the isolated storage."""
    payload = json.loads(BANCAMIA_FIXTURE.read_text())["inputs"]
    tmp_input = isolated_storage / "bancamia_input.json"
    tmp_input.write_text(json.dumps(payload, default=str))

    loader = UserInputLoader()
    user_input = loader.cargar(tmp_input)
    provider = build_v27_provider()
    request_obj = SimulationContextBuilder(provider=provider).construir(user_input)

    engine = NexaPricingEngine(parametrizacion=provider)
    _, graph = engine.calcular(request_obj, with_lineage=True)

    # Re-persist to the isolated repo so the test storage is fully ours.
    repo = LineageSnapshotRepository(base_dir=isolated_storage)
    repo.save(graph)
    return graph.simulation_id


@pytest.fixture(scope="module")
def use_case(isolated_storage: Path) -> AuditSimulationUseCase:
    repo = LineageSnapshotRepository(base_dir=isolated_storage)
    return AuditSimulationUseCase(lineage_repo=repo)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c


# ---------------------------------------------------------------------------
# Use-case tests (no HTTP)
# ---------------------------------------------------------------------------


def test_use_case_raises_when_no_lineage(use_case):
    with pytest.raises(AuditNotAvailableError):
        use_case.execute("nonexistent-sim-" + uuid.uuid4().hex)


def test_use_case_builds_audit_for_bancamia(use_case, bancamia_sim_id):
    audit = use_case.execute(bancamia_sim_id)
    assert audit.simulation_id == bancamia_sim_id
    assert audit.lineage.nodes_count >= 20
    assert audit.engine_version == "engine-v2"
    # formula_set is derived from the active parametrization version; assert the
    # naming contract instead of a specific version (WAVE 14 wires the live hash).
    assert audit.formula_set.startswith("formula-set-"), (
        f"formula_set must follow 'formula-set-<version>' contract, got {audit.formula_set!r}"
    )
    assert isinstance(audit.parametrization_hashes, dict)


def test_audit_includes_formulas_summary(use_case, bancamia_sim_id):
    audit = use_case.execute(bancamia_sim_id)
    # at least one formula recorded
    assert len(audit.formulas) >= 1
    for f in audit.formulas:
        assert f.used_count >= 1
        assert f.calculator
        assert f.stage


def test_audit_parameters_used_split_request_vs_param(use_case, bancamia_sim_id):
    audit = use_case.execute(bancamia_sim_id)
    used = audit.parameters_used
    # request inputs should contain panel knobs
    request_keys = set(used.request.keys())
    assert any("panel" in k for k in request_keys), (
        f"expected panel.* keys in request inputs, got {sorted(request_keys)[:5]}"
    )
    # excel refs should be present
    assert len(used.excel_refs) >= 1
    for r in used.excel_refs:
        assert r.source_type == "excel"


def test_explain_value_returns_chain(use_case, bancamia_sim_id):
    exp = use_case.explain_value(bancamia_sim_id, "request.panel.margen")
    assert exp.value_name == "request.panel.margen"
    assert exp.explanation.startswith("request.panel.margen")
    # the trace_back chain should be non-empty (panel.margen has 2 refs)
    assert len(exp.refs_chain) >= 1


def test_explain_value_missing_raises(use_case, bancamia_sim_id):
    with pytest.raises(ValueNotFoundError):
        use_case.explain_value(bancamia_sim_id, "definitely.not.in.graph")


def test_list_simulations_includes_bancamia(use_case, bancamia_sim_id):
    items = use_case.list_simulations(limit=10)
    ids = [s.simulation_id for s in items]
    assert bancamia_sim_id in ids
    for s in items:
        if s.simulation_id == bancamia_sim_id:
            assert s.nodes_count >= 20
            assert len(s.stages) >= 1


# ---------------------------------------------------------------------------
# Synthetic graph tests — exercise build pure logic (no engine dependency)
# ---------------------------------------------------------------------------


def _synthetic_graph(sim_id: str) -> LineageGraph:
    """Build a small lineage graph deterministically for DTO tests."""
    node_a = LineageNode(
        trace_id=uuid.uuid4().hex,
        simulation_id=sim_id,
        stage="PAYROLL_BUILD",
        calculator="NominaCalculator.compute",
        value_name="payroll.bruto[Agente]",
        value=1_750_905.0,
        formula="salario_base * (1 + recargos)",
        inputs=(
            LineageRef(SOURCE_TYPE_REQUEST, "request.cadena_a.salario_base", 1_750_905.0),
            LineageRef(SOURCE_TYPE_PARAMETRIZATION, "hr.nomina[Agente].salario", 1_750_905.0),
            LineageRef(SOURCE_TYPE_EXCEL, "Excel:HR-Nomina!C12", 1_750_905.0,
                       sheet="HR-Nomina", cell="C12"),
        ),
    )
    node_b = LineageNode(
        trace_id=uuid.uuid4().hex,
        simulation_id=sim_id,
        stage="PRICING_BUILD",
        calculator="ProfitabilityCalculator.calcular_factor_billing",
        value_name="pricing.factor_billing[Voz]",
        value=0.6543,
        formula="costo / ((1-margen)*(1-op)*(1-com)*(1-mk)*(1+desc))",
        inputs=(
            LineageRef(SOURCE_TYPE_REQUEST, "request.panel.margen", 0.21),
        ),
    )
    return LineageGraph(
        simulation_id=sim_id,
        nodes=(node_a, node_b),
        roots=(node_b.trace_id,),
        parametrization_hashes={},
    )


def test_synthetic_audit_groups_formulas(tmp_path):
    sim_id = "synth-" + uuid.uuid4().hex[:8]
    repo = LineageSnapshotRepository(base_dir=tmp_path)
    repo.save(_synthetic_graph(sim_id))
    audit = AuditSimulationUseCase(lineage_repo=repo).execute(sim_id)
    formulas = {f.formula for f in audit.formulas}
    assert "salario_base * (1 + recargos)" in formulas
    assert any("factor_billing" in f.formula or "margen" in f.formula for f in audit.formulas)
    assert audit.lineage.stages_summary["PAYROLL_BUILD"] == 1
    assert audit.lineage.stages_summary["PRICING_BUILD"] == 1


def test_synthetic_audit_collects_unique_excel_refs(tmp_path):
    sim_id = "synth-" + uuid.uuid4().hex[:8]
    repo = LineageSnapshotRepository(base_dir=tmp_path)
    repo.save(_synthetic_graph(sim_id))
    audit = AuditSimulationUseCase(lineage_repo=repo).execute(sim_id)
    excel_refs = audit.parameters_used.excel_refs
    assert any(r.sheet == "HR-Nomina" and r.cell == "C12" for r in excel_refs)


# ---------------------------------------------------------------------------
# HTTP endpoint tests (TestClient)
# ---------------------------------------------------------------------------


def _override_repo(monkeypatch, client, storage_dir: Path) -> None:
    """Force the audit endpoints to use our isolated storage.

    Uses app.dependency_overrides so the override is actually picked up by
    FastAPI's Depends() resolution (monkeypatching the module attribute is
    insufficient because Depends() captures the function reference at import
    time, not at request time).
    """
    from nexa_engine.db.dependencies import get_audit_use_case as _dep_fn
    from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase
    from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository

    def _factory() -> AuditSimulationUseCase:
        repo = LineageSnapshotRepository(base_dir=storage_dir)
        return AuditSimulationUseCase(lineage_repo=repo)

    monkeypatch.setitem(client.app.dependency_overrides, _dep_fn, _factory)


def test_http_audit_returns_404_for_missing_sim(client, isolated_storage, monkeypatch):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get(f"/api/v1/audit/simulation/nonexistent-{uuid.uuid4().hex}")
    assert r.status_code == 404


def test_http_audit_response_schema_strict(client, isolated_storage, bancamia_sim_id, monkeypatch):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get(f"/api/v1/audit/simulation/{bancamia_sim_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    # required top-level keys per the api-v1 audit contract
    for key in (
        "simulation_id",
        "api_version",
        "engine_version",
        "formula_set",
        "parametrization_hashes",
        "lineage",
        "formulas",
        "parameters_used",
        "generated_at",
    ):
        assert key in body, f"missing key in audit response: {key}"
    assert body["api_version"] == "api-v1"
    assert body["lineage"]["nodes_count"] >= 20
    assert isinstance(body["formulas"], list)


def test_http_explain_returns_chain(client, isolated_storage, bancamia_sim_id, monkeypatch):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get(
        f"/api/v1/audit/simulation/{bancamia_sim_id}/explain",
        params={"value_name": "request.panel.margen"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["value_name"] == "request.panel.margen"
    assert "request.panel.margen" in body["explanation"]


def test_http_explain_missing_value_returns_404(client, isolated_storage, bancamia_sim_id, monkeypatch):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get(
        f"/api/v1/audit/simulation/{bancamia_sim_id}/explain",
        params={"value_name": "definitely.not.in.graph"},
    )
    assert r.status_code == 404


def test_http_list_simulations(client, isolated_storage, bancamia_sim_id, monkeypatch):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get("/api/v1/audit/simulations")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    sim_ids = [it["simulation_id"] for it in items]
    assert bancamia_sim_id in sim_ids


def test_http_baseline_diff_missing_baseline_returns_404(
    client, isolated_storage, bancamia_sim_id, monkeypatch
):
    _override_repo(monkeypatch, client, isolated_storage)
    r = client.get(
        f"/api/v1/audit/simulation/{bancamia_sim_id}/baseline-diff",
        params={"baseline_id": "does_not_exist"},
    )
    assert r.status_code == 404


def test_baseline_diff_for_known_case_via_use_case(isolated_storage, bancamia_sim_id):
    """Diff vs a real certified baseline using the use-case directly."""
    repo = LineageSnapshotRepository(base_dir=isolated_storage)
    uc = AuditSimulationUseCase(lineage_repo=repo)
    baseline_root = BACKEND_ROOT / "storage" / "baselines" / "v2-7-certified" / "cases"
    if not baseline_root.exists():
        pytest.skip("certified baselines not present")
    # Bancamia synthetic dataset != BaselineCert kpis exactly, but the API must
    # still return a structured diff (matches_baseline can be False).
    diff = uc.diff_vs_baseline(
        bancamia_sim_id, "bancamia_sac_inbound_fte", baseline_root
    )
    assert "matches_baseline" in diff
    assert "diff" in diff
    assert isinstance(diff["diff"], dict)
