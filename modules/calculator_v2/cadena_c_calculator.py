"""
Cálculo de costos para Cadena C (IA / automatización).

Componentes:
  - OPEX Fijo:              opex[] con tipo_gasto="Fijo"    → valor_total (pre-calculado frontend)
  - OPEX Variable:          opex[] con tipo_gasto="Variable" → valor_total (pre-calculado frontend)
  - CAPEX:                  inversiones_capex[].valor_mensual × (1+tasa)
  - Equipo Transversal:     recurso_humano_transversal.roles → calcular_costo_empresa(salario) × fte
  - Dispositivos Transv.:   recurso_humano_transversal.dispositivos_requeridos → precio × cant
  - Tarifa Canal:           tarifa_proveedor_canal[].valor_total (lista directa, pre-calculado frontend)
  - Tasa Escalamiento:      costo_variable.tasa_escalamiento → precio × vol × tasa
  - HITL Personal:          hitl.equipo → calcular_costo_empresa(salario) × fte
  - HITL Dispositivos:      hitl.dispositivos_requeridos → precio × cantidad_total

IPC:
  - Personal (equipo transversal, HITL personal): aplica double_h
  - Tecnología (OPEX, CAPEX, tarifas, dispositivos): aplica double_t

Salario: el request incluye salario base; se aplica calcular_costo_empresa() igual que Cadena B.
Volúmenes Cadena C: volumetria.{inbound|outbound}.canales[i].cadena_c.valor

Excel ref: 007_ElTiempo.xlsx — Cadena C.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from .nomina_calculator import calcular_costo_empresa

logger = logging.getLogger("nexa.motor_reglas.cadena_c")


class CadenaCCalculator:
    """Calcula costos mensuales de Cadena C aplicando factores IPC."""

    def __init__(self, request_data: Dict[str, Any]) -> None:
        self._cadena_c = request_data.get("condiciones_cadena_c") or {}
        self._volumetria = request_data.get("volumetria") or {}
        _indexacion = self._volumetria.get("indexacion") or {}
        self._tasa_interes = float(_indexacion.get("tasa_interes_mensual", 0))
        self._base = self._compute_base()

    # ── API pública ───────────────────────────────────────────────────────────

    def calcular_mes(self, double_h: float = 1.0, double_t: float = 1.0) -> Dict[str, float]:
        """Aplica factores IPC y retorna todos los componentes del mes.

        double_h: factor IPC acumulado para componente humano (equipo transversal y HITL personal)
        double_t: factor IPC acumulado para componente tecnológico (OPEX, CAPEX, tarifas, dispositivos)
        """
        b = self._base

        opex_fijo     = b["opex_fijo"]     * double_t
        opex_variable = b["opex_variable"] * double_t
        capex         = b["capex"]         * double_t
        equipo_tranv  = b["equipo_transversal_personal"] * double_h
        disp_tranv    = b["equipo_transversal_dispositivos"] * double_t
        tarifa_canal  = b["tarifa_canal"]  * double_t
        tasa_escal    = b["tasa_escalamiento"] * double_t
        hitl_personal = b["hitl_personal"] * double_h
        hitl_disp     = b["hitl_dispositivos"] * double_t

        costo_total = (
            opex_fijo + opex_variable + capex
            + equipo_tranv + disp_tranv
            + tarifa_canal + tasa_escal
            + hitl_personal + hitl_disp
        )

        logger.debug(
            "[cadena-c] mes: opex_f=%.0f opex_v=%.0f capex=%.0f "
            "tranv_p=%.0f tranv_d=%.0f tarifa=%.0f escal=%.0f hitl_p=%.0f hitl_d=%.0f total=%.0f",
            opex_fijo, opex_variable, capex,
            equipo_tranv, disp_tranv,
            tarifa_canal, tasa_escal, hitl_personal, hitl_disp, costo_total,
        )

        return {
            "costo_cadena_c":              costo_total,
            "opex_fijo_cadena_c":          opex_fijo,
            "opex_variable_cadena_c":      opex_variable,
            "capex_cadena_c":              capex,
            "equipo_transversal_cadena_c": equipo_tranv + disp_tranv,
            "tarifa_canal_cadena_c":       tarifa_canal,
            "tasa_escalamiento_cadena_c":  tasa_escal,
            "hitl_cadena_c":               hitl_personal + hitl_disp,
        }

    # ── Cálculo base (sin IPC, una vez en __init__) ───────────────────────────

    def _compute_base(self) -> Dict[str, float]:
        opex_fijo, opex_variable = self._calc_opex_por_tipo()
        capex = self._calc_capex()
        tranv_personal, tranv_dispositivos = self._calc_equipo_transversal()
        tarifa_canal = self._calc_tarifa_canal()
        tasa_escal = self._calc_tasa_escalamiento()
        hitl_personal, hitl_dispositivos = self._calc_hitl()

        logger.debug(
            "[cadena-c] base: opex_f=%.0f opex_v=%.0f capex=%.0f "
            "tranv_p=%.0f tranv_d=%.0f tarifa=%.0f escal=%.0f hitl_p=%.0f hitl_d=%.0f",
            opex_fijo, opex_variable, capex,
            tranv_personal, tranv_dispositivos,
            tarifa_canal, tasa_escal, hitl_personal, hitl_dispositivos,
        )
        return {
            "opex_fijo":                       opex_fijo,
            "opex_variable":                   opex_variable,
            "capex":                           capex,
            "equipo_transversal_personal":     tranv_personal,
            "equipo_transversal_dispositivos": tranv_dispositivos,
            "tarifa_canal":                    tarifa_canal,
            "tasa_escalamiento":               tasa_escal,
            "hitl_personal":                   hitl_personal,
            "hitl_dispositivos":               hitl_dispositivos,
        }

    def _calc_opex_por_tipo(self) -> Tuple[float, float]:
        """Separa OPEX por tipo_gasto: Fijo / Variable. valor_total pre-calculado por el frontend."""
        items = self._cadena_c.get("opex", [])
        fijo = 0.0
        variable = 0.0
        for item in items:
            valor = float(item.get("valor_total", 0))
            if str(item.get("tipo_gasto", "Fijo")).strip().lower() == "variable":
                variable += valor
            else:
                fijo += valor
        return fijo, variable

    def _calc_capex(self) -> float:
        """Base CAPEX: valor_mensual × (1+tasa). IPC (double_t) se aplica en calcular_mes()."""
        tasa = self._tasa_interes
        return sum(
            float(i.get("valor_mensual", 0)) * (1.0 + tasa)
            for i in self._cadena_c.get("inversiones_capex", [])
        )

    def _calc_equipo_transversal(self) -> Tuple[float, float]:
        """Personal y dispositivos del equipo transversal de Cadena C.

        Personal:     calcular_costo_empresa(salario_base) × fte  (double_h en calcular_mes)
        Dispositivos: precio × cantidad_atribuible_operacion       (double_t en calcular_mes)
        """
        rh = self._cadena_c.get("recurso_humano_transversal", {})

        personal = sum(
            calcular_costo_empresa(float(r.get("salario", 0)), 0.0) * float(r.get("fte", 0))
            for r in rh.get("roles", []) if r.get("activo", True)
        )
        dispositivos = sum(
            float(d.get("precio", 0)) * float(d.get("cantidad_atribuible_operacion", 0))
            for d in rh.get("dispositivos_requeridos", [])
        )
        return personal, dispositivos

    def _calc_tarifa_canal(self) -> float:
        """Tarifa proveedor por canal. valor_total pre-calculado por el frontend.

        Formato nuevo: tarifa_proveedor_canal = [{...}]  (lista directa)
        Formato legacy: tarifa_proveedor_canal = {"items": [{...}]}
        """
        raw = self._cadena_c.get("tarifa_proveedor_canal", [])
        if isinstance(raw, dict):
            items = raw.get("items", [])
        else:
            items = raw if isinstance(raw, list) else []
        return sum(float(i.get("valor_total", 0)) for i in items)

    def _calc_tasa_escalamiento(self) -> float:
        """precio × volumen_cadena_c × tasa para inbound y outbound."""
        escalamiento = self._cadena_c.get("costo_variable", {}).get("tasa_escalamiento", {})
        vol_in = self._get_volumenes("inbound")
        vol_out = self._get_volumenes("outbound")
        total = sum(
            float(i.get("precio", 0)) * vol_in.get(i.get("canal", ""), 0.0) * float(i.get("tasa", 0))
            for i in escalamiento.get("inbound", [])
        )
        total += sum(
            float(i.get("precio", 0)) * vol_out.get(i.get("canal", ""), 0.0) * float(i.get("tasa", 0))
            for i in escalamiento.get("outbound", [])
        )
        return total

    def _calc_hitl(self) -> Tuple[float, float]:
        """Personal HITL (calcular_costo_empresa) y dispositivos HITL."""
        hitl = self._cadena_c.get("hitl", {})
        personal = sum(
            calcular_costo_empresa(float(e.get("salario", 0)), 0.0) * float(e.get("fte", 0))
            for e in hitl.get("equipo", []) if e.get("activo", True)
        )
        dispositivos = sum(
            float(d.get("precio", 0)) * float(d.get("cantidad_total", 0))
            for d in hitl.get("dispositivos_requeridos", [])
        )
        return personal, dispositivos

    # ── Helper volumetría ─────────────────────────────────────────────────────

    def _get_volumenes(self, direction: str) -> Dict[str, float]:
        """Extrae volúmenes Cadena C por nombre de canal desde volumetria."""
        canales = self._volumetria.get(direction, {}).get("canales", [])
        result: Dict[str, float] = {}
        for canal_data in canales:
            nombre = canal_data.get("canal", "")
            cadena_c_data = canal_data.get("cadena_c")
            if isinstance(cadena_c_data, dict) and nombre:
                result[nombre] = float(cadena_c_data.get("valor", 0))
        return result
