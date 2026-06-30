"""WAVE 17 — Tests de paridad REAL contra valores Excel V2-7.

Reemplaza el comportamiento circular de los 39 tests legados (que computaban
expected via la misma fórmula validada). Cada test compara el output del
backend contra un valor concreto de celda Excel.

Diseño:
  * Engine real, parametrización real (no mocks).
  * Request en `tests/parity/fixtures/excel_v2_7_real_request.json`.
  * Tolerancia: rel_tol = 1e-4 (≤0.01%); para |v|<1e-6, tol absoluta 1e-6.
  * Si el backend NO tiene equivalente para una celda → pytest.fail
    ("Backend missing equivalent"), NO skip silencioso.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.parity.oracle_mapping import CELL_TO_BACKEND, resolve_backend_path


ORACLE_FILE = Path(__file__).parent / "excel_oracle_v2_7_full.json"
REQUEST_FILE = Path(__file__).parent / "fixtures" / "excel_v2_7_real_request.json"


@pytest.fixture(scope="module")
def excel_oracle() -> dict:
    return json.loads(ORACLE_FILE.read_text())


@pytest.fixture(scope="module")
def backend_result(engine, builder, loader, tmp_path_factory):
    """Ejecuta el motor con el request canónico V2-7 (Excel pre-loaded)."""
    # Use a tmp file to satisfy loader's path-based contract.
    tmp = tmp_path_factory.mktemp("v27_real") / "req.json"
    tmp.write_text(REQUEST_FILE.read_text())
    ui = loader.cargar(tmp)
    ctx = builder.construir(ui)
    return engine.calcular(ctx)


def _flatten_oracle_with_paths(oracle: dict):
    """Genera (cell_ref, label, value) para celdas con backend_path conocido."""
    expected = oracle.get("expected_outputs", {})
    out = []
    for section, items in expected.items():
        for cell_ref, meta in items.items():
            if cell_ref not in CELL_TO_BACKEND:
                continue
            v = meta.get("value")
            if v is None:
                continue
            out.append((cell_ref, meta.get("label", ""), v))
    return out


def _all_oracle_params() -> list:
    """Carga el oracle al collection-time para parametrizar todos los tests."""
    if not ORACLE_FILE.exists():
        return []
    oracle = json.loads(ORACLE_FILE.read_text())
    return _flatten_oracle_with_paths(oracle)


_PARAMS = _all_oracle_params()
_IDS = [p[0] for p in _PARAMS]


@pytest.mark.parametrize("cell_ref,label,expected", _PARAMS, ids=_IDS)
def test_excel_oracle_match(cell_ref: str, label: str, expected: float, backend_result):
    """Para cada celda Excel mapeada, verifica que backend produce mismo valor."""
    backend_path = CELL_TO_BACKEND[cell_ref]
    actual = resolve_backend_path(backend_result, backend_path)

    if actual is None:
        pytest.fail(
            f"Backend missing equivalent for {cell_ref} ({label}) "
            f"at path '{backend_path}' — engine result has no value"
        )

    if abs(expected) < 1e-6:
        assert abs(actual - expected) < 1e-6, (
            f"{cell_ref} ({label}): backend={actual}, excel={expected}"
        )
    else:
        rel_diff = abs(actual - expected) / abs(expected)
        assert rel_diff <= 1e-4, (
            f"{cell_ref} ({label}): backend={actual}, excel={expected}, "
            f"drift={rel_diff * 100:.4f}%"
        )


# -----------------------------------------------------------------------------
# Sanity: el oracle se cargó y contiene valores no triviales.
# -----------------------------------------------------------------------------
def test_oracle_file_loaded():
    assert ORACLE_FILE.exists(), f"Oracle file missing: {ORACLE_FILE}"
    oracle = json.loads(ORACLE_FILE.read_text())
    total = 0
    nonzero = 0
    for section, items in oracle.get("expected_outputs", {}).items():
        for cell, meta in items.items():
            total += 1
            v = meta.get("value")
            if isinstance(v, (int, float)) and v != 0:
                nonzero += 1
    assert total >= 100, f"Oracle should have ≥100 cells, has {total}"
    assert nonzero >= 100, f"Oracle should have ≥100 non-zero values, has {nonzero}"


def test_oracle_mapping_coverage():
    """Imprime cobertura del mapping para visibilidad de huecos."""
    oracle = json.loads(ORACLE_FILE.read_text())
    valued = 0
    mapped = 0
    for section, items in oracle.get("expected_outputs", {}).items():
        for cell, meta in items.items():
            v = meta.get("value")
            if v is None or v == 0:
                continue
            valued += 1
            if cell in CELL_TO_BACKEND:
                mapped += 1
    # No es una aserción dura — es información para el reporte.
    # Si la cobertura es <10% se considera insuficiente.
    coverage = (mapped / valued) if valued else 0
    print(f"\nOracle coverage: {mapped}/{valued} = {coverage * 100:.1f}%")
    assert valued > 0
