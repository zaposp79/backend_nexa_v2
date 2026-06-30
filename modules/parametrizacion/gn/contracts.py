"""GN module upload contract — single source of truth.

Based on production file: GN_productiva_2026-05-11-10-25-28.xlsx

Sheet inventory:
  GN-LV  — catalog by column, 23 columns.

Column-type decisions
---------------------
All GN-LV columns are catalogs (string lists).  Values like
``"70% SMMLV - 30% IPC"`` (Componente) and ``"Comisión de Administración…"``
(Poliza) must be preserved as strings — they are NOT percentage values even
though they contain ``%``.

``PeriodoPago``: the production values are strings like ``"Mensual"``,
``"Anual"``, etc. — typed as ``catalog``.
"""

from nexa_engine.modules.parametrizacion.shared.contracts.base import (
    ColumnContract,
    ColumnType,
    ModuleContract,
    SheetContract,
    SheetType,
)

_CAT = ColumnType.CATALOG

GN_LV = SheetContract(
    excel_name="GN-LV",
    required=True,
    sheet_type=SheetType.CATALOG_BY_COLUMN,
    columns=[
        ColumnContract("Ciudad",            _CAT),
        ColumnContract("Localidad",         _CAT),
        ColumnContract("Servicio",          _CAT),
        ColumnContract("CategoriaServicio", _CAT),
        ColumnContract("CentroCosto",       _CAT),
        ColumnContract("Componente",        _CAT),  # may contain "70% SMMLV…"
        ColumnContract("Poliza",            _CAT),  # may contain descriptive strings
        ColumnContract("ComponenteFijo",    _CAT),
        ColumnContract("HardwareSoftware",  _CAT),
        ColumnContract("PeriodoPago",       _CAT),  # "Mensual", "Anual", etc.
        ColumnContract("Cadena",            _CAT),
        ColumnContract("ComponenteVariable", _CAT),
        ColumnContract("ModeloCombro",      _CAT),
        ColumnContract("Modalidad",         _CAT),
        ColumnContract("ReglaNegocio",      _CAT),
        ColumnContract("Canal",             _CAT),
        ColumnContract("Metrica",           _CAT),
        ColumnContract("Cliente",           _CAT),
        ColumnContract("TipoCobro",         _CAT),
        ColumnContract("TipoCliente",       _CAT),
        ColumnContract("Rubro",             _CAT),
        ColumnContract("UnidadMedida",      _CAT),
        ColumnContract("Divisa",            _CAT),
    ],
    allow_trailing_unnamed=False,
)

GN_CONTRACT = ModuleContract(
    module="gn",
    sheet_prefix="GN-",
    sheets=[GN_LV],
)
