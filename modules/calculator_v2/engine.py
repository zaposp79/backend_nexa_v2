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

from .context_builder import build_base_context
from .formula_evaluator import evaluate_formula
from .models import ResultadoMes, RubroMaestro, SimulationResultV2, VisionPyG
from .no_payroll_calculator import NoPayrollCalculator
from .nomina_calculator import NominaCalculator
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


class MotorDeReglas:
    def __init__(self, rubros_repo: RubrosRepository) -> None:
        self._repo = rubros_repo

    def calcular(self, request_data: Dict[str, Any]) -> SimulationResultV2:
        datos_op = request_data.get("datos_operativos", {})
        duracion_meses = int(datos_op.get("duracion_meses", 10))
        simulation_id = str(uuid.uuid4())

        rubros = self._repo.get_rubros_maestros()

        # Pre-computar valores aggregated que no cambian mes a mes
        nomina_fija = NominaCalculator(request_data).calcular()
        ciudad = datos_op.get("ciudad", "")
        costo_fijo_estacion = self._repo.get_hr_costo_fijo_estacion(ciudad)
        no_payroll_fijo = NoPayrollCalculator(request_data, costo_fijo_estacion).calcular()

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

        # Ingreso base calculado sobre costo_op a plena capacidad (sin IPC, ramp=1).
        # Excel V2-8: Hoja Maestra!C296 — valor fijo; pricing usa tasa ponderada para extensión.
        _ctx_base = build_base_context(request_data, 1, ramp_up_override=ramp_up_campana)
        ingreso_cadena_a_base, _ = self._compute_ingreso_cadena_a_hm(
            nomina_fija + no_payroll_fijo, _ctx_base, for_pricing=True
        )

        # Cache de ingreso HM por factor IPC (pricing) — constante dentro del mismo factor
        _hm_ingreso_cache: Dict[float, float] = {1.0: ingreso_cadena_a_base}

        # Pólizas activas del deal (para filtrar por mes en costos reales)
        _polizas_todos: List[Dict] = _ctx_base.get("polizas_activas", [])

        for mes in range(1, duracion_meses + 1):
            ctx = build_base_context(request_data, mes, ramp_up_override=ramp_up_campana)
            ramp_up = ctx["ramp_up_mes"]

            # Factor IPC para este mes del deal
            # Excel: aplica desde el mes_ajuste (enero=1) del año siguiente al inicio del deal
            ipc_factor = (
                _compute_ipc_factor(fecha_inicio, mes, mes_ajuste_ipc, ipc_rates)
                if ipc_activo else 1.0
            )

            # Costos mensuales ajustados por IPC según componente configurado
            nomina_mes = nomina_fija * ipc_factor if comp_humano == "IPC" else nomina_fija
            no_payroll_mes = no_payroll_fijo * ipc_factor if comp_tecnologico == "IPC" else no_payroll_fijo
            costo_op_mes = nomina_mes + no_payroll_mes

            # Ingreso (pricing): HM con tasa ponderada para extensión — cacheado por factor IPC
            # Excel V2-8: 'Hoja Maestra Escenarios'!C266 — precio estable aunque Seriedad expire en M7
            if ipc_factor not in _hm_ingreso_cache:
                ingreso_ipc, _ = self._compute_ingreso_cadena_a_hm(
                    costo_op_mes, _ctx_base, for_pricing=True
                )
                _hm_ingreso_cache[ipc_factor] = ingreso_ipc
            ingreso_mes = _hm_ingreso_cache[ipc_factor]

            # Costo real mensual: pólizas con extensión aplican tasa completa hasta mes <= meses_extension
            # Excel V2-8: 'Visión P&G'!R69 — Componente Financiero varía entre M6 y M7-10
            polizas_activas_mes = [
                p for p in _polizas_todos
                if not p.get("aplica_extension")
                or mes <= int(p.get("meses_extension") or 9999)
            ]
            ctx_cost = {**_ctx_base, "polizas_activas": polizas_activas_mes}
            _, componentes_cost_mes = self._compute_ingreso_cadena_a_hm(
                costo_op_mes, ctx_cost, for_pricing=False
            )

            ctx["nomina_total_mensual"] = nomina_mes
            ctx["no_payroll_total_mensual"] = no_payroll_mes
            ctx["costo_cadena_b"] = 0.0
            ctx["costo_cadena_c"] = 0.0
            ctx["comision_admin_mensual"] = 0.0  # ya incluida en polizas_mensual

            # Componentes financieros reales del mes (ICA/GMF con N de pólizas activas este mes)
            ctx["ica_hm"] = componentes_cost_mes.get("ica_hm", 0.0)
            ctx["gmf_hm"] = componentes_cost_mes.get("gmf_hm", 0.0)
            ctx["comision_admin_hm"] = componentes_cost_mes.get("comision_admin_hm", 0.0)
            ctx["polizas_puras_hm"] = componentes_cost_mes.get("polizas_puras_hm", 0.0)

            # Ingreso Cadena A: ingreso HM (pricing, ponderado) × ramp_up del mes
            ctx["ingreso_cadena_a"] = ingreso_mes * ramp_up

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

        totales = self._calcular_totales(resultados_por_mes)
        vision = self._construir_vision_pyg(resultados_por_mes, duracion_meses)

        return SimulationResultV2(
            simulation_id=simulation_id,
            cliente=datos_op.get("cliente"),
            servicio=datos_op.get("servicio"),
            duracion_meses=duracion_meses,
            meses=resultados_por_mes,
            totales=totales,
            vision_pyg=vision,
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
            # Excel P&G R73 "Pólizas adicionales" = ICA + GMF + Comisión + Pólizas_puras
            #   (suma total de la hoja Pólizas - Costo Financiación)
            # Excel P&G R69 "Componente Financiero" = ICA + GMF + Comisión + R73
            #   → doble conteo intencional: ICA+GMF+Comisión aparecen en R70/R71/R72 Y dentro de R73
            ica = ctx.get("ica_hm", 0.0)
            gmf = ctx.get("gmf_hm", 0.0)
            comision = ctx.get("comision_admin_hm", 0.0)
            polizas_puras = ctx.get("polizas_puras_hm", 0.0)
            polizas_adicionales = ica + gmf + comision + polizas_puras   # R73
            return ica + gmf + comision + polizas_adicionales             # R69

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
        #   Pólizas con extensión usan tasa ponderada = pct × (ext_meses / duracion_total)
        #   → Hoja Maestra!C264 "Polizas" = 2,539,284 (ej. Seriedad: 0.0005 × 6/10 = 0.000300)
        #   → El ingreso resultante es el precio estable durante toda la vida del deal.
        #
        # for_pricing=False (costo real mensual):
        #   El caller pre-filtra polizas_activas según qué pólizas aún aplican este mes.
        #   La tasa se usa al valor completo (sin ponderación) sobre la lista recibida.
        #   → P&G usa tasa completa M1-M6 (ext=6), luego 0 para M7-M10.
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

            # Excel V2-8: 'Hoja Maestra Escenarios'!C264 — póliza con extensión
            # for_pricing=True → tasa promedio ponderada sobre duración total del deal
            #   pct × (meses_extension / duracion_meses)  ← HM usa este promedio para pricing estable
            # for_pricing=False → tasa completa (caller ya filtró qué pólizas aplican este mes)
            if for_pricing and p.get("aplica_extension", False):
                ext_meses = int(p.get("meses_extension", 1)) or 1
                duracion_total = int(ctx.get("meses_proyecto", 10)) or 10
                if ext_meses < duracion_total:
                    pct = pct * (ext_meses / duracion_total)

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

        # Paso 4: numerador = N + ICA + GMF; denominador con contingencias completas
        numerador = N + ica_pricing + gmf_pricing
        denominador = factor_margen * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
        if denominador <= 0:
            return 0.0, {}

        componentes_hm = {
            "ica_hm": ica_pricing,
            "gmf_hm": gmf_pricing,
            "comision_admin_hm": admin_pricing,
            "polizas_puras_hm": pol_pricing,
        }
        return numerador / denominador, componentes_hm

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

        return VisionPyG(
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
        )
