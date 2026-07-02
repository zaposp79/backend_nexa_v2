"""OP module upload contract — single source of truth.

Based on production file: OP_productiva_2026-05-11-10-35-25.xlsx

Sheet inventory (all optional):
  OP-LV, OP-OPEXFijo, OP-HardSoft, OP-DispositivoRequerido,
  OP-Componente, OP-ComponenteAcumulado, OP-Poliza, OP-PolizaFija, OP-Costo,
  OP-MargenObjetivo, OP-MargenBruto, OP-GraficoMargenBruto, OP-ICA.

Column-type decisions
---------------------
OP-Componente.Valor
    Production values: ``0.0527``, ``0.12`` — decimal fractions (IPC index).
    Typed ``percentage_decimal``: ``"0.0527"`` → ``0.0527`` (no ``%`` suffix).

OP-ComponenteAcumulado.Valor
    Cumulative factors like ``1``, ``1.24``, ``1.39``.  Typed ``factor``.

OP-Poliza.Porcentaje / OP-Poliza.PorcentajeExigido
    Insurance rates as decimal fractions (e.g. ``0.005``, ``0.0062``).
    Column renamed from ``Valor`` to ``Porcentaje`` in Excel V2-8; added
    ``PorcentajeExigido`` as second numeric column.
    Both typed ``percentage_decimal``.

OP-ICA.Valor
    Production values like ``0.6``.  The validator emits a warning if ICA >
    5% because the business unit uses the column with ambiguous scale.
    Typed ``decimal`` (store as-is) pending explicit business approval to
    normalize to the standard decimal fraction.  Range warnings are generated
    by :class:`~op.validators.validator.OPValidator`.

OP-MargenBruto / OP-GraficoMargenBruto
    Report-style sheets from the workbook with margin data by service/client.
    OP-MargenBruto: detailed breakdown by Servicio + Cliente + MargenBruto (3 cols).
    OP-GraficoMargenBruto: summary by Servicios + MargenBruto (2 cols).
    The ``MargenBruto`` column is typed as ``percentage_decimal``: decimal
    fractions like ``0.13`` (13%), ``-0.22`` (-22%), ``null`` for #DIV/0! errors.

OP-HardSoft.Tipo
    Multi-value string like ``"Operativo;Agente"`` — typed ``raw_text`` to
    preserve the separator.
"""

from nexa_engine.modules.parametrizacion.shared.contracts.base import (
    ColumnContract,
    ColumnType,
    ModuleContract,
    SheetContract,
    SheetType,
)

_CAT = ColumnType.CATALOG
_S = ColumnType.STRING
_RT = ColumnType.RAW_TEXT
_PCT = ColumnType.PERCENTAGE_DECIMAL
_DEC = ColumnType.DECIMAL
_FAC = ColumnType.FACTOR
_NUM = ColumnType.NUMBER
_MON = ColumnType.MONEY
_INT = ColumnType.INT

OP_LV = SheetContract(
    excel_name="OP-LV",
    required=False,
    sheet_type=SheetType.CATALOG_BY_COLUMN,
    columns=[
        ColumnContract("ICA",                  _CAT),
        ColumnContract("DispositivoRequerido", _CAT),
        ColumnContract("DuracionMes",          _INT),
        ColumnContract("InteresIndexMensual",  _DEC),
    ],
    allow_trailing_unnamed=False,
)

OP_OPEX_FIJO = SheetContract(
    excel_name="OP-OPEXFijo",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("OPEXItem", _S),
        ColumnContract("Valor",    _MON),
    ],
    allow_trailing_unnamed=False,
)

OP_HARD_SOFT = SheetContract(
    excel_name="OP-HardSoft",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("HardwareSoftware", _S),
        ColumnContract("Valor",            _MON),
        ColumnContract("CantidadMes",      _INT),
        ColumnContract("Tipo",             _RT),  # "Operativo;Agente"
    ],
    allow_trailing_unnamed=False,
)

OP_DISPOSITIVO_REQUERIDO = SheetContract(
    excel_name="OP-DispositivoRequerido",
    required=False,
    sheet_type=SheetType.CATALOG_BY_COLUMN,
    columns=[ColumnContract("DispositivoRequerido", _CAT)],
    allow_trailing_unnamed=False,
)

OP_COMPONENTE = SheetContract(
    excel_name="OP-Componente",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Componente", _S),
        ColumnContract("Año",        _INT),
        ColumnContract("Valor",      _PCT),  # 0.0527 = 5.27% IPC — decimal
    ],
    allow_trailing_unnamed=False,
)

OP_COMPONENTE_ACUMULADO = SheetContract(
    excel_name="OP-ComponenteAcumulado",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Componente", _S),
        ColumnContract("Año",        _INT),
        ColumnContract("Valor",      _FAC),  # cumulative factor: 1, 1.24, 1.39
    ],
    allow_trailing_unnamed=False,
)

OP_POLIZA = SheetContract(
    excel_name="OP-Poliza",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Poliza",               _S),
        ColumnContract("Porcentaje",           _PCT),  # 0.005 = 0.5% — decimal
        ColumnContract("PorcentajeExigido",    _PCT),  # required percentage
    ],
    allow_trailing_unnamed=False,
)

OP_POLIZA_FIJA = SheetContract(
    excel_name="OP-PolizaFija",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Poliza",      _S),
        ColumnContract("Porcentaje",  _PCT),  # fixed percentage
    ],
    allow_trailing_unnamed=False,
)

OP_COSTO = SheetContract(
    excel_name="OP-Costo",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("CostoOperativo", _S),
        ColumnContract("Valor",          _MON),
    ],
    allow_trailing_unnamed=False,
)

OP_MARGEN_OBJETIVO = SheetContract(
    excel_name="OP-MargenObjetivo",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Cadena",       _S),
        ColumnContract("Porcentaje",   _PCT),
    ],
    allow_trailing_unnamed=False,
)


OP_MARGEN_BRUTO = SheetContract(
    excel_name="OP-MargenBruto",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Servicio",    _S),
        ColumnContract("Cliente",     _S),
        ColumnContract("MargenBruto", _PCT),
    ],
    allow_trailing_unnamed=False,
)


OP_GRAFICO_MARGEN_BRUTO = SheetContract(
    excel_name="OP-GraficoMargenBruto",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Servicios",   _S),
        ColumnContract("MargenBruto", _PCT),
    ],
    allow_trailing_unnamed=False,
)


OP_ICA = SheetContract(
    excel_name="OP-ICA",
    required=False,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Ciudad", _S),
        ColumnContract("ICA",    _S),   # category (e.g. "Tasa", "Avisos & Tableros")
        ColumnContract("Valor",  _DEC), # decimal — unit ambiguous, see docstring
    ],
    allow_trailing_unnamed=False,
)


OP_CONTRACT = ModuleContract(
    module="op",
    sheet_prefix="OP-",
    sheets=[
        OP_LV,
        OP_OPEX_FIJO,
        OP_HARD_SOFT,
        OP_DISPOSITIVO_REQUERIDO,
        OP_COMPONENTE,
        OP_COMPONENTE_ACUMULADO,
        OP_POLIZA,
        OP_POLIZA_FIJA,
        OP_COSTO,
        OP_MARGEN_OBJETIVO,
        OP_MARGEN_BRUTO,
        OP_GRAFICO_MARGEN_BRUTO,
        OP_ICA,
    ],
)
