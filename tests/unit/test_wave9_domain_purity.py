"""
WAVE 9 — Domain purity & strangler shim tests.

Validates:
  1. New domain calculators produce identical numerics to legacy paths.
  2. domain/* modules don't import IO/logging/JSON/openpyxl/HTTP libraries.
  3. application/ports are importable and the null implementations are no-ops.
  4. infrastructure/logging.StructuredLogger emits messages.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Numeric parity — domain vs legacy
# ---------------------------------------------------------------------------


def test_factor_billing_matches_legacy_formula():
    from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator

    m, op_c, com_c, mk, d = 0.20, 0.06, 0.05, 0.04, 0.03
    fb = ProfitabilityCalculator.calcular_factor_billing(m, op_c, com_c, mk, d)
    expected = (1 - m) * (1 - op_c) * (1 - com_c) * (1 - mk) * (1 + d)
    assert fb == pytest.approx(expected, rel=1e-12)


def test_factor_margenes_panel_canonical():
    # Phase 5I: shared_calc.utils deleted. ProfitabilityCalculator is now the single source.
    from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator

    class _Panel:
        margen = 0.18
        op_cont = 0.05
        com_cont = 0.04
        markup = 0.02
        descuento = 0.01

    result = ProfitabilityCalculator.calcular_factor_margenes(_Panel())
    expected = (1 - 0.18) * (1 - 0.05) * (1 - 0.04) * (1 - 0.02) * (1 + 0.01)
    assert result == pytest.approx(expected, rel=1e-12)


def test_factor_aumento_canonical():
    # Phase 5I: shared_calc.utils deleted. PayrollCalculator is now the single source.
    from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

    cases = {1: 1.0, 12: 1.0, 13: 1.10, 24: 1.10, 25: 1.21, 36: 1.21}
    for mes, expected in cases.items():
        result = PayrollCalculator.calcular_factor_aumento(mes, 0.10, 13)
        assert result == pytest.approx(expected, rel=1e-9), f"mes={mes}"


def test_pricing_componentes_label_matches_legacy():
    from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator
    from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

    for modelo, pct in [
        ("Fijo FTE", 1.0),
        ("Variable", 0.0),
        ("Híbrido", 0.6),
        ("desconocido", 1.0),
        ("desconocido", 0.5),
    ]:
        assert VisionTarifasCalculator._componentes_label(
            modelo, pct
        ) == PricingCalculator.derivar_componentes_label(modelo, pct)


def test_financial_pure_calculators_basic():
    from nexa_engine.modules.calculator_motor.formulas.costos_financieros.financiacion import FinancialCalculator

    # ICA gross-up: base = costo/factor + polizas + financiacion
    ica = FinancialCalculator.calcular_ica(
        costo=1000.0, polizas=10.0, financiacion=5.0, tasa_ica=0.01, factor_margenes=0.8
    )
    expected = ((1000.0 / 0.8) + 10.0 + 5.0) * 0.01
    assert ica == pytest.approx(expected, rel=1e-12)

    # GMF
    gmf = FinancialCalculator.calcular_gmf(
        costo=1000.0, polizas=10.0, financiacion=5.0, tasa_gmf=0.004
    )
    assert gmf == pytest.approx((1000 + 10 + 5) * 0.004, rel=1e-12)


def test_staffing_rampup_clamps():
    from nexa_engine.modules.cadena_a.staffing.calculators import StaffingCalculator

    assert StaffingCalculator.aplicar_rampup(10.0, 0.5) == 5.0
    assert StaffingCalculator.aplicar_rampup(10.0, 0.0) == 0.0
    assert StaffingCalculator.aplicar_rampup(-5.0, 0.5) == 0.0


# ---------------------------------------------------------------------------
# 2. Domain purity — static import scan
# ---------------------------------------------------------------------------


DOMAIN_FORBIDDEN_TOP_LEVEL = {
    "logging",
    "requests",
    "httpx",
    "fastapi",
    "openpyxl",
    "xlrd",
    "pandas",
}


def _domain_files():
    root = Path(__file__).resolve().parents[2] / "domain"
    # Only the WAVE9-added sub-domains. The legacy domain/models/, services/, etc.
    # are not yet pure — they're Pydantic + helpers and pre-date WAVE 9.
    wave9_subdirs = ["pricing", "payroll", "staffing", "financial", "profitability", "risk", "shared"]
    for sub in wave9_subdirs:
        for f in (root / sub).glob("*.py"):
            yield f


def test_domain_modules_do_not_import_io():
    """No WAVE 9 domain/* module imports logging/requests/openpyxl/etc."""
    violations: list[str] = []
    for path in _domain_files():
        src = path.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in DOMAIN_FORBIDDEN_TOP_LEVEL:
                        violations.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top in DOMAIN_FORBIDDEN_TOP_LEVEL:
                        violations.append(f"{path}: from {node.module}")
    assert not violations, "Domain purity violated:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# 3. Ports — null implementations
# ---------------------------------------------------------------------------


def test_null_logger_is_silent(caplog):
    from nexa_engine.modules.shared.ports.logger import NullLogger

    log = NullLogger()
    with caplog.at_level(logging.INFO):
        log.info("hello", x=1)
        log.warning("warn", y=2)
        log.debug("d")
        log.error("e")
    assert caplog.records == []


def test_null_trace_emitter_returns_none():
    from nexa_engine.modules.shared.ports.trace_emitter import NullTraceEmitter

    tracer = NullTraceEmitter()
    assert tracer.emit("stage", {"a": 1}, {"b": 2}, "src") is None


def test_iparametrization_provider_lives_in_ports():
    from typing import Protocol

    from nexa_engine.modules.shared.ports.parametrization_provider import (
        IParametrizationProvider,
    )

    # The ports module is the single canonical home of the Protocol; the legacy
    # modules/shared/i_parametrization_provider.py shim was removed.
    assert issubclass(IParametrizationProvider, Protocol)
    assert (
        IParametrizationProvider.__module__
        == "nexa_engine.modules.shared.ports.parametrization_provider"
    )


# ---------------------------------------------------------------------------
# 4. Infrastructure logger — emits real records
# ---------------------------------------------------------------------------


def test_structured_logger_emits(caplog):
    from nexa_engine.modules.shared.infrastructure.logging import StructuredLogger

    log = StructuredLogger("nexa_engine.test.wave9")
    with caplog.at_level(logging.INFO, logger="nexa_engine.test.wave9"):
        log.info("[PAYROLL_BUILD] op=test", mes=1, value=42)
    assert any("[PAYROLL_BUILD]" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 5. Use cases — DI works with null ports
# ---------------------------------------------------------------------------


def test_build_pricing_use_case_runs_with_null_ports():
    from nexa_engine.modules.calculator_motor.use_cases.build_pricing import BuildPricingUseCase

    uc = BuildPricingUseCase()  # NullLogger + NullTraceEmitter
    fb = uc.calcular_factor_billing(0.2, 0.06, 0.05, 0.04, 0.03, cadena="A")
    assert fb > 0
    ingreso = uc.calcular_ingreso_bruto(costo=1000.0, factor_billing=fb)
    assert ingreso == pytest.approx(1000.0 / fb, rel=1e-12)


def test_build_payroll_use_case_runs():
    from nexa_engine.modules.cadena_a.use_cases.build_payroll import BuildPayrollUseCase

    uc = BuildPayrollUseCase()
    f = uc.calcular_factor_indexacion(
        factor_base=1.18, pct_aumento=0.10, mes_aplicacion=13, mes=14
    )
    assert f == pytest.approx(1.18 * 1.10, rel=1e-12)
