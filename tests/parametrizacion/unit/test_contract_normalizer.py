"""Unit tests for ContractValueNormalizer.

Validates every ColumnType conversion rule individually, then verifies
characterization values from the production Excel files.
"""

from __future__ import annotations

import pytest

from nexa_engine.modules.parametrizacion.shared.contracts.base import (
    ColumnContract,
    ColumnType,
    ModuleContract,
    SheetContract,
    SheetType,
)
from nexa_engine.modules.parametrizacion.shared.contracts.normalizer import (
    ContractValueNormalizer,
    normalize_sheets_by_contract,
)
from nexa_engine.modules.shared.exceptions import ValidationError

_PCT = ColumnType.PERCENTAGE_DECIMAL
_DEC = ColumnType.DECIMAL
_FAC = ColumnType.FACTOR
_NUM = ColumnType.NUMBER
_MON = ColumnType.MONEY
_INT = ColumnType.INT
_CAT = ColumnType.CATALOG
_S = ColumnType.STRING


def _contract(*columns: tuple) -> ModuleContract:
    """Helper: build a minimal ModuleContract for one sheet."""
    cols = [ColumnContract(h, t) for h, t in columns]
    sheet = SheetContract("TEST", required=True, sheet_type=SheetType.TABLE_ROWS, columns=cols)
    return ModuleContract(module="test", sheet_prefix="TEST", sheets=[sheet])


# ---------------------------------------------------------------------------
# percentage_decimal
# ---------------------------------------------------------------------------

class TestPercentageDecimal:

    def _norm(self, val):
        contract = _contract(("Valor", _PCT))
        result = normalize_sheets_by_contract({"TEST": [{"valor": val}]}, contract)
        return result["TEST"][0]["valor"]

    def test_percent_string_17(self):
        assert self._norm("17.00%") == pytest.approx(0.17)

    def test_percent_string_18(self):
        assert self._norm("18.00%") == pytest.approx(0.18)

    def test_percent_string_10_50(self):
        assert self._norm("10.50%") == pytest.approx(0.105)

    def test_percent_string_comma_separator(self):
        assert self._norm("10,50%") == pytest.approx(0.105)

    def test_percent_string_32_92(self):
        assert self._norm("32.92%") == pytest.approx(0.3292)

    def test_already_decimal_float(self):
        """0.17 stays 0.17 — no double division."""
        assert self._norm(0.17) == pytest.approx(0.17)

    def test_already_decimal_string(self):
        """'0.0735' → 0.0735 — no division (no % suffix)."""
        assert self._norm("0.0735") == pytest.approx(0.0735)

    def test_small_decimal_0_7(self):
        assert self._norm("0.7") == pytest.approx(0.7)

    def test_small_decimal_0_085(self):
        assert self._norm("0.085") == pytest.approx(0.085)

    def test_small_decimal_0_0833(self):
        assert self._norm("0.0833") == pytest.approx(0.0833)

    def test_integer_float(self):
        """Integer float (1.0) → 1.0 as-is."""
        assert self._norm(1.0) == pytest.approx(1.0)

    def test_none_returns_none(self):
        assert self._norm(None) is None

    def test_invalid_percent_string_raises(self):
        with pytest.raises(ValidationError):
            self._norm("abc%")


# ---------------------------------------------------------------------------
# decimal
# ---------------------------------------------------------------------------

class TestDecimal:

    def _norm(self, val):
        contract = _contract(("Valor", _DEC))
        result = normalize_sheets_by_contract({"TEST": [{"valor": val}]}, contract)
        return result["TEST"][0]["valor"]

    def test_decimal_string(self):
        assert self._norm("0.0153") == pytest.approx(0.0153)

    def test_decimal_float(self):
        assert self._norm(0.0527) == pytest.approx(0.0527)

    def test_does_not_divide_percent_string(self):
        """Decimal type does NOT treat % strings as percentage — error."""
        # A value like "17.00%" in a decimal column is a data quality issue
        # The % is stripped and 17.0 is returned (same as old heuristic)
        # since decimal just parses the numeric part
        # Actually % strings should fail decimal type or be stored as-is...
        # Per spec: decimal does NOT divide. But a % suffix is unexpected.
        # Implementation: _as_float strips % via _parse_numeric_str? No.
        # _as_float calls _parse_numeric_str which does NOT strip %.
        # So "17.00%" in a decimal column raises ValidationError.
        with pytest.raises(ValidationError):
            self._norm("17.00%")

    def test_comma_decimal_separator(self):
        assert self._norm("0,0153") == pytest.approx(0.0153)

    def test_none_returns_none(self):
        assert self._norm(None) is None


# ---------------------------------------------------------------------------
# factor
# ---------------------------------------------------------------------------

