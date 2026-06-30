"""F6 — Oracle validation mesh tests.

Suite parametrizada que ejerce ≥150 checkpoints (`oracle_mesh_mapping.py`)
contra el output del motor con el request canónico V2-7. Tolerancia técnica
1e-6 (objetivo conceptual: 0.00%). NO se enmascara ninguna falla — el
heatmap por stage se construye desde los resultados reales.

Conventions:
  * Si el extractor devuelve None → pytest.fail con "Backend missing".
    Esto detecta huecos semánticos (categoría de drift estructural).
  * Si Excel value == 0 y backend == 0 → pass.
  * Si Excel value == 0 y backend != 0 → fail (tolerancia absoluta 1e-6).
  * Si Excel != 0 → drift relativo |b-e|/|e| < 1e-6.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from tests.parity.oracle_mesh_mapping import CHECKPOINTS, MeshCheckpoint


MESH_FILE = Path(__file__).parent / "excel_oracle_v2_7_mesh.json"
REQUEST_FILE = Path(__file__).parent / "fixtures" / "excel_v2_7_real_request.json"

# Tolerancia técnica para flotantes (objetivo 0.00% — esto cubre solo el
# error de IEEE-754 acumulado, no permite drift estructural).
REL_TOL = 1e-6
ABS_TOL = 1e-6


def _load_mesh() -> dict:
    if not MESH_FILE.exists():
        return {"cells": {}}
    return json.loads(MESH_FILE.read_text())


_MESH = _load_mesh()


def _expected_for(excel_ref: str) -> Optional[float]:
    cell = _MESH.get("cells", {}).get(excel_ref)
    if cell is None:
        return None
    v = cell.get("value")
    return float(v) if isinstance(v, (int, float)) else None


@pytest.fixture(scope="module")
def backend_result(engine, builder, loader, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("v27_mesh") / "req.json"
    tmp.write_text(REQUEST_FILE.read_text())
    ui = loader.cargar(tmp)
    ctx = builder.construir(ui)
    return engine.calcular(ctx)


_IDS = [c.id for c in CHECKPOINTS]


@pytest.mark.parametrize("checkpoint", CHECKPOINTS, ids=_IDS)
def test_oracle_mesh_checkpoint(checkpoint: MeshCheckpoint, backend_result):
    expected = _expected_for(checkpoint.excel)
    if expected is None:
        pytest.skip(
            f"No oracle value for {checkpoint.excel} (mesh extraction did not capture it)"
        )

    actual = checkpoint.extractor(backend_result)
    if actual is None:
        pytest.fail(
            f"[{checkpoint.stage}] {checkpoint.id}: backend has no value at "
            f"{checkpoint.excel} (expected={expected})"
        )

    if abs(expected) < ABS_TOL:
        assert abs(actual) < ABS_TOL, (
            f"[{checkpoint.stage}] {checkpoint.id}: backend={actual}, "
            f"excel={expected} (Excel {checkpoint.excel})"
        )
        return

    tol = checkpoint.rel_tol if checkpoint.rel_tol is not None else REL_TOL
    rel = abs(actual - expected) / abs(expected)
    assert rel < tol, (
        f"[{checkpoint.stage}] {checkpoint.id}: backend={actual}, "
        f"excel={expected}, drift={rel * 100:.4f}% "
        f"(Excel {checkpoint.excel})"
    )


def test_mesh_catalog_size():
    """F6 invariant: el catálogo debe tener ≥150 checkpoints."""
    assert len(CHECKPOINTS) >= 150, (
        f"Mesh catalog has {len(CHECKPOINTS)} checkpoints — target ≥150"
    )


def test_mesh_file_loaded():
    assert MESH_FILE.exists(), f"Missing mesh oracle file: {MESH_FILE}"
    data = json.loads(MESH_FILE.read_text())
    cells = data.get("cells", {})
    assert len(cells) >= 200, f"Mesh file has {len(cells)} cells (target ≥200)"
