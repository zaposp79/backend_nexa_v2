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
    """Vision general por servicio por Cadena (A/B/C).

    Excel 'Cost to Serve'!C34/G34/K34 — CTS por cadena con desglose de componentes.
    Cadena A: valores per-FTE. Cadenas B/C: totales mensuales absolutos.
    Participacion (%): fraccion del componente sobre el CTS total de su propia cadena.
    Participacion de cadena: fraccion volumetrica global (Panel!W32/X32/Y32).
    """
    perfiles = vision_cts.get("perfiles") or []
    cadenas_list = vision_cts.get("cadenas") or []

    prl_total  = float(vision_cts.get("payroll_total") or 0)
    npl_total  = float(vision_cts.get("no_payroll_total") or 0)
    # Excel CTS = Payroll + No Payroll (excluye ICA/GMF/polizas/comision/financiacion)
    cts_base   = prl_total + npl_total

    # Nomina Loaded = Salario Fijo + Salario Variable (crucero es item separado)
    sal_fijo   = sum(float(p.get("salario_fijo", 0))   for p in perfiles)
    sal_var    = sum(float(p.get("salario_variable", 0)) for p in perfiles)
    nom_loaded = sal_fijo + sal_var
    crucero    = sum(float(p.get("crucero", 0))         for p in perfiles)
    opex_it    = sum(float(p.get("opex_it", 0))         for p in perfiles)
    inversiones = sum(float(p.get("inversiones", 0))    for p in perfiles)
    costos_fijos = sum(float(p.get("costos_fijos", 0))  for p in perfiles)
    cap_ini    = sum(float(p.get("capacitacion_inicial", 0))   for p in perfiles)
    cap_rot    = sum(float(p.get("capacitacion_rotacion", 0))  for p in perfiles)
    examenes   = sum(float(p.get("examenes", 0))               for p in perfiles)
    estudios   = sum(float(p.get("estudios_seguridad", 0))     for p in perfiles)

    # Divisor: por perfil, si unidad == "FTE" → fte × igf (volumen); si no → fte crudo.
    # Esto permite mezclar canales con unidad FTE y canales con unidad Volumen.
    _igf = float(vision_cts.get("igf") or 0.0)
    _fte_stored = int(vision_cts.get("n_fte_total") or 0)
    if perfiles:
        _divisor = 0.0
        for _p in perfiles:
            _p_fte = int(_p.get("fte", 0) or 0)
            _p_unidad = (_p.get("unidad") or "FTE").upper()
            if _p_unidad == "FTE" and _igf > 0:
                _divisor += _p_fte * _igf
            else:
                _divisor += _p_fte
        fte = max(_divisor, 1)
    else:
        fte = max(_fte_stored, 1)

    # Participaciones volumetricas globales (almacenadas en engine._build_cadenas)
    _b_data = next((c for c in cadenas_list if c.get("cadena") == "CADENA B"), None)
    _c_data = next((c for c in cadenas_list if c.get("cadena") == "CADENA C"), None)
    _part_b = float((_b_data or {}).get("participacion", 0.0))
    _part_c = float((_c_data or {}).get("participacion", 0.0))
    _part_a = max(0.0, 1.0 - _part_b - _part_c)

    def _item(total: float, base_for_pct: float) -> Dict[str, Any]:
        pct = (base_for_pct / cts_base) if cts_base > 0 else 0.0
        return {"total": round(total / fte, 2), "participacion": _pct_str(pct)}

    cadena_a = {
        "nombre": "cadena_a",
        "participacion": round(_part_a, 6),
        # CTS = Payroll + No Payroll (sin financiero)
        "cost_to_serve":        _item(cts_base,    cts_base),
        "payroll":              _item(prl_total,   prl_total),
        # Nomina Loaded = Salario Fijo + Salario Variable
        "nomina_loaded":        _item(nom_loaded,  nom_loaded),
        "salario_fijo":         _item(sal_fijo,    sal_fijo),
        "salario_variable":     _item(sal_var,     sal_var),
        "capacitacion_inicial": _item(cap_ini,     cap_ini),
        "capacitacion_rotacion":_item(cap_rot,     cap_rot),
        "examenes_medicos":     _item(examenes,    examenes),
        "estudios_seguridad":   _item(estudios,    estudios),
        "crucero":              _item(crucero,     crucero),
        "no_payroll":           _item(npl_total,   npl_total),
        "opex_fijo":            _item(opex_it,     opex_it),
        "inversiones":          _item(inversiones, inversiones),
        "costos_fijos_x_estacion": _item(costos_fijos, costos_fijos),
    }

    _z = {"total": 0.0, "participacion": "0.00"}

    # Cadena B — componentes desde desglose almacenado en engine._build_cadenas
    if _b_data:
        _b_total = float(_b_data.get("total", 0))
        _b_vol   = float(_b_data.get("volumen") or 0)  # X31: volumen mensual Cadena B
        _b_div   = max(_b_vol, 1)                       # divisor: volumen (interacciones/mes)
        _b_des = _b_data.get("desglose") or {}
        _b_opex      = float(_b_des.get("opex_fijo", 0))
        _b_cap       = float(_b_des.get("capex", 0))
        _b_sm        = float(_b_des.get("sm", 0))
        _b_comp_fijo = _b_opex + _b_cap + _b_sm
        _b_tarifa    = float(_b_des.get("tarifa", 0))
        _b_opex_var  = float(_b_des.get("opex_variable", 0))
        _b_escal     = float(_b_des.get("tasa_escalamiento", 0))
        _b_hitl      = float(_b_des.get("hitl", 0))
        _b_comp_var  = _b_tarifa + _b_opex_var + _b_escal + _b_hitl

        def _bi(val: float, base: float) -> Dict[str, Any]:
            pct = (base / _b_total) if _b_total > 0 else 0.0
            return {"total": round(val / _b_div, 2), "participacion": _pct_str(pct)}

        cadena_b = {
            "nombre": "cadena_b",
            "participacion": round(_part_b, 6),
            "cost_to_serve":       _bi(_b_total,     _b_total),
            "componente_fijo":     _bi(_b_comp_fijo, _b_comp_fijo),
            "opex":                _bi(_b_opex,      _b_opex),
            "inversiones":         _bi(_b_cap,       _b_cap),
            "s_y_m":               _bi(_b_sm,        _b_sm),
            "componente_variable": _bi(_b_comp_var,  _b_comp_var),
            "tarifa":              _bi(_b_tarifa,    _b_tarifa),
            "opex_variable":       _bi(_b_opex_var,  _b_opex_var),
            "tasa_escalamiento":   _bi(_b_escal,     _b_escal),
            "hitl":                _bi(_b_hitl,      _b_hitl),
        }
    else:
        cadena_b = {
            "nombre": "cadena_b",
            "participacion": "0.00",
            "cost_to_serve": _z, "componente_fijo": _z, "opex": _z, "inversiones": _z,
            "s_y_m": _z, "componente_variable": _z, "tarifa": _z, "opex_variable": _z,
            "tasa_escalamiento": _z, "hitl": _z,
        }

    # Cadena C — componentes desde desglose almacenado en engine._build_cadenas
    if _c_data:
        _c_total = float(_c_data.get("total", 0))
        _c_vol   = float(_c_data.get("volumen") or 0)  # Y31: volumen mensual Cadena C
        _c_div   = max(_c_vol, 1)                       # divisor: volumen (interacciones/mes)
        _c_des = _c_data.get("desglose") or {}
        _c_tar_prov  = float(_c_des.get("tarifa_proveedor", 0))
        _c_opex      = float(_c_des.get("opex_fijo", 0))
        _c_cap       = float(_c_des.get("capex", 0))
        _c_equipo    = float(_c_des.get("equipo_integracion", 0))
        _c_costo_int = _c_opex + _c_cap + _c_equipo
        _c_escal     = float(_c_des.get("tasa_escalamiento", 0))
        _c_opex_var  = float(_c_des.get("opex_variable", 0))
        _c_hitl      = float(_c_des.get("hitl", 0))
        _c_costo_var = _c_escal + _c_opex_var + _c_hitl

        def _ci(val: float, base: float) -> Dict[str, Any]:
            pct = (base / _c_total) if _c_total > 0 else 0.0
            return {"total": round(val / _c_div, 2), "participacion": _pct_str(pct)}

        cadena_c = {
            "nombre": "cadena_c",
            "participacion": round(_part_c, 6),
            "cost_to_serve":      _ci(_c_total,     _c_total),
            "tarifa_proveedor":   _ci(_c_tar_prov,  _c_tar_prov),
            "costo_integracion":  _ci(_c_costo_int, _c_costo_int),
            "opex":               _ci(_c_opex,      _c_opex),
            "inversiones":        _ci(_c_cap,       _c_cap),
            "equipo_integracion": _ci(_c_equipo,    _c_equipo),
            "costo_variable":     _ci(_c_costo_var, _c_costo_var),
            "tasa_escalamiento":  _ci(_c_escal,     _c_escal),
            "opex_variable":      _ci(_c_opex_var,  _c_opex_var),
            "hitl":               _ci(_c_hitl,      _c_hitl),
        }
    else:
        cadena_c = {
            "nombre": "cadena_c",
            "participacion": "0.00",
            "cost_to_serve": _z, "tarifa_proveedor": _z, "costo_integracion": _z,
            "opex": _z, "inversiones": _z, "equipo_integracion": _z,
            "costo_variable": _z, "tasa_escalamiento": _z, "opex_variable": _z, "hitl": _z,
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
            participacion = canal_data.get("participacion") or {}
            participation_a = participacion.get("participacion_a", 0)
            participation_b = participacion.get("participacion_b", 0)
            participation_c = participacion.get("participacion_c", 0)
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
            cap_ini      = sum(float(p.get("capacitacion_inicial",  0)) for p in perfiles)
            cap_rot      = sum(float(p.get("capacitacion_rotacion", 0)) for p in perfiles)
            examenes     = sum(float(p.get("examenes",              0)) for p in perfiles)
            estudios     = sum(float(p.get("estudios_seguridad",    0)) for p in perfiles)
            cts_ponderado = (cts_base * participation_a) + (0 * participation_b) + (0 * participation_c)   # TODO: calcular CTS ponderado por canal (Excel: =(C34*C31)+(G34*G31)+(K34*K31))

            def _item(total: float, base_for_pct: float, _fte: float = fte, _base: float = cts_base) -> Dict[str, Any]:
                pct = (base_for_pct / _base) if _base > 0 else 0.0
                return {"total": round(total / _fte, 2), "participacion": _pct_str(pct)}

            _z = {"total": 0.0, "participacion": "0.00"}
            data_items = [
                {
                    "nombre": "cadena_a",
                    "participacion": participation_a,
                    "cost_to_serve":            _item(cts_base,    cts_base),
                    "payroll":                  _item(prl_total,   prl_total),
                    "nomina_loaded":            _item(nom_loaded,  nom_loaded),
                    "salario_fijo":             _item(sal_fijo,    sal_fijo),
                    "salario_variable":         _item(sal_var,     sal_var),
                    "capacitacion_inicial":     _item(cap_ini,     cap_ini),
                    "capacitacion_rotacion":    _item(cap_rot,     cap_rot),
                    "examenes_medicos":         _item(examenes,    examenes),
                    "estudios_seguridad":       _item(estudios,    estudios),
                    "crucero":                  _item(crucero,     crucero),
                    "no_payroll":               _item(npl_total,   npl_total),
                    "opex_fijo":                _item(opex_it,     opex_it),
                    "inversiones":              _item(inversiones, inversiones),
                    "costos_fijos_x_estacion":  _item(costos_fijos, costos_fijos),
                },
                {"nombre": "cadena_b", "participacion": participation_b},
                {"nombre": "cadena_c", "participacion": participation_c},
            ]
            result.append({
                "modalidad": modalidad_key.capitalize(),
                "canal": canal,
                "ctsPonderado": cts_ponderado,
                "data": data_items,
            })
    return result


def _build_vision_general_canal(
    vision_por_canal: Dict[str, Any],
    cadenas_list: List[Dict[str, Any]],
    igf: float,
) -> List[Dict[str, Any]]:
    """Vision general por canal.

    Excel C64: volumen = vol_a + vol_b + vol_c (total interactions per canal).
    Excel D/E: Cadena A participacion = valor_canal / total_valor_direction; valor = costo_directo/fte.
    Excel F/G: Cadena B participacion = vol_b_canal / tvol_b_direction; valor = cadena_b_monthly_dir / tvol_b_direction.
    Excel H/I: Cadena C — same pattern as B.
    Excel J: ctsPonderado = valor_a * part_a + valor_b * part_b + valor_c * part_c.
    """
    cadena_b_obj = next((c for c in cadenas_list if c.get("cadena") == "CADENA B"), {})
    cadena_c_obj = next((c for c in cadenas_list if c.get("cadena") == "CADENA C"), {})

    # First pass: derive vol_b and vol_c per canal using stored participacion ratios
    canal_volumes: Dict[tuple, Dict[str, float]] = {}
    for dir_key in ("inbound", "outbound"):
        for cd in (vision_por_canal.get(dir_key) or []):
            canal_name = cd.get("canal", "")
            fte = float(cd.get("fte", 0))
            # FTE → volume using IGF; if unidad=Volumen the perfiles store it directly
            perfs = cd.get("perfiles") or []
            unidad = next((p.get("unidad", "FTE") for p in perfs if p.get("unidad")), "FTE")
            vol_a = fte * igf if unidad == "FTE" else fte

            part_dict = cd.get("participacion") or {}
            part_a = float(part_dict.get("participacion_a", 0))
            part_b = float(part_dict.get("participacion_b", 0))
            part_c = float(part_dict.get("participacion_c", 0))

            if part_a > 0 and vol_a > 0:
                vol_total = vol_a / part_a
                vol_b = part_b * vol_total
                vol_c = part_c * vol_total
            else:
                vol_b = 0.0
                vol_c = 0.0

            canal_volumes[(dir_key, canal_name)] = {
                "vol_a": vol_a, "vol_b": vol_b, "vol_c": vol_c,
                "part_a": part_a, "part_b": part_b, "part_c": part_c,
            }

    # Aggregate totals per direction
    tvol_b: Dict[str, float] = {}
    tvol_c: Dict[str, float] = {}
    total_valor_dir: Dict[str, float] = {}
    for dir_key in ("inbound", "outbound"):
        tvol_b[dir_key] = sum(v["vol_b"] for k, v in canal_volumes.items() if k[0] == dir_key)
        tvol_c[dir_key] = sum(v["vol_c"] for k, v in canal_volumes.items() if k[0] == dir_key)
        total_valor_dir[dir_key] = sum(
            _costo_directo_per_fte(cd)
            for cd in (vision_por_canal.get(dir_key) or [])
            if float(cd.get("fte", 0)) > 0
        )

    result = []
    for dir_key in ("inbound", "outbound"):
        cadena_b_monthly = float(cadena_b_obj.get(dir_key, 0))
        cadena_c_monthly = float(cadena_c_obj.get(dir_key, 0))
        _tvol_b = tvol_b[dir_key]
        _tvol_c = tvol_c[dir_key]
        _total_valor_a = total_valor_dir[dir_key]

        canales = []
        for cd in (vision_por_canal.get(dir_key) or []):
            canal_name = cd.get("canal", "")
            fte = float(cd.get("fte", 0))
            activo = fte > 0

            valor_a = round(_costo_directo_per_fte(cd), 2) if activo else 0.0
            pct_a = round(valor_a / _total_valor_a, 10) if (activo and _total_valor_a > 0) else 0.0

            vols = canal_volumes.get((dir_key, canal_name), {})
            vol_a = vols.get("vol_a", 0.0)
            vol_b = vols.get("vol_b", 0.0)
            vol_c = vols.get("vol_c", 0.0)
            part_a = vols.get("part_a", 0.0)
            part_b = vols.get("part_b", 0.0)
            part_c = vols.get("part_c", 0.0)

            has_b = vol_b > 0 and _tvol_b > 0
            valor_b = round(cadena_b_monthly / _tvol_b, 2) if has_b else 0.0
            pct_b = round(vol_b / _tvol_b, 10) if has_b else 0.0

            has_c = vol_c > 0 and _tvol_c > 0
            valor_c = round(cadena_c_monthly / _tvol_c, 2) if has_c else 0.0
            pct_c = round(vol_c / _tvol_c, 10) if has_c else 0.0

            cts_ponderado = round(valor_a * part_a + valor_b * part_b + valor_c * part_c, 2)

            canales.append({
                "canal": canal_name,
                "volumen": round(vol_a + vol_b + vol_c, 2),
                "cadena_a": {"participacion": pct_a, "valor": valor_a, "activo": activo},
                "cadena_b": {"participacion": pct_b, "valor": valor_b, "activo": has_b},
                "cadena_c": {"participacion": pct_c, "valor": valor_c, "activo": has_c},
                "ctsPonderado": cts_ponderado,
            })
        result.append({"nombre": dir_key, "canales": canales})
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
    periodo_pago = result.get("periodo_pago")

    header = {
        "cliente":            result.get("cliente"),
        "servicio":           result.get("servicio"),
        "tipo_cliente":       result.get("tipo_cliente"),
        "antiguedad_cliente": result.get("antiguedad_cliente"),
        "periodo_pago":       periodo_pago,
        "fecha_inicio":       result.get("fecha_inicio"),
        "duracion_meses":     result.get("duracion_meses"),
        "ciudad":             result.get("ciudad"),
        "sede":               result.get("sede"),
    }

    # Excel 'Vision Cost To Serve'!B19 — ingreso_neto del primer mes al 100% ramp
    _economics = (result.get("vision_imprimible") or {}).get("seccion_02_economics") or {}
    ingreso_b19 = _economics.get("ingreso_mensual") or vision_cts.get("ingreso_mensual", 0.0)

    # Excel 'Vision Cost To Serve'!H19 — CTS Mensual = HME!C258 + C268 + C278
    # Cadena A: cts_mensual (payroll + no_payroll + financiero — tal como lo reporta HME!C258)
    # Cadenas B/C: total_hme = Op + Pol + ICA + GMF (HME!C268 / C278, incluye financieros)
    _cadenas_list = vision_cts.get("cadenas") or []
    _cts_b = next((c.get("total_hme", c.get("total", 0.0)) for c in _cadenas_list if c.get("cadena") == "CADENA B"), 0.0)
    _cts_c = next((c.get("total_hme", c.get("total", 0.0)) for c in _cadenas_list if c.get("cadena") == "CADENA C"), 0.0)
    cts_mensual = vision_cts.get("cts_mensual", 0.0) + _cts_b + _cts_c
    valor_contrato = vision_cts.get("valor_total_contrato", 0.0)
    requiere_aprobacion = False
    
    if(valor_contrato >= 1000000000):
        requiere_aprobacion = True
    elif(valor_contrato/periodo_pago >= 200000000):
        requiere_aprobacion = True
    elif(valor_contrato/periodo_pago >= 100000000):
        requiere_aprobacion = True

    summary_cards = [
        {
            "key": "ingreso",
            "label": "Ingreso",
            "value": ingreso_b19,
            "format": "currency",
        },
        {
            "key": "costo",
            "label": "CTS Mensual",
            "value": cts_mensual,
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
            "value": vision_cts.get("cts_por_fte", 0.0),
            "format": "currency",
        },
        {
            "key": "valor_contrato",
            "label": "Valor Total Contrato",
            "value": valor_contrato,
            "format": "currency",
        },
        {
            "key": "requiere_aprobacion",
            "label": "Requiere aprobacion",
            "value": requiere_aprobacion,
            "format": "boolean",
        }
    ]

    # Scores de riesgo vienen de vision_imprimible.seccion_05_control (calculado en _build_control)
    control_riesgo: Dict[str, Any] = (result.get("vision_imprimible") or {}).get("seccion_05_control") or {}

    # Sección: factor_de_riesgo — 10 ítems desde seccion_05_control.preguntas
    # Excel V2-8: 'Vision Cost To Serve'!G213:G241 + lookup Riesgo!V2:Y12
    _RIESGO_DETALLE: Dict[str, Dict[str, str]] = {
        "Clasificación de oportunidad": {
            "Alto": "Negocio encima de 1000 SMLV (facturación mensual): exposición financiera significativa, mayor responsabilidad operativa",
            "Medio": "",
            "Bajo": "No requiere aprobación: impacto absorbible dentro de márgenes normales",
        },
        "Tipo de cliente": {
            "Alto": "Externo sin vínculo con Nexa ni Grupo Aval: comportamiento comercial incierto",
            "Medio": "",
            "Bajo": "Grupo Aval: relación conocida, respaldo institucional, condiciones estándar",
        },
        "Período de pago": {
            "Alto": "Pago mayor a 60 días: impacto directo en flujo de caja, mayor necesidad de capital de trabajo",
            "Medio": "Pago entre 30 y 60 días: presión moderada sobre flujo de caja, manejable con planeación",
            "Bajo": "Pago a 30 días o menos: flujo de caja predecible, menor presión sobre capital de trabajo",
        },
        "Experiencia con el cliente": {
            "Alto": "Sin historial: riesgo alto de desalineación en expectativas, procesos y SLAs",
            "Medio": "",
            "Bajo": "Con historial: patrones operativos y comerciales conocidos, menor probabilidad de sorpresas",
        },
        "Presupuesto de imprevistos": {
            "Alto": "Sí (>$0): el cliente reconoce incertidumbre — señal de mayor complejidad o alcance no definido",
            "Medio": "",
            "Bajo": "No (=$0): alcance bien definido, sin colchón para desviaciones — exige mayor control de cambios",
        },
        "Alertas activadas": {
            "Alto": "3 alertas: concentración de riesgos críticos, requiere revisión antes de avanzar",
            "Medio": "1-2 alertas: riesgo manejable con mitigadores definidos por factor",
            "Bajo": "No se generan alertas: perfil de riesgo bajo, proceder con condiciones estándar",
        },
        "Complejidad": {
            "Alto": "Alta complejidad multicanal (≥10): agentes especializados, mayor costo de error y recontacto",
            "Medio": "Complejidad moderada (≥5): proceso definido con variabilidad y excepciones recurrentes",
            "Bajo": "Baja complejidad (≤4): proceso estandarizado, repetitivo, alto potencial de automatización",
        },
        "Capacitaciones": {
            "Alto": "Mayor a 20 días: ramp-up prolongado, mayor costo de habilitación y retraso en productividad",
            "Medio": "Entre 10 y 20 días: tiempo manejable, requiere planificación de recursos de formación",
            "Bajo": "Menor a 10 días: ramp-up corto, inicio rápido y costo de habilitación bajo",
        },
        "Rotación": {
            "Alto": "Superior a 10%: inestabilidad operativa, costo recurrente de reposición y riesgo de SLA",
            "Medio": "Entre 5% y 10%: impacto manejable con plan de retención y protocolo de reposición activo",
            "Bajo": "Menor a 5%: operación estable, bajo costo de reposición, alta continuidad del conocimiento",
        },
        "Dependencia de terceros": {
            "Alto": "Mayor a 50%: fallas externas impactan SLAs directamente sin control de Nexa",
            "Medio": "Entre 10% y 50%: dependencia moderada, gestionable con acuerdos de servicio definidos",
            "Bajo": "Menor a 10%: ejecución bajo control directo de Nexa, mínima exposición externa",
        },
    }

    # preguntas vienen en orden 1-10; el campo `factor` es la pregunta textual de OP (no el nombre canónico).
    # Mapeamos por id (1-10) para relacionar cada pregunta con el nombre canónico de _RIESGO_DETALLE.
    _preguntas_by_id = {_p.get("id"): _p for _p in (control_riesgo.get("preguntas") or [])}
    _factor_riesgo_items = []
    for _pid, (_fname, _niveles) in enumerate(_RIESGO_DETALLE.items(), start=1):
        _nivel = (_preguntas_by_id.get(_pid) or {}).get("nivel", "")
        _factor_riesgo_items.append({
            "factor": _fname,
            "detalle": _niveles.get(_nivel, ""),
            "riesgo": _nivel,
        })

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
            "items": _factor_riesgo_items,
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
            "items": _build_vision_general_canal(vision_por_canal, _cadenas_list, vision_cts.get("igf", 0.0)),
        },
        {
            "key": "perfiles",
            "label": "Desglose por Perfil",
            "source": "vision_cts.perfiles",
            "items": perfiles,
        },
    ]

    # Charts: proporcion_nomina_cargo — proporción por cargo de estructura (excl. agente base)
    # Excel Graficos: AI5:AJ28 = cargo / SUMIFS(nóminas, todos los cargos de estructura)
    # Retorna todos los cargos (incluidos con valor=0), agrupados por perfil.
    nomina_por_cargo: Dict[str, float] = vision_cts.get("nomina_por_cargo") or {}
    total_estructura = sum(v for v in nomina_por_cargo.values() if v > 0) or 1.0
    # Proporciones globales (misma estructura de staff para todos los perfiles)
    cargo_proportions = [
        {"nombre": cargo, "valor": round(monto / total_estructura, 4)}
        for cargo, monto in nomina_por_cargo.items()
    ]
    # Estructura por-perfil: cada perfil muestra los mismos cargos globales
    proporcion_por_perfil = [
        {"perfil": p.get("nombre", ""), "data": cargo_proportions}
        for p in perfiles
    ]

    # proporcion_nomina_grupo — grupos de estructura por perfil
    # Excel Graficos: AH31:AI33 = SUMIF(grupo, proporciones) filtrado por perfil activo
    nomina_grupos: Dict[str, Any] = vision_cts.get("nomina_grupos_por_perfil") or {}
    proporcion_por_grupo = [
        {"perfil": p.get("nombre", ""), "data": nomina_grupos.get(p.get("nombre", ""), [])}
        for p in perfiles
    ]

    score_total = round(float(control_riesgo.get("score_deal", 0.0)), 2)
    score_cliente = round(float(control_riesgo.get("score_cliente", 0.0)), 2)
    score_operativo = round(float(control_riesgo.get("score_operativo", 0.0)), 2)

    charts = {
        "proporcion_nomina_cargo": proporcion_por_perfil,
        "proporcion_nomina_grupo": proporcion_por_grupo,
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
