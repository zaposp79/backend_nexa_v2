"""
calculator_motor/formulas/graphics/models.py
--------------------------------------------
Output models for the graph calculation layer.

Excel V2-8 · Hoja 'Graficos'
  - Grafico 1: Bandas Visión Final (A5:I93)
  - Grafico 2: Ratios Cost To Serve (P4:BH29)
  - Grafico 3: Ingresos Netos por Mes (P42:BW47)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PortfolioClienteRow:
    """Single client row from the portfolio reference table."""
    categoria: str
    cliente: str
    margen_bruto: float


@dataclass
class GraficoBandasResult:
    """
    Quartile band series for the 'Bandas Visión Final' chart.

    Excel V2-8 · Graficos!G6:G9, I4:I5
    Formula: QUARTILE.INC(FILTER(portfolio_margins, categoria=service_category), quart)

    The chart shows where the current deal's margin falls relative to the
    historical client portfolio in the same service category.
    """
    categoria_servicio: str
    cliente_nombre: str

    # Portfolio quartile bands — Excel V2-8: Graficos!G6:G9
    # QUARTILE.INC with quart 1..4 over margins filtered by categoria_servicio
    quartil_1: Optional[float]   # 25th percentile (Q1)
    quartil_2: Optional[float]   # 50th percentile — median (Q2)
    quartil_3: Optional[float]   # 75th percentile (Q3)
    quartil_4: Optional[float]   # maximum (Q4 = quart=4)

    # Portfolio category average — Excel V2-8: Graficos!I4 (IFS lookup to C3/C30/etc.)
    promedio_categoria: Optional[float]

    # Specific client historical margin — Excel V2-8: Graficos!I5
    # FILTER(C5:C93, categoria=current AND cliente=current)
    margen_historico_cliente: Optional[float]

    # Current deal margin from PricingResult — overlay on chart
    margen_deal_actual: float

    def as_dict(self) -> dict:
        return {
            "categoria_servicio": self.categoria_servicio,
            "cliente_nombre": self.cliente_nombre,
            "bandas_portfolio": {
                "quartil_1": self.quartil_1,
                "quartil_2": self.quartil_2,
                "quartil_3": self.quartil_3,
                "quartil_4": self.quartil_4,
                "promedio_categoria": self.promedio_categoria,
            },
            "margen_historico_cliente": self.margen_historico_cliente,
            "margen_deal_actual": self.margen_deal_actual,
        }


@dataclass
class CostoRolEscenario:
    """
    Loaded payroll cost for one role in one scenario.

    Excel V2-8 · Graficos!Q5:AE28 — one cell per (role, scenario).
    Formula: SUMIFS('Nomina Loaded'!col$43:col$66, $B$43:$B$66, role_name)
             + SUMIFS('Nomina Loaded'!col$155:col$178, $B$155:$B$178, role_name)
    """
    rol_nombre: str
    costo_total: float           # COP, mes 1 (reference month matches Nomina Loaded)
    categoria: str = ""          # "Operaciones" | "Recursos humanos" | "Otros"


@dataclass
class EscenarioCostoRoles:
    """
    Absolute loaded payroll cost for all roles in one scenario.

    Excel V2-8 · Graficos!P4:AF29 — one column block per scenario.
    """
    escenario_label: str         # exact Excel label (e.g. "Escenario SAC Actual")
    canal: str                   # backend canal identifier
    modalidad: str               # backend modalidad identifier
    costos_por_rol: List[CostoRolEscenario] = field(default_factory=list)

    @property
    def total_por_rol(self) -> Dict[str, float]:
        """Row-indexed cost dict for downstream ratio computation."""
        return {r.rol_nombre: r.costo_total for r in self.costos_por_rol}

    @property
    def total_escenario(self) -> float:
        """Sum of all role costs in this scenario (= AF column for this scenario)."""
        return sum(r.costo_total for r in self.costos_por_rol)

    def as_dict(self) -> dict:
        return {
            "escenario_label": self.escenario_label,
            "canal": self.canal,
            "modalidad": self.modalidad,
            "costos_por_rol": [
                {"rol_nombre": r.rol_nombre, "costo_total": r.costo_total, "categoria": r.categoria}
                for r in self.costos_por_rol
            ],
            "total_escenario": self.total_escenario,
        }


@dataclass
class GraficoRatiosCTSResult:
    """
    Graph 2 — Ratios Vision Cost To Serve.

    Excel V2-8 · Graficos!P4:BH29.

    Block A (P4:AF29): absolute loaded payroll cost by role × scenario.
    Block B (AR4:BH29): ratios = role_cost / column_denominator.
    Denominator excludes "Agente Básico 1" (Excel $AR$24).
    selected_ratio_column = "Total" per VCT!C125 = "Total" (static, V2-8).
    """
    escenarios: List[EscenarioCostoRoles] = field(default_factory=list)

    # Block B ratios — {escenario_label: {rol_nombre: ratio}}
    ratios_por_escenario: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # AJ / BH column — ratio for selected_ratio_column ("Total")
    ratio_actual: Dict[str, float] = field(default_factory=dict)

    # AF column: total per role across all scenarios
    total_por_rol: Dict[str, float] = field(default_factory=dict)

    # AJ column lookup — always "Total" per VCT!C125 (static "Total" for V2-8)
    selected_ratio_column: str = "Total"

    # Traceability
    excel_trace: str = "Graficos!P4:BH29"
    deferred_items: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "escenarios": [e.as_dict() for e in self.escenarios],
            "total_por_rol": self.total_por_rol,
            "ratios_por_escenario": self.ratios_por_escenario,
            "ratio_actual": self.ratio_actual,
            "selected_ratio_column": self.selected_ratio_column,
            "excel_trace": self.excel_trace,
            "deferred_items": self.deferred_items,
        }


@dataclass
class MesIngresoNeto:
    """
    One data point for Graph 3.

    Excel V2-8 · Graficos!P46:BW46 (x-axis month index)
                              P47:BW47 (y-axis ingreso_neto or None)
    Formula row 47: =IF('Visión P&G'!$C$27>=0,'Visión P&G'!C$27,NA())
    """
    mes: int
    ingreso_neto: Optional[float]   # None when value < 0 (maps to Excel NA())


@dataclass
class GraficoIngresosMensualesResult:
    """
    Graph 3 — Ingresos Netos por Mes.

    Excel V2-8 · Graficos!P42:BW47.
    Source: 'Visión P&G'!C27:BJ27 (row 27 = Ingreso Neto).
    Only shows months where ingreso_neto >= 0 (negative → None/NA).
    """
    meses: List[MesIngresoNeto] = field(default_factory=list)
    periodos: int = 0
    ingreso_neto_max: float = 0.0
    excel_trace: str = "Graficos!P42:BW47"

    def as_dict(self) -> dict:
        return {
            "periodos": self.periodos,
            "ingreso_neto_max": self.ingreso_neto_max,
            "meses": [
                {"mes": p.mes, "ingreso_neto": p.ingreso_neto}
                for p in self.meses
            ],
            "excel_trace": self.excel_trace,
        }


@dataclass
class WaterfallItem:
    """
    One row in the Graph 4 waterfall table.

    Excel V2-8 · Graficos!P65:S81 — columns: Concepto | Total | Promedio | % sobre Ingreso Neto
    """
    concepto: str
    total: float
    promedio: float          # total / meses_contrato
    pct_ingreso_neto: float  # total / ingreso_neto_total  (0.0 when ingreso_neto_total == 0)
    tipo: str                # "ingreso" | "costo" | "subtotal" | "utilidad"
    orden: int


@dataclass
class GraficoWaterfallTableResult:
    """
    Graph 4 — Waterfall Precio Total (table slice).

    Excel V2-8 · Graficos!P65:S81.
    Source: SUM aggregates from 'Visión P&G' rows (C18/C27/C31/C45/C55/C30/C74/C79:BJ*)
    Deferred: P53:AA57 ArrayFormulas waterfall chart segments.
    """
    items: List[WaterfallItem]
    meses_contrato: int
    excel_trace: str = "Graficos!P65:S81"

    def as_dict(self) -> dict:
        return {
            "meses_contrato": self.meses_contrato,
            "excel_trace": self.excel_trace,
            "items": [
                {
                    "concepto": it.concepto,
                    "total": it.total,
                    "promedio": it.promedio,
                    "pct_ingreso_neto": it.pct_ingreso_neto,
                    "tipo": it.tipo,
                    "orden": it.orden,
                }
                for it in self.items
            ],
        }


@dataclass(frozen=True)
class GraficoCtsBargainingZoneResult:
    """
    Graph 5 — CTS Deal Bargaining Zone.

    Excel V2-8 · Graficos!P84:Q93.

    Stacked-bar series that shows whether the deal's ingreso_deal clears
    the cost floor (cts_deal) and the margin target (meta_ingreso).

    Q84 = costo_mensual_promedio
    Q85 = ingreso_neto_total / meses_contrato
    Q86 = margen_objetivo (panel.margen)
    Q87 = Q84 / (1 - Q86)
    Q88 = MAX(Q85, Q87) * 1.05
    Q90 = Q84
    Q91 = Q88 - Q84
    Q92 = Q88 - Q87
    Q93 = Q85
    """
    cts_deal: float         # Q84 — costo mensual promedio
    ingreso_deal: float     # Q85 — ingreso_neto_total / meses_contrato
    margen_objetivo: float  # Q86 — panel.margen
    meta_ingreso: float     # Q87 — cts_deal / (1 - margen_objetivo)
    eje_max: float          # Q88 — MAX(ingreso_deal, meta_ingreso) * 1.05
    pierde_plata: float     # Q90 — cts_deal
    no_cumple_meta: float   # Q91 — eje_max - cts_deal
    zona_segura: float      # Q92 — eje_max - meta_ingreso
    marcador: float         # Q93 — ingreso_deal
    excel_trace: str = "Graficos!P84:Q93"

    def as_dict(self) -> dict:
        return {
            "cts_deal": self.cts_deal,
            "ingreso_deal": self.ingreso_deal,
            "margen_objetivo": self.margen_objetivo,
            "meta_ingreso": self.meta_ingreso,
            "eje_max": self.eje_max,
            "pierde_plata": self.pierde_plata,
            "no_cumple_meta": self.no_cumple_meta,
            "zona_segura": self.zona_segura,
            "marcador": self.marcador,
            "excel_trace": self.excel_trace,
        }


@dataclass
class GraficosResult:
    """Container for all computed graph series."""
    bandas_vision_final: Optional[GraficoBandasResult] = None
    ratios_cost_to_serve: Optional[GraficoRatiosCTSResult] = None
    ingresos_mensuales: Optional[GraficoIngresosMensualesResult] = None
    waterfall_table: Optional[GraficoWaterfallTableResult] = None
    cts_bargaining_zone: Optional[GraficoCtsBargainingZoneResult] = None

    def as_dict(self) -> dict:
        return {
            "bandas_vision_final": (
                self.bandas_vision_final.as_dict()
                if self.bandas_vision_final else None
            ),
            "ratios_cost_to_serve": (
                self.ratios_cost_to_serve.as_dict()
                if self.ratios_cost_to_serve else None
            ),
            "ingresos_mensuales": (
                self.ingresos_mensuales.as_dict()
                if self.ingresos_mensuales else None
            ),
            "waterfall_table": (
                self.waterfall_table.as_dict()
                if self.waterfall_table else None
            ),
            "cts_bargaining_zone": (
                self.cts_bargaining_zone.as_dict()
                if self.cts_bargaining_zone else None
            ),
        }
