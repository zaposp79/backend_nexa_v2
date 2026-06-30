"""Tests that OP-MargenBruto → get_portfolio_clientes() pipeline works end-to-end.

Source: active OP parametrization (storage/parametrization/op/...)
Path: FinancialParametrizationRepository.get_raw_op_data()
       → ParametrizationProvider.get_portfolio_clientes()
       → {clientes, promedios_por_categoria}
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider


@pytest.fixture(scope="module")
def provider():
    return ParametrizationProvider.build()


class TestOPPortfolioClientes:
    def test_get_portfolio_clientes_returns_dict(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip(
                "OP_CONTRACT_GAP: active OP version unavailable or lacks margenbruto sheet. "
                "Ensure active OP version file exists and contains margenbruto sheet."
            )
        assert "clientes" in result
        assert "promedios_por_categoria" in result

    def test_clientes_list_not_empty(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP — margenbruto sheet unavailable")
        assert len(result["clientes"]) > 0

    def test_clientes_have_required_fields(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP")
        for row in result["clientes"]:
            assert "categoria" in row, f"Missing 'categoria' in row: {row}"
            assert "cliente" in row, f"Missing 'cliente' in row: {row}"
            assert "margen_bruto" in row, f"Missing 'margen_bruto' in row: {row}"
            assert isinstance(row["margen_bruto"], float), f"margen_bruto must be float: {row}"

    def test_promedios_keyed_by_short_category_name(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP")
        promedios = result["promedios_por_categoria"]
        assert len(promedios) > 0
        # Keys must be short servicio names (matching linea_negocio / datos_operativos.servicio)
        # Verify keys are short names (not long descriptive names)
        for key in promedios:
            # Short names are <= 20 chars; long OP-GraficoMargenBruto names are much longer
            assert len(key) <= 30, f"promedio key looks like a long name (not short servicio): {key!r}"

    def test_sac_category_present(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP")
        sac_rows = [r for r in result["clientes"] if r["categoria"] == "SAC"]
        assert len(sac_rows) >= 5, "Expected at least 5 SAC rows in active OP portfolio"

    def test_promedios_sac_is_numeric(self, provider):
        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP")
        promedios = result["promedios_por_categoria"]
        if "SAC" not in promedios:
            pytest.skip("SAC not in active OP portfolio categories")
        assert isinstance(promedios["SAC"], float)

    def test_graph_calculator_consumes_op_rows(self, provider):
        """Full path: provider → PortfolioClienteRow → GraficoBandasCalculator."""
        from nexa_engine.modules.calculator_motor.formulas.graphics.calculator import (
            GraficoBandasCalculator,
        )
        from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
            GraficoBandasResult,
            PortfolioClienteRow,
        )

        result = provider.get_portfolio_clientes()
        if result is None:
            pytest.skip("OP_CONTRACT_GAP")

        portfolio = [
            PortfolioClienteRow(
                categoria=r["categoria"],
                cliente=r["cliente"],
                margen_bruto=r["margen_bruto"],
            )
            for r in result["clientes"]
        ]
        promedios = result["promedios_por_categoria"]

        # Use first available category
        categories = list({r.categoria for r in portfolio})
        if not categories:
            pytest.skip("No categories in portfolio")

        cat = categories[0]
        clients_in_cat = [r for r in portfolio if r.categoria == cat]

        calc = GraficoBandasCalculator()
        bandas = calc.calcular(
            categoria_servicio=cat,
            cliente_nombre=clients_in_cat[0].cliente if clients_in_cat else "UNKNOWN",
            deal_margin=0.15,
            portfolio=portfolio,
            promedios_por_categoria=promedios,
        )
        assert isinstance(bandas, GraficoBandasResult)
        # Q4 must be the maximum margin in that category
        numeric_margins = [r.margen_bruto for r in clients_in_cat if isinstance(r.margen_bruto, float)]
        if numeric_margins:
            assert bandas.quartil_4 == pytest.approx(max(numeric_margins), abs=1e-9)

    def test_no_yaml_fallback_used(self, provider):
        """Verify OP data is read through the provider, not from a YAML file."""
        import os

        # No portfolio YAML should exist under modules/
        forbidden_paths = [
            "modules/shared/config/business_rules/portfolio_clientes.yaml",
            "modules/parametrizacion/op/defaults/portfolio_clientes.yaml",
        ]
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for rel_path in forbidden_paths:
            full = os.path.join(base, rel_path)
            assert not os.path.exists(full), (
                f"Forbidden portfolio YAML found: {full}. "
                "Portfolio data must come from active OP parametrization only."
            )
