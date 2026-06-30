"""OpenAPI guardrails for the public v1 API surface."""
from __future__ import annotations

from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401
from nexa_engine.app import create_app


EXPECTED_VISION_PATHS = {
    "/api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro",
    "/api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro/recalculate",
    "/api/v1/simulation/{simulation_id}/results/vision-pyg",
    "/api/v1/simulation/{simulation_id}/results/cost-to-serve",
    "/api/v1/simulation/{simulation_id}/results/vision-imprimible",
}

FORBIDDEN_SEGMENTS = ("/internal", "/raw", "/debug", "/legacy")
REMOVED_PATHS = {
    "/api/v1/simulation/{simulation_id}/results/vision-tarifas",
    "/api/v1/simulation/{simulation_id}/results/vision-pyg/internal",
    "/api/v1/simulation/{simulation_id}/results/vision-pyg/screen",
}


def _openapi_schema() -> dict:
    client = TestClient(create_app())
    return client.get("/openapi.json").json()


def test_public_openapi_has_no_legacy_or_internal_paths():
    schema = _openapi_schema()
    paths = schema.get("paths", {})

    for path in paths:
        assert not any(segment in path for segment in FORBIDDEN_SEGMENTS), path

    for removed_path in REMOVED_PATHS:
        assert removed_path not in paths


def test_public_openapi_vision_paths_are_only_final_v1_contracts():
    schema = _openapi_schema()
    paths = schema.get("paths", {})

    for expected_path in EXPECTED_VISION_PATHS:
        assert expected_path in paths

    visible_vision_paths = {
        path
        for path in paths
        if path.startswith("/api/v1/simulation/")
        and "/results/" in path
        and ("vision-" in path or "cost-to-serve" in path)
    }
    assert visible_vision_paths == EXPECTED_VISION_PATHS


def test_public_openapi_has_unique_operation_ids_and_summaries():
    schema = _openapi_schema()
    operation_ids: list[str] = []

    for path, methods in schema.get("paths", {}).items():
        for method, spec in methods.items():
            assert spec.get("summary"), f"Missing summary for {method.upper()} {path}"
            operation_id = spec.get("operationId")
            assert operation_id, f"Missing operationId for {method.upper()} {path}"
            operation_ids.append(operation_id)

    assert len(operation_ids) == len(set(operation_ids)), "Duplicate operationId detected"


def test_modelo_cobro_openapi_examples_are_present():
    schema = _openapi_schema()
    path = "/api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro"
    op = schema["paths"][path]["get"]

    example = op["responses"]["200"]["content"]["application/json"]["example"]
    assert example["success"] is True
    assert example["data"]["selected_view_id"] == "escenario_1"
    assert example["data"]["cliente"] == "Banco de Bogotá"


def test_modelo_cobro_recalculate_request_example_is_present():
    schema = _openapi_schema()
    model = schema["components"]["schemas"]["ModeloCobroRecalculateRequest"]
    examples = model.get("examples") or []

    assert examples, "Expected request example for ModeloCobroRecalculateRequest"
    assert examples[0]["view_id"] == "total"
    assert examples[0]["overrides"]["modelo_cobro"] == "Fijo"
