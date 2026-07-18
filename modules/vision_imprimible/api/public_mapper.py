"""Projection from the persisted engine result to the screen-ready public API."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from nexa_engine.modules.vision_imprimible.api.response_models import (
    VisionImprimibleDataV1,
)


_APPROVAL_ACTOR_KEYS = [
    "elaborador_pricing",
    "revisor_director_senior_comercial",
    "revisor_gerente_desarrollo_negocios",
    "aprobador_director_pricing",
    "aprobador_gerente_general",
]

_ADJUSTMENT_NAMES = (
    "margen_objetivo_cadena_a",
    "contingencia_operativa",
    "contingencia_comercial",
    "markup",
    "descuento",
)


def _number(value: Any, default: float | int | None = 0.0) -> Any:
    return default if value is None else value


def _prune_empty(value: Any) -> Any:
    """Recursively drop null/empty containers while preserving 0 and False."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            pruned = _prune_empty(item)
            if pruned is not None and pruned != "" and pruned != [] and pruned != {}:
                result[key] = pruned
        return result if result else None
    if isinstance(value, list):
        items = [_prune_empty(item) for item in value]
        items = [item for item in items if item is not None and item != "" and item != [] and item != {}]
        return items if items else None
    if value in (None, "", [], {}):
        return None
    return value


def _canonical(document: dict[str, Any]) -> dict[str, Any]:
    vision = document.get("vision_imprimible")
    return vision if isinstance(vision, dict) else {}


def _section(document: dict[str, Any], key: str) -> Any:
    canonical = _canonical(document)
    if key in canonical:
        return canonical.get(key)
    return document.get(key)


def _labelize(key: str) -> str:
    return key.replace("_", " ").capitalize()


def _item(key: str, value: Any, label: str | None = None) -> dict[str, Any]:
    return {"key": key, "label": label or _labelize(key), "value": value}


def _valid_scenarios(document: dict[str, Any]) -> list[dict[str, Any]]:
    comparisons = deepcopy(_section(document, "comparativo_escenarios") or [])
    channels = ((document.get("vision_tarifas") or {}).get("canales") or [])
    result: list[dict[str, Any]] = []

    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            continue
        escenario = str(comparison.get("escenario") or "").strip()
        modalidad = str(comparison.get("modalidad_canal") or "").strip()
        modelo = str(comparison.get("modelo_cobro") or "").strip()
        if not escenario or not modalidad or modalidad == "-" or not modelo or modelo == "0":
            continue

        channel = channels[index] if index < len(channels) and isinstance(channels[index], dict) else {}
        result.append(
            {
                "escenario": escenario,
                "modalidad_canal": modalidad,
                "modelo_cobro": modelo,
                "componente_fijo": channel.get("componente_fijo"),
                "componente_variable": channel.get("componente_variable"),
                "tarifa_fija": channel.get("tarifa_fijo_fte"),
                "tarifa_variable": channel.get("tarifa_variable"),
                "canales": comparison.get("canales") or channel.get("canal") or comparison.get("canal"),
            }
        )
    return result


def _build_header(document: dict[str, Any]) -> dict[str, Any]:
    ficha = deepcopy(_section(document, "ficha_deal") or {})
    return {
        "cliente": ficha.get("cliente"),
        "servicio": ficha.get("linea_negocio") or ficha.get("servicio"),
        "ciudad": ficha.get("ciudad"),
        "sede": ficha.get("sede"),
        "tipo_cliente": ficha.get("tipo_cliente"),
        "fecha_inicio": ficha.get("fecha_inicio"),
        "meses_contrato": ficha.get("meses_contrato"),
        "moneda": ficha.get("divisa") or "COP",
    }


def _build_summary_cards(document: dict[str, Any]) -> list[dict[str, Any]]:
    kpis = deepcopy(_section(document, "kpis") or {})
    config = deepcopy(_section(document, "configuracion_comercial") or {})
    risk = deepcopy(_section(document, "evaluacion_riesgo") or {})
    cards = [
        {"key": "ingreso_mensual", "label": "Ingreso mensual", "value": _number(config.get("ingreso_mensual", kpis.get("ingreso_mensual")))},
        {"key": "costo_mensual", "label": "Costo mensual", "value": _number(config.get("costo_mensual_total", kpis.get("costo_mensual_promedio")))},
        {"key": "valor_total_contrato", "label": "Valor total contrato", "value": _number(config.get("valor_total_deal", kpis.get("valor_total_deal")))},
        {"key": "score_deal", "label": "Score deal", "value": _number(risk.get("score_total"))},
    ]
    return cards