class TestFactor:

    def _norm(self, val):
        contract = _contract(("Valor", _FAC))
        result = normalize_sheets_by_contract({"TEST": [{"valor": val}]}, contract)
        return result["TEST"][0]["valor"]

    def test_one(self):
        assert self._norm(1) == pytest.approx(1.0)

    def test_factor_1_24(self):
        assert self._norm(1.24) == pytest.approx(1.24)

    def test_factor_1_39(self):
        assert self._norm(1.39) == pytest.approx(1.39)

    def test_factor_string(self):
        assert self._norm("1.24") == pytest.approx(1.24)

    def test_factor_not_divided(self):
        """1.24 must NOT be divided; it is a multiplicative factor."""
        assert self._norm(1.24) > 1.0


# ---------------------------------------------------------------------------
# money / number
# ---------------------------------------------------------------------------

class TestMoneyNumber:

    def _norm(self, val, col_type=_MON):
        contract = _contract(("Valor", col_type))
        result = normalize_sheets_by_contract({"TEST": [{"valor": val}]}, contract)
        return result["TEST"][0]["valor"]

    def test_large_monetary_int(self):
        assert self._norm(1750905) == pytest.approx(1750905.0)

    def test_small_monetary_float(self):
        assert self._norm(11.757) == pytest.approx(11.757)

    def test_monetary_string(self):
        assert self._norm("153301") == pytest.approx(153301.0)

    def test_no_rounding(self):
        assert self._norm(415975.45769999997) == pytest.approx(415975.45769999997)

    def test_zero(self):
        assert self._norm(0) == pytest.approx(0.0)

    def test_number_type(self):
        assert self._norm(20.0, _NUM) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# int
# ---------------------------------------------------------------------------

class TestInt:

    def _norm(self, val):
        contract = _contract(("Mes", _INT))
        result = normalize_sheets_by_contract({"TEST": [{"mes": val}]}, contract)
        return result["TEST"][0]["mes"]

    def test_integer(self):
        assert self._norm(1) == 1
        assert isinstance(self._norm(1), int)

    def test_integer_from_string(self):
        assert self._norm("2026") == 2026

    def test_integer_from_float_string(self):
        assert self._norm("2026.0") == 2026

    def test_integer_from_float(self):
        assert self._norm(60.0) == 60

    def test_non_integer_decimal_raises(self):
        with pytest.raises(ValidationError):
            self._norm(1.5)

    def test_non_integer_string_raises(self):
        with pytest.raises(ValidationError):
            self._norm("1.5")

    def test_none_returns_none(self):
        assert self._norm(None) is None


# ---------------------------------------------------------------------------
# string / catalog
# ---------------------------------------------------------------------------

class TestStringCatalog:

    def _norm(self, val, col_type=_CAT):
        contract = _contract(("Nombre", col_type))
        result = normalize_sheets_by_contract({"TEST": [{"nombre": val}]}, contract)
        return result["TEST"][0]["nombre"]

    def test_plain_string(self):
        assert self._norm("Cobranzas") == "Cobranzas"

    def test_string_with_embedded_percent(self):
        """Strings containing % must NOT be converted — they are descriptive text."""
        assert self._norm("70% SMMLV - 30% IPC") == "70% SMMLV - 30% IPC"

    def test_string_with_special_chars(self):
        txt = "Comisión de Administración (1,18% sobre ventas Comercial-Operaciones)"
        assert self._norm(txt) == txt

    def test_accents_preserved(self):
        assert self._norm("Prestación") == "Prestación"

    def test_external_whitespace_trimmed(self):
        assert self._norm("  Director de cuentas  ") == "Director de cuentas"

    def test_internal_spaces_preserved(self):
        assert self._norm("Centro de Costo") == "Centro de Costo"

    def test_none_returns_none(self):
        assert self._norm(None) is None

    def test_empty_string_returns_none(self):
        assert self._norm("") is None


# ---------------------------------------------------------------------------
# Security: injection prevention (from normalizer.py guard)
# ---------------------------------------------------------------------------

class TestInjectionPrevention:

    def _norm(self, val):
        contract = _contract(("Col", _S))
        result = normalize_sheets_by_contract({"TEST": [{"col": val}]}, contract)
        return result["TEST"][0]["col"]

    def test_rejects_equals_prefix(self):
        with pytest.raises(ValidationError):
            self._norm("=SUM(A1:A10)")

    def test_rejects_at_prefix(self):
        with pytest.raises(ValidationError):
            self._norm("@cmd /c evil")

    def test_accepts_leading_minus_number(self):
        """'-5' is a valid negative number string, not injection."""
        contract = _contract(("Col", _NUM))
        result = normalize_sheets_by_contract({"TEST": [{"col": "-5"}]}, contract)
        assert result["TEST"][0]["col"] == pytest.approx(-5.0)

    def test_accepts_leading_plus_number(self):
        contract = _contract(("Col", _NUM))
        result = normalize_sheets_by_contract({"TEST": [{"col": "+3.14"}]}, contract)
        assert result["TEST"][0]["col"] == pytest.approx(3.14)


