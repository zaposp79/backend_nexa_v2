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
        opex_fijo_in  = b["opex_fijo_in"]  * double_t
        opex_fijo_out = b["opex_fijo_out"] * double_t
        opex_variable = b["opex_variable"] * double_t
        opex_var_in   = b["opex_var_in"]   * double_t
        opex_var_out  = b["opex_var_out"]  * double_t
        capex         = b["capex"]         * double_t
        capex_in      = b["capex_in"]      * double_t
        capex_out     = b["capex_out"]     * double_t
        equipo_tranv  = b["equipo_transversal_personal"] * double_h
        disp_tranv    = b["equipo_transversal_dispositivos"] * double_t
        # Excel V2-8: 'Visión P&G'!C60 · fórmula: =SUMPRODUCT(...)*(1+IPC)*(1+IPC) — factor tecnológico al cuadrado.
        tarifa_canal     = b["tarifa_canal"]     * double_t * double_t
        tarifa_canal_in  = b["tarifa_canal_in"]  * double_t * double_t
        tarifa_canal_out = b["tarifa_canal_out"] * double_t * double_t
        escal_in      = b["tasa_escal_in"]  * double_t
        escal_out     = b["tasa_escal_out"] * double_t
        tasa_escal    = escal_in + escal_out
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
            "componente_fijo_cadena_c":    opex_fijo + capex + equipo_tranv + disp_tranv,
            "componente_variable_cadena_c": opex_variable + tarifa_canal + tasa_escal + hitl_personal + hitl_disp,
            "opex_fijo_cadena_c":          opex_fijo,
            "opex_fijo_inbound_cadena_c":  opex_fijo_in,
            "opex_fijo_outbound_cadena_c": opex_fijo_out,
            "opex_variable_cadena_c":      opex_variable,
            "opex_var_inbound_cadena_c":   opex_var_in,
            "opex_var_outbound_cadena_c":  opex_var_out,
            "capex_cadena_c":              capex,
            "capex_inbound_cadena_c":      capex_in,
            "capex_outbound_cadena_c":     capex_out,
            "equipo_transversal_cadena_c": equipo_tranv + disp_tranv,
            "tarifa_canal_cadena_c":            tarifa_canal,
            "tarifa_canal_inbound_cadena_c":    tarifa_canal_in,
            "tarifa_canal_outbound_cadena_c":   tarifa_canal_out,
            "tasa_escalamiento_cadena_c":          tasa_escal,
            "tasa_escalamiento_inbound_cadena_c":  escal_in,
            "tasa_escalamiento_outbound_cadena_c": escal_out,
            "hitl_cadena_c":               hitl_personal + hitl_disp,
            # Componente humano: solo costos de personal (IPC double_h) — para vision CTS
            "equipo_personal_cadena_c":    equipo_tranv,
            "hitl_personal_cadena_c":      hitl_personal,
        }

    # ── Cálculo base (sin IPC, una vez en __init__) ───────────────────────────

    def _compute_base(self) -> Dict[str, float]:
        opex_fijo_in, opex_fijo_out, opex_var_in, opex_var_out = self._calc_opex_directional()
        capex_in, capex_out = self._calc_capex_directional()
        tranv_personal, tranv_dispositivos = self._calc_equipo_transversal()
        tarifa_in, tarifa_out = self._calc_tarifa_canal()
        escal_in, escal_out = self._calc_tasa_escalamiento()
        hitl_personal, hitl_dispositivos = self._calc_hitl()

        logger.debug(
            "[cadena-c] base: opex_f=%.0f opex_v=%.0f capex=%.0f "
            "tranv_p=%.0f tranv_d=%.0f tarifa=%.0f escal_in=%.0f escal_out=%.0f hitl_p=%.0f hitl_d=%.0f",
            opex_fijo_in + opex_fijo_out, opex_var_in + opex_var_out, capex_in + capex_out,
            tranv_personal, tranv_dispositivos,
            tarifa_in + tarifa_out, escal_in, escal_out, hitl_personal, hitl_dispositivos,
        )
        return {
            "opex_fijo":                       opex_fijo_in + opex_fijo_out,
            "opex_fijo_in":                    opex_fijo_in,
            "opex_fijo_out":                   opex_fijo_out,
            "opex_variable":                   opex_var_in + opex_var_out,
            "opex_var_in":                     opex_var_in,
            "opex_var_out":                    opex_var_out,
            "capex":                           capex_in + capex_out,
            "capex_in":                        capex_in,
            "capex_out":                       capex_out,
            "equipo_transversal_personal":     tranv_personal,
            "equipo_transversal_dispositivos": tranv_dispositivos,
            "tarifa_canal":                    tarifa_in + tarifa_out,
            "tarifa_canal_in":                 tarifa_in,
            "tarifa_canal_out":                tarifa_out,
            "tasa_escal_in":                   escal_in,
            "tasa_escal_out":                  escal_out,
            "hitl_personal":                   hitl_personal,
            "hitl_dispositivos":               hitl_dispositivos,
        }

    def _calc_opex_por_tipo(self) -> Tuple[float, float]:
        """Separa OPEX por tipo_gasto: Fijo / Variable. valor_total pre-calculado por el frontend."""
        fi, fo, vi, vo = self._calc_opex_directional()
        return fi + fo, vi + vo

    def _calc_opex_directional(self) -> Tuple[float, float, float, float]:
        """(fijo_in, fijo_out, var_in, var_out) por modalidad de item."""
        items = self._cadena_c.get("opex", [])
        fijo_in = fijo_out = var_in = var_out = 0.0
        for item in items:
            valor = float(item.get("valor_total", 0))
            is_var = str(item.get("tipo_gasto", "Fijo")).strip().lower() == "variable"
            is_in = str(item.get("modalidad", "")).strip().lower() == "inbound"
            if is_var:
                if is_in:
                    var_in += valor
                else:
                    var_out += valor
            else:
                if is_in:
                    fijo_in += valor
                else:
                    fijo_out += valor
        return fijo_in, fijo_out, var_in, var_out

    def _calc_capex(self) -> float:
        """Base CAPEX: valor_mensual × (1+tasa). IPC (double_t) se aplica en calcular_mes()."""
        ci, co = self._calc_capex_directional()
        return ci + co

    def _calc_capex_directional(self) -> Tuple[float, float]:
        """(capex_in, capex_out) por modalidad de item. Base = valor_mensual × (1+tasa)."""
        tasa = self._tasa_interes
        capex_in = capex_out = 0.0
        for i in self._cadena_c.get("inversiones_capex", []):
            valor = float(i.get("valor_mensual", 0)) * (1.0 + tasa)
            if str(i.get("modalidad", "")).strip().lower() == "inbound":
                capex_in += valor
            else:
                capex_out += valor
        return capex_in, capex_out

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

    def _calc_tarifa_canal(self) -> Tuple[float, float]:
        """Tarifa proveedor por canal, split por modalidad. Retorna (tarifa_in, tarifa_out).

        Formato nuevo: tarifa_proveedor_canal = [{...}]  (lista directa)
        Formato legacy: tarifa_proveedor_canal = {"items": [{...}]}
        """
        raw = self._cadena_c.get("tarifa_proveedor_canal", [])
        if isinstance(raw, dict):
            items = raw.get("items", [])
        else:
            items = raw if isinstance(raw, list) else []
        tarifa_in = tarifa_out = 0.0
        for i in items:
            valor = float(i.get("valor_total", 0))
            if str(i.get("modalidad", "")).strip().lower() == "inbound":
                tarifa_in += valor
            else:
                tarifa_out += valor
        return tarifa_in, tarifa_out

    def _calc_tasa_escalamiento(self) -> tuple[float, float]:
        """precio × volumen_cadena_c × tasa. Retorna (escal_inbound, escal_outbound)."""
        escalamiento = self._cadena_c.get("costo_variable", {}).get("tasa_escalamiento", {})
        vol_in = self._get_volumenes("inbound")
        vol_out = self._get_volumenes("outbound")
        escal_in = sum(
            float(i.get("precio", 0)) * vol_in.get(i.get("canal", ""), 0.0) * float(i.get("tasa", 0))
            for i in escalamiento.get("inbound", [])
        )
        escal_out = sum(
            float(i.get("precio", 0)) * vol_out.get(i.get("canal", ""), 0.0) * float(i.get("tasa", 0))
            for i in escalamiento.get("outbound", [])
        )
        return escal_in, escal_out

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
