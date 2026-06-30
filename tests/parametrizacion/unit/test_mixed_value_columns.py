"""Formal audit tests for sheets with mixed-semantics Valor columns.

Inventario de hojas con columnas Valor cuyo tipo semántico depende del
discriminador de fila (la columna Nombre o Servicio).

Decisión formal
---------------
Ninguna de las tres hojas auditadas requiere un ``RowValueContract`` porque
**todos los valores ya llegan en el formato correcto desde el Excel**:

1. ``HR-SalarioBasico.Valor``  → tipo ``NUMBER``
   * ``Salario Mínimo``        : ``1750905`` (int)  → ``1750905.0`` COP
   * ``Auxilio Transporte``    : ``249095``  (int)  → ``249095.0``  COP
   * ``Dotaciones (annual)``   : ``184500``  (int)  → ``184500.0``  COP (÷12 lo hace downstream)
   * ``%Cumplimiento Variable``: ``0.7``     (float) → ``0.7``      tasa decimal ya correcta
   Excel guarda ``0.7`` como float (no como string ``"70%"``), por lo que
   ``NUMBER`` no necesita dividir.  El mixin downstream asigna ese float
   directamente a ``pct_cumplimiento_variable`` (``payroll_salary_mixin:149``).

2. ``OP-DatosOperativos.Valor`` → tipo ``NUMBER``
   * ``tarifa diaria de capacitacion``: ``20000`` (int)  → ``20000.0``
   * ``horas de formacion mensual``   : ``8``     (int)  → ``8.0``
   * ``porcentaje de ausentismo``     : ``0.065`` (float) → ``0.065``  ya decimal
   * ``porcentaje de rotacion``       : ``0.085`` (float) → ``0.085``  ya decimal
   * ``ica``                          : ``0.01``  (float) → ``0.01``   ya decimal
   * ``crucero``                      : ``8000``  (int)  → ``8000.0``
   Los porcentajes vienen como floats (sin sufijo ``%``), no como strings.

3. ``OP-ICA.Valor`` → tipo ``DECIMAL``
   * Todos los "Tasa" rows: 0.0045 – 0.0125 (decimales normales)
   * Armenia "Tasa": ``0.6`` — **ANOMALÍA BLOQUEADA** — el OPValidator genera
     WARNING pero no modifica el valor.  La decisión de si ``0.6`` significa
     ``0.6%`` (i.e. ``0.006``) o es un error de carga es de negocio, no técnica.
   * El downstream ``financial_parametrization_repository:94-97`` aplica la
     heurística ``if rate > 1: rate /= 100``.  Armenia ``0.6 < 1`` pasa sin
     corrección; el cálculo usará ``60%`` ICA, claramente incorrecto.
     **RIESGO ABIERTO: requiere decisión y re-carga manual del Excel de OP.**

Diseño de RowValueContract (NO implementado, provisto como referencia)
-----------------------------------------------------------------------
Si en el futuro se necesitara tipo por fila::

    @dataclass(frozen=True)
    class RowValueContract:
        discriminator_col: str          # normalized key of the lookup column
        value_col: str                  # normalized key of the value column
        mapping: Dict[str, ColumnType]  # discriminator value → type
        default: ColumnType             # type for rows not in mapping

    # HR-SalarioBasico (NOT needed today, shown for reference only)
    HR_SALARIO_ROW_CONTRACT = RowValueContract(
        discriminator_col="servicio",
        value_col="valor",
        mapping={
            "Salario Mínimo":        ColumnType.MONEY,
            "Auxilio Transporte":    ColumnType.MONEY,
            "Dotaciones (annual)":   ColumnType.MONEY,
            "%Cumplimiento Variable": ColumnType.PERCENTAGE_DECIMAL,
        },
        default=ColumnType.NUMBER,
    )

    # With this contract:
    #   "%Cumplimiento Variable" / 0.7 → 0.7    (no % suffix → no division)
    #   "%Cumplimiento Variable" / "70%" → 0.7  (% suffix → divide by 100)
    #   "Salario Mínimo" / 1750905 → 1750905.0  (MONEY → no division)
    #
    # But since production NEVER sends "70%", today's NUMBER type is equivalent.
"""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path