# ---------------------------------------------------------------------------
# Characterization tests against expected production values
# ---------------------------------------------------------------------------

class TestProductionCharacterization:
    """Verify exact output values expected from real production Excel data."""

    def _norm_sheet(self, sheet_name, rows, contract):
        return normalize_sheets_by_contract({sheet_name: rows}, contract)[sheet_name]

    def test_hr_rentabilidad_minimo_17pct(self):
        """HR-Rentabilidad 'Minimo'='17.00%' → 0.17 (not 17.0)."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [{"categoriaservicio": "Cobranzas", "minimo": "17.00%", "margenobjetivo": "18.00%"}]
        result = self._norm_sheet("HR-Rentabilidad", rows, HR_CONTRACT)
        assert result[0]["minimo"] == pytest.approx(0.17)
        assert result[0]["margenobjetivo"] == pytest.approx(0.18)

    def test_hr_rentabilidad_multiple_values(self):
        """Full set of HR-Rentabilidad percentages from production."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [
            {"categoriaservicio": "Cobranzas",         "minimo": "17.00%", "margenobjetivo": "18.00%"},
            {"categoriaservicio": "Sac",                "minimo": "17.00%", "margenobjetivo": "18.00%"},
            {"categoriaservicio": "Ventas multicanal",  "minimo": "17.00%", "margenobjetivo": "18.00%"},
            {"categoriaservicio": "SACO",               "minimo": "10.50%", "margenobjetivo": "10.50%"},
        ]
        result = self._norm_sheet("HR-Rentabilidad", rows, HR_CONTRACT)
        assert result[0]["minimo"] == pytest.approx(0.17)
        assert result[2]["minimo"] == pytest.approx(0.17)
        assert result[3]["minimo"] == pytest.approx(0.105)
        assert result[3]["margenobjetivo"] == pytest.approx(0.105)

    def test_hr_autrot_valor_decimal(self):
        """HR-AutRot 'Valor'='0.0735' stays as 0.0735 — not divided."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [{"tipo": "Ausentismo", "servicio": "Cobranzas", "mes": 1, "valor": "0.0735"}]
        result = self._norm_sheet("HR-AutRot", rows, HR_CONTRACT)
        assert result[0]["valor"] == pytest.approx(0.0735)

    def test_hr_campana_valor_factor(self):
        """HR-Campana 'Valor'=0.85 stays as 0.85 (ramp-up factor, no division)."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [
            {"categoriaservicio": "Cobranzas", "mes": 1, "valor": "0.85"},
            {"categoriaservicio": "Sac",        "mes": 1, "valor": "0.9"},
            {"categoriaservicio": "Cobranzas", "mes": 60, "valor": "1"},
        ]
        result = self._norm_sheet("HR-Campana", rows, HR_CONTRACT)
        assert result[0]["valor"] == pytest.approx(0.85)
        assert result[1]["valor"] == pytest.approx(0.9)
        assert result[2]["valor"] == pytest.approx(1.0)

    def test_hr_campana_mes_is_int(self):
        """HR-Campana 'Mes' is typed int."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [{"categoriaservicio": "Cob", "mes": "1", "valor": "0.85"}]
        result = self._norm_sheet("HR-Campana", rows, HR_CONTRACT)
        assert result[0]["mes"] == 1
        assert isinstance(result[0]["mes"], int)

    def test_hr_costo_fijo_valor_monetary(self):
        """HR-CostoFijo 'Valor' values are monetary COP — not divided."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [
            {"localidad": "Barranquilla - Barranquilla", "servicio": "Energía",         "valor": 153301},
            {"localidad": "Barranquilla - Barranquilla", "servicio": "Aseo y Cafeteria","valor": 11.757},
        ]
        result = self._norm_sheet("HR-CostoFijo", rows, HR_CONTRACT)
        assert result[0]["valor"] == pytest.approx(153301.0)
        assert result[1]["valor"] == pytest.approx(11.757)

    def test_op_componente_valor_decimal(self):
        """OP-Componente 'Valor'='0.0527' stays as 0.0527 (decimal, no %  suffix)."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [{"componente": "IPC", "ano": 2025, "valor": "0.0527"}]
        result = self._norm_sheet("OP-Componente", rows, OP_CONTRACT)
        assert result[0]["valor"] == pytest.approx(0.0527)

    def test_op_componente_acumulado_factor(self):
        """OP-ComponenteAcumulado 'Valor' values are multiplicative factors."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [
            {"componente": "IPC", "ano": 2025, "valor": 1},
            {"componente": "IPC", "ano": 2026, "valor": 1.24},
            {"componente": "IPC", "ano": 2027, "valor": 1.39},
        ]
        result = self._norm_sheet("OP-ComponenteAcumulado", rows, OP_CONTRACT)
        assert result[0]["valor"] == pytest.approx(1.0)
        assert result[1]["valor"] == pytest.approx(1.24)
        assert result[2]["valor"] == pytest.approx(1.39)

    def test_op_poliza_valor_decimal(self):
        """OP-Poliza 'Valor' values are decimal fractions."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [
            {"poliza": "Póliza de Seriedad",     "valor": "0.005"},
            {"poliza": "Póliza de Cumplimiento", "valor": "0.0062"},
        ]
        result = self._norm_sheet("OP-Poliza", rows, OP_CONTRACT)
        assert result[0]["valor"] == pytest.approx(0.005)
        assert result[1]["valor"] == pytest.approx(0.0062)

    def test_op_tasa_valor_decimal_string(self):
        """OP-Tasa 'valor'='0.0153' → float 0.0153 (typed decimal)."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [{"tasa": "tasa interes mensual", "valor": "0.0153"}]
        result = self._norm_sheet("OP-Tasa", rows, OP_CONTRACT)
        assert result[0]["valor"] == pytest.approx(0.0153)
        assert isinstance(result[0]["valor"], float)

    def test_hr_salario_basico_cumplimineto_variable(self):
        """%Cumplimiento Variable row: valor='0.7' → 0.7 (already decimal, number type)."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [
            {"servicio": "Salario Mínimo",           "valor": "1750905"},
            {"servicio": "%Cumplimiento Variable",   "valor": "0.7"},
        ]
        result = self._norm_sheet("HR-SalarioBasico", rows, HR_CONTRACT)
        assert result[0]["valor"] == pytest.approx(1750905.0)
        assert result[1]["valor"] == pytest.approx(0.7)

    def test_gn_lv_string_with_embedded_percent_preserved(self):
        """GN-LV 'Componente' may contain '70% SMMLV - 30% IPC' — must stay string."""
        from nexa_engine.modules.parametrizacion.gn.contracts import GN_CONTRACT
        rows = [{"componente": "70% SMMLV - 30% IPC", "ciudad": "Bogota",
                 "localidad": "Bogota Norte", "servicio": "Cob", "categoriaservicio": "BPO",
                 "centrocosto": "CC", "poliza": "P1", "componentefijo": "F",
                 "hardwaresoftware": "PC", "periodopago": "Mensual", "cadena": "A",
                 "componentevariable": "V", "modelocombro": "M", "modalidad": "I",
                 "reglanegocio": "R", "canal": "D", "metrica": "M2", "cliente": "BM",
                 "tipocobro": "T", "tipocliente": "TA", "rubro": "R1", "unidadmedida": "U"}]
        result = self._norm_sheet("GN-LV", rows, GN_CONTRACT)
        assert result[0]["componente"] == "70% SMMLV - 30% IPC"

    def test_hr_op_catalogs_trim_only(self):
        """Catalog values get external whitespace trimmed, accents preserved."""
        from nexa_engine.modules.parametrizacion.hr.contracts import HR_CONTRACT
        rows = [{"tipo": " Empleado ", "rol": "  Director de cuentas  ",
                 "servicio": "Cobranzas", "prestaciones": "Cesantías",
                 "ssparafiscales": "Salud", "recargo": "Recargo festivo"}]
        result = self._norm_sheet("HR-LV", rows, HR_CONTRACT)
        assert result[0]["tipo"] == "Empleado"
        assert result[0]["rol"] == "Director de cuentas"
        assert result[0]["prestaciones"] == "Cesantías"  # accent preserved

    def test_op_hard_soft_cantidad_mes_is_int(self):
        """OP-HardSoft 'CantidadMes' typed as int."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [{"hardwaresoftware": "Computador", "valor": 3508260, "cantidadmes": "60", "tipo": "Operativo"}]
        result = self._norm_sheet("OP-HardSoft", rows, OP_CONTRACT)
        assert result[0]["cantidadmes"] == 60
        assert isinstance(result[0]["cantidadmes"], int)

    def test_op_componente_ano_is_int(self):
        """OP-Componente 'Año' → int."""
        from nexa_engine.modules.parametrizacion.op.contracts import OP_CONTRACT
        rows = [{"componente": "IPC", "ano": "2025", "valor": "0.0527"}]
        result = self._norm_sheet("OP-Componente", rows, OP_CONTRACT)
        assert result[0]["ano"] == 2025
        assert isinstance(result[0]["ano"], int)
