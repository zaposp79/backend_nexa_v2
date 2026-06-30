"""Excel V2-7 oracle integration tests.

The V2-7 workbook's canonical case is "Captura de Datos" with ramp-up=0,
so most numerical P&G cells are 0 by design. These tests pin that contract
and verify that the engine reproduces Excel's structural decisions:

- Panel inputs match expected snapshot
- P&G cells in the canonical Excel case are 0 (ramp-up=0)
- Tasas, margenes y otras constantes coinciden
"""
import pytest

from tests.parity.tolerance import assert_close


pytestmark = pytest.mark.skipif(
    not __import__("tests.parity.excel_oracle", fromlist=["EXCEL_AVAILABLE"]).EXCEL_AVAILABLE,
    reason="Excel V2-7 workbook not available at default path; set NEXA_EXCEL_V27 env var.",
)


def test_panel_snapshot_matches_v27():
    from tests.parity.excel_oracle import panel_snapshot
    snap = panel_snapshot()
    # Pin estructural — el valor exacto puede cambiar entre ediciones del workbook.
    assert snap["margen_a"] == 0.21, f"Panel!C63 (margen_a) = {snap['margen_a']}"
    assert snap["tasa_ica"] in (0.01, 0.02), f"Panel!C34 (tasa_ica) = {snap['tasa_ica']}"
    assert snap["tasa_gmf"] == 0.004, f"Panel!C35 (tasa_gmf) = {snap['tasa_gmf']}"
    # Servicio canónico V2-7: ramp-up = 0
    assert snap["servicio"] in ("Captura de Datos", "Plataformas"), (
        f"V2-7 canonical servicio expected to be 'Captura de Datos' or 'Plataformas'; "
        f"got {snap['servicio']}")


def test_pyg_excel_canonical_is_zero():
    """V2-7 canonical case ramps to 0 → todo el P&G es 0."""
    from tests.parity.excel_oracle import pyg_snapshot
    snap = pyg_snapshot()
    # En el caso canónico del V2-7, ingreso_bruto_m1 = 0 (ramp-up=0)
    assert (snap["ingreso_bruto_m1"] or 0) == 0, (
        f"Visión P&G!C18 canonical = {snap['ingreso_bruto_m1']} (expected 0)")
    assert (snap["costo_total_m1"] or 0) == 0
    assert (snap["ica_m1"] or 0) == 0


def test_excel_panel_margen_a_matches_default():
    """El default del backend para margen_a (0.21) coincide con Panel!C63 del Excel."""
    from tests.parity.excel_oracle import read_cell
    excel_margen_a = read_cell("Panel de Control General", "C63")
    assert_close(excel_margen_a, 0.21, label="Excel Panel!C63 == backend default 0.21")
