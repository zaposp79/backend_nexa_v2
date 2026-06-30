"""WAVE 15 — EXPERIMENTAL_OVERRIDE coverage."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred


from nexa_engine.modules.certification.models import CertificationFailureError


def test_experimental_top_level_flag_blocks(use_case, bancamia_request, build_solicitud):
    payload = dict(bancamia_request)
    payload["experimental"] = True
    solicitud = build_solicitud(bancamia_request)
    with pytest.raises(CertificationFailureError) as exc_info:
        use_case.execute(solicitud, raw_user_input=payload)
    assert exc_info.value.code == "EXPERIMENTAL_OVERRIDE"
    assert "experimental" in exc_info.value.details.get("fields", [])[0]


def test_experimental_nested_metadata_blocks(use_case, bancamia_request, build_solicitud):
    payload = dict(bancamia_request)
    payload["metadata"] = {"experimental_flags": {"early_pricing": True}}
    solicitud = build_solicitud(bancamia_request)
    with pytest.raises(CertificationFailureError) as exc_info:
        use_case.execute(solicitud, raw_user_input=payload)
    err = exc_info.value
    assert err.code == "EXPERIMENTAL_OVERRIDE"
    fields = err.details.get("fields", [])
    assert any("experimental_flags" in f for f in fields)


def test_experimental_prefix_blocks(use_case, bancamia_request, build_solicitud):
    payload = dict(bancamia_request)
    panel = dict(payload.get("panel_de_control", {}))
    panel["_experimental_margin"] = 0.5
    payload["panel_de_control"] = panel
    solicitud = build_solicitud(bancamia_request)
    with pytest.raises(CertificationFailureError) as exc_info:
        use_case.execute(solicitud, raw_user_input=payload)
    assert exc_info.value.code == "EXPERIMENTAL_OVERRIDE"