def _build_ficha_section(document: dict[str, Any]) -> dict[str, Any] | None:
    ficha = deepcopy(_section(document, "ficha_deal") or {})
    config = deepcopy(_section(document, "configuracion_comercial") or {})
    items = [
        _item("cliente", ficha.get("cliente"), "Cliente"),
        _item("servicio", ficha.get("linea_negocio") or ficha.get("servicio"), "Servicio"),
        _item("ciudad", ficha.get("ciudad"), "Ciudad"),
        _item("sede", ficha.get("sede"), "Sede"),
        _item("tipo_cliente", ficha.get("tipo_cliente"), "Tipo cliente"),
        _item("antiguedad_cliente", ficha.get("antiguedad_cliente"), "Antiguedad cliente"),
        _item("fecha_inicio", ficha.get("fecha_inicio"), "Fecha inicio"),
        _item("meses_contrato", ficha.get("meses_contrato"), "Meses contrato"),
        _item("periodo_pago_dias", ficha.get("periodo_pago_dias"), "Periodo pago dias"),
        _item("ajuste_precio_componente_humano", ficha.get("ajuste_precio_tipo"), "Ajuste precio componente humano"),
        _item("ajuste_precio_componente_tecnologico", ficha.get("ajuste_precio_tecnologico"), "Ajuste precio componente tecnologico"),
        _item("ajuste_precio_frecuencia", ficha.get("ajuste_precio_frecuencia"), "Ajuste precio frecuencia"),
        _item("volumen_base_mensual", config.get("volumen_base_mensual"), "Volumen base mensual"),
        _item("descuento_aplicado", config.get("descuento"), "Descuento aplicado"),
        _item("porcentaje_imprevisto", (next((r for r in (deepcopy(_section(document, "reglas_negocio") or {}).get("reglas") or []) if r.get("nombre") == "imprevistos"), {}) or {}).get("aplicado"), "Porcentaje imprevisto"),
    ]
    section = {
        "id": "ficha_deal",
        "title": "Ficha del deal",
        "type": "summary_grid",
        "items": items,
    }
    return _prune_empty(section)


def _margin_status(kpis: dict[str, Any]) -> str | None:
    if "estado_margen" in kpis:
        return kpis.get("estado_margen")
    if kpis.get("cumple_margen_minimo") is True:
        return "cumple_minimo"
    if kpis.get("cumple_margen_minimo") is False:
        return "bajo_minimo"
    return None


def _build_economics_section(document: dict[str, Any]) -> dict[str, Any] | None:
    kpis = deepcopy(_section(document, "kpis") or {})
    ficha = deepcopy(_section(document, "ficha_deal") or {})
    config = deepcopy(_section(document, "configuracion_comercial") or {})
    scenarios = _valid_scenarios(document)
    items = [
        _item("ingreso_mensual", config.get("ingreso_mensual", kpis.get("ingreso_mensual")), "Ingreso mensual"),
        _item("escenario_seleccionado", scenarios[0]["escenario"] if scenarios else config.get("escenario_seleccionado"), "Escenario seleccionado"),
        _item("costo_mensual", config.get("costo_mensual_total", kpis.get("costo_mensual_promedio")), "Costo mensual"),
        _item("margen_deal", config.get("margen_objetivo_cadena_a", kpis.get("pct_utilidad_neta_total")), "Margen deal"),
        _item("estado_margen", _margin_status(kpis), "Estado margen"),
        _item("valor_total_contrato", config.get("valor_total_deal", kpis.get("valor_total_deal")), "Valor total contrato"),
        _item("moneda", ficha.get("divisa") or "COP", "Moneda"),
    ]
    section = {
        "id": "economics",
        "title": "Economics",
        "type": "summary_grid",
        "items": items,
        "labels": {
            "cumple_minimo": "Cumple minimo",
            "bajo_minimo": "Bajo minimo",
            "excede_maximo": "Excede maximo",
            "dentro_rango": "Dentro rango",
        },
    }
    return _prune_empty(section)


