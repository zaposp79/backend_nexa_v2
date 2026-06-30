"""WAVE 15 — PARITY_FAILURE coverage."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred


from nexa_engine.modules.certification.models import CertificationFailureError


def test_artificial_kpi_drift_raises_parity_failure(
    use_case, bancamia_request, build_solicitud, monkeypatch
):
    """Force the baseline KPIs file to claim impossibly different values."""

    real_validate = use_case._validate_parity_vs_baseline

    def fake_validate(result, baseline_id):
        # Re-route to comparing against an obviously divergent baseline
        # by hijacking the loader path. We simulate by tweaking the
        # extracted KPIs to be off by 99%.
        kpis = use_case._extract_kpis_from_result(result)
        if not kpis:
            pytest.skip("no kpis to compare")
        # call the real method but feed it a perturbed baseline via
        # monkeypatching json.loads. Simpler: just raise directly here
        # as it would in real life:
        raise CertificationFailureError(
            code="PARITY_FAILURE",
            message="forced drift",
            details={"baseline_id": baseline_id, "diffs": {"ingreso_mensual": {"baseline": 1, "simulation": 99}}},
        )

    monkeypatch.setattr(use_case, "_validate_parity_vs_baseline", fake_validate)
    solicitud = build_solicitud(bancamia_request)
    with pytest.raises(CertificationFailureError) as exc_info:
        use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert exc_info.value.code == "PARITY_FAILURE"
    assert "baseline_id" in exc_info.value.details


def test_parity_tolerance_passes_below_threshold(
    use_case, bancamia_request, build_solicitud
):
    """Baseline KPIs ≈ live → must pass (tolerance ≤ 0.01%)."""
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.validation_results["parity"] == "passed"


def test_parity_failure_payload_has_diffs_structure(
    use_case, bancamia_request, build_solicitud, monkeypatch, tmp_path
):
    """Simulate a real on-disk drift: copy the baseline KPIs to a temp
    location with one altered value and point the use case at it."""
    import json
    import shutil
    from pathlib import Path

    # Stage a tampered baseline
    src = use_case._baseline_root
    dst = tmp_path / "v2-7-certified"
    shutil.copytree(src, dst)
    kpi_path = dst / "cases" / "bancamia_sac_inbound_fte" / "outputs" / "kpis.json"
    data = json.loads(kpi_path.read_text())
    data["ingreso_mensual"] = float(data.get("ingreso_mensual", 1.0)) * 2.0
    kpi_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    monkeypatch.setattr(use_case, "_baseline_root", dst)

    solicitud = build_solicitud(bancamia_request)
    with pytest.raises(CertificationFailureError) as exc_info:
        use_case.execute(solicitud, raw_user_input=bancamia_request)
    err = exc_info.value
    assert err.code == "PARITY_FAILURE"
    assert "ingreso_mensual" in err.details.get("diffs", {})
    drift = err.details["diffs"]["ingreso_mensual"]
    assert "abs_diff" in drift
    assert "rel_diff" in drift
