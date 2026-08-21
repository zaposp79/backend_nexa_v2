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


def _pct_str(v: Any) -> str:
    """Convierte un float a porcentaje string con 2 decimales."""
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _compute_cts_ponderado_from_items(items: List[Dict[str, Any]]) -> float:
    """Excel: =(C34*C31)+(G34*G31)+(K34*K31)
    C34/G34/K34 = cost_to_serve.total; C31/G31/K31 = participacion (float).
    """
    total = 0.0
    for item in items:
        cts = item.get("cost_to_serve")
        if cts:
            total += float(cts.get("total", 0)) * float(item.get("participacion", 0))
    return round(total, 2)


def _build_vision_por_servicio(vision_cts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Vision general por servicio (Cadena A) para la sección del mismo nombre.

    Excel 'Cost to Serve'!C36 = SUM(C37:C38) = Payroll + No Payroll (sin financiero).
    Nómina Loaded = Salario Fijo + Salario Variable (crucero es fila separada).
    Participación (%) = componente / (Payroll + No Payroll).
    """
    fte = max(int(vision_cts.get("n_fte_total") or 1), 1)
    perfiles = vision_cts.get("perfiles") or []

    prl_total  = float(vision_cts.get("payroll_total") or 0)
    npl_total  = float(vision_cts.get("no_payroll_total") or 0)
    # Excel CTS = Payroll + No Payroll (excluye ICA/GMF/pólizas/comisión/financiación)
    cts_base   = prl_total + npl_total

    # Nómina Loaded = Salario Fijo + Salario Variable (crucero es ítem separado)
    sal_fijo   = sum(float(p.get("salario_fijo", 0))   for p in perfiles)
    sal_var    = sum(float(p.get("salario_variable", 0)) for p in perfiles)
    nom_loaded = sal_fijo + sal_var
    crucero    = sum(float(p.get("crucero", 0))         for p in perfiles)
    opex_it    = sum(float(p.get("opex_it", 0))         for p in perfiles)
    inversiones = sum(float(p.get("inversiones", 0))    for p in perfiles)
    costos_fijos = sum(float(p.get("costos_fijos", 0))  for p in perfiles)

    def _item(total: float, base_for_pct: float) -> Dict[str, Any]:
        pct = (base_for_pct / cts_base) if cts_base > 0 else 0.0
        return {"total": round(total / fte, 2), "participacion": _pct_str(pct)}

    cadena_a = {
        "nombre": "cadena_a",
        "participacion": _pct_str(1.0),
        # CTS = Payroll + No Payroll (sin financiero)
        "cost_to_serve":        _item(cts_base,    cts_base),
        "payroll":              _item(prl_total,   prl_total),
        # Nómina Loaded = Salario Fijo + Salario Variable
        "nomina_loaded":        _item(nom_loaded,  nom_loaded),
        "salario_fijo":         _item(sal_fijo,    sal_fijo),
        "salario_variable":     _item(sal_var,     sal_var),
        "capacitacion_inicial": _item(0, 0),
        "capacitacion_rotacion":_item(0, 0),
        "examenes_medicos":     _item(0, 0),
        "estudios_seguridad":   _item(0, 0),
        "crucero":              _item(crucero,     crucero),
        "no_payroll":           _item(npl_total,   npl_total),
        "opex_fijo":            _item(opex_it,     opex_it),
        "inversiones":          _item(inversiones, inversiones),
        "costos_fijos_x_estacion": _item(costos_fijos, costos_fijos),
    }

    _z = {"total": 0.0, "participacion": "0.00"}
    cadena_b = {
        "nombre": "cadena_b",
        "participacion": "0.00",
        "cost_to_serve":       _z,
        "componente_fijo":     _z,
        "opex":                _z,
        "inversiones":         _z,
        "s_y_m":               _z,
        "componente_variable": _z,
        "tarifa":              _z,
        "opex_variable":       _z,
        "tasa_escalamiento":   _z,
        "hitl":                _z,
    }
    cadena_c = {
        "nombre": "cadena_c",
        "participacion": "0.00",
        "cost_to_serve":       _z,
        "tarifa_proveedor":    _z,
        "costo_integracion":   _z,
        "opex":                _z,
        "inversiones":         _z,
        "equipo_integracion":  _z,
        "costo_variable":      _z,
        "tasa_escalamiento":   _z,
        "opex_variable":       _z,
        "hitl":                _z,
    }
    return [cadena_a, cadena_b, cadena_c]


def _costo_directo_per_fte(canal_data: Dict[str, Any]) -> float:
    """Excel CTS canal: costo_directo / fte (sin financiero).
    Cada perfil tiene costo_directo = payroll + no_payroll (sin ICA/GMF/pólizas).
    """
    perfiles = canal_data.get("perfiles") or []
    fte = float(canal_data.get("fte", 0))
    if fte <= 0:
        return 0.0
    cd_total = sum(float(p.get("costo_directo", 0)) for p in perfiles)
    return cd_total / fte


def _build_vision_detallada_canal(vision_por_canal: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Vision detallada por canal — desglosa Payroll y No Payroll por canal (Cadena A).

    Mismo patrón que _build_vision_por_servicio pero acotado a cada canal.
    Los perfiles del canal ya incluyen todos los sub-campos calculados por CTSCalculator.
    """
    result = []
    for modalidad_key in ("inbound", "outbound"):
        for canal_data in (vision_por_canal.get(modalidad_key) or []):
            canal = canal_data.get("canal", "")
            fte_raw = float(canal_data.get("fte", 0))
            perfiles = canal_data.get("perfiles") or []

            if fte_raw <= 0:
                _z = {"total": 0.0, "participacion": "0.00"}
                data_items = [
                    {
                        "nombre": "cadena_a",
                        "participacion": "0.00",
                        "cost_to_serve":            _z,
                        "payroll":                  _z,
                        "nomina_loaded":            _z,
                        "salario_fijo":             _z,
                        "salario_variable":         _z,
                        "capacitacion_inicial":     _z,
                        "capacitacion_rotacion":    _z,
                        "examenes_medicos":         _z,
                        "estudios_seguridad":       _z,
                        "crucero":                  _z,
                        "no_payroll":               _z,
                        "opex_fijo":                _z,
                        "inversiones":              _z,
                        "costos_fijos_x_estacion":  _z,
                    },
                    {"nombre": "cadena_b", "participacion": "0.00"},
                    {"nombre": "cadena_c", "participacion": "0.00"},
                ]
                result.append({"modalidad": modalidad_key.capitalize(), "canal": canal, "data": data_items})
                continue

            fte = fte_raw
            prl_total    = sum(float(p.get("payroll",        0)) for p in perfiles)
            npl_total    = sum(float(p.get("no_payroll",     0)) for p in perfiles)
            cts_base     = prl_total + npl_total
            sal_fijo     = sum(float(p.get("salario_fijo",   0)) for p in perfiles)
            sal_var      = sum(float(p.get("salario_variable", 0)) for p in perfiles)
            nom_loaded   = sal_fijo + sal_var
            crucero      = sum(float(p.get("crucero",        0)) for p in perfiles)
            opex_it      = sum(float(p.get("opex_it",        0)) for p in perfiles)
            inversiones  = sum(float(p.get("inversiones",    0)) for p in perfiles)
            costos_fijos = sum(float(p.get("costos_fijos",   0)) for p in perfiles)

            def _item(total: float, base_for_pct: float, _fte: float = fte, _base: float = cts_base) -> Dict[str, Any]:
                pct = (base_for_pct / _base) if _base > 0 else 0.0
                return {"total": round(total / _fte, 2), "participacion": _pct_str(pct)}

            _z = {"total": 0.0, "participacion": "0.00"}
            data_items = [
                {
                    "nombre": "cadena_a",
                    "participacion": "1.00",
                    "cost_to_serve":            _item(cts_base,    cts_base),
                    "payroll":                  _item(prl_total,   prl_total),
                    "nomina_loaded":            _item(nom_loaded,  nom_loaded),
                    "salario_fijo":             _item(sal_fijo,    sal_fijo),
                    "salario_variable":         _item(sal_var,     sal_var),
                    "capacitacion_inicial":     _item(0, 0),
                    "capacitacion_rotacion":    _item(0, 0),
                    "examenes_medicos":         _item(0, 0),
                    "estudios_seguridad":       _item(0, 0),
                    "crucero":                  _item(crucero,     crucero),
                    "no_payroll":               _item(npl_total,   npl_total),
                    "opex_fijo":                _item(opex_it,     opex_it),
                    "inversiones":              _item(inversiones, inversiones),
                    "costos_fijos_x_estacion":  _item(costos_fijos, costos_fijos),
                },
                {"nombre": "cadena_b", "participacion": "0.00"},
                {"nombre": "cadena_c", "participacion": "0.00"},
            ]
            result.append({
                "modalidad": modalidad_key.capitalize(),
                "canal": canal,
                "data": data_items,
            })
    return result


def _build_vision_general_canal(vision_por_canal: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Vision general por canal.

    Excel: Cadena A $ = costo_directo/fte por tipo de canal (sin financiero).
    Excel: % = valor_canal / sum(valores_activos_todos_canales).
    """
    # Denominador para % = suma de costo_directo/fte de todos los canales activos
    total_valor = 0.0
    for modalidad_key in ("inbound", "outbound"):
        for cd in (vision_por_canal.get(modalidad_key) or []):
            if float(cd.get("fte", 0)) > 0:
                total_valor += _costo_directo_per_fte(cd)

    result = []
    for modalidad_key in ("inbound", "outbound"):
        canales_raw = vision_por_canal.get(modalidad_key) or []
        canales = []
        for cd in canales_raw:
            fte = float(cd.get("fte", 0))
            activo = fte > 0
            valor = round(_costo_directo_per_fte(cd), 2) if activo else 0.0
            pct = round(valor / total_valor, 10) if (activo and total_valor > 0) else 0.0
            canales.append({
                "canal": cd.get("canal", ""),
                "volumen": cd.get("fte", 0),
                "cadena_a": {
                    "participacion": pct,
                    "valor": valor,
                    "activo": activo,
                },
                "cadena_b": {"participacion": 0, "valor": 0, "activo": False},
                "cadena_c": {"participacion": 0, "valor": 0, "activo": False},
                "ctsPonderado": valor,
            })
        result.append({"nombre": modalidad_key, "canales": canales})
    return result


_DETALLE_FACTOR_RIESGOS = [
    {
        "categoria": "Operativo",
        "descripcion": "Cubre sobredotación, rotación, ramp-up extendido, recontacto y fallas de terceros",
        "niveles": [
            {"nivel": "Bajo", "desde": 1, "hasta": 4},
            {"nivel": "Medio", "desde": 5, "hasta": 8},
            {"nivel": "Alto", "desde": 9, "hasta": 12},
        ],
    },
    {
        "categoria": "Comercial",
        "descripcion": "Cubre mora en pago, cambios de alcance, terminación anticipada y renegociaciones",
        "niveles": [
            {"nivel": "Bajo", "desde": 1, "hasta": 3},
            {"nivel": "Medio", "desde": 4, "hasta": 7},
            {"nivel": "Alto", "desde": 8, "hasta": 12},
        ],
    },
]


def _build_from_v2_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Construye el contrato de pantalla CTS desde un resultado del Motor de Reglas (v2)."""
    simulation_id = result.get("simulation_id")
    vision_cts: Dict[str, Any] = result.get("vision_cts") or {}
    perfiles: List[Dict[str, Any]] = vision_cts.get("perfiles") or []
    vision_por_canal: Dict[str, Any] = vision_cts.get("vision_por_canal") or {}

    header = {
        "cliente":            result.get("cliente"),
        "servicio":           result.get("servicio"),
        "tipo_cliente":       result.get("tipo_cliente"),
        "antiguedad_cliente": result.get("antiguedad_cliente"),
        "periodo_pago":       result.get("periodo_pago"),
        "fecha_inicio":       result.get("fecha_inicio"),
        "duracion_meses":     result.get("duracion_meses"),
        "ciudad":             result.get("ciudad"),
        "sede":               result.get("sede"),
    }

    summary_cards = [
        {
            "key": "ingreso",
            "label": "Ingreso",
            "value": vision_cts.get("ingreso_mensual", 0.0),
            "format": "currency",
        },
        {
            "key": "costo",
            "label": "CTS Mensual",
            "value": vision_cts.get("cts_mensual", 0.0),
            "format": "currency",
        },
        {
            "key": "margen",
            "label": "Margen",
            "value": vision_cts.get("margen", 0.0),
            "format": "percent",
        },
        {
            "key": "cts",
            "label": "CTS por FTE",
            "value": vision_cts.get("costo_directo_por_fte", 0.0),
            "format": "currency",
        },
        {
            "key": "valor_contrato",
            "label": "Valor Total Contrato",
            "value": vision_cts.get("valor_total_contrato", 0.0),
            "format": "currency",
        },
    ]

    # Sección: factor_de_riesgo (evaluación resumida — stub basado en valor contrato)
    valor_contrato = float(vision_cts.get("valor_total_contrato") or 0)
    if valor_contrato > 5_000_000_000:
        nivel_riesgo, detalle_riesgo = "Alto", "El contrato requiere aprobación por valor superior a 5000 SMLV"
    elif valor_contrato > 1_000_000_000:
        nivel_riesgo, detalle_riesgo = "Medio", "El contrato requiere revisión: valor entre 1000 y 5000 SMLV"
    else:
        nivel_riesgo, detalle_riesgo = "Bajo", "No requiere aprobación: impacto absorbible dentro de márgenes normales"

    _vgs_items = _build_vision_por_servicio(vision_cts)
    _cts_ponderado = _compute_cts_ponderado_from_items(_vgs_items)

    sections: List[Dict[str, Any]] = [
        {
            "key": "totales",
            "label": "Totales Cadena A",
            "source": "vision_cts",
            "items": [
                {
                    "n_fte_total": vision_cts.get("n_fte_total"),
                    "payroll_total": vision_cts.get("payroll_total"),
                    "no_payroll_total": vision_cts.get("no_payroll_total"),
                    "costo_directo_total": vision_cts.get("costo_directo_total"),
                    "financiero_total": vision_cts.get("financiero_total"),
                    "cts_total": vision_cts.get("cts_total"),
                    "payroll_por_fte": vision_cts.get("payroll_por_fte"),
                    "no_payroll_por_fte": vision_cts.get("no_payroll_por_fte"),
                    "costo_directo_por_fte": vision_cts.get("costo_directo_por_fte"),
                    "financiero_por_fte": vision_cts.get("financiero_por_fte"),
                    "cts_por_fte": vision_cts.get("cts_por_fte"),
                }
            ],
        },
        {
            "key": "factor_de_riesgo",
            "label": "Factor de riesgo",
            "source": "vision_cts",
            "items": [
                {
                    "factor": "Clasificación de oportunidad",
                    "detalle": detalle_riesgo,
                    "riesgo": nivel_riesgo,
                }
            ],
        },
        {
            "key": "detalle_factor_riesgos",
            "label": "Detalle factor de riesgos",
            "source": "",
            "items": _DETALLE_FACTOR_RIESGOS,
        },
        {
            "key": "reglas_de_negocio",
            "label": "Reglas de negocio",
            "source": "",
            "items": vision_cts.get("reglas_negocio") or [],
        },
        {
            "key": "cadenas_estructura_de_equipo",
            "label": "Cadenas",
            "source": "",
            "items": vision_cts.get("cadenas") or [],
        },
        {
            "key": "vision_general_por_servicio",
            "label": "Vision general por servicio",
            "source": "",
            "cts_ponderado": _cts_ponderado,
            "items": _vgs_items,
        },
        {
            "key": "vision_detallada_por_canal",
            "label": "Vision detallada por canal",
            "source": "",
            "items": _build_vision_detallada_canal(vision_por_canal),
        },
        {
            "key": "vision_general_por_canal",
            "label": "Vision general por canal",
            "source": "",
            "items": _build_vision_general_canal(vision_por_canal),
        },
        {
            "key": "perfiles",
            "label": "Desglose por Perfil",
            "source": "vision_cts.perfiles",
            "items": perfiles,
        },
    ]

    # Charts: proporcion_nomina_cargo — proporción por cargo de estructura (excl. agente base)
    # Excel Graficos: AI5:AJ28 = cargo / SUMIFS(nóminas, "<>"&"Agente Básico 1")
    nomina_por_cargo: Dict[str, float] = vision_cts.get("nomina_por_cargo") or {}
    total_estructura = sum(nomina_por_cargo.values()) or 1.0
    proporcion_cargo = [
        {"nombre": cargo, "valor": round(monto / total_estructura, 4)}
        for cargo, monto in nomina_por_cargo.items()
        if monto > 0
    ]

    # Scores de riesgo vienen de vision_imprimible.seccion_05_control (calculado en _build_control)
    control_riesgo: Dict[str, Any] = (result.get("vision_imprimible") or {}).get("seccion_05_control") or {}
    score_total = round(float(control_riesgo.get("score_deal", 0.0)), 2)
    score_cliente = round(float(control_riesgo.get("score_cliente", 0.0)), 2)
    score_operativo = round(float(control_riesgo.get("score_operativo", 0.0)), 2)

    charts = {
        "proporcion_nomina_cargo": proporcion_cargo,
        "proporcion_nomina_grupo": [{"perfil": p.get("nombre", ""), "data": []} for p in perfiles],
        "evaluacion_de_riesgo": [
            {"nombre": "Total", "valor": score_total},
            {"nombre": "Cliente", "valor": score_cliente},
            {"nombre": "Operativo", "valor": score_operativo},
        ],
        "data_status": {
            "available_charts": 0,
            "missing_charts": 0,
        },
    }

    return {
        "version": "v2",
        "simulation_id": simulation_id,
        "header": header,
        "summary_cards": summary_cards,
        "sections": sections,
        "charts": charts,
        "metadata": {
            "source": "motor_de_reglas_v2",
            "missing_fields": [],
        },
    }


def build_vision_cts_from_result(pricing_result_dict: dict) -> dict:
    """Build screen-ready CTS contract from persisted pricing_result."""
    result = pricing_result_dict or {}

    # Motor de Reglas v2: estructura diferente (vision_cts directo)
    if result.get("version") == "v2":
        return _build_from_v2_result(result)

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
