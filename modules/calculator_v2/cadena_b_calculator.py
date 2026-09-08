"""
Cálculo de costos para Cadena B (tecnológica).

Componentes del Fijo (OPEX + CAPEX + S&M):
  - OPEX Fijo:    ítems opex.items[] con tipo_gasto="Fijo"    → Componente Fijo
  - OPEX Variable: ítems opex.items[] con tipo_gasto="Variable" → Componente Variable
  - CAPEX:        inversiones_capex[].valor_mensual × (1+tasa) × double_t  → Componente Fijo
  - S&M personal:     equipo_soporte_mantenimiento.roles → calcular_costo_empresa(salario) × fte (double_h)
  - S&M dispositivos: equipo_soporte_mantenimiento.dispositivos_requeridos → precio × cantidad (double_t)

Componentes del Variable (Tarifa + Escalamiento + HITL):
  - Tarifa Canal:        precio × volumen Cadena B × IPC tecnológico  → Componente Variable
  - Tasa Escalamiento:   precio_precalc × vol × tasa × IPC tecnológico → Componente Variable
  - HITL:                personal (IPC humano) + dispositivos (IPC tecn) → Componente Variable

IPC:
  - Personal (S&M, HITL): aplica componente_humano (double_h)
  - Tecnología (OPEX, tarifas, HITL dispositivos, S&M dispositivos): aplica componente_tecnológico (double_t)
  - CAPEX: se aplica double_t; base = valor_mensual × (1 + tasa_interes_mensual)
  - S&M dispositivos: Excel V2-8 'Costo Fijo'!D206 = SUMPRODUCT(C98:C103×D98:D103) — incluido desde V2-8

Volúmenes Cadena B: volumetria.{inbound|outbound}.canales[i].cadena_b.valor
Cadenas activas: validadas en engine.py antes de instanciar este calculador.

Excel ref: 006_ElTiempo.xlsx — 'Costo Fijo' / 'Costo Variable'.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .nomina_calculator import calcular_costo_empresa

logger = logging.getLogger("nexa.motor_reglas.cadena_b")


class CadenaBCalculator:
    """Calcula costos mensuales de Cadena B aplicando factores IPC."""

    def __init__(self, request_data: Dict[str, Any]) -> None:
        self._cadena_b = request_data.get("condiciones_cadena_b") or {}
        self._volumetria = request_data.get("volumetria") or {}
        _indexacion = self._volumetria.get("indexacion") or {}
        self._tasa_interes = float(_indexacion.get("tasa_interes_mensual", 0))
        self._base = self._compute_base()

    # ── API pública ───────────────────────────────────────────────────────────

    def calcular_mes(self, double_h: float = 1.0, double_t: float = 1.0) -> Dict[str, float]:
        """Aplica factores IPC y retorna todos los componentes del mes.

        double_h: factor IPC acumulado para componente humano (personal S&M y HITL)
        double_t: factor IPC acumulado para componente tecnológico (OPEX, tarifas, dispositivos)
        """
        b = self._base

        # Componente Fijo = OPEX Fijo + CAPEX + S&M
        opex_fijo = b["opex_fijo"] * double_t
        capex = b["capex"] * double_t
        # Excel V2-8: S&M = personal (double_h) + dispositivos (double_t)
        # 'Costo Fijo'!D206 = SUMPRODUCT('Condiciones Cadena B'!C98:C103×D98:D103)
        sm = b["sm_personal"] * double_h + b["sm_dispositivos"] * double_t
        comp_fijo = opex_fijo + capex + sm

        # Componente Variable = OPEX Variable + Tarifa Canal + Tasa Escalamiento + HITL
        opex_var = b["opex_variable"] * double_t
        tarifa_in = b["tarifa_canal_in"] * double_t
        tarifa_out = b["tarifa_canal_out"] * double_t
        tarifa = tarifa_in + tarifa_out
        escal_in = b["tasa_escal_in"] * double_t
        escal_out = b["tasa_escal_out"] * double_t
        escal = escal_in + escal_out
        hitl = b["hitl_personal"] * double_h + b["hitl_dispositivos"] * double_t
        comp_var = opex_var + tarifa + escal + hitl

        costo_total = comp_fijo + comp_var

        opex_fijo_in  = b["opex_fijo_in"]  * double_t
        opex_fijo_out = b["opex_fijo_out"] * double_t
        opex_var_in   = b["opex_var_in"]   * double_t
        opex_var_out  = b["opex_var_out"]  * double_t
        capex_in      = b["capex_in"]      * double_t
        capex_out     = b["capex_out"]     * double_t

        return {
            "costo_cadena_b":          costo_total,
            "componente_fijo_b":       comp_fijo,
            "componente_variable_b":   comp_var,
            "opex_fijo_cadena_b":      opex_fijo,
            "opex_fijo_inbound_cadena_b":  opex_fijo_in,
            "opex_fijo_outbound_cadena_b": opex_fijo_out,
            "capex_cadena_b":          capex,
            "capex_inbound_cadena_b":  capex_in,
            "capex_outbound_cadena_b": capex_out,
            "sm_cadena_b":             sm,
            "opex_variable_cadena_b":  opex_var,
            "opex_var_inbound_cadena_b":  opex_var_in,
            "opex_var_outbound_cadena_b": opex_var_out,
            "tarifa_canal_cadena_b":             tarifa,
            "tarifa_canal_inbound_cadena_b":     tarifa_in,
            "tarifa_canal_outbound_cadena_b":    tarifa_out,
            "tasa_escalamiento_cadena_b":        escal,
            "tasa_escalamiento_inbound_cadena_b":  escal_in,
            "tasa_escalamiento_outbound_cadena_b": escal_out,
            "hitl_cadena_b":           hitl,
            # Componente humano: solo costos de personal (IPC double_h) — para vision CTS
            "sm_personal_cadena_b":    b["sm_personal"] * double_h,
            "hitl_personal_cadena_b":  b["hitl_personal"] * double_h,
        }

    # ── Cálculo base (sin IPC, una vez en __init__) ───────────────────────────

    def _compute_base(self) -> Dict[str, float]:
        opex_fijo_in, opex_fijo_out, opex_var_in, opex_var_out = self._calc_opex_directional()
        capex_in, capex_out = self._calc_capex_directional()
        sm_personal = self._calc_sm()
        tarifa_in, tarifa_out = self._calc_tarifa_canal()
        escal_in, escal_out = self._calc_tasa_escalamiento()
        hitl_personal, hitl_dispositivos = self._calc_hitl()
        sm_dispositivos = self._calc_sm_dispositivos()
        logger.debug(
            "[cadena-b] base: opex_fijo=%.0f opex_var=%.0f capex=%.0f "
            "sm_p=%.0f sm_d=%.0f tarifa_in=%.0f tarifa_out=%.0f escal_in=%.0f escal_out=%.0f hitl_p=%.0f hitl_d=%.0f",
            opex_fijo_in + opex_fijo_out, opex_var_in + opex_var_out, capex_in + capex_out,
            sm_personal, sm_dispositivos,
            tarifa_in, tarifa_out, escal_in, escal_out, hitl_personal, hitl_dispositivos,
        )
        return {
            "opex_fijo": opex_fijo_in + opex_fijo_out,
            "opex_fijo_in": opex_fijo_in,
            "opex_fijo_out": opex_fijo_out,
            "opex_variable": opex_var_in + opex_var_out,
            "opex_var_in": opex_var_in,
            "opex_var_out": opex_var_out,
            "capex": capex_in + capex_out,
            "capex_in": capex_in,
            "capex_out": capex_out,
            "sm_personal": sm_personal,
            "sm_dispositivos": sm_dispositivos,
            "tarifa_canal_in": tarifa_in,
            "tarifa_canal_out": tarifa_out,
            "tasa_escal_in": escal_in,
            "tasa_escal_out": escal_out,
            "hitl_personal": hitl_personal,
            "hitl_dispositivos": hitl_dispositivos,
        }

    def _calc_opex_por_tipo(self) -> tuple[float, float]:
        """Separa OPEX por tipo_gasto: Fijo → Componente Fijo, Variable → Componente Variable."""
        fi, fo, vi, vo = self._calc_opex_directional()
        return fi + fo, vi + vo

    def _calc_opex_directional(self) -> tuple[float, float, float, float]:
        """(fijo_in, fijo_out, var_in, var_out) por modalidad de item."""
        items = self._cadena_b.get("opex", {}).get("items", [])
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
        """Base CAPEX: valor_mensual × (1+tasa). IPC (double_t) se aplica en calcular_mes().

        Excel 006 'Costo Fijo': base CAPEX = valor_mensual × (1+tasa_interes_mensual).
        El valor_mensual del request ya incorpora (1+tasa)^meses/meses, y Excel multiplica
        nuevamente por (1+tasa) → base = valor_total × (1+tasa)^(meses+1) / meses.
        """
        ci, co = self._calc_capex_directional()
        return ci + co

    def _calc_capex_directional(self) -> tuple[float, float]:
        """(capex_in, capex_out) por modalidad de item. Base = valor_mensual × (1+tasa)."""
        tasa = self._tasa_interes
        capex_in = capex_out = 0.0
        for i in self._cadena_b.get("inversiones_capex", []):
            valor = float(i.get("valor_mensual", 0)) * (1.0 + tasa)
            if str(i.get("modalidad", "")).strip().lower() == "inbound":
                capex_in += valor
            else:
                capex_out += valor
        return capex_in, capex_out

    def _calc_sm(self) -> float:
        """Personal S&M: calcular_costo_empresa(salario) × fte para roles activos.

        Excel V2-8: 'Costo Fijo'!E187:E198 = costo_empresa × FTE por rol.
        Campo activado: usa 'activado' (request) o 'activo' (legacy) con default True.
        """
        sm = self._cadena_b.get("equipo_soporte_mantenimiento", {})
        total = 0.0
        for r in sm.get("roles", []):
            activo = r.get("activado", r.get("activo", True))
            if not activo:
                continue
            total += calcular_costo_empresa(float(r.get("salario", 0)), 0.0) * float(r.get("fte", 0))
        return total

    def _calc_sm_dispositivos(self) -> float:
        """OPEX de dispositivos del equipo S&M: precio × cantidad_atribuible_a_la_operacion.

        Excel V2-8: 'Costo Fijo'!D206 = SUMPRODUCT('Condiciones Cadena B'!$C$98:$C$103×$D$98:$D$103)
        Dispositivos: Dispositivo Principal, Monitores, Headset, MS365, Power BI, Costo Puesto.
        IPC tecnológico (double_t) se aplica en calcular_mes().
        """
        sm = self._cadena_b.get("equipo_soporte_mantenimiento", {})
        return sum(
            float(d.get("precio", 0)) * float(
                d.get("cantidad_atribuible_a_la_operacion",
                      d.get("cantidad_atribuible_operacion",
                            d.get("cantidad",
                                  d.get("cantidad_total", 0))))
            )
            for d in sm.get("dispositivos_requeridos", [])
        )

    def _calc_tarifa_canal(self) -> tuple[float, float]:
        """precio × volumen_cadena_b por canal. Retorna (tarifa_inbound, tarifa_outbound)."""
        tarifas = self._cadena_b.get("costo_variable", {}).get("tarifas_por_canal", {})
        vol_in = self._get_volumenes("inbound")
        vol_out = self._get_volumenes("outbound")
        tarifa_in = sum(
            float(i.get("precio", 0)) * vol_in.get(i.get("canal", ""), 0.0)
            for i in tarifas.get("inbound", [])
        )
        tarifa_out = sum(
            float(i.get("precio", 0)) * vol_out.get(i.get("canal", ""), 0.0)
            for i in tarifas.get("outbound", [])
        )
        return tarifa_in, tarifa_out

    def _calc_tasa_escalamiento(self) -> tuple[float, float]:
        """precio_precalc × volumen × tasa. Retorna (escal_inbound, escal_outbound)."""
        escalamiento = self._cadena_b.get("costo_variable", {}).get("tasa_escalamiento", {})
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

    def _calc_hitl(self) -> tuple[float, float]:
        """Personal HITL (calcular_costo_empresa) y costo de dispositivos HITL."""
        hitl = self._cadena_b.get("hitl", {})
        personal = sum(
            calcular_costo_empresa(float(r.get("salario", 0)), 0.0) * float(r.get("fte", 0))
            for r in hitl.get("equipo", []) if r.get("activo", True)
        )
        dispositivos = sum(
            float(d.get("precio", 0)) * float(d.get("cantidad_total", 0))
            for d in hitl.get("dispositivos_requeridos", [])
        )
        return personal, dispositivos

    # ── Helper volumetría ─────────────────────────────────────────────────────

    def _get_volumenes(self, direction: str) -> Dict[str, float]:
        """Extrae volúmenes Cadena B por nombre de canal desde volumetria."""
        canales = self._volumetria.get(direction, {}).get("canales", [])
        result: Dict[str, float] = {}
        for canal_data in canales:
            nombre = canal_data.get("canal", "")
            cadena_b_data = canal_data.get("cadena_b")
            if isinstance(cadena_b_data, dict) and nombre:
                result[nombre] = float(cadena_b_data.get("valor", 0))
        return result
