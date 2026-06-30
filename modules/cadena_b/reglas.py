"""
nexa_engine/calculators/cadena_b.py
=====================================
Calculador de costos de Cadena B — Plataforma Digital — Capas 4-5 del pipeline.

Responsabilidad
---------------
Calcular el costo mensual total de la plataforma de canales digitales:
OPEX fijo, inversiones amortizadas, equipo de Soporte y Mantenimiento (S&M),
costos variables por canal, escalamiento de capacidad y equipo HITL.

Estructura de costos Cadena B
------------------------------
  OPEX fijo plataforma  = Σ(opex_fijo_canal) × factor_ajuste
  Inversiones amortizadas = inversion_mensual × factor_ajuste
  S&M                   = (personal_sm + herramientas_sm) × factor_ajuste
                          (solo si hay operación activa en alguna modalidad)
  Costo variable        = Σ(volumen × tarifa_unitaria × factor_ajuste)
  Escalamiento          = Σ(volumen × pct_esc × costo_esc × factor_ajuste)
  HITL                  = (personal_hitl + herramientas_hitl) × factor_ajuste
                          (solo si hay operación activa)

Consume
-------
  - ParametrosCadenaB: canales, equipo S&M, dispositivos, costos variable/HITL

Produce
-------
  ResultadoCadenaB con todos los componentes de costo desglosados.
"""

from __future__ import annotations

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator
from nexa_engine.modules.shared.models import (
    CanalCadenaB,
    ParametrosCadenaB,
    ResultadoCadenaB,
)
from nexa_engine.modules.shared.precision import cop_round  # H-05 FIX: Excel-compatible rounding