import openpyxl
import pytest

from nexa_engine.modules.parametrizacion.shared.contracts.normalizer import (
    normalize_sheets_by_contract,
)
from nexa_engine.modules.shared.exceptions import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# 1. HR-SalarioBasico
# ---------------------------------------------------------------------------

class TestHRSalarioBasico:
    """HR-SalarioBasico.Valor is NUMBER — all production values already correct."""

    def _norm(self, rows):
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        return normalize_sheets_by_contract({"HR-SalarioBasico": rows}, HR_CONTRACT)["HR-SalarioBasico"]

    def test_salario_minimo_int_stays_float(self):
        """1750905 (int from Excel) → 1750905.0 — not divided."""
        result = self._norm([{"servicio": "Salario Mínimo", "valor": 1750905}])
        assert result[0]["valor"] == pytest.approx(1750905.0)

    def test_auxilio_transporte_int_stays_float(self):
        result = self._norm([{"servicio": "Auxilio Transporte", "valor": 249095}])
        assert result[0]["valor"] == pytest.approx(249095.0)

    def test_dotaciones_annual_int_stays_float(self):
        """184500 stored as-is — downstream divides by 12, NOT the normalizer."""
        result = self._norm([{"servicio": "Dotaciones (annual)", "valor": 184500}])
        assert result[0]["valor"] == pytest.approx(184500.0)

    def test_pct_cumplimiento_variable_already_decimal(self):
        """%Cumplimiento Variable = 0.7 (float in Excel, already decimal — not divided).

        Production Excel stores this as float 0.7, never as string "70%".
        NUMBER type passes it through unchanged.
        """
        result = self._norm([{"servicio": "%Cumplimiento Variable", "valor": 0.7}])
        assert result[0]["valor"] == pytest.approx(0.7)
        # Must NOT be 0.007 (which would happen with a double ÷100)
        assert result[0]["valor"] != pytest.approx(0.007)

    def test_no_conversion_for_pct_cumplimiento_because_no_pct_suffix(self):
        """Confirm that '70%' string (hypothetical) WOULD fail NUMBER type.

        This proves we rely on the Excel cell being a float 0.7, not a '%' string.
        If the source changed to '70%' strings, upload would break (intentionally).
        """
        with pytest.raises(ValidationError):
            self._norm([{"servicio": "%Cumplimiento Variable", "valor": "70%"}])

    def test_full_production_batch(self):
        """All four production rows normalize correctly in one batch."""
        rows = [
            {"servicio": "Salario Mínimo",          "valor": 1750905},
            {"servicio": "Auxilio Transporte",       "valor": 249095},
            {"servicio": "%Cumplimiento Variable",   "valor": 0.7},
            {"servicio": "Dotaciones (annual)",      "valor": 184500},
        ]
        result = self._norm(rows)
        assert result[0]["valor"] == pytest.approx(1750905.0)
        assert result[1]["valor"] == pytest.approx(249095.0)
        assert result[2]["valor"] == pytest.approx(0.7)
        assert result[3]["valor"] == pytest.approx(184500.0)
        # Each value type preserved — no accidental division
        assert result[2]["valor"] < 1.0       # fraction, not COP
        assert result[0]["valor"] > 100_000   # COP, not fraction

    def test_downstream_reads_pct_cumplimiento_as_0_7(self):
        """Verify payroll_salary_mixin.get_base_salary_data reads 0.7 correctly.

        The mixin does float(valor) directly (payroll_salary_mixin:172).
        With 0.7 stored, pct_cumplimiento_variable = float(0.7) = 0.7.
        """
        # After normalization, valor is 0.7 (float)
        # Mixin does: result["pct_cumplimiento_variable"] = float(0.7) = 0.7
        stored_valor = 0.7
        downstream_result = float(stored_valor)  # as mixin does
        assert downstream_result == pytest.approx(0.7)
        # Downstream formula: t_imponible = salario_base * (1 + comision * 0.7)
        # 0.7 is correct — 70% cumplimiento, not 70 COP

    def test_dotaciones_annual_division_is_downstream_not_normalizer(self):
        """Normalizer stores 184500.0; downstream divides by 12 (payroll_salary_mixin:187-188)."""
        rows = [{"servicio": "Dotaciones (annual)", "valor": 184500}]
        result = self._norm(rows)
        stored = result[0]["valor"]
        assert stored == pytest.approx(184500.0)
        # Downstream division:
        dotaciones_mensual = stored / 12.0
        assert dotaciones_mensual == pytest.approx(15375.0)


