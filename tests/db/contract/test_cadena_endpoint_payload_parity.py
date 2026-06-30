"""Contract tests: cadena parametrization endpoints return correct payloads.

Después de la refactorización arquitectónica (FASE modularidad):
- Las rutas activas son /simulation/input/chain-*/parametros.
- Las rutas /parametrization/cadena-* fueron eliminadas.
- ParametrosCadenasBC fue dividido en ParametrosCadenaB y ParametrosCadenaC.

Los tests garantizan:
1. Cada endpoint retorna HTTP 200 con un payload válido.
2. Cadena B y Cadena C retornan el mismo payload (misma fuente de datos OP/HR).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[4]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
    from nexa_engine.app import create_app
    with TestClient(create_app()) as c:
        yield c


def _get(client: TestClient, path: str) -> dict:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} → {resp.status_code}: {resp.text[:200]}"
    return resp.json()


def test_cadena_a_endpoint_returns_payload(client):
    payload = _get(client, "/api/v1/simulation/input/chain-a/parametros")
    assert "ratios" in payload
    assert "opex_fijo" in payload
    assert "hardware_software" in payload


def test_cadena_b_endpoint_returns_payload(client):
    payload = _get(client, "/api/v1/simulation/input/chain-b/parametros")
    assert "dispositivos_requeridos" in payload
    assert "equipo_hitl" in payload


def test_cadena_c_endpoint_returns_payload(client):
    payload = _get(client, "/api/v1/simulation/input/chain-c/parametros")
    assert "dispositivos_requeridos" in payload
    assert "equipo_hitl" in payload


def test_cadena_b_and_c_return_identical_payload(client):
    b = _get(client, "/api/v1/simulation/input/chain-b/parametros")
    c = _get(client, "/api/v1/simulation/input/chain-c/parametros")
    assert b == c, "Cadena B and C should return same payload (same underlying OP/HR data)"
