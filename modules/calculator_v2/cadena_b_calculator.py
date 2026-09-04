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
        tarifa = b["tarifa_canal"] * double_t
        escal = b["tasa_escalamiento"] * double_t
        hitl = b["hitl_personal"] * double_h + b["hitl_dispositivos"] * double_t
        comp_var = opex_var + tarifa + escal + hitl

        costo_total = comp_fijo + comp_var

        return {
            "costo_cadena_b":          costo_total,
            "componente_fijo_b":       comp_fijo,
            "componente_variable_b":   comp_var,
            "opex_fijo_cadena_b":      opex_fijo,
            "capex_cadena_b":          capex,
            "sm_cadena_b":             sm,
            "opex_variable_cadena_b":  opex_var,
            "tarifa_canal_cadena_b":   tarifa,
            "tasa_escalamiento_cadena_b": escal,
            "hitl_cadena_b":           hitl,
        }

    # ── Cálculo base (sin IPC, una vez en __init__) ───────────────────────────

    def _compute_base(self) -> Dict[str, float]:
        opex_fijo, opex_variable = self._calc_opex_por_tipo()
        capex = self._calc_capex()
        sm_personal = self._calc_sm()
        tarifa_canal = self._calc_tarifa_canal()
        tasa_escal = self._calc_tasa_escalamiento()
        hitl_personal, hitl_dispositivos = self._calc_hitl()
        sm_dispositivos = self._calc_sm_dispositivos()
        logger.debug(
            "[cadena-b] base: opex_fijo=%.0f opex_var=%.0f capex=%.0f "
            "sm_p=%.0f sm_d=%.0f tarifa=%.0f escal=%.0f hitl_p=%.0f hitl_d=%.0f",
            opex_fijo, opex_variable, capex,
            sm_personal, sm_dispositivos,
            tarifa_canal, tasa_escal, hitl_personal, hitl_dispositivos,
        )
        return {
            "opex_fijo": opex_fijo,
            "opex_variable": opex_variable,
            "capex": capex,
            "sm_personal": sm_personal,
            "sm_dispositivos": sm_dispositivos,
            "tarifa_canal": tarifa_canal,
            "tasa_escalamiento": tasa_escal,
            "hitl_personal": hitl_personal,
            "hitl_dispositivos": hitl_dispositivos,
        }

    def _calc_opex_por_tipo(self) -> tuple[float, float]:
        """Separa OPEX por tipo_gasto: Fijo → Componente Fijo, Variable → Componente Variable."""
        items = self._cadena_b.get("opex", {}).get("items", [])
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
        """Base CAPEX: valor_mensual × (1+tasa). IPC (double_t) se aplica en calcular_mes().

        Excel 006 'Costo Fijo': base CAPEX = valor_mensual × (1+tasa_interes_mensual).
        El valor_mensual del request ya incorpora (1+tasa)^meses/meses, y Excel multiplica
        nuevamente por (1+tasa) → base = valor_total × (1+tasa)^(meses+1) / meses.
        """
        tasa = self._tasa_interes
        return sum(
            float(i.get("valor_mensual", 0)) * (1.0 + tasa)
            for i in self._cadena_b.get("inversiones_capex", [])
        )

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

    def _calc_tarifa_canal(self) -> float:
        """precio × volumen_cadena_b por canal (inbound y outbound)."""
        tarifas = self._cadena_b.get("costo_variable", {}).get("tarifas_por_canal", {})
        vol_in = self._get_volumenes("inbound")
        vol_out = self._get_volumenes("outbound")
        total = sum(
            float(i.get("precio", 0)) * vol_in.get(i.get("canal", ""), 0.0)
            for i in tarifas.get("inbound", [])
        )
        total += sum(
            float(i.get("precio", 0)) * vol_out.get(i.get("canal", ""), 0.0)
            for i in tarifas.get("outbound", [])
        )
        return total

    def _calc_tasa_escalamiento(self) -> float:
        """precio_precalc × volumen × tasa (precio ya incluye tarifa por canal escalado)."""
        escalamiento = self._cadena_b.get("costo_variable", {}).get("tasa_escalamiento", {})
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
