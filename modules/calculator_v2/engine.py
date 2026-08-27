"""
Motor de Reglas — motor de cálculo basado en rubros maestro.

Pipeline por capa:
  1. Nómina       — NominaCalculator (aggregated, Python)
  2. No Payroll   — NoPayrollCalculator (aggregated, Python)
  3. Costo Cadena — formula
  4. P&G Ingresos — formula (ingreso_cadena_a → ingreso_neto)
  5. Financiero   — aggregated Python (ICA, GMF, pólizas) — depende de ingreso_neto
  6. Costo Total  — formula
  7. KPIs         — formula (contribución, utilidad)

Resolución de dependencia circular ICA/GMF ↔ ingreso_neto:
  El ingreso se calcula primero sobre costos operativos (nomina + no_payroll).
  Los costos financieros se calculan después sobre ese ingreso.
  Costo total = operativo + financiero (secuencial, sin iteración).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .cadena_b_calculator import CadenaBCalculator
from .context_builder import build_base_context
from .cts_calculator import CTSCalculator
from .escenarios_enricher import enrich_perfiles_with_escenarios
from .formula_evaluator import evaluate_formula
from .models import PerfilCTS, ResultadoMes, RubroMaestro, SimulationResultV2, VisionCostToServe, VisionPyG
from .no_payroll_calculator import NoPayrollCalculator
from .nomina_calculator import NominaCalculator
from .vision_imprimible_builder import build_vision_imprimible
from .vision_tarifas_builder import build_vision_tarifas
from .rubros_repository import RubrosRepository

logger = logging.getLogger("nexa.motor_reglas.engine")

# IDs de rubros que usan calculadores Python (tipo_calculo: aggregated)
# comision_admin_mensual: ya está incluida dentro de polizas_mensual → siempre 0
# ingreso_cadena_a: calculado por _compute_ingreso_cadena_a_hm (fórmula Hoja Maestra)
_AGGREGATED_IDS = {
    "nomina_total_mensual",
    "no_payroll_total_mensual",
    "ingreso_cadena_a",
    "costo_cadena_b",
    "costo_cadena_c",
    "comision_admin_mensual",
    # Computado en context_builder desde perfiles.estaciones_presenciales — no pisar con fórmula
    "estaciones_trabajo",
    # Sub-componentes de nómina: calculados en NominaCalculator × double_h — no pisar con fórmula
    # Excel V2-8: 'Nomina Loaded'!K108:K127 (salario_fijo) y K198:K217 (comisiones brutas)
    "nomina_loaded_mensual",
    "salario_fijo_mensual",
    "salario_variable_mensual",
    # Capital charge diferido: calculado en el loop (CT[k-1] × meses_cc × tasa × IPC_k) — no pisar con fórmula
    # Excel V2-8: 'Pólizas - Costo Financiacion'!L528:L606 × "Activado" × IPC_factor
    "costos_financiacion_mensual",
    # Cadena B: calculados por CadenaBCalculator × IPC — no pisar con fórmula de rubros
    "componente_fijo_b",
    "componente_variable_b",
    "opex_fijo_cadena_b",
    "opex_variable_cadena_b",
    "capex_cadena_b",
    "sm_cadena_b",
    "tarifa_canal_cadena_b",
    "tasa_escalamiento_cadena_b",
    "hitl_cadena_b",
    # ingreso_cadena_b: computado en el loop con ramp_up × IPC_incremental (mirrors ingreso_cadena_a)
    "ingreso_cadena_b",
}

# Excel V2-8: 'Pólizas - Costo Financiacion'!D338 = FILTER(Panel!D45) × 1.42
# La Hoja Maestra aplica este factor a la comision admin en el cálculo de pricing
_COMISION_ADMIN_FACTOR_HM = 1.42

# Rubros financieros calculados en Python DESPUÉS de ingreso_neto
# costo_fijo_externo: depende de ingreso_neto; pct_costo_fijo viene de GN (no cargado aún → 0)
_FINANCIAL_AGGREGATED = {
    "ica_mensual",
    "gmf_mensual",
    "polizas_mensual",
    "componente_financiero_total",
    "costo_fijo_externo",
}

_VISION_PYG_KEYS = [
    "ingreso_bruto",
    "ingreso_neto",
    "costo_total",
    "contribucion",
    "pct_contribucion",
    "utilidad_neta",
    "pct_utilidad_neta",
    "nomina_total_mensual",
    "no_payroll_total_mensual",
    "componente_financiero_total",
]


def _calendar_year_month(fecha_inicio: datetime, mes_numero: int) -> Tuple[int, int]:
    """Retorna (año, mes) calendario para el mes N del deal (mes_numero base 1)."""
    total_months = fecha_inicio.month + (mes_numero - 1)
    year = fecha_inicio.year + (total_months - 1) // 12
    month = ((total_months - 1) % 12) + 1
    return year, month


def _compute_ipc_factor(
    fecha_inicio: datetime,
    mes_numero: int,
    mes_ajuste: int,
    ipc_rates: Dict[int, float],
) -> float:
    """Factor IPC acumulado para el mes del deal.

    # Excel V2-8: 'Panel de Control General'!L9-L10 — Frecuencia=Anual, Mes ajuste=1
    # El IPC del año X aplica desde el 1ro del mes_ajuste de ese año.
    # El año de inicio del deal es el año base (factor=1.0).
    """
    año_cal, mes_cal = _calendar_year_month(fecha_inicio, mes_numero)
    año_inicio = fecha_inicio.year

    factor = 1.0
    for año in range(año_inicio + 1, año_cal + 1):
        # IPC del año actual aplica solo si ya se superó el mes de ajuste
        if año == año_cal and mes_cal < mes_ajuste:
            break
        rate = ipc_rates.get(año, 0.0)
        factor *= (1.0 + rate)

    return factor


def _compute_ipc_incremental(
    fecha_inicio: datetime,
    mes_numero: int,
    mes_ajuste: int,
    ipc_rates: Dict[int, float],
) -> float:
    """Factor IPC incremental del año calendario del mes para P&G.

    # Excel V2-8: 'Tasas, TRM, Polizas'!J8:O16 "Aumento x Año"
    # El P&G aplica este factor EXTRA sobre los costos del NL (que ya tienen el acumulado).
    # Para ingreso: mismo factor como única aplicación sobre HM_avg.
    """
    año_cal, mes_cal = _calendar_year_month(fecha_inicio, mes_numero)
    año_inicio = fecha_inicio.year
    if año_cal <= año_inicio or mes_cal < mes_ajuste:
        return 0.0
    return ipc_rates.get(año_cal, 0.0)


def _compute_avg_ipc_factor_single(
    fecha_inicio: Optional[datetime],
    duracion_meses: int,
    mes_ajuste: int,
    ipc_rates: Dict[int, float],
    ipc_activo: bool,
) -> float:
    """Factor IPC promedio simple (NL-level) sobre todos los meses del deal.

    # Excel V2-8: 'Hoja Maestra'!C258 — SUMPRODUCT(NomLoaded!D15:BK33) / duracion
    # El NL aplica IPC acumulado a cada mes; el HM promedia esos valores.
    """
    if not ipc_activo or not fecha_inicio:
        return 1.0
    total = sum(
        _compute_ipc_factor(fecha_inicio, mes, mes_ajuste, ipc_rates)
        for mes in range(1, duracion_meses + 1)
    )
    return total / duracion_meses


class MotorDeReglas:
    def __init__(self, rubros_repo: RubrosRepository) -> None:
        self._repo = rubros_repo

    def calcular(self, request_data: Dict[str, Any]) -> SimulationResultV2:
        # Enriquece perfiles con modelo de cobro del Panel (escenarios) antes de cualquier cálculo
        request_data = enrich_perfiles_with_escenarios(request_data)

        datos_op = request_data.get("datos_operativos", {})
        duracion_meses = int(datos_op.get("duracion_meses", 10))
        simulation_id = str(uuid.uuid4())

        rubros = self._repo.get_rubros_maestros()

        # Pre-computar valores aggregated que no cambian mes a mes
        _nomina_calc = NominaCalculator(request_data)
        nomina_fija = _nomina_calc.calcular()
        _nomina_detalle = _nomina_calc.calcular_detalle()
        _nomina_desglose_cargo = _nomina_calc.desglose_por_cargo()
        _nomina_grupos_por_perfil = _nomina_calc.proporcion_nomina_por_grupo()
        ciudad = datos_op.get("ciudad", "")
        sede = datos_op.get("sede", "")
        costo_fijo_estacion = self._repo.get_hr_costo_fijo_estacion(ciudad, localidad=sede)
        _no_pay_calc = NoPayrollCalculator(request_data, costo_fijo_estacion)
        no_payroll_fijo = _no_pay_calc.calcular()
        _no_payroll_detalle = _no_pay_calc.calcular_detalle()

        # Cadenas activas — controlan qué componentes se incluyen en el cálculo
        _vol_data = request_data.get("volumetria") or {}

        # Cadena A — activa por defecto. Usa AND: si cualquier dirección la deshabilita → inactiva.
        _cadena_a_activa = (
            _vol_data.get("inbound", {}).get("cadenas_activas", {}).get("cadena_a", True)
            and _vol_data.get("outbound", {}).get("cadenas_activas", {}).get("cadena_a", True)
        )
        if not _cadena_a_activa:
            # Zerear todos los componentes de Cadena A para que no afecten el P&G
            nomina_fija = 0.0
            no_payroll_fijo = 0.0
            _nomina_detalle = {k: 0.0 for k in _nomina_detalle}
            _no_payroll_detalle = {k: 0.0 for k in _no_payroll_detalle}
            _nomina_desglose_cargo = {}
            _nomina_grupos_por_perfil = {}

        # Cadena B — activa si alguna dirección tiene cadena_b: true en cadenas_activas
        _cadena_b_activa = (
            _vol_data.get("inbound", {}).get("cadenas_activas", {}).get("cadena_b", False)
            or _vol_data.get("outbound", {}).get("cadenas_activas", {}).get("cadena_b", False)
        )
        _cadena_b_calc: Optional[CadenaBCalculator] = (
            CadenaBCalculator(request_data)
            if _cadena_b_activa and request_data.get("condiciones_cadena_b")
            else None
        )

        # Ramp-up desde HR-Campaña (prioridad sobre request.datos_operativos.ramp_up)
        servicio = datos_op.get("servicio", "")
        ramp_up_campana = self._repo.get_ramp_up_campana(servicio)

        # ── IPC indexación anual ────────────────────────────────────────────
        # Excel V2-8: 'Panel de Control General'!L7-L10
        # Tasas leídas desde OP-Componente en CosmosDB (domain='op').
        ipc_rates = self._repo.get_ipc_rates_op()
        indexacion = request_data.get("volumetria", {}).get("indexacion", {})
        comp_humano = str(indexacion.get("componente_humano", "")).upper()
        comp_tecnologico = str(indexacion.get("componente_tecnologico", "")).upper()
        mes_ajuste_ipc = int(indexacion.get("mes_aplicacion", 1))
        # Excel V2-8: 'Panel de Control General'!C21 / L8 — si False, tarifa no escala con IPC
        aplica_indexacion_tarifa = bool(indexacion.get("aplica_indexacion_tarifa", True))

        fecha_inicio: Optional[datetime] = None
        fecha_inicio_str = datos_op.get("fecha_inicio", "")
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str[:10], "%Y-%m-%d")
        except Exception:
            logger.warning("[motor-reglas] sim=%s fecha_inicio inválida '%s' — IPC no se aplicará", simulation_id, fecha_inicio_str)

        ipc_activo = bool(
            fecha_inicio and ipc_rates and (comp_humano == "IPC" or comp_tecnologico == "IPC")
        )

        logger.info(
            "[motor-reglas] sim=%s nomina=%.0f no_payroll=%.0f meses=%d ramp_src=%s ipc_activo=%s rates=%s",
            simulation_id, nomina_fija, no_payroll_fijo, duracion_meses,
            "cosmos" if ramp_up_campana else "request", ipc_activo, ipc_rates,
        )

        resultados_por_mes: List[ResultadoMes] = []

        # Ingreso base Hoja Maestra — se calcula sobre el costo promedio IPC del deal.
        # Excel V2-8: 'Hoja Maestra'!C296 — SUMPRODUCT(NomLoaded!D15:BK33) / duracion como base.
        # El NL aplica IPC acumulado (simple) a cada mes; la HM promedia esos valores para
        # obtener un ingreso estable que luego el P&G escala con el IPC incremental del año.
        _ctx_base = build_base_context(request_data, 1, ramp_up_override=ramp_up_campana)
        # HM usa costo promedio con IPC solo si la tarifa está indexada.
        # Si aplica_indexacion_tarifa=False, tarifa es fija → HM se basa en costos del mes 1.
        # Excel V2-8: 'Hoja Maestra'!C258 — solo promedia cuando la tarifa escala con IPC.
        _avg_ipc = (
            _compute_avg_ipc_factor_single(
                fecha_inicio, duracion_meses, mes_ajuste_ipc, ipc_rates, ipc_activo
            )
            if aplica_indexacion_tarifa else 1.0
        )
        _avg_nomina = nomina_fija * (_avg_ipc if comp_humano == "IPC" else 1.0)
        _avg_no_payroll = no_payroll_fijo * (_avg_ipc if comp_tecnologico == "IPC" else 1.0)
        ingreso_cadena_a_base, componentes_pricing = self._compute_ingreso_cadena_a_hm(
            _avg_nomina + _avg_no_payroll, _ctx_base, for_pricing=True
        )

        # Ingreso Cadena B base — mirrors HM formula: C304 = C303/(1-margen_b)
        # Excel V2-8: 'Hoja Maestra Escenarios'!C268 = N_b_op + ICA_b + GMF_b + Pol_b
        # ICA_b = C304×tasa_ica (on billing); GMF_b = N_b_op×tasa_gmf (on op cost)
        # Pol_b = C304×tasa_pol (on billing).
        # Solución analítica: C304 = N_b_op × (1+tasa_gmf) / (denom_b − tasa_ica − tasa_pol)
        _ingreso_b_base = 0.0
        if _cadena_b_calc:
            _costo_b_op = _cadena_b_calc.calcular_mes(1.0, 1.0)["costo_cadena_b"]
            _margen_b_base = float(_ctx_base.get("margen_b", 0.30))
            _factor_b = 1.0 - _margen_b_base
            _denom_b = (
                _factor_b
                * (1.0 - float(_ctx_base.get("cont_op", 0.0)))
                * (1.0 - float(_ctx_base.get("cont_com", 0.0)))
                * (1.0 - float(_ctx_base.get("markup", 0.0)))
                * (1.0 + float(_ctx_base.get("descuento", 0.0)))
            )
            _tasa_ica_hm_b = float(_ctx_base.get("tasa_ica", 0.01))
            _tasa_gmf_hm_b = float(_ctx_base.get("tasa_gmf", 0.004))
            _tasa_pol_b_pricing = sum(
                float(p.get("pct_poliza", 0)) * float(p.get("pct_atribuible", 0))
                for p in _ctx_base.get("polizas_activas", [])
                if "comisi" not in str(p.get("nombre", "")).lower()
            )
            _adj_denom_b = _denom_b - _tasa_ica_hm_b - _tasa_pol_b_pricing
            if _adj_denom_b > 0:
                _ingreso_b_base = _costo_b_op * (1.0 + _tasa_gmf_hm_b) / _adj_denom_b

        # Pólizas activas del deal (para filtrar por mes en costos reales)
        _polizas_todos: List[Dict] = _ctx_base.get("polizas_activas", [])

        # Costos Financiación — Excel V2-8: 'Pólizas - Costo Financiacion'!D515-D516
        # Panel!C21="Si" → cons_costo_de_financiacion > 0 en el request.
        # D515 = IFS(periodo_pago=30→1, 60→2, 90→3, else→4) = meses de capital charge.
        # D516 = tasa mensual = Panel!L11 = indexacion.tasa_interes_mensual.
        # Formula PCF!col_k = D515[k-1] × D516 × SUMIFS(CT![k-1], canal, modalidad)
        # CT (Costos Totales) = SUMIFS(NominaLoaded!col + NoPayroll!col, perfil) — IPC simple NL-level.
        # El P&G multiplica por (1 + IPC_incremental) — capa P&G sobre la base NL.
        tasa_interes = float(indexacion.get("tasa_interes_mensual", 0.0))
        periodo_pago_dias = int(datos_op.get("periodo_pago", 30))
        cons_financiacion = float(datos_op.get("cons_costo_de_financiacion", 0.0))
        financiacion_activa = cons_financiacion > 0 and tasa_interes > 0
        # meses_cc = D515 = IFS(D514=30→1, 60→2, 90→3, else→4) — ref PCF!D515 ArrayFormula
        if periodo_pago_dias == 30:
            meses_cc = 1
        elif periodo_pago_dias == 60:
            meses_cc = 2
        elif periodo_pago_dias == 90:
            meses_cc = 3
        else:
            meses_cc = 4
        # Factores IPC de la capa NL (acumulados, simple) del mes anterior.
        # CT[k-1] = (nomina_fija + no_payroll_fijo) × ipc_factor_{k-1} — base del capital charge.
        _prev_h_factor = 1.0   # ipc_factor_{k-1} para comp_humano
        _prev_t_factor = 1.0   # ipc_factor_{k-1} para comp_tecnologico

        for mes in range(1, duracion_meses + 1):
            ctx = build_base_context(request_data, mes, ramp_up_override=ramp_up_campana)
            ramp_up = ctx["ramp_up_mes"]

            # Factor IPC acumulado del NL para este mes (Tasas "Aumento Acumulado")
            ipc_factor = (
                _compute_ipc_factor(fecha_inicio, mes, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 1.0
            )
            # Factor IPC incremental del P&G para este mes (Tasas "Aumento x Año")
            # Excel V2-8: costos P&G = costo_NL × (1 + IPC_incremental); doble aplicación
            ipc_incremental = (
                _compute_ipc_incremental(fecha_inicio, mes, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 0.0
            )

            # Factor de escala para costos:
            # - aplica_indexacion_tarifa=True  → doble IPC (NL-level × P&G-level incremental)
            # - aplica_indexacion_tarifa=False → solo IPC simple del NL (factor acumulado)
            # Excel V2-8: P&G R38 formula aplica el extra IPC solo cuando la tarifa está indexada.
            _extra_ipc = (1.0 + ipc_incremental) if aplica_indexacion_tarifa else 1.0
            double_h = ipc_factor * _extra_ipc if comp_humano == "IPC" else 1.0
            double_t = ipc_factor * _extra_ipc if comp_tecnologico == "IPC" else 1.0
            nomina_mes = nomina_fija * double_h
            no_payroll_mes = no_payroll_fijo * double_t
            costo_op_mes = nomina_mes + no_payroll_mes

            # Ingreso: HM × (1 + IPC_incremental) — IPC simple siempre aplica al ingreso
            # Excel V2-8: 'Visión P&G'!R20 = HM!C296 × ramp × (1 + INDEX(Tasas!J8:O16,...))
            # La diferencia entre aplica=True/False está en el HM base (avg vs base costs).
            ingreso_mes = ingreso_cadena_a_base * (1.0 + ipc_incremental)

            # Pólizas con extensión: aplican durante todo el contrato (meses_extension = meses EXTRA
            # más allá del fin del contrato, no el total de meses activos).
            # Ej: contrato 10M + meses_extension=2 → póliza activa M1-M12, pero el loop solo llega M10.
            polizas_activas_mes = [
                p for p in _polizas_todos
                if not p.get("aplica_extension")
                or mes <= duracion_meses + int(p.get("meses_extension") or 0)
            ]
            ctx_cost = {**_ctx_base, "polizas_activas": polizas_activas_mes}
            _, componentes_cost_mes = self._compute_ingreso_cadena_a_hm(
                costo_op_mes, ctx_cost, for_pricing=False
            )

            ctx["nomina_total_mensual"] = nomina_mes
            ctx["no_payroll_total_mensual"] = no_payroll_mes
            if _cadena_b_calc:
                ctx.update(_cadena_b_calc.calcular_mes(double_h, double_t))
            else:
                ctx["costo_cadena_b"] = 0.0
                ctx["componente_fijo_b"] = 0.0
                ctx["componente_variable_b"] = 0.0
                ctx["opex_fijo_cadena_b"] = 0.0
                ctx["opex_variable_cadena_b"] = 0.0
                ctx["capex_cadena_b"] = 0.0
                ctx["sm_cadena_b"] = 0.0
                ctx["tarifa_canal_cadena_b"] = 0.0
                ctx["tasa_escalamiento_cadena_b"] = 0.0
                ctx["hitl_cadena_b"] = 0.0
            ctx["costo_cadena_c"] = 0.0
            ctx["comision_admin_mensual"] = 0.0  # ya incluida en polizas_mensual

            # Sub-componentes para formato periods — mismo factor doble IPC que el total
            ctx["nomina_loaded_mensual"] = _nomina_detalle["nomina_loaded"] * double_h
            ctx["crucero_total_mensual"] = _nomina_detalle["crucero_total"] * double_h
            ctx["capacitacion_rotacion_mensual"] = _nomina_detalle["capacitacion_rotacion"] * double_h
            ctx["salario_fijo_mensual"] = _nomina_detalle["salario_fijo"] * double_h
            ctx["salario_variable_mensual"] = _nomina_detalle["salario_variable"] * double_h
            # Informativo — mismo factor IPC que nómina; no suma a costo_total (igual que Excel col AM=col W)
            ctx["recargos_horas_extra_mensual"] = _nomina_detalle.get("recargos_horas_extra", 0.0) * double_h
            ctx["opex_fijo_mensual"] = _no_payroll_detalle["opex_fijo"] * double_t
            ctx["inversiones_mensual"] = _no_payroll_detalle["inversiones"] * double_t
            ctx["costos_fijos_mensual"] = _no_payroll_detalle["costos_fijos"] * double_t

            # Componentes financieros reales del mes (ICA/GMF con N de pólizas activas este mes)
            ctx["ica_hm"] = componentes_cost_mes.get("ica_hm", 0.0)
            ctx["gmf_hm"] = componentes_cost_mes.get("gmf_hm", 0.0)
            ctx["comision_admin_hm"] = componentes_cost_mes.get("comision_admin_hm", 0.0)
            ctx["polizas_puras_hm"] = componentes_cost_mes.get("polizas_puras_hm", 0.0)
            # Excel V2-8: ICA/GMF/Pólizas de Cadena B (billing A+B+C en Pólizas-FC M162:M233).
            # ICA_b = ingreso_b_unramped × tasa_ica (on billing, mirrors Pólizas sheet row)
            # GMF_b = costo_b_op_mes × tasa_gmf (on operational cost, NOT on ingreso)
            # Pol_b = ingreso_b_unramped × tasa_pol (on billing, same as ICA)
            if _cadena_b_calc and _ingreso_b_base > 0:
                _ingreso_b_unramped = _ingreso_b_base * (1.0 + ipc_incremental)
                _tasa_ica_b = float(ctx.get("tasa_ica", 0.01))
                _tasa_gmf_b = float(ctx.get("tasa_gmf", 0.004))
                _tasa_pol_b_mes = sum(
                    float(p.get("pct_poliza", 0)) * float(p.get("pct_atribuible", 0))
                    for p in polizas_activas_mes
                    if "comisi" not in str(p.get("nombre", "")).lower()
                )
                ctx["ica_hm"] += _ingreso_b_unramped * _tasa_ica_b
                ctx["gmf_hm"] += ctx["costo_cadena_b"] * _tasa_gmf_b
                ctx["polizas_puras_hm"] += _ingreso_b_unramped * _tasa_pol_b_mes

            # Suma financiera completa (ICA + GMF + Comisión + puras) — base para otros cálculos.
            # La vista P&G row 73 usa solo polizas_puras_hm (ver screen_mapper.py).
            ctx["polizas_adicionales_hm"] = (
                ctx["ica_hm"] + ctx["gmf_hm"] + ctx["comision_admin_hm"] + ctx["polizas_puras_hm"]
            )

            # Ingreso Cadena A: ingreso HM (pricing, ponderado) × ramp_up del mes
            ctx["ingreso_cadena_a"] = ingreso_mes * ramp_up

            # Ingreso Cadena B: base × IPC_incremental × ramp_up (mirrors ingreso_cadena_a).
            # Excel V2-8: 'Visión P&G'!J21 = C304 × J15(ramp_up) × (1+IPC_anual)
            if _cadena_b_calc:
                ctx["ingreso_cadena_b"] = _ingreso_b_base * (1.0 + ipc_incremental) * ramp_up
            else:
                ctx["ingreso_cadena_b"] = 0.0

            # Capital charge diferido — PCF!col_k = meses_cc[k-1] × tasa × CT[k-1] × (1+IPC_incr_k)
            # CT[k-1] = NominaLoaded[k-1] + NoPayroll[k-1] con IPC simple (ipc_factor NL-level).
            # El P&G aplica (1+ipc_incremental_k) como capa adicional (no reaplicar double_h).
            # Mes 1 = 0 (no hay mes k-1); activo desde mes 2 si financiacion_activa.
            if financiacion_activa and mes > 1:
                _h_base = nomina_fija * _prev_h_factor
                _t_base = no_payroll_fijo * _prev_t_factor
                ctx["costos_financiacion_mensual"] = (
                    (_h_base + _t_base) * meses_cc * tasa_interes * (1.0 + ipc_incremental)
                )
            else:
                ctx["costos_financiacion_mensual"] = 0.0

            # Actualiza factores IPC del mes actual (se usarán como base del mes siguiente).
            _prev_h_factor = ipc_factor if (comp_humano == "IPC" and ipc_activo) else 1.0
            _prev_t_factor = ipc_factor if (comp_tecnologico == "IPC" and ipc_activo) else 1.0

            # Evaluar rubros en orden topológico
            for rubro in rubros:
                valor = self._evaluar_rubro(rubro, ctx)
                ctx[rubro.id] = valor

            # Solo valores numéricos en el modelo (strings y listas del contexto se excluyen)
            valores_num = {
                k: float(v) for k, v in ctx.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }
            resultados_por_mes.append(ResultadoMes(mes=mes, valores=valores_num))

        # Excel V2-8: meses de extensión de pólizas post-contrato aparecen como columnas adicionales.
        # Se agregan como ResultadoMes separados — el mapper los expone como periods adicionales
        # y _calcular_totales los incluye en los totales automáticamente.
        _ext_meses = self._build_extension_months(
            polizas_todos=_polizas_todos,
            duracion_meses=duracion_meses,
            fecha_inicio=fecha_inicio,
            mes_ajuste_ipc=mes_ajuste_ipc,
            ipc_rates=ipc_rates,
            ipc_activo=ipc_activo,
            aplica_indexacion_tarifa=aplica_indexacion_tarifa,
            comp_humano=comp_humano,
            comp_tecnologico=comp_tecnologico,
            nomina_fija=nomina_fija,
            no_payroll_fijo=no_payroll_fijo,
            ctx_base=_ctx_base,
        )
        resultados_por_mes.extend(_ext_meses)

        totales = self._calcular_totales(resultados_por_mes)

        # Extra mes N+1: el capital charge basado en CT[N] se paga en el mes N+1.
        # _prev_h/_t_factor al salir del loop = ipc_factor del último mes (base de CT[N]).
        # PCF tiene una columna adicional más allá de duracion_meses que se suma a totales.
        if financiacion_activa:
            ipc_incr_n1 = (
                _compute_ipc_incremental(fecha_inicio, duracion_meses + 1, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 0.0
            )
            _h_base_n = nomina_fija * _prev_h_factor
            _t_base_n = no_payroll_fijo * _prev_t_factor
            extra_fin = (_h_base_n + _t_base_n) * meses_cc * tasa_interes * (1.0 + ipc_incr_n1)
            totales["costos_financiacion_mensual"] = (
                totales.get("costos_financiacion_mensual", 0.0) + extra_fin
            )

        vision = self._construir_vision_pyg(resultados_por_mes, duracion_meses)

        # Componentes financieros base (100% ramp, sin IPC) — reutiliza el call de pricing
        # Excel V2-8: 'Visión Cost To Serve' — financiero = ICA + GMF + Comision + Polizas
        # (componentes de la Hoja Maestra Escenarios, for_pricing=True, una sola vez)
        ica_b = componentes_pricing.get("ica_hm", 0.0)
        gmf_b = componentes_pricing.get("gmf_hm", 0.0)
        com_b = componentes_pricing.get("comision_admin_hm", 0.0)
        pol_b = componentes_pricing.get("polizas_puras_hm", 0.0)
        componente_financiero_base = ica_b + gmf_b + com_b + pol_b

        componentes_pricing_fin = {
            "ica": ica_b, "gmf": gmf_b, "polizas": pol_b, "comision": com_b,
            "financiacion": totales.get("costos_financiacion_mensual", 0.0),
        }
        vision_cts = self._construir_vision_cts(
            request_data=request_data,
            costo_fijo_estacion=costo_fijo_estacion,
            ctx_base=_ctx_base,
            nomina_base=nomina_fija,
            ingreso_base=ingreso_cadena_a_base,
            componente_financiero_base=componente_financiero_base,
            totales=totales,
            duracion_meses=duracion_meses,
            componentes_pricing_fin=componentes_pricing_fin,
            nomina_desglose_cargo=_nomina_desglose_cargo,
            nomina_grupos_por_perfil=_nomina_grupos_por_perfil,
        )

        cts_perfiles_raw = (
            [p.model_dump() for p in vision_cts.perfiles] if vision_cts else []
        )
        # vision_imprimible y vision_tarifas solo usan meses del contrato (sin extensión).
        # Los meses de extensión son puramente financieros (sin datos operativos) y romperían
        # helpers como _primer_mes_ramp1 que usa meses[-1] como fallback.
        meses_contrato_raw = [m.model_dump() for m in resultados_por_mes[:duracion_meses]]
        meses_raw = [m.model_dump() for m in resultados_por_mes]

        try:
            vision_imprimible = build_vision_imprimible(
                request_data=request_data,
                meses=meses_contrato_raw,
                totales=totales,
                duracion_meses=duracion_meses,
                cts_perfiles=cts_perfiles_raw,
                cts_mensual=vision_cts.cts_mensual if vision_cts else None,
            )
        except Exception as exc:
            logger.warning("[motor-reglas] Error construyendo VisionImprimible: %s", exc)
            vision_imprimible = None

        try:
            vision_tarifas = build_vision_tarifas(
                request_data=request_data,
                meses=meses_contrato_raw,
                totales=totales,
                duracion_meses=duracion_meses,
                cts_perfiles=cts_perfiles_raw,
            )
        except Exception as exc:
            logger.warning("[motor-reglas] Error construyendo VisionTarifas: %s", exc)
            vision_tarifas = None

        return SimulationResultV2(
            simulation_id=simulation_id,
            cliente=datos_op.get("cliente"),
            servicio=datos_op.get("servicio"),
            tipo_cliente=datos_op.get("tipo_cliente"),
            antiguedad_cliente=datos_op.get("antiguedad_cliente"),
            periodo_pago=int(datos_op.get("periodo_pago", 30)) if datos_op.get("periodo_pago") is not None else None,
            fecha_inicio=datos_op.get("fecha_inicio"),
            duracion_meses=duracion_meses,
            ciudad=datos_op.get("ciudad"),
            sede=datos_op.get("sede"),
            meses=resultados_por_mes,
            totales=totales,
            vision_pyg=vision,
            vision_cts=vision_cts,
            vision_imprimible=vision_imprimible,
            vision_tarifas=vision_tarifas,
        )

    # ── Evaluación por tipo ────────────────────────────────────────────────

    def _evaluar_rubro(self, rubro: RubroMaestro, ctx: Dict[str, Any]) -> float:
        if rubro.id in _AGGREGATED_IDS:
            # Ya inyectado en el contexto antes del loop
            return float(ctx.get(rubro.id, 0.0))

        if rubro.id in _FINANCIAL_AGGREGATED:
            return self._evaluar_financiero(rubro.id, ctx)

        if rubro.tipo_calculo == "formula":
            try:
                return evaluate_formula(rubro.formula.expresion, ctx)
            except ValueError as exc:
                logger.warning("[motor-reglas] rubro=%s mes=%s → %s → 0", rubro.id, ctx.get("mes_numero"), exc)
                return 0.0

        return 0.0

    def _evaluar_financiero(self, rubro_id: str, ctx: Dict[str, Any]) -> float:
        # Excel P&G: ICA, GMF y Pólizas se calculan SIEMPRE sobre ingreso HM (constante),
        # no sobre ingreso_neto (que varía con ramp-up). Los valores HM se inyectan en ctx
        # antes del loop de rubros en calcular().

        if rubro_id == "ica_mensual":
            # Excel Pólizas-FC E162: ICA = (N / (1-margen)) × tasa_ica — valor HM constante
            return ctx.get("ica_hm", 0.0)

        if rubro_id == "gmf_mensual":
            # Excel Pólizas-FC E243: GMF = N × tasa_gmf — valor HM constante
            return ctx.get("gmf_hm", 0.0)

        if rubro_id == "polizas_mensual":
            # Excel Pólizas-FC: pólizas puras (IRF + Responsabilidad) — valor HM constante
            return ctx.get("polizas_puras_hm", 0.0)

        if rubro_id == "componente_financiero_total":
            # Excel P&G I69 = SUM(I70:I74) = ICA + GMF + Comisión + Pólizas_puras + CostosFinancieros
            ica = ctx.get("ica_hm", 0.0)
            gmf = ctx.get("gmf_hm", 0.0)
            comision = ctx.get("comision_admin_hm", 0.0)
            polizas_puras = ctx.get("polizas_puras_hm", 0.0)
            costos_fin = ctx.get("costos_financiacion_mensual", 0.0)  # Excel V2-8 P&G R74
            return ica + gmf + comision + polizas_puras + costos_fin

        if rubro_id == "costo_fijo_externo":
            # pct_costo_fijo viene de parametrización GN (no cargada aún) → 0 por ahora
            return 0.0

        return 0.0

    @staticmethod
    def _compute_ingreso_cadena_a_hm(
        costo_op: float, ctx: Dict[str, Any], for_pricing: bool = True
    ) -> tuple:
        """Fórmula analítica de Hoja Maestra para ingreso_cadena_a.

        # Excel V2-8: 'Hoja Maestra Escenarios'!C266 (= C295/C296/.../C300)
        # Resuelve la circularidad ICA/GMF/pol/admin ↔ ingreso sin iteración Excel.
        #
        # for_pricing=True (HM pricing):
        #   Pólizas con extensión aplican al 100% durante todo el contrato.
        #   Los meses extra (meses_extension) se amortizan en pol_ext_amortized.
        #   → El ingreso resultante es el precio estable durante toda la vida del deal.
        #
        # for_pricing=False (costo real mensual):
        #   El caller pre-filtra polizas_activas según mes <= duracion + meses_extension.
        #   meses_extension = meses EXTRA más allá del fin del contrato (no total de meses).
        #
        # Pasos:
        #   base = costo_op / (1-margen)
        #   pol_p   = base × tasa_pol_excl_admin
        #   admin_p = base × (pct_comision × 1.42 × pct_atribuible)   [D338×1.42]
        #   N = costo_op + pol_p + admin_p
        #   ICA_p = N / (1-margen) × tasa_ica        [E162: divide por (1-margen)]
        #   GMF_p = N × tasa_gmf                     [E243: sin division de margen]
        #   numerador = N + ICA_p + GMF_p
        #   ingreso = numerador / ((1-margen) × (1-cont_op) × (1-cont_com) × (1-markup) × (1+descuento))
        """
        margen_a = float(ctx.get("margen_a", 0.18))
        tasa_ica = float(ctx.get("tasa_ica", 0.01))
        tasa_gmf = float(ctx.get("tasa_gmf", 0.004))
        cont_op = float(ctx.get("cont_op", 0.0))
        cont_com = float(ctx.get("cont_com", 0.0))
        markup = float(ctx.get("markup", 0.0))
        descuento = float(ctx.get("descuento", 0.0))
        polizas_activas: List[Dict] = ctx.get("polizas_activas", [])

        factor_margen = 1.0 - margen_a  # = 0.82 para margen 18%
        if factor_margen <= 0:
            return 0.0, {}

        # Tasas de pólizas: separar puras (IRF, Responsabilidad) de comision admin
        # Excel V2-8: 'Panel de Control General'!F38-F45 — aplica_extension + meses_extension
        tasa_pol_excl_admin = 0.0
        tasa_admin_pricing = 0.0
        for p in polizas_activas:
            nombre = str(p.get("nombre", "")).lower()
            pct = float(p.get("pct_poliza", 0)) * float(p.get("pct_atribuible", 0))

            # meses_extension = meses EXTRA más allá del fin del contrato (no el total de meses).
            # La póliza aplica al 100% durante todo el contrato; los meses extra se amortizan
            # en pol_ext_amortized (bloque for_pricing abajo).

            if "comisi" in nombre:
                # Hoja Maestra D338 = Panel!D45 × 1.42 → aplica factor a toda la pct efectiva
                tasa_admin_pricing += pct * _COMISION_ADMIN_FACTOR_HM
            else:
                tasa_pol_excl_admin += pct

        # Paso 1: pol y admin sobre base = costo_op / (1-margen)
        base_ingreso = costo_op / factor_margen
        pol_pricing = base_ingreso * tasa_pol_excl_admin
        admin_pricing = base_ingreso * tasa_admin_pricing

        # Paso 2: N (base para ICA y GMF)
        N = costo_op + pol_pricing + admin_pricing

        # Paso 3: ICA_p y GMF_p con sus fórmulas exactas de la hoja Pólizas-FC
        ica_pricing = (N / factor_margen) * tasa_ica
        gmf_pricing = N * tasa_gmf

        # Paso 3b: costo amortizado de meses de extensión más allá del contrato
        # Excel V2-8: 'Hoja Maestra Escenarios'!C264 — SUMPRODUCT sobre todos los meses (1..ext)
        # divide por meses_proyecto; los meses de extensión elevan el promedio de pólizas.
        pol_ext_amortized = 0.0
        if for_pricing:
            duracion_total = int(ctx.get("meses_proyecto", 10)) or 10
            for p in polizas_activas:
                if "comisi" in str(p.get("nombre", "")).lower():
                    continue
                if not p.get("aplica_extension", False):
                    continue
                extra_meses = int(p.get("meses_extension", 0)) or 0
                if extra_meses <= 0:
                    continue
                pct_ext = float(p.get("pct_poliza", 0)) * float(p.get("pct_atribuible", 0))
                pol_ext_amortized += extra_meses * base_ingreso * pct_ext
            if duracion_total > 0:
                pol_ext_amortized /= duracion_total

        # Paso 4: numerador = N + ICA + GMF + costo extensión amortizado
        numerador = N + ica_pricing + gmf_pricing + pol_ext_amortized
        denominador = factor_margen * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
        if denominador <= 0:
            return 0.0, {}

        # Excel V2-8: pol_ext_amortized contribuye al numerador (y al ingreso_cadena_a_base)
        # pero también debe incluirse en polizas_puras_hm para que el CTS financiero sea correcto.
        # Sin esto, componente_financiero_base queda subestimado por pol_ext_amortized.
        componentes_hm = {
            "ica_hm": ica_pricing,
            "gmf_hm": gmf_pricing,
            "comision_admin_hm": admin_pricing,
            "polizas_puras_hm": pol_pricing + pol_ext_amortized,
        }
        return numerador / denominador, componentes_hm

    # ── Meses de extensión de pólizas ─────────────────────────────────────

    @staticmethod
    def _build_extension_months(
        polizas_todos: List[Dict[str, Any]],
        duracion_meses: int,
        fecha_inicio: Optional[datetime],
        mes_ajuste_ipc: int,
        ipc_rates: Dict[int, float],
        ipc_activo: bool,
        aplica_indexacion_tarifa: bool,
        comp_humano: str,
        comp_tecnologico: str,
        nomina_fija: float,
        no_payroll_fijo: float,
        ctx_base: Dict[str, Any],
    ) -> List[ResultadoMes]:
        """Construye periodos adicionales para meses de extensión de pólizas post-contrato.

        # Excel V2-8: 'Visión P&G' columnas post-contrato — pólizas con aplica_extension=True y
        # meses_extension > 0 generan costos en meses duracion+1 … duracion+meses_extension.
        # meses_extension = meses EXTRA más allá del fin del contrato (no el total).
        # En esos meses: ICA=0, GMF=0, Comision=0 (sin actividad operativa).
        # R73 = polizas_puras_ext; R69 = R73 (sin ICA ni GMF).
        # La base usa el IPC del mes k para consistencia con el P&G mensual.
        """
        margen_a = float(ctx_base.get("margen_a", 0.18))
        factor_margen = 1.0 - margen_a
        if factor_margen <= 0:
            return []

        # max_extension = máximo de meses extra entre todas las pólizas con extensión
        max_extension = max(
            (int(p.get("meses_extension") or 0) for p in polizas_todos if p.get("aplica_extension")),
            default=0,
        )
        if max_extension <= 0:
            return []

        ext_resultados: List[ResultadoMes] = []
        for mes_ext in range(duracion_meses + 1, duracion_meses + max_extension + 1):
            # ext_num = número de mes de extensión (1-based desde el fin del contrato)
            ext_num = mes_ext - duracion_meses
            tasa_pol_ext = sum(
                float(p.get("pct_poliza", 0)) * float(p.get("pct_atribuible", 0))
                for p in polizas_todos
                if p.get("aplica_extension")
                and "comisi" not in str(p.get("nombre", "")).lower()
                and ext_num <= int(p.get("meses_extension") or 0)
            )
            if tasa_pol_ext <= 0:
                continue

            # IPC del mes de extensión — misma lógica que el loop del contrato
            ipc_factor = (
                _compute_ipc_factor(fecha_inicio, mes_ext, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 1.0
            )
            ipc_incr = (
                _compute_ipc_incremental(fecha_inicio, mes_ext, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 0.0
            )
            extra_ipc = (1.0 + ipc_incr) if aplica_indexacion_tarifa else 1.0
            double_h = ipc_factor * extra_ipc if comp_humano == "IPC" else 1.0
            double_t = ipc_factor * extra_ipc if comp_tecnologico == "IPC" else 1.0

            nomina_ext    = nomina_fija      * double_h
            nopayroll_ext = no_payroll_fijo  * double_t
            base_ingreso_ext = (nomina_ext + nopayroll_ext) / factor_margen

            # Costo póliza ext (sin ICA/GMF — no hay actividad operativa en meses de extensión)
            pol_ext = base_ingreso_ext * tasa_pol_ext
            # R73 = pol_puras (ICA=0, GMF=0, Comision=0); R69 = R73
            comp_fin_ext = pol_ext

            ext_resultados.append(ResultadoMes(
                mes=mes_ext,
                valores={
                    "componente_financiero_total": comp_fin_ext,
                    "polizas_puras_hm":            pol_ext,
                    "polizas_adicionales_hm":      pol_ext,
                    "polizas_mensual":             pol_ext,
                    "ica_hm":                      0.0,
                    "gmf_hm":                      0.0,
                    "ica_mensual":                 0.0,
                    "gmf_mensual":                 0.0,
                    "comision_admin_hm":           0.0,
                    "costo_total":                 comp_fin_ext,
                    "ingreso_bruto":               0.0,
                    "ingreso_neto":                0.0,
                    "contribucion":                -comp_fin_ext,
                    # Excel V2-8: BJ87 = BJ31-BJ34-BJ86; meses ext tienen costo_fijo=0
                    "utilidad_neta":               -comp_fin_ext,
                    "nomina_total_mensual":        0.0,
                    "no_payroll_total_mensual":    0.0,
                    "ramp_up_mes":                 0.0,
                },
            ))

        return ext_resultados

    # ── Visión Cost-to-Serve ───────────────────────────────────────────────

    def _construir_vision_cts(
        self,
        request_data: Dict[str, Any],
        costo_fijo_estacion: float,
        ctx_base: Dict[str, Any],
        nomina_base: float,
        ingreso_base: float,
        componente_financiero_base: float,
        totales: Dict[str, float],
        duracion_meses: int = 1,
        componentes_pricing_fin: Optional[Dict[str, float]] = None,
        nomina_desglose_cargo: Optional[Dict[str, float]] = None,
        nomina_grupos_por_perfil: Optional[Dict[str, Any]] = None,
    ) -> Optional[VisionCostToServe]:
        """Construye la Visión Cost-to-Serve.

        # Excel V2-8: 'Visión Cost To Serve' — Economics + por Cadena + por Perfil
        # Payroll por perfil incluye overhead de staff ratios (supervisores, directores)
        #   via nomina_base que proviene de NominaCalculator (incluye todos los cargos).
        # Financiero = ICA + GMF + Comision + Polizas (una vez, sin duplicar estructura R69).
        # ingreso_mensual = promedio del deal (valor_total_contrato / duracion_meses).
        """
        try:
            margen = float(ctx_base.get("margen_a", 0.18))
            fte_total = int(ctx_base.get("fte_total_cadena_a", 0))

            cts_calc = CTSCalculator(request_data, costo_fijo_estacion)
            perfiles_raw = cts_calc.calcular(
                margen, componente_financiero_base, nomina_base,
                componentes_fin=componentes_pricing_fin,
            )

            if not perfiles_raw:
                return None

            perfiles_cts = [PerfilCTS(**p) for p in perfiles_raw]

            payroll_total = sum(p.payroll for p in perfiles_cts)
            no_payroll_total = sum(p.no_payroll for p in perfiles_cts)
            costo_directo_total = sum(p.costo_directo for p in perfiles_cts)
            financiero_total = sum(p.financiero for p in perfiles_cts)
            cts_total = costo_directo_total + financiero_total

            fte_safe = max(fte_total, 1)

            # Excel CTS: ingreso_mensual = ingreso_neto a 100% ramp (sin IPC, sin ramp-down).
            # factor_neto = ratio ingreso_neto / ingreso_bruto del deal (captura imprevistos,
            # contingencias, markup, descuento aplicados en los rubros del P&G).
            # valor_total_contrato = suma de ingreso_neto mensual real (con IPC + ramp).
            ingreso_bruto_total = totales.get("ingreso_bruto", ingreso_base * float(duracion_meses))
            ingreso_neto_total = totales.get("ingreso_neto", ingreso_bruto_total)
            factor_neto = (ingreso_neto_total / ingreso_bruto_total) if ingreso_bruto_total > 0 else 1.0
            ingreso_mensual = ingreso_base * factor_neto
            valor_total_contrato = ingreso_neto_total

            reglas_negocio = self._build_reglas_negocio(ctx_base, totales, ingreso_neto_total)
            cadenas = self._build_cadenas(request_data, totales)
            vision_por_canal = self._build_vision_por_canal(perfiles_cts)

            return VisionCostToServe(
                cts_mensual=round(cts_total, 2),
                ingreso_mensual=round(ingreso_mensual, 2),
                margen=margen,
                valor_total_contrato=round(valor_total_contrato, 2),
                n_fte_total=fte_total,
                payroll_total=round(payroll_total, 2),
                no_payroll_total=round(no_payroll_total, 2),
                costo_directo_total=round(costo_directo_total, 2),
                financiero_total=round(financiero_total, 2),
                cts_total=round(cts_total, 2),
                payroll_por_fte=round(payroll_total / fte_safe, 2),
                no_payroll_por_fte=round(no_payroll_total / fte_safe, 2),
                costo_directo_por_fte=round(costo_directo_total / fte_safe, 2),
                financiero_por_fte=round(financiero_total / fte_safe, 2),
                cts_por_fte=round(cts_total / fte_safe, 2),
                perfiles=perfiles_cts,
                reglas_negocio=reglas_negocio,
                cadenas=cadenas,
                vision_por_canal=vision_por_canal,
                nomina_por_cargo=nomina_desglose_cargo or {},
                nomina_grupos_por_perfil=nomina_grupos_por_perfil or {},
            )
        except Exception as exc:
            logger.warning("[motor-reglas] Error construyendo VisionCostToServe: %s", exc)
            return None

    @staticmethod
    def _build_reglas_negocio(
        ctx_base: Dict[str, Any],
        totales: Dict[str, float],
        ingreso_neto_total: float,
    ) -> List[Dict[str, Any]]:
        """Construye la lista de reglas de negocio del deal con % y valor monetario.

        Excel V2-8: 'Visión Cost To Serve' — Sección 07 (filas 189-205)
        """
        def _pct(key: str, default: float = 0.0) -> float:
            return float(ctx_base.get(key, default))

        def _valor(totales_key: str, pct: float, fallback: float = 0.0) -> float:
            v = totales.get(totales_key)
            if v is not None:
                return round(float(v), 0)
            # Aproximación: porcentaje × ingreso_neto_total
            return round(ingreso_neto_total * pct, 0) if ingreso_neto_total > 0 else fallback

        margen_a = _pct("margen_a", 0.18)
        margen_b = _pct("margen_b", 0.30)
        margen_c = _pct("margen_c", 0.18)
        cont_op = _pct("cont_op", 0.0)
        cont_com = _pct("cont_com", 0.0)
        markup = _pct("markup", 0.0)
        descuento = _pct("descuento", 0.0)
        imprevistos = _pct("pct_imprevistos", 0.10)

        # Cadenas B/C: porcentaje = 0 si no tienen costo en este deal
        costo_b = float(totales.get("costo_cadena_b", 0))
        costo_c = float(totales.get("costo_cadena_c", 0))

        # imprevistos_valor reutilizado para derivar ingreso_bruto_total
        imprevistos_valor = _valor("imprevistos_valor", imprevistos)

        # ingreso_bruto_total = antes de imprevistos (Excel: Ingreso Cadena A P&G)
        # ingreso_neto_total ya viene descontado de imprevistos → es el valor_total_deal
        ingreso_bruto_total = float(totales.get("ingreso_bruto") or (ingreso_neto_total + imprevistos_valor))

        return [
            # porcentaje en decimal (0.18, no 18) — el front aplica ×100 para mostrar %
            # Margen Cadena A valor = ingreso bruto total (antes de imprevistos)
            {"concepto": "Margen Cadena A", "porcentaje": margen_a, "valor": round(ingreso_bruto_total, 0)},
            {"concepto": "Margen Cadena B", "porcentaje": margen_b if costo_b > 0 else 0.0, "valor": round(costo_b * margen_b / max(1 - margen_b, 0.01), 0)},
            {"concepto": "Margen Cadena C", "porcentaje": margen_c if costo_c > 0 else 0.0, "valor": round(costo_c * margen_c / max(1 - margen_c, 0.01), 0)},
            {"concepto": "Contingencia Operativa", "porcentaje": cont_op, "valor": _valor("contingencia_operativa_valor", cont_op)},
            {"concepto": "Contingencia Comercial", "porcentaje": cont_com, "valor": _valor("contingencia_comercial_valor", cont_com)},
            {"concepto": "Markup (complejidad, horarios)", "porcentaje": markup, "valor": _valor("markup_valor", markup)},
            {"concepto": "Descuento volumen", "porcentaje": descuento, "valor": _valor("descuento_valor", descuento)},
            {"concepto": "Imprevistos", "porcentaje": imprevistos, "valor": imprevistos_valor},
            # valor_total_deal = ingreso_neto_total (ya descontado imprevistos, con descuento incluido)
            {"concepto": "valor_total_deal", "porcentaje": None, "valor": round(ingreso_neto_total, 0)},
        ]

    @staticmethod
    def _build_cadenas(
        request_data: Dict[str, Any],
        totales: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Construye el desglose de costos por Cadena B y C.

        Excel V2-8: 'Visión Cost To Serve' — Sección cadenas (Estructura del Equipo — Cadenas B/C)
        Solo incluye una cadena si está activa en volumetria.cadenas_activas Y tiene condiciones.
        """
        cadenas = []
        _vol = request_data.get("volumetria") or {}

        def _cadena_activa(nombre: str) -> bool:
            return (
                _vol.get("inbound", {}).get("cadenas_activas", {}).get(nombre, False)
                or _vol.get("outbound", {}).get("cadenas_activas", {}).get(nombre, False)
            )

        cadena_b = request_data.get("condiciones_cadena_b")
        cadena_c = request_data.get("condiciones_cadena_c")

        if cadena_b is not None and _cadena_activa("cadena_b"):
            total_b = round(float(totales.get("costo_cadena_b", 0.0)), 2)
            comp_fijo_b = round(float(totales.get("componente_fijo_b", 0.0)), 2)
            comp_var_b = round(float(totales.get("componente_variable_b", 0.0)), 2)
            cadenas.append({
                "cadena": "CADENA B",
                "total": total_b,
                "inbound": 0,
                "outbound": total_b,
                "componentes": [
                    {"concepto": "Componente Humano", "total": comp_fijo_b, "inbound": 0, "outbound": comp_fijo_b},
                    {"concepto": "Componente Tecnológico", "total": comp_var_b, "inbound": 0, "outbound": comp_var_b},
                ],
            })

        if cadena_c is not None and _cadena_activa("cadena_c"):
            total_c = round(float(totales.get("costo_cadena_c", 0.0)), 2)
            cadenas.append({
                "cadena": "CADENA C",
                "total": total_c,
                "inbound": 0,
                "outbound": total_c,
                "componentes": [
                    {"concepto": "Componente Humano", "total": total_c, "inbound": 0, "outbound": total_c},
                    {"concepto": "Componente Tecnológico", "total": 0, "inbound": 0, "outbound": 0},
                ],
            })

        return cadenas

    @staticmethod
    def _build_vision_por_canal(perfiles: List["PerfilCTS"]) -> Dict[str, Any]:
        """Agrupa perfiles por modalidad → canal para la visión detallada y general.

        Excel V2-8: 'Visión Cost To Serve' — Sección 04/05 (canales Inbound/Outbound)
        """
        # Agrupar por (modalidad, canal)
        from collections import defaultdict
        grupos: Dict = defaultdict(lambda: {"perfiles": [], "fte": 0, "cts": 0.0})

        for p in perfiles:
            key = (p.modalidad.lower(), p.canal)
            g = grupos[key]
            g["perfiles"].append(p.model_dump())
            g["fte"] += p.fte
            g["cts"] += p.costo_total

        # Construir estructura por modalidad
        result: Dict[str, List[Dict]] = {"inbound": [], "outbound": []}
        for (modalidad, canal), g in grupos.items():
            modalidad_key = "inbound" if "inbound" in modalidad else "outbound"
            result[modalidad_key].append({
                "canal": canal,
                "fte": g["fte"],
                "cts_total": round(g["cts"], 2),
                "perfiles": g["perfiles"],
            })

        return result

    # ── Agregación post-cálculo ────────────────────────────────────────────

    @staticmethod
    def _calcular_totales(meses: List[ResultadoMes]) -> Dict[str, float]:
        totales: Dict[str, float] = {}
        for resultado in meses:
            for key, val in resultado.valores.items():
                if isinstance(val, (int, float)):
                    totales[key] = totales.get(key, 0.0) + val
        return totales

    @staticmethod
    def _construir_vision_pyg(meses: List[ResultadoMes], n_meses: int) -> VisionPyG:
        def serie(key: str) -> List[float]:
            return [float(m.valores.get(key, 0.0)) for m in meses]

        def serie_opt(key: str) -> Optional[List[float]]:
            """Retorna la serie solo si al menos un mes tiene valor distinto de 0."""
            vals = [float(m.valores.get(key, 0.0)) for m in meses]
            return vals if any(v != 0.0 for v in vals) else None

        return VisionPyG(
            ramp_up=serie("ramp_up_mes"),
            ingreso_bruto=serie("ingreso_bruto"),
            ingreso_neto=serie("ingreso_neto"),
            costo_total=serie("costo_total"),
            contribucion=serie("contribucion"),
            pct_contribucion=serie("pct_contribucion"),
            utilidad_neta=serie("utilidad_neta"),
            pct_utilidad_neta=serie("pct_utilidad_neta"),
            nomina_total_mensual=serie("nomina_total_mensual"),
            no_payroll_total_mensual=serie("no_payroll_total_mensual"),
            componente_financiero_total=serie("componente_financiero_total"),
            costo_cadena_b=serie_opt("costo_cadena_b"),
            componente_fijo_b=serie_opt("componente_fijo_b"),
            opex_fijo_cadena_b=serie_opt("opex_fijo_cadena_b"),
            capex_cadena_b=serie_opt("capex_cadena_b"),
            sm_cadena_b=serie_opt("sm_cadena_b"),
            componente_variable_b=serie_opt("componente_variable_b"),
            tarifa_canal_cadena_b=serie_opt("tarifa_canal_cadena_b"),
            opex_variable_cadena_b=serie_opt("opex_variable_cadena_b"),
            tasa_escalamiento_cadena_b=serie_opt("tasa_escalamiento_cadena_b"),
            hitl_cadena_b=serie_opt("hitl_cadena_b"),
        )