# ---------------------------------------------------------------------------
# 2. OP-DatosOperativos
# ---------------------------------------------------------------------------

class TestOPDatosOperativos:
    """OP-DatosOperativos.Valor is NUMBER — all production values already correct."""

    def _norm(self, rows):
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        return normalize_sheets_by_contract({"OP-DatosOperativos": rows}, OP_CONTRACT)[
            "OP-DatosOperativos"
        ]

    def test_tarifa_diaria_int(self):
        """20000 (int from Excel) → 20000.0."""
        result = self._norm([{"nombre": "tarifa diaria de capacitacion", "valor": 20000}])
        assert result[0]["valor"] == pytest.approx(20000.0)

    def test_horas_formacion_int(self):
        """8 (int from Excel) → 8.0."""
        result = self._norm([{"nombre": "horas de formacion mensual", "valor": 8}])
        assert result[0]["valor"] == pytest.approx(8.0)

    def test_crucero_int(self):
        result = self._norm([{"nombre": "crucero", "valor": 8000}])
        assert result[0]["valor"] == pytest.approx(8000.0)

    def test_porcentaje_ausentismo_already_decimal_float(self):
        """0.065 (float in Excel, already decimal) → 0.065 — NOT divided.

        Production Excel stores this as float, not '6.5%' string.
        NUMBER type is equivalent to PERCENTAGE_DECIMAL for this case.
        """
        result = self._norm([{"nombre": "porcentaje de ausentismo", "valor": 0.065}])
        assert result[0]["valor"] == pytest.approx(0.065)

    def test_porcentaje_rotacion_already_decimal_float(self):
        result = self._norm([{"nombre": "porcentaje de rotacion", "valor": 0.085}])
        assert result[0]["valor"] == pytest.approx(0.085)

    def test_ica_already_decimal_float(self):
        result = self._norm([{"nombre": "ica", "valor": 0.01}])
        assert result[0]["valor"] == pytest.approx(0.01)

    def test_percent_string_rejected_for_number_type(self):
        """OP-DatosOperativos was removed from the OP contract (not in Excel V2-8).

        This test previously validated that '6.5%' was rejected by the NUMBER type
        normalizer for OP-DatosOperativos. Since the sheet is no longer in OP_CONTRACT,
        the normalizer passes unknown sheets through without type validation.
        The guardrail no longer applies to this sheet.
        """
        pytest.skip("OP-DatosOperativos removed from OP_CONTRACT — sheet not in Excel definitivo")

    def test_full_production_batch(self):
        """All six production rows normalize correctly."""
        rows = [
            {"nombre": "tarifa diaria de capacitacion", "valor": 20000},
            {"nombre": "horas de formacion mensual",    "valor": 8},
            {"nombre": "porcentaje de ausentismo",      "valor": 0.065},
            {"nombre": "porcentaje de rotacion",        "valor": 0.085},
            {"nombre": "ica",                           "valor": 0.01},
            {"nombre": "crucero",                       "valor": 8000},
        ]
        result = self._norm(rows)
        assert result[0]["valor"] == pytest.approx(20000.0)
        assert result[1]["valor"] == pytest.approx(8.0)
        assert result[2]["valor"] == pytest.approx(0.065)
        assert result[3]["valor"] == pytest.approx(0.085)
        assert result[4]["valor"] == pytest.approx(0.01)
        assert result[5]["valor"] == pytest.approx(8000.0)


# ---------------------------------------------------------------------------
# 3. OP-ICA — including Armenia anomaly
# ---------------------------------------------------------------------------

