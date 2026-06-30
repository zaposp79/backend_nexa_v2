"""Chart contract mapper for Vision Cost To Serve.

Reads from persisted pricing_result dict and emits chart configurations
with data from vision_imprimible and cost_to_serve sections.

No Excel, no runtime providers, no engine coupling.
Pure read-only composition from stable persisted shapes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ChartsMapper:
    """Builds chart contracts from persisted result dict."""

    def __init__(self, pricing_result: Dict[str, Any]):
        """Initialize with persisted result dictionary.

        Args:
            pricing_result: Dict with structure:
                {
                    "cost_to_serve": {...},
                    "vision_imprimible": {...} | None,
                    # OR (backward compat):
                    "vision_por_servicio": [...],
                    "vision_por_canal": [...],
                    ...
                }
        """
        self.result = pricing_result or {}

    def build_charts(self) -> Dict[str, Any]:
        """Build complete chart contract with data and gaps.

        Returns:
            {
                "charts": [
                    {
                        "id": "chart_id",
                        "title": "...",
                        "type": "bar_horizontal|pie|...",
                        "source": "...",
                        "x_axis": {...},
                        "y_axis": {...},
                        "series": [...],
                        "data": [...]
                    }
                ],
                "gaps": [
                    {
                        "chart_id": "...",
                        "reason": "...",
                        "required_source": "..."
                    }
                ]
            }
        """
        charts = []
        gaps = []

        # Build available charts
        cts_chart = self._build_cts_por_cadena_stacked()
        if cts_chart:
            charts.append(cts_chart)

        canal_fte = self._build_vision_por_canal_fte()
        if canal_fte:
            charts.append(canal_fte)

        servicio_econ = self._build_vision_por_servicio_economics()
        if servicio_econ:
            charts.append(servicio_econ)

        fte_pie = self._build_fte_estructura_pie()
        if fte_pie:
            charts.append(fte_pie)

        nomina_cargo = self._build_nomina_por_cargo()
        if nomina_cargo:
            charts.append(nomina_cargo)

        desglose_b = self._build_desglose_b_por_componente()
        if desglose_b:
            charts.append(desglose_b)

        # Collect gaps for non-implemented charts
        gaps.extend(self._gap_nomina_por_grupo())
        gaps.extend(self._gap_detalle_canal_waterfall())
        gaps.extend(self._gap_risk_heatmap())
        gaps.extend(self._gap_comparativo_escenarios())

        return {
            "charts": charts,
            "gaps": gaps,
        }

    # ────────────────────────────────────────────────────────────────────────
    # Chart builders (implemented)
    # ────────────────────────────────────────────────────────────────────────

    def _build_cts_por_cadena_stacked(self) -> Optional[Dict[str, Any]]:
        """CTS Ponderado por Cadena A/B/C (stacked bar)."""
        cts = self._get_cost_to_serve()
        if not cts:
            return None

        return {
            "id": "cts_por_cadena_stacked",
            "title": "CTS Ponderado por Cadena",
            "type": "bar_stacked",
            "source": "pricing_result.cost_to_serve",
            "x_axis": {
                "field": "cadena",
                "format": "string",
            },
            "y_axis": {
                "field": "cts_ponderado",
                "format": "currency",
            },
            "series": [
                {
                    "name": "Cadena A",
                    "value_field": "cts_cadena_a",
                },
                {
                    "name": "Cadena B",
                    "value_field": "cts_cadena_b",
                },
                {
                    "name": "Cadena C",
                    "value_field": "cts_cadena_c",
                },
            ],
            "data": [
                {
                    "cadena": "A",
                    "cts_cadena_a": cts.get("cts_cadena_a", 0.0),
                    "cts_cadena_b": 0.0,
                    "cts_cadena_c": 0.0,
                    "cts_ponderado": cts.get("cts_cadena_a", 0.0),
                },
                {
                    "cadena": "B",
                    "cts_cadena_a": 0.0,
                    "cts_cadena_b": cts.get("cts_cadena_b", 0.0),
                    "cts_cadena_c": 0.0,
                    "cts_ponderado": cts.get("cts_cadena_b", 0.0),
                },
                {
                    "cadena": "C",
                    "cts_cadena_a": 0.0,
                    "cts_cadena_b": 0.0,
                    "cts_cadena_c": cts.get("cts_cadena_c", 0.0),
                    "cts_ponderado": cts.get("cts_cadena_c", 0.0),
                },
            ],
        }

    def _build_vision_por_canal_fte(self) -> Optional[Dict[str, Any]]:
        """FTE por Canal (horizontal bar)."""
        canales = self._get_vision_por_canal()
        if not canales:
            return None

        # Filter to active channels only
        activos = [c for c in canales if c.get("estado", "Activo") == "Activo"]
        data = [
            {
                "canal": c.get("canal", ""),
                "fte": c.get("fte", 0.0),
            }
            for c in activos
        ]

        return {
            "id": "vision_por_canal_fte",
            "title": "FTE por Canal",
            "type": "bar_horizontal",
            "source": "pricing_result.vision_imprimible.vision_por_canal",
            "x_axis": {
                "field": "fte",
                "format": "number",
            },
            "y_axis": {
                "field": "canal",
                "format": "string",
            },
            "series": [
                {
                    "name": "FTE",
                    "value_field": "fte",
                }
            ],
            "data": data,
        }

    def _build_vision_por_servicio_economics(self) -> Optional[Dict[str, Any]]:
        """Economics por Servicio (Ingreso vs CTS grouped bar)."""
        servicios = self._get_vision_por_servicio()
        if not servicios:
            return None

        data = [
            {
                "servicio": s.get("servicio", ""),
                "ingreso_mensual": s.get("ingreso_mensual", 0.0),
                "cts_ponderado": s.get("cts_ponderado", 0.0),
                "margen": s.get("margen", 0.0),
            }
            for s in servicios
        ]

        return {
            "id": "vision_por_servicio_economics",
            "title": "Economics por Servicio",
            "type": "bar_grouped",
            "source": "pricing_result.vision_imprimible.vision_por_servicio",
            "x_axis": {
                "field": "servicio",
                "format": "string",
            },
            "y_axis": {
                "field": "amount",
                "format": "currency",
            },
            "series": [
                {
                    "name": "Ingreso Mensual",
                    "value_field": "ingreso_mensual",
                },
                {
                    "name": "CTS Ponderado",
                    "value_field": "cts_ponderado",
                },
                {
                    "name": "Margen",
                    "value_field": "margen",
                },
            ],
            "data": data,
        }

    def _build_fte_estructura_pie(self) -> Optional[Dict[str, Any]]:
        """FTE Distribution — Agentes vs Soporte (pie chart)."""
        equipo = self._get_estructura_equipo()
        if not equipo:
            return None

        fte_agentes = equipo.get("fte_agentes", 0.0)
        fte_soporte = equipo.get("fte_soporte", 0.0)
        fte_total = equipo.get("fte_total", 0.0)

        # Calculate percentages
        pct_agentes = (fte_agentes / fte_total * 100) if fte_total > 0 else 0.0
        pct_soporte = (fte_soporte / fte_total * 100) if fte_total > 0 else 0.0

        return {
            "id": "fte_estructura_pie",
            "title": "Distribución FTE — Agentes vs Soporte",
            "type": "pie",
            "source": "pricing_result.vision_imprimible.estructura_equipo",
            "series": [
                {
                    "name": "Agentes",
                    "value_field": "fte_agentes",
                },
                {
                    "name": "Soporte",
                    "value_field": "fte_soporte",
                },
            ],
            "data": [
                {
                    "label": "Agentes",
                    "value": fte_agentes,
                    "percentage": pct_agentes,
                },
                {
                    "label": "Soporte",
                    "value": fte_soporte,
                    "percentage": pct_soporte,
                },
            ],
        }

    def _build_nomina_por_cargo(self) -> Optional[Dict[str, Any]]:
        """Participación Nómina por Cargo (horizontal bar)."""
        equipo = self._get_estructura_equipo()
        if not equipo:
            return None

        por_cargo = equipo.get("por_cargo", [])
        if not por_cargo:
            return None

        costo_total = equipo.get("costo_total_mensual", 0.0)

        data = [
            {
                "cargo_tipo": c.get("cargo_tipo", ""),
                "costo_mensual": c.get("costo_mensual", 0.0),
                "fte": c.get("fte", 0.0),
                "pct_participacion": (
                    c.get("costo_mensual", 0.0) / costo_total * 100
                    if costo_total > 0
                    else 0.0
                ),
            }
            for c in por_cargo
        ]

        return {
            "id": "nomina_por_cargo",
            "title": "Participación Nómina por Cargo",
            "type": "bar_horizontal",
            "source": "pricing_result.vision_imprimible.estructura_equipo.por_cargo",
            "x_axis": {
                "field": "pct_participacion",
                "format": "percentage",
            },
            "y_axis": {
                "field": "cargo_tipo",
                "format": "string",
            },
            "series": [
                {
                    "name": "Participación %",
                    "value_field": "pct_participacion",
                }
            ],
            "data": data,
        }

    def _build_desglose_b_por_componente(self) -> Optional[Dict[str, Any]]:
        """Desglose Cadena B — Componentes (horizontal bar)."""
        cts = self._get_cost_to_serve()
        if not cts or "desglose_b" not in cts:
            return None

        desglose_b = cts["desglose_b"]

        data = [
            {
                "componente": "Fijo",
                "monto": desglose_b.get("componente_fijo", 0.0),
            },
            {
                "componente": "Variable",
                "monto": desglose_b.get("componente_variable", 0.0),
            },
            {
                "componente": "OpEx",
                "monto": desglose_b.get("opex", 0.0),
            },
            {
                "componente": "Inversiones",
                "monto": desglose_b.get("inversiones", 0.0),
            },
            {
                "componente": "Soporte/Mantenimiento",
                "monto": desglose_b.get("soporte_mantenimiento", 0.0),
            },
        ]

        return {
            "id": "desglose_b_por_componente",
            "title": "Desglose Cadena B — Componentes",
            "type": "bar_horizontal",
            "source": "pricing_result.cost_to_serve.desglose_b",
            "x_axis": {
                "field": "monto",
                "format": "currency",
            },
            "y_axis": {
                "field": "componente",
                "format": "string",
            },
            "series": [
                {
                    "name": "Monto",
                    "value_field": "monto",
                }
            ],
            "data": data,
        }

    # ────────────────────────────────────────────────────────────────────────
    # Gap reporters (not yet implemented)
    # ────────────────────────────────────────────────────────────────────────

    def _gap_nomina_por_grupo(self) -> List[Dict[str, str]]:
        """Gap: Nómina por Grupo (Operaciones, QA, HR, etc.)."""
        return [
            {
                "chart_id": "nomina_por_grupo",
                "reason": "missing_semantic_group_mapping",
                "required_source": "grupo_semantico persisted in estructura_equipo.por_cargo or external parametrization",
            }
        ]

    def _gap_detalle_canal_waterfall(self) -> List[Dict[str, str]]:
        """Gap: Waterfall CTS Step-by-Step (A → B → Financiero → CTS)."""
        return [
            {
                "chart_id": "detalle_canal_waterfall",
                "reason": "missing_waterfall_fact",
                "required_source": "WaterfallCTS structured fact in cost_to_serve (steps: cadena_a, cadena_b, financiero, total)",
            }
        ]

    def _gap_risk_heatmap(self) -> List[Dict[str, str]]:
        """Gap: Risk Heatmap (Total, Cliente, Operativo)."""
        return [
            {
                "chart_id": "risk_heatmap",
                "reason": "risk_contract_not_defined_for_cts",
                "required_source": "evaluacion_riesgo (currently only in vision_imprimible, not in /cost-to-serve endpoint)",
            }
        ]

    def _gap_comparativo_escenarios(self) -> List[Dict[str, str]]:
        """Gap: Comparativo de Escenarios por Canal."""
        return [
            {
                "chart_id": "comparativo_escenarios",
                "reason": "scenario_variants_not_persisted_for_cts",
                "required_source": "escenarios_comerciales[] per channel in cost_to_serve result",
            }
        ]

    # ────────────────────────────────────────────────────────────────────────
    # Data extraction helpers
    # ────────────────────────────────────────────────────────────────────────

    def _get_cost_to_serve(self) -> Optional[Dict[str, Any]]:
        """Extract cost_to_serve section from result."""
        if "cost_to_serve" in self.result:
            return self.result["cost_to_serve"]
        return None

    def _get_vision_imprimible(self) -> Optional[Dict[str, Any]]:
        """Extract vision_imprimible section from result."""
        if "vision_imprimible" in self.result:
            return self.result["vision_imprimible"]
        return None

    def _get_vision_por_servicio(self) -> List[Dict[str, Any]]:
        """Extract vision_por_servicio array (from vision_imprimible or root)."""
        # Try vision_imprimible first (canonical)
        vi = self._get_vision_imprimible()
        if vi and "vision_por_servicio" in vi:
            return vi.get("vision_por_servicio", [])
        # Fallback to root (backward compat with serializer)
        return self.result.get("vision_por_servicio", [])

    def _get_vision_por_canal(self) -> List[Dict[str, Any]]:
        """Extract vision_por_canal array (from vision_imprimible or root)."""
        # Try vision_imprimible first (canonical)
        vi = self._get_vision_imprimible()
        if vi and "vision_por_canal" in vi:
            return vi.get("vision_por_canal", [])
        # Fallback to root (backward compat with serializer)
        return self.result.get("vision_por_canal", [])

    def _get_estructura_equipo(self) -> Optional[Dict[str, Any]]:
        """Extract estructura_equipo object (from vision_imprimible or root)."""
        # Try vision_imprimible first (canonical)
        vi = self._get_vision_imprimible()
        if vi and "estructura_equipo" in vi:
            return vi.get("estructura_equipo")
        # Fallback to root (backward compat with serializer)
        return self.result.get("estructura_equipo")


def build_charts_from_result(pricing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to build charts from result dict.

    Args:
        pricing_result: Persisted pricing result (from storage or API).

    Returns:
        Chart contract dict with charts[] and gaps[].
    """
    mapper = ChartsMapper(pricing_result)
    return mapper.build_charts()
