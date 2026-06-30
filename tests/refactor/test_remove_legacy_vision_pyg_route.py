from __future__ import annotations

from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401

from nexa_engine.app import create_app


ACTIVE_ROUTE = "/api/v1/simulation/{simulation_id}/results/vision-pyg"
REMOVED_ROUTES = {
    "/api/v1/simulation/{simulation_id}/vision/pyg",
    "/api/v1/simulation/{simulation_id}/results/vision-pyg/internal",
    "/api/v1/simulation/{simulation_id}/results/vision-pyg/screen",
}


def test_legacy_vision_pyg_routes_are_not_registered():
    app = create_app()
    registered_paths = {route.path for route in app.routes}

    for route in REMOVED_ROUTES:
        assert route not in registered_paths
    assert ACTIVE_ROUTE in registered_paths


def test_openapi_does_not_publish_legacy_vision_pyg_routes():
    client = TestClient(create_app())

    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})

    for route in REMOVED_ROUTES:
        assert route not in paths
    assert ACTIVE_ROUTE in paths