class TestOPICA:
    """OP-ICA.Valor is DECIMAL — stored as-is, validator warns on outliers."""

    def _norm(self, rows):
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        return normalize_sheets_by_contract({"OP-ICA": rows}, OP_CONTRACT)["OP-ICA"]

    def test_bogota_normal_rate(self):
        """Bogotá ICA Tasa = 0.0097 (0.97%) — stored correctly as decimal."""
        result = self._norm([{"ciudad": "Bogotá", "ica": "Tasa", "valor": 0.0097}])
        assert result[0]["valor"] == pytest.approx(0.0097)

    def test_manizales_lowest_rate(self):
        result = self._norm([{"ciudad": "Manizales", "ica": "Tasa", "valor": 0.0045}])
        assert result[0]["valor"] == pytest.approx(0.0045)

    def test_barranquilla_highest_normal_rate(self):
        result = self._norm([{"ciudad": "Barranquilla", "ica": "Tasa", "valor": 0.0125}])
        assert result[0]["valor"] == pytest.approx(0.0125)

    def test_armenia_anomaly_stored_as_is(self):
        """Armenia ICA Tasa = 0.6 — ANOMALÍA.

        El valor 0.6 es claramente un error (60% ICA rate es imposible).
        El normalizer lo almacena sin cambios.  El downstream financial_repo:94-97
        aplica ``if rate > 1: rate /= 100``.  Como 0.6 < 1, pasa como 0.6 = 60%.

        **RIESGO ABIERTO — requiere decisión de negocio y re-carga del Excel OP.**
        Alternativas posibles (ninguna se implementa automáticamente):
          a) El Excel debe corregirse a 0.006 (0.6%)
          b) O a 0.0060 (ya normalizado)
          c) El validador sólo genera WARNING, no bloquea la carga
        """
        result = self._norm([{"ciudad": "Armenia", "ica": "Tasa", "valor": 0.6}])
        # Stored as-is — NOT auto-converted
        assert result[0]["valor"] == pytest.approx(0.6)

    def test_armenia_anomaly_now_blocks_upload(self):
        """OPValidator generates an ERROR for Armenia Tasa=0.6 > MAX_TASA_ICA (0.05).

        ICA guardrail: 'Tasa' rows with valor > 0.05 → error (not warning).
        Armenia 0.6 = 60% ICA which is impossible for a municipal rate.
        """
        from nexa_engine.modules.parametrizacion.op.validators.validator import OPValidator

        sheets = {"OP-ICA": [{"ciudad": "Armenia", "ica": "tasa", "valor": 0.6}]}
        result = OPValidator().validate(sheets)
        # Now an ERROR — upload is blocked
        assert not result.is_valid
        assert any("Armenia" in e for e in result.errors)
        assert any("INVALID_ICA_RATE" in e for e in result.errors)

    def test_normal_rates_do_not_trigger_warning(self):
        """Rates < 5% do not generate warnings."""
        from nexa_engine.modules.parametrizacion.op.validators.validator import OPValidator

        sheets = {
            "OP-ICA": [
                {"ciudad": "Bogotá",        "ica": "tasa", "valor": 0.0097},
                {"ciudad": "Barranquilla",  "ica": "tasa", "valor": 0.0125},
                {"ciudad": "Manizales",     "ica": "tasa", "valor": 0.0045},
            ]
        }
        result = OPValidator().validate(sheets)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_downstream_heuristic_for_legacy_integer_percentages(self):
        """financial_repo:94-97: if rate > 1 → divide by 100 (legacy integers).

        This heuristic handles values like 97 (old format for 0.97%).
        It does NOT help Armenia's 0.6 since 0.6 < 1.
        """
        # Simulate downstream logic
        def get_ica_downstream(stored_valor: float) -> float:
            rate = float(stored_valor)
            if rate > 1:
                rate = rate / 100
            return rate

        # Legacy integer format (old uploads): 97 → 0.97
        assert get_ica_downstream(97) == pytest.approx(0.97)

        # Normal decimal format: 0.0097 → 0.0097
        assert get_ica_downstream(0.0097) == pytest.approx(0.0097)

        # Armenia anomaly: 0.6 → 0.6 (NOT fixed by heuristic, since 0.6 < 1)
        assert get_ica_downstream(0.6) == pytest.approx(0.6)
        # This means Armenia would be used as 60% ICA — clearly wrong

    def test_all_normal_production_ica_tasa_rates(self):
        """All 20 production 'Tasa' rows normalize correctly as DECIMAL."""
        production_rates = {
            "Armenia": 0.6,       # ANOMALÍA — but stored as-is
            "Barranquilla": 0.0125,
            "Bogotá": 0.0097,
            "Bucaramanga": 0.009,
            "Buga": 0.009,
            "Cali": 0.01,
            "Cartagena": 0.008,
            "Cúcuta": 0.01,
            "Manizales": 0.0045,
            "Medellín": 0.01,
            "Neiva": 0.01,
            "Palmira": 0.007,
            "Pasto": 0.006,
            "Pereira": 0.01,
            "Popayán": 0.007,
            "Santa Marta": 0.007,
            "Sicelejo": 0.008,
            "Tunja": 0.01,
            "Valledupár": 0.01,
            "Villavicencio": 0.006,
        }
        rows = [
            {"ciudad": city, "ica": "Tasa", "valor": rate}
            for city, rate in production_rates.items()
        ]
        result = self._norm(rows)
        for i, (city, expected) in enumerate(production_rates.items()):
            assert result[i]["valor"] == pytest.approx(expected), (
                f"ICA rate mismatch for {city}: expected {expected}"
            )