def _build_configuracion_section(document: dict[str, Any]) -> dict[str, Any] | None:
    config = deepcopy(_section(document, "configuracion_comercial") or {})
    scenarios = _valid_scenarios(document)
    first = scenarios[0] if scenarios else {}
    items = [
        _item("modelo_cobro", config.get("modelo_cobro_principal", first.get("modelo_cobro")), "Modelo cobro"),
        _item("componente_fijo", config.get("pct_fijo_global", first.get("componente_fijo")), "Componente fijo"),
        _item("componente_variable", config.get("pct_variable_global", first.get("componente_variable")), "Componente variable"),
        _item("tarifa_fija", config.get("tarifa_fija", first.get("tarifa_fija")), "Tarifa fija"),
        _item("tarifa_variable", config.get("tarifa_variable", first.get("tarifa_variable")), "Tarifa variable"),
        _item("escenario_seleccionado", first.get("escenario") or config.get("escenario_seleccionado"), "Escenario seleccionado"),
        _item("canales", first.get("canales"), "Canales"),
    ]
    section = {
        "id": "configuracion_comercial",
        "title": "Configuracion comercial",
        "type": "summary_grid",
        "items": items,
    }
    return _prune_empty(section)


def _build_charts(document: dict[str, Any]) -> dict[str, Any]:
    waterfall = deepcopy(_section(document, "waterfall_promedio") or {})
    months = deepcopy(_section(document, "pyg_por_mes") or [])

    charts: dict[str, Any] = {}
    if waterfall:
        charts["waterfall"] = {
            "id": "waterfall",
            "title": "Waterfall",
            "type": "waterfall",
            "source": "vision_imprimible.waterfall_promedio",
            "data": [{"key": key, "value": value} for key, value in waterfall.items()],
        }
    if months:
        charts["evolucion_ingreso_neto"] = {
            "id": "evolucion_ingreso_neto",
            "title": "Evolucion ingreso neto",
            "type": "line",
            "source": "vision_imprimible.pyg_por_mes",
            "data": [
                {
                    "mes": item.get("mes"),
                    "ingreso_neto": _number(item.get("ingreso_neto")),
                }
                for item in months
                if isinstance(item, dict)
            ],
        }
    return charts


def _build_analisis_section(document: dict[str, Any], charts: dict[str, Any]) -> dict[str, Any] | None:
    items = [chart for chart in charts.values() if chart.get("id") in {"waterfall", "evolucion_ingreso_neto"}]
    section = {
        "id": "analisis_grafico",
        "title": "Analisis grafico",
        "type": "charts",
        "items": items,
    }
    return _prune_empty(section)


def _build_comparativo_section(document: dict[str, Any]) -> dict[str, Any] | None:
    scenarios = _valid_scenarios(document)
    config = deepcopy(_section(document, "configuracion_comercial") or {})
    section = {
        "id": "comparativo_escenarios",
        "title": "Comparativo escenarios",
        "type": "comparison_table",
        "items": scenarios,
        "total": {
            "modelo_cobro": config.get("modelo_cobro_principal"),
            "componente_fijo": config.get("pct_fijo_global"),
            "componente_variable": config.get("pct_variable_global"),
            "tarifa_fija": config.get("tarifa_fija"),
            "tarifa_variable": config.get("tarifa_variable"),
        },
        "nota": (deepcopy(_section(document, "comparativo_escenarios_meta") or {}) or {}).get("nota"),
    }
    return _prune_empty(section)


def _build_control_section(document: dict[str, Any]) -> dict[str, Any] | None:
    risk = deepcopy(_section(document, "evaluacion_riesgo") or {})
    kpis = deepcopy(_section(document, "kpis") or {})
    control = deepcopy(_section(document, "control_aprobacion") or {})
    item = {
        "nivel_riesgo": {
            "score_cliente": _number(risk.get("score_cliente")),
            "score_operativo": _number(risk.get("score_operativo")),
            "score_deal": _number(risk.get("score_total")),
            "clasificacion": risk.get("clasificacion_total"),
        },
        "facturacion_mensual_proyectada": _number(kpis.get("facturacion_mensual_proyectada")),
        "requiere_aprobacion": bool(risk.get("requiere_aprobacion")) if risk else None,
        "aprobaciones": deepcopy(control.get("aprobaciones") or []),
        "criterios_riesgo": deepcopy(risk.get("criterios") or []),
    }
    thresholds = deepcopy(control.get("umbrales") or control.get("thresholds") or [])
    if thresholds:
        item["umbrales_aprobacion"] = thresholds
    section = {
        "id": "control_aprobacion",
        "title": "Control aprobacion",
        "type": "detail_card",
        "items": [item],
    }
    return _prune_empty(section)


