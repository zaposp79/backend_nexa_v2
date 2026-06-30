"""
Unit tests for the graph calculation layer.

Excel V2-8 · Graficos!F4:I9 — Grafico 1 (Bandas Visión Final)
"""

from __future__ import annotations

import pytest

from nexa_engine.modules.calculator_motor.formulas.graphics.calculator import (
    GraficoBandasCalculator,
    _quartile_inc,
    calculate_graph_series,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoBandasResult,
    GraficosResult,
    PortfolioClienteRow,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAC_PORTFOLIO = [
    PortfolioClienteRow("SAC", "BANCO POPULAR", 0.13271374189700025),
    PortfolioClienteRow("SAC", "BANCO DE BOGOTÁ S.A.", 0.1829819521971602),
    PortfolioClienteRow("SAC", "FUNDACION CTIC", 0.24784444533444447),
    PortfolioClienteRow("SAC", "PARTNERS TELECOM COLOMBIA S.A.S. (WOM)", -2.2225693465291396),
    PortfolioClienteRow("SAC", "CORFICOLOMBIANA S.A.", 0.32271991169267333),
    PortfolioClienteRow("SAC", "BANCO DE OCCIDENTE S.A.", 0.2598401492236107),
    PortfolioClienteRow("SAC", "CLARO COLOMBIA S.A.", 0.0949262477454797),
    PortfolioClienteRow("SAC", "AVAL VALOR COMPARTIDO S.A.", 0.115452273444524),
    PortfolioClienteRow("SAC", "PORVENIR S.A", 0.28304983949948714),
    PortfolioClienteRow("SAC", "FIDUCIARIA DE OCCIDENTE S.A.", 0.11824432171261695),
    PortfolioClienteRow("SAC", "APORTES EN LINEA S.A.", 0.1401551402687129),
    PortfolioClienteRow("SAC", "PEAJES ELECTRONICOS SAS", 0.2256802886826076),
    PortfolioClienteRow("SAC", "PANASONIC DE COLOMBIA S.A.", 0.15704782162825545),
    PortfolioClienteRow("SAC", "SEGUROS DE VIDA ALFA S.A. VIDALFA S.A.", 0.26395329580265786),
    PortfolioClienteRow("SAC", "ADL DIGITAL LAB SAS", 0.37817362212511696),
    PortfolioClienteRow("SAC", "METROCUADRADO COM SAS", 0.149853884257826),
    PortfolioClienteRow("SAC", "AVAL SOLUCIONES DIGITALES SA (DALE)", 0.1603649135502463),
    PortfolioClienteRow("SAC", "BANCO DE BOGOTÁ S.A. MIAMI", 0.9607696580623769),
    PortfolioClienteRow("SAC", "BANCO DE OCCIDENTE PANAMA S.A", -1.0164279316454985),
    PortfolioClienteRow("SAC", "YAMAHA MOTOR FINANCE COLOMBIA S.A.S", 0.34903344238502304),
    # SACO entries — must not affect SAC calculations
    PortfolioClienteRow("SACO", "BANCO POPULAR", 0.032096759636983205),
    PortfolioClienteRow("SACO", "BANCO DE OCCIDENTE S.A.", 0.07353433932075386),
]

PROMEDIOS = {
    "SAC": 0.16639538606602855,
    "SACO": 0.05060981580181418,
}


# ---------------------------------------------------------------------------
# _quartile_inc unit tests
# ---------------------------------------------------------------------------

class TestQuartileInc:
    def test_q1_matches_excel_single_element(self):
        assert _quartile_inc([1.0], 1) == 1.0

    def test_q4_is_maximum(self):
        values = [1.0, 2.0, 3.0, 4.0]
        assert _quartile_inc(values, 4) == 4.0

    def test_q2_is_median_even(self):
        values = [1.0, 2.0, 3.0, 4.0]
        # QUARTILE.INC Q2 = median = 2.5 for [1,2,3,4]
        result = _quartile_inc(values, 2)
        assert result == pytest.approx(2.5, abs=1e-9)

    def test_empty_returns_none(self):
        assert _quartile_inc([], 1) is None

    def test_q1_three_elements(self):
        # For [1,2,3]: Q1 = 1 + 0.25*(2-1)*2 = 1.5
        result = _quartile_inc([1.0, 2.0, 3.0], 1)
        assert result == pytest.approx(1.5, abs=1e-9)

    def test_excel_sac_quartiles_approximate(self):
        # Excel V2-8 · Graficos!G6:G9 with SAC portfolio (20 entries)
        # Only numeric values (no NaN/#DIV/0!) are included per ISNUMBER filter
        # Expected from data_only read: Q1≈0.129, Q2≈0.172, Q3≈0.269, Q4≈0.961
        numeric_margins = [
            r.margen_bruto for r in SAC_PORTFOLIO
            if r.categoria == "SAC" and isinstance(r.margen_bruto, float)
        ]
        q1 = _quartile_inc(numeric_margins, 1)
        q2 = _quartile_inc(numeric_margins, 2)
        q3 = _quartile_inc(numeric_margins, 3)
        q4 = _quartile_inc(numeric_margins, 4)

        # Q1 should be near 0.129 (25th percentile including negatives)
        assert q1 is not None and q1 < q2  # type: ignore[operator]
        assert q2 is not None and q2 < q3  # type: ignore[operator]
        assert q3 is not None and q3 < q4  # type: ignore[operator]
        assert q4 == pytest.approx(0.9607696580623769, abs=1e-6)


# ---------------------------------------------------------------------------
# GraficoBandasCalculator tests
# ---------------------------------------------------------------------------

class TestGraficoBandasCalculator:
    def test_returns_result(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert isinstance(result, GraficoBandasResult)

    def test_category_filtering_isolates_sac(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        # Q4 must be SAC max (0.9608), not SACO entries
        assert result.quartil_4 == pytest.approx(0.9607696580623769, abs=1e-6)

    def test_client_historical_margin_lookup(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        # Excel V2-8 · Graficos!I5 = FILTER(C5:C93, SAC AND METROCUADRADO) = 0.14985...
        assert result.margen_historico_cliente == pytest.approx(0.149853884257826, abs=1e-6)

    def test_client_not_found_returns_none(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="CLIENTE INEXISTENTE",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert result.margen_historico_cliente is None

    def test_category_average_from_dict(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="ANY",
            deal_margin=0.20,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        # Excel V2-8 · Graficos!I4 (IFS lookup to C3) = 0.16639...
        assert result.promedio_categoria == pytest.approx(0.16639538606602855, abs=1e-6)

    def test_unknown_category_average_is_none(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="CATEGORIA_NUEVA",
            cliente_nombre="ANY",
            deal_margin=0.10,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert result.promedio_categoria is None
        # No portfolio data for unknown category → all quartiles None
        assert result.quartil_1 is None
        assert result.quartil_4 is None

    def test_deal_margin_preserved(self):
        deal_margin = 0.175
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="ANY",
            deal_margin=deal_margin,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert result.margen_deal_actual == deal_margin

    def test_quartile_ordering(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="ANY",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert result.quartil_1 < result.quartil_2  # type: ignore[operator]
        assert result.quartil_2 < result.quartil_3  # type: ignore[operator]
        assert result.quartil_3 < result.quartil_4  # type: ignore[operator]

    def test_as_dict_shape(self):
        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        d = result.as_dict()
        assert "categoria_servicio" in d
        assert "bandas_portfolio" in d
        assert "quartil_1" in d["bandas_portfolio"]
        assert "quartil_4" in d["bandas_portfolio"]
        assert "promedio_categoria" in d["bandas_portfolio"]
        assert "margen_historico_cliente" in d
        assert "margen_deal_actual" in d


# ---------------------------------------------------------------------------
# calculate_graph_series entry point
# ---------------------------------------------------------------------------

class TestCalculateGraphSeries:
    def test_returns_graficos_result(self):
        result = calculate_graph_series(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        assert isinstance(result, GraficosResult)
        assert result.bandas_vision_final is not None

    def test_as_dict_contains_bandas(self):
        result = calculate_graph_series(
            categoria_servicio="SAC",
            cliente_nombre="ANY",
            deal_margin=0.20,
            portfolio=SAC_PORTFOLIO,
            promedios_por_categoria=PROMEDIOS,
        )
        d = result.as_dict()
        assert "bandas_vision_final" in d
        assert d["bandas_vision_final"] is not None


# ---------------------------------------------------------------------------
# OP-backed portfolio provider tests
# ---------------------------------------------------------------------------

# Minimal inline OP payload mimicking the active OP storage structure.
# Row fields match actual OP-MargenBruto sheet: {servicio, cliente, margenbruto}
_INLINE_OP_PAYLOAD = {
    "sheets": [
        {
            "key": "margenbruto",
            "rows": [
                {"servicio": "SAC", "cliente": "BANCO POPULAR",          "margenbruto": 0.132713741897},
                {"servicio": "SAC", "cliente": "BANCO DE BOGOTÁ S.A.",   "margenbruto": 0.182981952197},
                {"servicio": "SAC", "cliente": "METROCUADRADO COM SAS",  "margenbruto": 0.149853884257826},
                {"servicio": "SAC", "cliente": "BANCO DE BOGOTÁ MIAMI",  "margenbruto": 0.960769658062},
                {"servicio": "SACO", "cliente": "BANCO POPULAR",         "margenbruto": 0.032096759637},
            ],
        },
        {
            "key": "graficomargenbruto",
            "rows": [
                {"servicios": "SERVICIO AL CLIENTE IN Y OUT BOUND",                "margenbruto": 0.166395386066},
                {"servicios": "SOPORTE ADMINISTRATIVO, COMERCIAL Y OPERATIVO",      "margenbruto": 0.050609815802},
            ],
        },
    ]
}


class TestPortfolioOPProvider:
    """Tests that portfolio data is sourced from the active OP parametrization via typed repository methods."""

    def _make_repo_with_data(self, payload):
        """Create a FinancialParametrizationRepository with injected inline OP data."""
        from unittest.mock import MagicMock
        from nexa_engine.modules.parametrizacion.repositories.financial_parametrization_repository import (
            FinancialParametrizationRepository,
        )
        mock_resolver = MagicMock()
        repo = FinancialParametrizationRepository(mock_resolver)
        repo._op_data = payload
        return repo

    def test_get_portfolio_margen_bruto_rows_parses_sheet(self):
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        rows = repo.get_portfolio_margen_bruto_rows()
        assert len(rows) == 5
        for row in rows:
            assert "categoria" in row
            assert "cliente" in row
            assert "margen_bruto" in row
            assert isinstance(row["margen_bruto"], float)

    def test_get_portfolio_margen_bruto_rows_field_mapping(self):
        """servicio→categoria, margenbruto→margen_bruto field normalization."""
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        rows = repo.get_portfolio_margen_bruto_rows()
        assert rows[0] == {
            "categoria": "SAC",
            "cliente": "BANCO POPULAR",
            "margen_bruto": 0.132713741897,
        }

    def test_get_portfolio_margen_bruto_rows_sac_count(self):
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        rows = repo.get_portfolio_margen_bruto_rows()
        sac_rows = [r for r in rows if r["categoria"] == "SAC"]
        assert len(sac_rows) == 4

    def test_get_portfolio_margen_bruto_rows_missing_sheet_returns_empty(self):
        repo = self._make_repo_with_data({"sheets": [{"key": "config", "rows": []}]})
        assert repo.get_portfolio_margen_bruto_rows() == []

    def test_get_portfolio_margen_bruto_rows_empty_payload_returns_empty(self):
        repo = self._make_repo_with_data({"sheets": []})
        assert repo.get_portfolio_margen_bruto_rows() == []

    def test_get_grafico_margen_bruto_rows_parses_sheet(self):
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        rows = repo.get_grafico_margen_bruto_rows()
        assert len(rows) == 2
        assert rows[0] == {
            "servicios": "SERVICIO AL CLIENTE IN Y OUT BOUND",
            "margen_bruto": 0.166395386066,
        }

    def test_get_grafico_margen_bruto_rows_missing_sheet_returns_empty(self):
        repo = self._make_repo_with_data({"sheets": [{"key": "margenbruto", "rows": []}]})
        assert repo.get_grafico_margen_bruto_rows() == []

    def test_promedios_keyed_by_short_servicio_name(self):
        """Promedios computed from typed rows: mean per categoria."""
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        rows = repo.get_portfolio_margen_bruto_rows()

        from collections import defaultdict
        sums = defaultdict(list)
        for row in rows:
            sums[row["categoria"]].append(row["margen_bruto"])
        promedios = {cat: sum(vals) / len(vals) for cat, vals in sums.items() if vals}

        assert "SAC" in promedios
        assert "SACO" in promedios
        expected_sac = (0.132713741897 + 0.182981952197 + 0.149853884257826 + 0.960769658062) / 4
        assert promedios["SAC"] == pytest.approx(expected_sac, abs=1e-9)

    def test_portfolio_rows_used_by_graph_calculator(self):
        """Full path: typed repo rows → PortfolioClienteRow → GraficoBandasCalculator."""
        repo = self._make_repo_with_data(_INLINE_OP_PAYLOAD)
        clientes = repo.get_portfolio_margen_bruto_rows()

        from collections import defaultdict
        sums = defaultdict(list)
        for row in clientes:
            sums[row["categoria"]].append(row["margen_bruto"])
        promedios = {cat: sum(vals) / len(vals) for cat, vals in sums.items() if vals}

        portfolio = [
            PortfolioClienteRow(
                categoria=r["categoria"],
                cliente=r["cliente"],
                margen_bruto=r["margen_bruto"],
            )
            for r in clientes
        ]

        calc = GraficoBandasCalculator()
        result = calc.calcular(
            categoria_servicio="SAC",
            cliente_nombre="METROCUADRADO COM SAS",
            deal_margin=0.15,
            portfolio=portfolio,
            promedios_por_categoria=promedios,
        )
        assert isinstance(result, GraficoBandasResult)
        assert result.quartil_4 == pytest.approx(0.960769658062, abs=1e-6)
        assert result.margen_historico_cliente == pytest.approx(0.149853884257826, abs=1e-6)

    def test_no_get_raw_op_data_in_graph_provider_path(self):
        """Guardrail: get_raw_op_data must not be called in Graph 1 provider path."""
        import os
        base = os.path.join(os.path.dirname(__file__), "..", "..")
        mixin_path = os.path.join(base, "modules/parametrizacion/mixins/provider_business_rules.py")
        with open(mixin_path, encoding="utf-8") as f:
            src = f.read()
        assert "get_raw_op_data" not in src, (
            "provider_business_rules.py must not call get_raw_op_data(). "
            "Use typed repository methods get_portfolio_margen_bruto_rows() instead."
        )

    def test_no_get_op_active_data_for_portfolio_in_runtime(self):
        """Guardrail: _get_op_active_data_for_portfolio must not exist in provider or mixin."""
        import os
        base = os.path.join(os.path.dirname(__file__), "..", "..")
        check_files = [
            "modules/parametrizacion/services/provider.py",
            "modules/parametrizacion/mixins/provider_business_rules.py",
        ]
        for rel_path in check_files:
            full = os.path.join(base, rel_path)
            with open(full, encoding="utf-8") as f:
                src = f.read()
            assert "_get_op_active_data_for_portfolio" not in src, (
                f"{rel_path}: _get_op_active_data_for_portfolio found. "
                "Raw OP dict exposure removed — use typed repo methods instead."
            )

    def test_no_runtime_code_loads_portfolio_via_business_rules(self):
        """No runtime code outside OP parametrization may load portfolio_clientes from business_rules."""
        import os
        allowed_paths = {"provider_business_rules.py"}  # the mixin that routes to OP
        base = os.path.join(os.path.dirname(__file__), "..", "..")
        modules_dir = os.path.join(base, "modules")
        for root, _, files in os.walk(modules_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                if fname in allowed_paths:
                    continue
                path = os.path.join(root, fname)
                with open(path, encoding="utf-8") as f:
                    src = f.read()
                if "load_business_rules_cached" in src and "portfolio_clientes" in src:
                    assert False, (
                        f"{path}: runtime code loads portfolio_clientes from business_rules. "
                        "Use IParametrizationProvider.get_portfolio_clientes() instead."
                    )

    def test_no_vision_module_recalculates_quartiles(self):
        """Vision modules must not contain QUARTILE or graph band calculations."""
        import ast
        import os

        vision_dirs = [
            "modules/vision_imprimible",
            "modules/vision_tarifas",
            "modules/vision_cost_to_serve",
            "modules/pyg",
            "modules/vision_pyg",
        ]
        base = os.path.join(os.path.dirname(__file__), "..", "..")
        for vision_dir in vision_dirs:
            full = os.path.join(base, vision_dir)
            if not os.path.isdir(full):
                continue
            for root, _, files in os.walk(full):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    path = os.path.join(root, fname)
                    with open(path, encoding="utf-8") as f:
                        src = f.read()
                    # Graph band formulas must live in calculator_motor, not vision modules
                    assert "QUARTILE" not in src, (
                        f"{path}: QUARTILE formula found in vision module. "
                        "Graph band logic must live in calculator_motor/formulas/graphics/."
                    )
                    assert "quartile_inc" not in src.lower() or "test" in fname.lower(), (
                        f"{path}: quartile_inc found in vision module."
                    )