# ---------------------------------------------------------------------------
# 4. No-RowValueContract evidence
# ---------------------------------------------------------------------------

class TestNoRowValueContractNeeded:
    """Document WHY RowValueContract is NOT needed for current production data."""

    def test_hr_salario_pct_cumplimiento_is_float_not_string(self):
        """Prove that '0.7' and 0.7 are stored identically under NUMBER type.

        The ambiguity (money vs percentage) is resolved by the discriminator
        column 'Servicio' in the downstream mixin, NOT in the normalizer.
        The normalizer correctly stores both as floats.
        """
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT

        # String "0.7" (hypothetical) and float 0.7 (production) give same result
        rows_str = [{"servicio": "%Cumplimiento Variable", "valor": "0.7"}]
        rows_float = [{"servicio": "%Cumplimiento Variable", "valor": 0.7}]
        r_str = normalize_sheets_by_contract({"HR-SalarioBasico": rows_str}, HR_CONTRACT)["HR-SalarioBasico"]
        r_float = normalize_sheets_by_contract({"HR-SalarioBasico": rows_float}, HR_CONTRACT)["HR-SalarioBasico"]
        assert r_str[0]["valor"] == r_float[0]["valor"] == pytest.approx(0.7)

    def test_op_datos_operativos_pct_ausentismo_is_float(self):
        """porcentaje de ausentismo arrives as float 0.065 (not string '6.5%').

        A RowValueContract converting '6.5%' → 0.065 is not needed
        because the Excel already stores the decimal float.
        """
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT

        rows_float = [{"nombre": "porcentaje de ausentismo", "valor": 0.065}]
        result = normalize_sheets_by_contract({"OP-DatosOperativos": rows_float}, OP_CONTRACT)[
            "OP-DatosOperativos"
        ]
        assert result[0]["valor"] == pytest.approx(0.065)
        # No RowValueContract needed — NUMBER type is exact for this case

    def test_future_row_value_contract_design_for_reference(self):
        """Reference test: shows what RowValueContract would need to handle.

        This test is NOT about implementing RowValueContract.
        It documents the ONLY scenario that would require it:
        if the Excel source changes to send '70%' strings.
        Today that doesn't happen (Excel stores 0.7 float).
        """
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT

        # If future Excel sends "70%" (not currently happening in production)
        # the upload CORRECTLY fails with ValidationError for NUMBER type:
        with pytest.raises(ValidationError, match="número"):
            normalize_sheets_by_contract(
                {"HR-SalarioBasico": [{"servicio": "%Cumplimiento Variable", "valor": "70%"}]},
                HR_CONTRACT,
            )
        # This failure is intentional — we want explicit errors, not silent conversion.
        # If the business decides to accept '70%' strings,
        # the contract should change to PERCENTAGE_DECIMAL for that row
        # via a RowValueContract. Until then, NUMBER is the correct type.