def _build_contingencias_section(document: dict[str, Any]) -> dict[str, Any] | None:
    rules = deepcopy((_section(document, "reglas_negocio") or {}).get("reglas") or [])
    kpis = deepcopy(_section(document, "kpis") or {})
    items = []
    for name in _ADJUSTMENT_NAMES:
        if name == "margen_objetivo_cadena_a":
            items.append(
                {
                    "concepto": name,
                    "aplicado": kpis.get("margen_objetivo_cadena_a") or (_section(document, "configuracion_comercial") or {}).get("margen_objetivo_cadena_a"),
                    "minimo": kpis.get("margen_minimo_requerido"),
                    "maximo": None,
                    "estado": _margin_status(kpis),
                }
            )
            continue
        item = next((rule for rule in rules if rule.get("nombre") == name), {})
        items.append(
            {
                "concepto": name,
                "aplicado": item.get("aplicado"),
                "minimo": item.get("min_valor"),
                "maximo": item.get("max_valor"),
                "estado": item.get("status"),
            }
        )
    section = {
        "id": "contingencias_ajustes",
        "title": "Contingencias y ajustes",
        "type": "table",
        "items": items,
    }
    return _prune_empty(section)


def _build_aprobaciones_section(document: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    container = deepcopy(_section(document, "aprobaciones") or {})
    control = deepcopy(_section(document, "control_aprobacion") or {})
    source = container if isinstance(container, dict) else {}
    if isinstance(control, dict):
        source.update({key: value for key, value in control.items() if key not in source})

    items = []
    missing = []
    for actor_key in _APPROVAL_ACTOR_KEYS:
        actor = source.get(actor_key)
        if isinstance(actor, dict):
            item = {"actor_key": actor_key, **actor}
        elif actor not in (None, "", [], {}):
            item = {"actor_key": actor_key, "nombre": actor}
        else:
            item = None

        if item:
            items.append(item)
        else:
            missing.append(f"aprobaciones.{actor_key}")

    section = None
    if items:
        section = {
            "id": "aprobaciones",
            "title": "Aprobaciones",
            "type": "approvals",
            "items": items,
        }
    return (_prune_empty(section) if section else None, missing)


def build_public_vision_imprimible(document: dict[str, Any]) -> VisionImprimibleDataV1:
    """Build and validate the screen-ready vision_imprimible contract from persisted data."""
    document = document or {}
    simulation_id = document.get("simulation_id")
    charts = _build_charts(document)

    sections = []
    missing_fields: list[str] = []
    for builder in (
        _build_ficha_section,
        _build_economics_section,
        _build_configuracion_section,
    ):
        built = builder(document)
        if built:
            sections.append(built)

    analisis = _build_analisis_section(document, charts)
    if analisis:
        sections.append(analisis)

    for builder in (
        _build_comparativo_section,
        _build_control_section,
        _build_contingencias_section,
    ):
        built = builder(document)
        if built:
            sections.append(built)

    approvals_section, approvals_missing = _build_aprobaciones_section(document)
    if approvals_section:
        sections.append(approvals_section)
    else:
        missing_fields.extend(approvals_missing)

    payload = {
        "version": "v1",
        "simulation_id": simulation_id,
        "header": _build_header(document),
        "summary_cards": _build_summary_cards(document),
        "sections": sections,
        "charts": charts,
        "metadata": {
            "source": "persisted_pricing_result",
            "missing_fields": missing_fields,
        },
    }
    pruned = _prune_empty(payload) or {}
    pruned.setdefault("header", {})
    pruned.setdefault("summary_cards", [])
    pruned.setdefault("sections", [])
    pruned.setdefault("charts", {})
    pruned.setdefault("metadata", {"source": "persisted_pricing_result", "missing_fields": missing_fields})
    return VisionImprimibleDataV1.model_validate(pruned)


__all__ = ["build_public_vision_imprimible"]
