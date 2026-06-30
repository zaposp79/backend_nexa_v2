"""Base types for Excel upload contracts.

Each module (GN, HR, OP) defines a :class:`ModuleContract` that is the single
source of truth for:

* Authorized sheet names (exact, case-sensitive).
* Required vs optional sheets.
* Expected column headers per sheet (exact, before normalization).
* Column-level type information (used by the contract normalizer).
* Whether trailing unnamed (None) column headers are allowed.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict


class SheetType(str, Enum):
    CATALOG_BY_COLUMN = "catalog_by_column"
    TABLE_ROWS = "table_rows"
    KEY_VALUE = "key_value"


class ColumnType(str, Enum):
    """Semantic type of a column's values.

    Controls how :class:`ContractValueNormalizer` converts raw cell values.

    string / catalog / raw_text
        Keep value as-is (external whitespace trimmed).
        Accents, internal spaces, symbols, and embedded % are preserved.
        No numeric conversion.

    percentage_decimal
        If the raw value is a string ending with ``%`` (e.g. ``"17.00%"``):
            strip %, parse float, divide by 100 → ``0.17``.
        Otherwise (already a decimal float or string like ``"0.17"``):
            parse as float, no division.

    decimal
        Parse as float.  No % stripping, no division.
        Suitable for rates already expressed as decimal (``0.0153``).

    factor
        Parse as float.  Multiplicators like ``1``, ``1.24``.
        Semantically different from decimal but same conversion.

    money / number
        Parse as float.  No rounding, no division.

    int
        Parse as integer.  Decimal strings that are whole numbers are accepted
        (``"2026.0"`` → ``2026``).  Non-integer decimals raise a
        :class:`ValidationError`.

    raw_value
        No conversion.  Return the raw openpyxl value unchanged.
    """

    STRING = "string"
    CATALOG = "catalog"
    RAW_TEXT = "raw_text"
    PERCENTAGE_DECIMAL = "percentage_decimal"
    DECIMAL = "decimal"
    FACTOR = "factor"
    MONEY = "money"
    NUMBER = "number"
    INT = "int"
    RAW_VALUE = "raw_value"


class ColumnContract(BaseModel):
    """Contract for a single Excel column.

    Attributes
    ----------
    excel_header:
        Exact column header as it appears in the production Excel file
        (stripped of leading/trailing whitespace, same case, accents, symbols).
    col_type:
        Semantic type that drives conversion in
        :class:`~shared.contracts.normalizer.ContractValueNormalizer`.
    nullable:
        When ``False``, empty cells cause a validation warning.
        (Default: ``True`` — empty cells silently become ``None``.)
    """

    model_config = ConfigDict(frozen=True)

    excel_header: str
    col_type: ColumnType
    nullable: bool = True

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) > 3:
                raise TypeError(
                    f"ColumnContract() takes at most 3 positional arguments ({len(args)} given)"
                )
            field_names = ("excel_header", "col_type", "nullable")
            for i, arg in enumerate(args):
                kwargs.setdefault(field_names[i], arg)
        super().__init__(**kwargs)


class SheetContract(BaseModel):
    """Contract for a single Excel sheet.

    Attributes
    ----------
    excel_name:
        Exact sheet name as it appears in the workbook (case-sensitive).
    required:
        Whether the sheet MUST be present in every upload.
    sheet_type:
        Structural classification of the sheet.
    columns:
        Ordered tuple of :class:`ColumnContract` that define exact headers and
        types.  Used both for header validation and for value normalization.
    allow_trailing_unnamed:
        When True, additional ``None`` / empty trailing columns in the Excel
        are silently ignored.  Named extra columns are still rejected.
    """

    model_config = ConfigDict(frozen=True)

    excel_name: str
    required: bool
    sheet_type: SheetType
    columns: tuple[ColumnContract, ...]
    allow_trailing_unnamed: bool = False

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) > 5:
                raise TypeError(
                    f"SheetContract() takes at most 5 positional arguments ({len(args)} given)"
                )
            field_names = ("excel_name", "required", "sheet_type", "columns", "allow_trailing_unnamed")
            for i, arg in enumerate(args):
                kwargs.setdefault(field_names[i], arg)
        super().__init__(**kwargs)

    @property
    def headers(self) -> tuple[str, ...]:
        """Exact header strings expected in the Excel (in contract order)."""
        return tuple(c.excel_header for c in self.columns)


class ModuleContract(BaseModel):
    """Contract for an entire module upload (GN, HR, or OP).

    Attributes
    ----------
    module:
        Module identifier (``"gn"``, ``"hr"``, ``"op"``).
    sheet_prefix:
        The prefix that all module sheets share (e.g. ``"HR-"``).
    sheets:
        Ordered tuple of :class:`SheetContract` — defines every authorized sheet.
        Sheets not listed here are rejected.
    """

    model_config = ConfigDict(frozen=True)

    module: str
    sheet_prefix: str
    sheets: tuple[SheetContract, ...]

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) > 3:
                raise TypeError(
                    f"ModuleContract() takes at most 3 positional arguments ({len(args)} given)"
                )
            field_names = ("module", "sheet_prefix", "sheets")
            for i, arg in enumerate(args):
                kwargs.setdefault(field_names[i], arg)
        super().__init__(**kwargs)

    def get_sheet(self, excel_name: str) -> Optional[SheetContract]:
        """Return the contract for *excel_name*, or ``None`` if not found."""
        return next((s for s in self.sheets if s.excel_name == excel_name), None)

    @property
    def authorized_names(self) -> FrozenSet[str]:
        return frozenset(s.excel_name for s in self.sheets)

    @property
    def required_names(self) -> FrozenSet[str]:
        return frozenset(s.excel_name for s in self.sheets if s.required)
