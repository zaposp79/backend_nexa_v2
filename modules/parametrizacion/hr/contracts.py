"""HR module upload contract — single source of truth.

Based on production file: HR_productiva_2026-05-11-09-52-29.xlsx

Sheet inventory:
  Required (17, all): HR-LV, HR-SalarioBasico, HR-Nomina, HR-Recargos,
                      HR-SegSocial, HR-Prestaciones, HR-Ratios,
                      HR-Complejidad, HR-Rentabilidad, HR-Campana,
                      HR-AutRot, HR-CostoFijo, HR-Med-Seg,
                      HR-Ratios-HITL, HR-Hora-GTR,
                      HR-EquipoHITL, HR-EquipoSoporteMantenimiento

Column-type decisions
---------------------
HR-SalarioBasico.Valor
    Typed as ``number``. Rows include both large monetary values (1 750 905 COP)
    and the ``%Cumplimiento Variable`` row which stores a decimal like ``0.7``.
    Since all values arrive as numeric strings without ``%`` suffix, ``number``
    is the correct type (no division).  Using ``percentage_decimal`` would give
    the same result for ``0.7`` (no ``%`` suffix → no division) but is
    semantically misleading for the monetary rows.

HR-Recargos.Valor / HR-SegSocial.Proporcion / HR-Prestaciones.Valor / HR-AutRot.Valor
    All arrive as decimal strings (``"0.35"``, ``"0.085"``, ``"0.0833"``).
    Typed as ``percentage_decimal``.  Since there is no ``%`` suffix the
    conversion is identical to ``decimal``, but the contract documents the
    intended semantics (these are rates expressed as decimal fractions).

HR-Rentabilidad.Minimo / HR-Rentabilidad.MargenObjetivo
    Arrive as ``"17.00%"`` strings (text with ``%``).
    Typed as ``percentage_decimal`` → ``"17.00%"`` → ``0.17``.
    The downstream repository (``profitability_parametrization_repository``)
    NO LONGER divides by 100 after this fix.

HR-Campana.Mes / HR-AutRot.Mes / OP-Componente.Año / OP-HardSoft.CantidadMes
    Typed as ``int``.

HR-LV columns (5)
    All catalog (string) — independent value lists per column:
    TipoRecurso, Cargo, Prestaciones, SS&Parafiscales, Recargo.
    EquipoHITL and EquipoSoporteMantenimiento removed (now separate optional sheets).
"""

from nexa_engine.modules.parametrizacion.shared.contracts.base import (
    ColumnContract,
    ColumnType,
    ModuleContract,
    SheetContract,
    SheetType,
)

_S = ColumnType.STRING
_CAT = ColumnType.CATALOG
_PCT = ColumnType.PERCENTAGE_DECIMAL
_DEC = ColumnType.DECIMAL
_NUM = ColumnType.NUMBER
_MON = ColumnType.MONEY
_INT = ColumnType.INT
_FAC = ColumnType.FACTOR

HR_LV = SheetContract(
    excel_name="HR-LV",
    required=True,
    sheet_type=SheetType.CATALOG_BY_COLUMN,
    columns=[
        ColumnContract("TipoRecurso",     _CAT),
        ColumnContract("Cargo",           _CAT),
        ColumnContract("Prestaciones",    _CAT),
        ColumnContract("SS&Parafiscales", _CAT),
        ColumnContract("Recargo",         _CAT),
    ],
    allow_trailing_unnamed=False,
)

HR_SALARIO_BASICO = SheetContract(
    excel_name="HR-SalarioBasico",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Servicio", _S),
        ColumnContract("Valor",    _NUM),  # monetary + %Cumplimiento (0.7 decimal)
    ],
    allow_trailing_unnamed=False,
)

HR_NOMINA = SheetContract(
    excel_name="HR-Nomina",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Cargo",       _S),
        ColumnContract("TipoRecurso", _S),
        ColumnContract("Cadena",      _S),
        ColumnContract("Salario",     _MON),
        ColumnContract("Comision",    _MON),
    ],
    allow_trailing_unnamed=True,
)

HR_RECARGOS = SheetContract(
    excel_name="HR-Recargos",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Recargo", _S),
        ColumnContract("Valor",   _PCT),  # 0.35 = 35% — decimal already
    ],
    allow_trailing_unnamed=False,
)

