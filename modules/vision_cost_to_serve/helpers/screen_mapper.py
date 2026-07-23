"""Screen contract mapper for Vision Cost To Serve.

Pure read-only composition from persisted pricing_result dict.
No Excel, no runtime providers, no formula duplication.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from nexa_engine.modules.vision_cost_to_serve.helpers.charts_mapper import (
    build_charts_from_result,
)


def _prune_empty(value: Any) -> Any:
    """Recursively drop null / empty containers while preserving 0 and False."""
    if isinstance(value, dict):
        pruned = {key: _prune_empty(item) for key, item in value.items()}
        kept = {}
        for key, item in pruned.items():
            if key == "missing_fields":
                kept[key] = [] if item is None else item
                continue
            if item is not None and item != "" and item != [] and item != {}:
                kept[key] = item
        return kept or None
    if isinstance(value, list):
        items = [_prune_empty(item) for item in value]
        kept = [item for item in items if item is not None and item != "" and item != [] and item != {}]
        return kept or None
    if value in (None, "", [], {}):
        return None
    return value


def _section(result: Dict[str, Any], key: str) -> Any:
    value = result.get(key)
    if value is not None:
        return value
    vision = result.get("vision_imprimible") or {}
    if isinstance(vision, dict):
        return vision.get(key)
    return None


def _header(result: Dict[str, Any]) -> Dict[str, Any]:
    ficha = deepcopy(_section(result, "ficha_deal") or {})
    resumen = deepcopy(_section(result, "resumen") or {})
    panel = deepcopy(_section(result, "panel") or {})
    servicio_rows = _section(result, "vision_por_servicio") or []
    first_service = servicio_rows[0] if isinstance(servicio_rows, list) and servicio_rows else {}

    return {
        "cliente": ficha.get("cliente") or resumen.get("cliente") or panel.get("cliente"),
        "servicio": (
            ficha.get("linea_negocio")
            or ficha.get("servicio")
            or resumen.get("linea_negocio")
            or panel.get("linea_negocio")
            or first_service.get("servicio")
        ),
        "ciudad": ficha.get("ciudad") or resumen.get("ciudad") or panel.get("ciudad"),
        "fecha_inicio": ficha.get("fecha_inicio") or resumen.get("fecha_inicio") or panel.get("fecha_inicio"),
        "fecha_fin": ficha.get("fecha_fin") or resumen.get("fecha_fin") or panel.get("fecha_fin"),
        "tipo_cuenta": ficha.get("tipo_cliente") or resumen.get("tipo_cliente") or panel.get("tipo_cliente"),
        "modelo": panel.get("modelo_cobro"),
        "ejecutivo": panel.get("ejecutivo") or panel.get("asesor") or panel.get("sales_owner"),
        "plazo_meses": ficha.get("meses_contrato") or resumen.get("meses_contrato") or panel.get("meses_contrato"),
        "sede": ficha.get("sede") or resumen.get("sede") or panel.get("sede"),
        "periodo_pago": (
            ficha.get("periodo_pago_dias")
            or resumen.get("periodo_pago_dias")
            or panel.get("periodo_pago_dias")
        ),
        "antiguedad_cliente": (
            ficha.get("antiguedad_cliente")
            or resumen.get("antiguedad_cliente")
            or panel.get("antiguedad_cliente")
        ),
        "componente_tecnologico": (
            ficha.get("ajuste_precio_tecnologico")
            or (panel.get("indexacion") or {}).get("componente_tecnologico")
        ),
        "frecuencia": (
            ficha.get("ajuste_precio_frecuencia")
            or (panel.get("indexacion") or {}).get("frecuencia")
        ),
    }


def _number(value: Any, default: float = 0.0) -> Any:
    return default if value is None else value


def _summary_cards(result: Dict[str, Any], has_risk: bool) -> List[Dict[str, Any]]:
    kpis = deepcopy(_section(result, "kpis") or {})
    cts = deepcopy(_section(result, "cost_to_serve") or {})
    risk = deepcopy(result.get("evaluacion_riesgo") or {})

    ingreso = kpis.get("ingreso_mensual")
    costo = kpis.get("costo_mensual_promedio")
    if costo is None:
        costo = kpis.get("costo_total_contrato")
    margen = (
        kpis.get("pct_utilidad_neta_total")
        if "pct_utilidad_neta_total" in kpis
        else kpis.get("margen")
    )

    cards = [
        {
            "key": "ingreso",
            "label": "Ingreso",
            "value": _number(ingreso),
            "format": "currency",
        },
        {
            "key": "costo",
            "label": "Costo",
            "value": _number(costo),
            "format": "currency",
        },
        {
            "key": "margen",
            "label": "Margen",
            "value": _number(margen),
            "format": "percent",
        },
        {
            "key": "cts",
            "label": "CTS",
            "value": _number(cts.get("cts_ponderado")),
            "format": "currency",
        },
    ]
    if has_risk:
        cards.append(
            {
                "key": "riesgo",
                "label": "Riesgo",
                "value": risk.get("clasificacion_total"),
                "score": _number(risk.get("score_total")),
                "format": "text",
            }
        )
    return cards


def _sections(result: Dict[str, Any], has_risk: bool) -> List[Dict[str, Any]]:
    sections = [
        {
            "key": "servicio",
            "label": "Servicio",
            "items": deepcopy(_section(result, "vision_por_servicio") or []),
            "source": "vision_por_servicio",
        },
        {
            "key": "canal",
            "label": "Canal",
            "items": deepcopy(_section(result, "vision_por_canal") or []),
            "source": "vision_por_canal",
        },
        {
            "key": "detalle_canal",
            "label": "Detalle Canal",
            "items": deepcopy(_section(result, "detalle_por_canal") or []),
            "source": "detalle_por_canal",
        },
        {
            "key": "equipo",
            "label": "Equipo",
            "items": [
                {
                    "roles": deepcopy((_section(result, "estructura_equipo") or {}).get("roles") or []),
                    "por_cargo": deepcopy((_section(result, "estructura_equipo") or {}).get("por_cargo") or []),
                    "fte_total": (_section(result, "estructura_equipo") or {}).get("fte_total"),
                    "fte_agentes": (_section(result, "estructura_equipo") or {}).get("fte_agentes"),
                    "fte_soporte": (_section(result, "estructura_equipo") or {}).get("fte_soporte"),
                    "costo_total_mensual": (_section(result, "estructura_equipo") or {}).get("costo_total_mensual"),
                }
            ],
            "source": "estructura_equipo",
        },
        {
            "key": "reglas",
            "label": "Reglas",
            "items": [
                {
                    "alerta": deepcopy((_section(result, "reglas_negocio") or {}).get("alerta") or {}),
                    "reglas": deepcopy((_section(result, "reglas_negocio") or {}).get("reglas") or []),
                    "costo_total": (_section(result, "reglas_negocio") or {}).get("costo_total"),
                    "valor_total_deal": (_section(result, "reglas_negocio") or {}).get("valor_total_deal"),
                }
            ],
            "source": "reglas_negocio",
        },
    ]

    if has_risk:
        sections.append(
            {
                "key": "riesgo",
                "label": "Riesgo",
                "items": [deepcopy(result.get("evaluacion_riesgo") or {})],
                "source": "evaluacion_riesgo",
            }
        )

    return sections


def _metadata(result: Dict[str, Any], has_risk: bool) -> Dict[str, Any]:
    sources = [
        "ficha_deal",
        "resumen",
        "panel",
        "kpis",
        "cost_to_serve",
        "vision_por_servicio",
        "vision_por_canal",
        "detalle_por_canal",
        "estructura_equipo",
        "reglas_negocio",
        "evaluacion_riesgo",
    ]
    available_sources = [source for source in sources if _section(result, source) is not None or result.get(source) is not None]
    missing_fields = [] if has_risk else ["evaluacion_riesgo"]
    return {
        "source": "persisted_pricing_result",
        "sources": available_sources,
        "missing_fields": missing_fields,
    }


def _charts(result: Dict[str, Any], has_risk: bool) -> Dict[str, Any]:
    charts = deepcopy(build_charts_from_result(result) or {})
    gaps = list(charts.get("gaps") or [])
    if has_risk:
        gaps = [gap for gap in gaps if gap.get("chart_id") != "risk_heatmap"]
    charts["gaps"] = gaps
    charts["data_status"] = {
        "available_charts": len(charts.get("charts") or []),
        "missing_charts": len(gaps),
        "missing_upstream_data": [gap.get("chart_id") for gap in gaps if gap.get("chart_id")],
    }
    return charts


def build_vision_cts_from_result(pricing_result_dict: dict) -> dict:
    """Build screen-ready CTS contract from persisted pricing_result."""
    result = pricing_result_dict or {}
    simulation_id = result.get("simulation_id")
    has_risk = bool(result.get("evaluacion_riesgo"))

    contract = {
        "version": "v1",
        "simulation_id": simulation_id,
        "header": _header(result),
        "summary_cards": _summary_cards(result, has_risk=has_risk),
        "sections": _sections(result, has_risk=has_risk),
        "charts": _charts(result, has_risk=has_risk),
        "metadata": _metadata(result, has_risk=has_risk),
    }
    return _prune_empty(contract) or {}
