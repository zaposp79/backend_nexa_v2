"""WAVE 17 — Mapping de celdas Excel V2-7 a paths del output del motor.

Cada entrada del oráculo (`excel_oracle_v2_7_full.json`) que tenga `backend_path`
puede ser evaluada por `resolve_backend_path(result, path)` para extraer el
valor que el motor produce. Si no hay equivalente directo, devuelve `None` y
el test debe fallar (no skip silencioso) — esa es la señal de hueco real.

Sintaxis del backend_path: simple dotted-path con soporte para índices y
filtros básicos:

    "cost_to_serve.cts_ponderado"
    "vision_tarifas.costo_cadena_a_total"
    "vision_pyg.filas[?key=='ingreso_bruto'].valores[5]"
    "vision_tarifas.canales[?nombre_canal=='WhatsApp'].tarifa_fijo_fte"
"""
from __future__ import annotations

import re
from dataclasses import is_dataclass, fields
from typing import Any, Optional


def _get_attr_or_key(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


_FILTER_RE = re.compile(r"^\[\?([a-zA-Z_]\w*)\s*==\s*'([^']*)'\]$")
_INDEX_RE = re.compile(r"^\[(\d+)\]$")


def _tokenize(path: str) -> list[str]:
    """Convierte 'a.b[?k=='v'].c[3]' en ['a','b','[?k==\\'v\\']','c','[3]']."""
    tokens: list[str] = []
    buf = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            i += 1
        elif ch == "[":
            if buf:
                tokens.append(buf)
                buf = ""
            j = path.find("]", i)
            tokens.append(path[i:j + 1])
            i = j + 1
        else:
            buf += ch
            i += 1
    if buf:
        tokens.append(buf)
    return tokens


def resolve_backend_path(result: Any, path: str) -> Optional[float]:
    """Devuelve el valor numérico de `result` en `path`, o None si no existe."""
    cur: Any = result
    for tok in _tokenize(path):
        if cur is None:
            return None
        m = _INDEX_RE.match(tok)
        if m:
            idx = int(m.group(1))
            if isinstance(cur, (list, tuple)) and 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                return None
            continue
        m = _FILTER_RE.match(tok)
        if m:
            key, expected = m.group(1), m.group(2)
            if not isinstance(cur, (list, tuple)):
                return None
            matches = [
                item for item in cur
                if str(_get_attr_or_key(item, key)) == expected
            ]
            if not matches:
                return None
            cur = matches[0]
            continue
        cur = _get_attr_or_key(cur, tok)
    if isinstance(cur, (int, float)):
        return float(cur)
    return None


# -----------------------------------------------------------------------------
# Tabla canónica de mapping: celda Excel → backend_path
# -----------------------------------------------------------------------------
# Solo los outputs que tienen una correspondencia razonable en el modelo
# actual del motor. Para los que NO la tienen, se omiten — el test
# correspondiente fallará con "Backend missing equivalent" (señal de hueco).

CELL_TO_BACKEND: dict[str, str] = {
    # Cost To Serve
    "Vision Cost To Serve!B19": "vision_tarifas.ingreso_mensual",
    # PROBLEMA 2 (Opción A): H19 = C40+C60 vive en vision_tarifas (escenario), no en
    # cost_to_serve.costo_total_acumulado (ahora nativo deal-wide, sin overwrite).
    "Vision Cost To Serve!H19": "vision_tarifas.costo_total_scenario",
    "Vision Cost To Serve!C31": "cost_to_serve.participacion_a",
    "Vision Cost To Serve!G31": "cost_to_serve.participacion_b",
    "Vision Cost To Serve!K31": "cost_to_serve.participacion_c",
    "Vision Cost To Serve!C34": "cost_to_serve.cts_cadena_a",
    "Vision Cost To Serve!G34": "cost_to_serve.cts_cadena_b",
    "Vision Cost To Serve!K34": "cost_to_serve.cts_cadena_c",
    "Vision Cost To Serve!G49": "cost_to_serve.cts_ponderado",

    # Vision Tarifas — niveles deal
    # C40 = Cadena A total (escenario 1 channel, Voz): maps to backend total ✓
    "Vision Tarifas_Modelo_Cobro!C40": "vision_tarifas.costo_cadena_a_total",
    # C50 = Cadena B cost for escenario-1's channel (Voz). Voz has no B volume → C50=0.
    # Backend: canales[0].cadena_b_atribuible = 0.0 (Voz channel B attribution).
    # NOTE: costo_cadena_b_total is the TOTAL annual B (≠ C50 which is per-escenario).
    "Vision Tarifas_Modelo_Cobro!C50": "vision_tarifas.canales[0].cadena_b_atribuible",
    "Vision Tarifas_Modelo_Cobro!C60": "vision_tarifas.costo_cadena_c_total",
    "Vision Tarifas_Modelo_Cobro!C72": "vision_tarifas.ingreso_mensual",

    # P&G monthly — Excel indexa por mes calendario (M1=Enero 2026 ... M12=Diciembre 2026).
    # El contrato comienza en fecha_inicio=2026-06-01, así que columna Excel H (M6) = contract M1.
    # Backend.vision_pyg.filas[].valores[k] indexa contract month (k=0 → M1 contractual).
    # Mapping calendar→contract: Excel H (calendar 6) → backend valores[0] (contract 1).
    #                            Excel J (calendar 8) → backend valores[2] (contract 3).
    "Visión P&G!H15": "vision_pyg.filas[?key=='rampup'].valores[0]",   # contrato M1
    "Visión P&G!J15": "vision_pyg.filas[?key=='rampup'].valores[2]",   # contrato M3
    "Visión P&G!H18": "vision_pyg.filas[?key=='ingreso_bruto'].valores[0]",
    "Visión P&G!J18": "vision_pyg.filas[?key=='ingreso_bruto'].valores[2]",
    "Visión P&G!H30": "vision_pyg.filas[?key=='costo_total'].valores[0]",
    "Visión P&G!J30": "vision_pyg.filas[?key=='costo_total'].valores[2]",
    "Visión P&G!H31": "vision_pyg.filas[?key=='costo_a'].valores[0]",
    "Visión P&G!J31": "vision_pyg.filas[?key=='costo_a'].valores[2]",
    "Visión P&G!H32": "vision_pyg.filas[?key=='payroll_a'].valores[0]",
    "Visión P&G!J32": "vision_pyg.filas[?key=='payroll_a'].valores[2]",
    "Visión P&G!H41": "vision_pyg.filas[?key=='no_payroll_a'].valores[0]",
    "Visión P&G!J41": "vision_pyg.filas[?key=='no_payroll_a'].valores[2]",
    "Visión P&G!H45": "vision_pyg.filas[?key=='costo_b'].valores[0]",
    "Visión P&G!J45": "vision_pyg.filas[?key=='costo_b'].valores[2]",
    "Visión P&G!H55": "vision_pyg.filas[?key=='costo_c'].valores[0]",
    "Visión P&G!J55": "vision_pyg.filas[?key=='costo_c'].valores[2]",
    "Visión P&G!H66": "vision_pyg.filas[?key=='ica'].valores[0]",
    "Visión P&G!J66": "vision_pyg.filas[?key=='ica'].valores[2]",
    "Visión P&G!H67": "vision_pyg.filas[?key=='gmf'].valores[0]",
    "Visión P&G!J67": "vision_pyg.filas[?key=='gmf'].valores[2]",
    "Visión P&G!H74": "vision_pyg.filas[?key=='contribucion'].valores[0]",
    "Visión P&G!J74": "vision_pyg.filas[?key=='contribucion'].valores[2]",
    "Visión P&G!H79": "vision_pyg.filas[?key=='utilidad_neta'].valores[0]",
    "Visión P&G!J79": "vision_pyg.filas[?key=='utilidad_neta'].valores[2]",

    # Inputs de Nomina — `salario_minimo` y `auxilio_transporte` son parametrización
    # interna (PayrollParametrizationRepository), no outputs del deal. No se exponen
    # vía PricingResult.panel. Estos mappings se omiten intencionalmente: comparar
    # un echo de parametrización contra sí mismo no añade señal sobre la corrección
    # del motor. WAVE 18 los reclasifica como "fuera de scope del oracle de outputs".

    # Panel inputs (input echo)
    "Panel de Control General!C63": "panel.margen",
    "Panel de Control General!D63": "panel.margen_b",
    "Panel de Control General!C35": "panel.tasa_gmf",
}


def list_mapped_cells() -> list[str]:
    """Lista las celdas con backend_path conocido."""
    return list(CELL_TO_BACKEND.keys())