HR_SEG_SOCIAL = SheetContract(
    excel_name="HR-SegSocial",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("SS&Parafiscales", _S),
        ColumnContract("Proporcion",      _PCT),  # 0.085 = 8.5% — decimal
    ],
    allow_trailing_unnamed=False,
)

HR_PRESTACIONES = SheetContract(
    excel_name="HR-Prestaciones",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Prestaciones", _S),
        ColumnContract("Valor",        _PCT),  # 0.0833 = 8.33% — decimal
    ],
    allow_trailing_unnamed=False,
)

HR_RATIOS = SheetContract(
    excel_name="HR-Ratios",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Cargo",             _S),
        ColumnContract("CategoriaServicio", _S),
        ColumnContract("Tipo",              _S),
        ColumnContract("Agentes",           _NUM),
    ],
    allow_trailing_unnamed=False,
)

HR_COMPLEJIDAD = SheetContract(
    excel_name="HR-Complejidad",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Complejidad", _S),
        ColumnContract("Valor",       _DEC),
    ],
    allow_trailing_unnamed=False,
)

HR_RENTABILIDAD = SheetContract(
    excel_name="HR-Rentabilidad",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("CategoriaServicio", _S),
        ColumnContract("Minimo",            _PCT),  # "17.00%" → 0.17
        ColumnContract("MargenObjetivo",    _PCT),  # "18.00%" → 0.18
    ],
    allow_trailing_unnamed=False,
)

HR_CAMPANA = SheetContract(
    excel_name="HR-Campana",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("CategoriaServicio", _S),
        ColumnContract("Mes",               _INT),  # 1..60
        ColumnContract("Valor",             _FAC),  # ramp-up factor: 0.85, 1.0, etc.
    ],
    allow_trailing_unnamed=False,
)

HR_AUT_ROT = SheetContract(
    excel_name="HR-AutRot",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Tipo",    _S),
        ColumnContract("Servicio", _S),
        ColumnContract("Mes",      _INT),
        ColumnContract("Valor",    _PCT),  # 0.0735 = 7.35% — decimal
    ],
    allow_trailing_unnamed=False,
)

HR_COSTO_FIJO = SheetContract(
    excel_name="HR-CostoFijo",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Ciudad",         _S),
        ColumnContract("Localidad",      _S),
        ColumnContract("ServicioPublico", _S),
        ColumnContract("Valor",          _MON),  # COP monetary (153301, 11.757)
    ],
    allow_trailing_unnamed=False,
)

HR_MED_SEG = SheetContract(
    excel_name="HR-Med-Seg",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Ciudad",      _S),
        ColumnContract("CentroCosto", _S),
        ColumnContract("Valor",       _MON),
    ],
    allow_trailing_unnamed=False,
)

HR_RATIOS_HITL = SheetContract(
    excel_name="HR-Ratios-HITL",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Cargo", _S),
        ColumnContract("Ratio", _NUM),
    ],
    allow_trailing_unnamed=False,
)

HR_HORA_GTR = SheetContract(
    excel_name="HR-Hora-GTR",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("Cargo", _S),
        ColumnContract("Hora",  _NUM),
    ],
    allow_trailing_unnamed=False,
)

HR_EQUIPO_HITL = SheetContract(
    excel_name="HR-EquipoHITL",
    required=True,
    sheet_type=SheetType.CATALOG_BY_COLUMN,
    columns=[
        ColumnContract("EquipoHITL", _CAT),
    ],
    allow_trailing_unnamed=False,
)

HR_EQUIPO_SOPORTE = SheetContract(
    excel_name="HR-EquipoSoporteMantenimiento",
    required=True,
    sheet_type=SheetType.TABLE_ROWS,
    columns=[
        ColumnContract("EquipoSoporteMantenimiento", _S),
    ],
    allow_trailing_unnamed=False,
)

HR_CONTRACT = ModuleContract(
    module="hr",
    sheet_prefix="HR-",
    sheets=[
        HR_LV,
        HR_SALARIO_BASICO,
        HR_NOMINA,
        HR_RECARGOS,
        HR_SEG_SOCIAL,
        HR_PRESTACIONES,
        HR_RATIOS,
        HR_COMPLEJIDAD,
        HR_RENTABILIDAD,
        HR_CAMPANA,
        HR_AUT_ROT,
        HR_COSTO_FIJO,
        HR_MED_SEG,
        HR_EQUIPO_HITL,
        HR_EQUIPO_SOPORTE,
        HR_RATIOS_HITL,
        HR_HORA_GTR,
    ],
)