class CadenaBCalculator:
    """
    Calcula los costos mensuales de la plataforma digital (Cadena B).
    """

    # ──────────────────────────────────────────────────────────────
    # Formula identifiers for audit trail and reproducibility
    # ──────────────────────────────────────────────────────────────
    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        OPEX_FIJO = "CADENA_B.OPEX_FIJO"  # Suma de opex_fijo_canal
        INVERSIONES = "CADENA_B.INVERSIONES"  # Inversiones amortizadas
        SOPORTE_MANTENIMIENTO = "CADENA_B.SOPORTE_MANTENIMIENTO"  # Personal S&M + herramientas (H-08)
        COSTO_VARIABLE = "CADENA_B.COSTO_VARIABLE"  # Σ(vol × tarifa) con H-05 cop_round
        ESCALAMIENTO = "CADENA_B.ESCALAMIENTO"  # Σ(vol × pct_esc × costo_esc) con H-05 cop_round
        HITL = "CADENA_B.HITL"  # Personal HITL + herramientas (H-08)
        FACTOR_PERSONAL = "CADENA_B.FACTOR_PERSONAL"  # Incremento salarial por mes

    def __init__(self, parametros: ParametrosCadenaB) -> None:
        self._parametros = parametros

    def calcular_para_mes(self, mes: int) -> ResultadoCadenaB:
        """
        Consolida todos los componentes de costo de Cadena B para el mes dado.

        Args:
            mes: Número de mes del contrato (determina el factor de ajuste).

        Returns:
            ResultadoCadenaB con cada componente de costo desglosado.
        """
        factor_personal = self._factor_ajuste_personal(mes)
        vol_ib, vol_ob  = self._volumenes_por_modalidad()

        opex_fijo      = self._costo_opex_fijo()
        inversiones    = self._costo_inversiones()
        sm             = self._costo_sm(vol_ib, vol_ob, factor_personal)
        costo_variable = self._costo_variable()
        escalamiento   = self._costo_escalamiento()
        hitl           = self._costo_hitl(vol_ib, vol_ob, factor_personal)

        _audit_trace(
            component   = "cadena_b",
            rule        = "CADENA_B.opex_fijo + inversiones + soporte_mantenimiento + costo_variable + escalamiento + hitl",
            formula     = (
                "opex_fijo = Σ(opex_fijo_canal); "
                "inversiones = inversion_mensual; "
                "sm = costo_personal_sm × factor_personal + opex_herramientas_sm; "
                "costo_variable = Σ(vol × tarifa_unitaria); "
                "escalamiento = Σ(vol × pct_esc × costo_esc); "
                "hitl = costo_personal_hitl × factor_personal + opex_herramientas_hitl"
            ),
            inputs      = {
                "n_canales":       len(self._parametros.canales),
                "vol_inbound":     vol_ib,
                "vol_outbound":    vol_ob,
                "factor_personal": factor_personal,
            },
            intermediate = {
                "opex_fijo":      opex_fijo,
                "inversiones":    inversiones,
                "soporte_mantenimiento": sm,
                "costo_variable": costo_variable,
                "escalamiento":   escalamiento,
                "hitl":           hitl,
            },
            result      = opex_fijo + inversiones + sm + costo_variable + escalamiento + hitl,  # sm is a local variable
            source      = "User-Input (condiciones_cadena_b)",
            mes         = mes,
            formula_ids = [
                self.FORMULA_ID.OPEX_FIJO,
                self.FORMULA_ID.INVERSIONES,
                self.FORMULA_ID.SOPORTE_MANTENIMIENTO,
                self.FORMULA_ID.COSTO_VARIABLE,
                self.FORMULA_ID.ESCALAMIENTO,
                self.FORMULA_ID.HITL,
                self.FORMULA_ID.FACTOR_PERSONAL,
            ],
        )

        return ResultadoCadenaB(
            opex_fijo      = opex_fijo,
            inversiones    = inversiones,
            soporte_mantenimiento = sm,
            costo_variable = costo_variable,
            escalamiento   = escalamiento,
            hitl           = hitl,
        )

    # ──────────────────────────────────────────────────────────────
    # Componentes de costo
    # ──────────────────────────────────────────────────────────────

    def _factor_ajuste_personal(self, mes: int) -> float:
        """Factor de incremento salarial para componentes de personal."""
        return PayrollCalculator.calcular_factor_aumento(
            mes,
            self._parametros.pct_aumento_personal,
            self._parametros.mes_aplicacion_aumento,
        )

    def _volumenes_por_modalidad(self):
        """Suma de volúmenes mensuales por modalidad para determinar actividad."""
        canales = self._parametros.canales
        vol_ib  = sum(c.volumen_mensual for c in canales if c.modalidad == "Inbound")
        vol_ob  = sum(c.volumen_mensual for c in canales if c.modalidad == "Outbound")
        return vol_ib, vol_ob

    def _costo_opex_fijo(self) -> float:
        """OPEX fijo de la plataforma digital: suma de OPEX por canal activo."""
        return sum(c.opex_fijo for c in self._parametros.canales)

    def _costo_inversiones(self) -> float:
        """Inversiones amortizadas mensualmente sobre la plataforma digital."""
        return self._parametros.inversion_mensual

    def _costo_sm(self, vol_inbound: float, vol_outbound: float,
                  factor_personal: float) -> float:
        """
        Costo del equipo de Soporte y Mantenimiento (S&M).

        Solo el componente de personal se indexa anualmente (human indexation).
        Las herramientas/dispositivos se mantienen a costo fijo.

        H-08 FIX: Apply cop_round() for Excel parity.
        """
        if (vol_inbound + vol_outbound) == 0:
            return 0.0
        p = self._parametros
        total = p.costo_personal_sm * factor_personal + p.opex_herramientas_sm
        return cop_round(total)  # H-08: Excel-compatible rounding

    def _costo_variable(self) -> float:
        """Costo variable total: suma de (volumen × tarifa unitaria) por canal.

        H-05 FIX: Round each channel's contribution before summing to maintain
        Excel-compatible ROUND_HALF_UP precision across all components.
        """
        return sum(
            cop_round(c.volumen_mensual * c.tarifa_unitaria)
            for c in self._parametros.canales
        )

    def _costo_escalamiento(self) -> float:
        """Costo de escalamiento de capacidad: proporcional al volumen y porcentaje de escala.

        H-05 FIX: Round each channel's escalamiento before summing for Excel parity.
        """
        return sum(
            cop_round(c.volumen_mensual * c.pct_escalamiento * c.costo_escalamiento)
            for c in self._parametros.canales
        )

    def _costo_hitl(self, vol_inbound: float, vol_outbound: float,
                    factor_personal: float) -> float:
        """
        Costo del equipo HITL (Human-in-the-Loop).

        Solo el componente de personal se indexa; herramientas se mantienen fijas.

        H-08 FIX: Apply cop_round() for Excel parity.
        """
        if (vol_inbound + vol_outbound) == 0:
            return 0.0
        p = self._parametros
        total = p.costo_personal_hitl * factor_personal + p.opex_herramientas_hitl
        return cop_round(total)  # H-08: Excel-compatible rounding
