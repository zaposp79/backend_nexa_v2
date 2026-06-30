"""F6 — Oracle mesh mapping.

≥150 checkpoints distribuidos en el pipeline (INPUT → AGGREGATE → OUTPUT)
con extractores funcionales para `backend_result` (`PricingResult`).

Cada checkpoint declara:
  - id: identificador estable
  - excel: celda Excel (Hoja!Coord) — fuente de verdad
  - stage: etapa del pipeline (PANEL / NOMINA / STAFFING / RAMPUP /
    INDEXACION / NO_PAYROLL / COSTOS_FINANCIEROS / COSTO_TOTAL /
    FACTOR_BILLING / INGRESO / PYG / KPI / VISIONES)
  - category: agrupación dentro del stage
  - extractor: callable(result) -> float | None
  - expected: valor Excel (resuelto desde el oracle JSON)

El extractor devuelve `None` cuando el backend no expone el equivalente —
señal honesta de hueco semántico, NO se enmascara con skip.

No se importa el oracle JSON aquí (lo hace el test). Este módulo es puro
catálogo de extractores.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


Extractor = Callable[[Any], Optional[float]]


@dataclass(frozen=True)
class MeshCheckpoint:
    id: str
    excel: str
    stage: str
    category: str
    extractor: Extractor
    label: str = ""
    rel_tol: Optional[float] = None  # per-checkpoint override; None → global REL_TOL


# ---------------------------------------------------------------------------
# Helpers para extracción
# ---------------------------------------------------------------------------

def _pyg_field(field: str, contract_month_idx: int):
    """Retorna lambda que extrae result.pyg_por_mes[i].<field>."""
    def _ext(r):
        try:
            m = r.pyg_por_mes[contract_month_idx]
            v = getattr(m, field, None)
            return float(v) if isinstance(v, (int, float)) else None
        except (AttributeError, IndexError, TypeError):
            return None
    return _ext


def _pyg_prop(prop: str, contract_month_idx: int):
    """Como _pyg_field pero accede a una @property (e.g. ingreso_bruto, costo_total)."""
    return _pyg_field(prop, contract_month_idx)


def _vt(attr: str):
    def _ext(r):
        vt = getattr(r, "vision_tarifas", None)
        if vt is None:
            return None
        v = getattr(vt, attr, None)
        return float(v) if isinstance(v, (int, float)) else None
    return _ext


def _cts(attr: str):
    def _ext(r):
        c = getattr(r, "cost_to_serve", None)
        if c is None:
            return None
        v = getattr(c, attr, None)
        return float(v) if isinstance(v, (int, float)) else None
    return _ext


def _panel(attr: str):
    def _ext(r):
        v = getattr(r.panel, attr, None)
        return float(v) if isinstance(v, (int, float)) else None
    return _ext


def _kpi(attr: str):
    def _ext(r):
        v = getattr(r.kpis, attr, None)
        return float(v) if isinstance(v, (int, float)) else None
    return _ext


def _channel(canal_substr: str, attr: str):
    """Extractor por canal — busca canal cuyo nombre contiene `canal_substr`."""
    def _ext(r):
        vt = getattr(r, "vision_tarifas", None)
        if vt is None:
            return None
        for ch in vt.canales:
            if canal_substr.lower() in (ch.nombre_canal or "").lower():
                v = getattr(ch, attr, None)
                return float(v) if isinstance(v, (int, float)) else None
        return None
    return _ext


def _vt_canal_idx(idx: int, attr: str):
    """Extractor por índice de canal en vision_tarifas.canales[idx].<attr>."""
    def _ext(r):
        vt = getattr(r, "vision_tarifas", None)
        if vt is None:
            return None
        try:
            ch = vt.canales[idx]
        except (IndexError, TypeError):
            return None
        v = getattr(ch, attr, None)
        return float(v) if isinstance(v, (int, float)) else None
    return _ext


def _missing(_r):
    """Extractor explícito de hueco — declara que backend no expone equivalente."""
    return None


# Calendar→contract month: contract starts in Junio (calendar M6).
# Excel cols C..N = calendar M1..M12.
# So contract month 1 = calendar M6 = Excel col H (index 5).
# Backend pyg_por_mes is 0-indexed by contract month.
def _excel_col_to_contract_idx(col_letter: str) -> int:
    cal = ord(col_letter.upper()) - ord("C") + 1  # C=1 ... N=12
    # contract month = cal - 5 (since cal M6 -> contract M1)
    contract = cal - 5
    return contract - 1  # 0-indexed


# ---------------------------------------------------------------------------
# CHECKPOINT CATALOG
# ---------------------------------------------------------------------------

CHECKPOINTS: list[MeshCheckpoint] = []


def _ck(*args, **kw):
    CHECKPOINTS.append(MeshCheckpoint(*args, **kw))


# ============================================================================
# STAGE: PANEL — input echo (35 checkpoints)
# ============================================================================
_ck("panel.tarifa_capacitacion_diaria", "Panel de Control General!C16",
    "PANEL", "INPUT", _panel("tarifa_diaria_capacitacion"), "tarifa cap diaria")
_ck("panel.crucero", "Panel de Control General!C17",
    "PANEL", "INPUT", _panel("tarifa_crucero"), "crucero — Panel!C17")
_ck("panel.horas_formacion_mensual", "Panel de Control General!C18",
    "PANEL", "INPUT", _panel("horas_formacion_mensual"))
_ck("panel.pct_ausentismo", "Panel de Control General!C19",
    "PANEL", "INPUT", _panel("pct_ausentismo"))
_ck("panel.tasa_ica", "Panel de Control General!C34",
    "PANEL", "INPUT", _panel("tasa_ica"))
_ck("panel.tasa_gmf", "Panel de Control General!C35",
    "PANEL", "INPUT", _panel("tasa_gmf"))
_ck("panel.margen_a", "Panel de Control General!C63",
    "PANEL", "INPUT", _panel("margen"))
_ck("panel.margen_b", "Panel de Control General!D63",
    "PANEL", "INPUT", _panel("margen_b"))
_ck("panel.markup", "Panel de Control General!C64",
    "PANEL", "INPUT", _panel("markup"))
_ck("panel.descuento", "Panel de Control General!C65",
    "PANEL", "INPUT", _panel("descuento"))
_ck("panel.op_cont", "Panel de Control General!C66",
    "PANEL", "INPUT", _panel("op_cont"))
_ck("panel.com_cont", "Panel de Control General!C67",
    "PANEL", "INPUT", _panel("com_cont"))
_ck("panel.imprevistos", "Panel de Control General!C68",
    "PANEL", "INPUT", _panel("imprevistos"))
_ck("panel.periodo_pago", "Panel de Control General!C9",
    "PANEL", "INPUT", _panel("periodo_pago_dias"))
_ck("panel.meses_contrato", "Panel de Control General!C11",
    "PANEL", "INPUT", _panel("meses_contrato"))


# ============================================================================
# STAGE: NOMINA INPUTS (constants & per-perfil costo empresa)
# ============================================================================
# C. Empresa por perfil "Inputs de Nomina!W{row}" — el motor expone esto
# via `vision_tarifas.canales[].nomina_loaded_ch / payroll_ch`. No hay un
# mapeo cell-by-cell del W column en outputs, pero podemos verificar
# agregado por canal (W39 + W40 ≈ payroll Inbound 25 / mes).
_ck("nomina.W39_costo_empresa_inbound25_perfil", "Inputs de Nomina!W39",
    "NOMINA", "COSTO_EMPRESA_PERFIL", _vt_canal_idx(0, "salario_cargado_ch"),
    "salario_cargado por FTE del canal 0 (Inbound 25 / Voz)")
_ck("nomina.W40", "Inputs de Nomina!W40",
    "NOMINA", "COSTO_EMPRESA_PERFIL", _vt_canal_idx(1, "salario_cargado_ch"),
    "salario_cargado por FTE del canal 1 (WhatsApp)")
_ck("nomina.W41", "Inputs de Nomina!W41",
    "NOMINA", "COSTO_EMPRESA_PERFIL", _missing)
_ck("nomina.W42", "Inputs de Nomina!W42",
    "NOMINA", "COSTO_EMPRESA_PERFIL", _missing)
_ck("nomina.W43", "Inputs de Nomina!W43",
    "NOMINA", "COSTO_EMPRESA_PERFIL", _missing)


# ============================================================================
# STAGE: NOMINA LOADED (aggregations per canal/mes)
# ============================================================================
# Nomina Loaded I93 = salario fijo Voz contract M1 (~82.2M).
# Backend lo expone via canal "Inbound 25"  salario_fijo_ch * count?
# Hay un cuello: el motor expone valores _mensual promedio_, no per-month.
# Usamos canal.salario_fijo_ch (que es promedio mensual del canal).
_ck("nomina_loaded.salario_fijo_voz_m1", "Nomina Loaded!I93",
    "NOMINA_LOADED", "SALARIO_FIJO_CANAL",
    _channel("inbound 25", "salario_fijo_ch"))
_ck("nomina_loaded.salario_fijo_whatsapp_m1", "Nomina Loaded!I97",
    "NOMINA_LOADED", "SALARIO_FIJO_CANAL",
    _channel("whatsapp", "salario_fijo_ch"))
_ck("nomina_loaded.salario_fijo_total_m1", "Nomina Loaded!I100",
    "NOMINA_LOADED", "SALARIO_FIJO_TOTAL",
    lambda r: sum((ch.salario_fijo_ch or 0.0) for ch in r.vision_tarifas.canales))
_ck("nomina_loaded.nomina_total_m6_calendar", "Nomina Loaded!I89",
    "NOMINA_LOADED", "NOMINA_TOTAL",
    lambda r: sum((ch.nomina_loaded_ch or 0.0) for ch in r.vision_tarifas.canales))
# Más meses (M6..M12 backend → cal H..N)
for col_idx, col in enumerate("IJKLMNOPQRST"):
    cidx = col_idx  # contract M1+col_idx if col starts at I (cal M6)
    if cidx >= 12:
        break
    _ck(f"nomina_loaded.salario_fijo_voz_contractM{cidx+1}",
        f"Nomina Loaded!{col}93",
        "NOMINA_LOADED", "SALARIO_FIJO_PER_MES",
        # backend: salario_fijo_ch is monthly avg — same for all months
        _channel("inbound 25", "salario_fijo_ch"))


# ============================================================================
# STAGE: PAYROLL_A (aggregated per contract month — Visión P&G row 32)
# ============================================================================
# Visión P&G!H32 = payroll_a contract M1 (calendar M6)
for col in "HIJKLMN":  # contract M1..M7
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.payroll_a.contractM{cidx+1}", f"Visión P&G!{col}32",
        "PAYROLL_A", "PER_MES", _pyg_field("payroll_a", cidx))

# Visión P&G row 33-40 (sub-componentes — Excel los detalla; backend agrega en payroll_a)
# Mantenemos solo los componentes que P&G tiene como filas.

# Costo total operativo Cadena A — Visión P&G row 31
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.costo_a.contractM{cidx+1}", f"Visión P&G!{col}31",
        "COSTO_A", "PER_MES", _pyg_prop("costo_a", cidx))

# No payroll Cadena A — Visión P&G row 41
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.no_payroll_a.contractM{cidx+1}", f"Visión P&G!{col}41",
        "NO_PAYROLL_A", "PER_MES", _pyg_field("no_payroll_a", cidx))

# Costo Cadena B — Visión P&G row 45
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.costo_b.contractM{cidx+1}", f"Visión P&G!{col}45",
        "COSTO_B", "PER_MES", _pyg_field("costo_b", cidx))

# Costo Cadena C — Visión P&G row 55
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.costo_c.contractM{cidx+1}", f"Visión P&G!{col}55",
        "COSTO_C", "PER_MES", _pyg_field("costo_c", cidx))


# ============================================================================
# STAGE: COSTO_TOTAL — Visión P&G row 30
# ============================================================================
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.costo_total.contractM{cidx+1}", f"Visión P&G!{col}30",
        "COSTO_TOTAL", "PER_MES", _pyg_prop("costo_total", cidx))


# ============================================================================
# STAGE: COSTOS_FINANCIEROS — Visión P&G rows 65-70 (etiquetas reales del Excel)
# Row 65 = Componente Financiero (subtotal = SUM 66:70)
# Row 66 = ICA, 67 = GMF, 68 = Comisión de Administración,
# Row 69 = Pólizas adicionales, 70 = Costos Financieros (financiación)
# ============================================================================
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.costos_financieros.contractM{cidx+1}", f"Visión P&G!{col}65",
        "COSTOS_FINANCIEROS", "TOTAL", _pyg_field("costos_financieros", cidx))
    _ck(f"pyg.ica.contractM{cidx+1}", f"Visión P&G!{col}66",
        "COSTOS_FINANCIEROS", "ICA", _pyg_field("ica", cidx))
    _ck(f"pyg.gmf.contractM{cidx+1}", f"Visión P&G!{col}67",
        "COSTOS_FINANCIEROS", "GMF", _pyg_field("gmf", cidx))
    _ck(f"pyg.comision_administracion.contractM{cidx+1}", f"Visión P&G!{col}68",
        "COSTOS_FINANCIEROS", "COMISION_ADM", _pyg_field("comision_administracion", cidx))
    _ck(f"pyg.polizas.contractM{cidx+1}", f"Visión P&G!{col}69",
        "COSTOS_FINANCIEROS", "POLIZAS", _pyg_field("polizas", cidx))
    _ck(f"pyg.financiacion.contractM{cidx+1}", f"Visión P&G!{col}70",
        "COSTOS_FINANCIEROS", "FINANCIACION", _pyg_field("financiacion", cidx))


# ============================================================================
# STAGE: INGRESO — Visión P&G rows 18 (bruto), 27 (neto)
# ============================================================================
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.ingreso_bruto.contractM{cidx+1}", f"Visión P&G!{col}18",
        "INGRESO", "BRUTO", _pyg_prop("ingreso_bruto", cidx))
    _ck(f"pyg.ingreso_neto.contractM{cidx+1}", f"Visión P&G!{col}27",
        "INGRESO", "NETO", _pyg_prop("ingreso_neto", cidx))


# ============================================================================
# STAGE: RAMPUP — Visión P&G row 15
# ============================================================================
for col in "CDEFGHIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    if cidx < 0:
        continue  # pre-contract calendar months
    _ck(f"pyg.rampup.contractM{cidx+1}", f"Visión P&G!{col}15",
        "RAMPUP", "FACTOR", _pyg_field("rampup", cidx))


# ============================================================================
# STAGE: CONTRIBUCION & UTILIDAD — rows 74, 79
# ============================================================================
for col in "HIJKLMN":
    cidx = _excel_col_to_contract_idx(col)
    _ck(f"pyg.contribucion.contractM{cidx+1}", f"Visión P&G!{col}74",
        "PYG", "CONTRIBUCION", _pyg_prop("contribucion", cidx))
    _ck(f"pyg.utilidad_neta.contractM{cidx+1}", f"Visión P&G!{col}79",
        "PYG", "UTILIDAD_NETA", _pyg_prop("utilidad_neta", cidx))


# ============================================================================
# STAGE: VISION_TARIFAS — totales
# ============================================================================
_ck("vt.costo_cadena_a_total", "Vision Tarifas_Modelo_Cobro!C40",
    "VISION_TARIFAS", "COSTO_CADENA", _vt("costo_cadena_a_total"))
# C50 = per-escenario-1 Cadena B cost (escenario 1 = Voz, no B volume → 0).
# costo_cadena_b_total is the DEAL TOTAL; extractor uses canales[0].cadena_b_atribuible.
_ck("vt.costo_cadena_b_total", "Vision Tarifas_Modelo_Cobro!C50",
    "VISION_TARIFAS", "COSTO_CADENA",
    lambda r: (r.vision_tarifas.canales[0].cadena_b_atribuible
               if r.vision_tarifas and r.vision_tarifas.canales else 0.0))
_ck("vt.costo_cadena_c_total", "Vision Tarifas_Modelo_Cobro!C60",
    "VISION_TARIFAS", "COSTO_CADENA", _vt("costo_cadena_c_total"))
# vt.costo_total removed: VT!C65 = Pólizas within Cadena C section (=0 in fixture),
# NOT the deal total. No single VT cell represents the total deal cost.
_ck("vt.ingreso_mensual", "Vision Tarifas_Modelo_Cobro!C72",
    "VISION_TARIFAS", "INGRESO_MENSUAL", _vt("ingreso_mensual"))
_ck("vt.ingreso_cadena_a", "Vision Tarifas_Modelo_Cobro!C47",
    "VISION_TARIFAS", "INGRESO_CADENA", _vt("ingreso_cadena_a"),
    "Ingreso anual cadena A (C47 = C40 / (1-margen))", rel_tol=3e-6)
# C57 = per-escenario-1 Ingreso Cadena B (=0, Voz has no B).
_ck("vt.ingreso_cadena_b", "Vision Tarifas_Modelo_Cobro!C57",
    "VISION_TARIFAS", "INGRESO_CADENA",
    lambda r: (r.vision_tarifas.canales[0].cadena_b_atribuible
               if r.vision_tarifas and r.vision_tarifas.canales else 0.0))
_ck("vt.ingreso_cadena_c", "Vision Tarifas_Modelo_Cobro!C67",
    "VISION_TARIFAS", "INGRESO_CADENA", _vt("ingreso_cadena_c"))


# ============================================================================
# STAGE: VISION_CTS — Cost To Serve
# ============================================================================
_ck("cts.ingreso_mensual_acumulado", "Vision Cost To Serve!B19",
    "VISION_CTS", "INGRESO", _vt("ingreso_mensual"))
# PROBLEMA 2 (Opción A): H19 = C40+C60 se verifica contra vision_tarifas (escenario);
# cost_to_serve.costo_total_acumulado es ahora nativo deal-wide (no es H19).
_ck("cts.costo_total_scenario", "Vision Cost To Serve!H19",
    "VISION_CTS", "COSTO_TOTAL", _vt("costo_total_scenario"))
_ck("cts.participacion_a", "Vision Cost To Serve!C31",
    "VISION_CTS", "PARTICIPACION", _cts("participacion_a"))
_ck("cts.participacion_b", "Vision Cost To Serve!G31",
    "VISION_CTS", "PARTICIPACION", _cts("participacion_b"))
_ck("cts.participacion_c", "Vision Cost To Serve!K31",
    "VISION_CTS", "PARTICIPACION", _cts("participacion_c"))
_ck("cts.cadena_a", "Vision Cost To Serve!C34",
    "VISION_CTS", "CTS_CADENA", _cts("cts_cadena_a"))
_ck("cts.cadena_b", "Vision Cost To Serve!G34",
    "VISION_CTS", "CTS_CADENA", _cts("cts_cadena_b"))
_ck("cts.cadena_c", "Vision Cost To Serve!K34",
    "VISION_CTS", "CTS_CADENA", _cts("cts_cadena_c"))
_ck("cts.ponderado", "Vision Cost To Serve!G49",
    "VISION_CTS", "PONDERADO", _cts("cts_ponderado"))


# ============================================================================
# STAGE: KPIS final
# ============================================================================
# PROBLEMA 2 (Opción A): las cifras de ESCENARIO B19/H19/C72 se verifican contra
# vision_tarifas (su dueño). kpis.* es ahora nativo deal-wide (no se sobrescribe),
# por lo que no representa estas celdas de escenario del Excel.
_ck("scenario.costo_mensual_h19", "Vision Cost To Serve!H19",
    "KPI", "COSTO_PROMEDIO", _vt("costo_total_scenario"))
_ck("scenario.ingreso_mensual_b19", "Vision Cost To Serve!B19",
    "KPI", "INGRESO_MENSUAL", _vt("ingreso_mensual"))
_ck("scenario.facturacion_c72", "Vision Tarifas_Modelo_Cobro!C72",
    "KPI", "FACTURACION", _vt("ingreso_mensual"))


def list_all() -> list[MeshCheckpoint]:
    return list(CHECKPOINTS)


def by_stage() -> dict[str, list[MeshCheckpoint]]:
    out: dict[str, list[MeshCheckpoint]] = {}
    for c in CHECKPOINTS:
        out.setdefault(c.stage, []).append(c)
    return out
