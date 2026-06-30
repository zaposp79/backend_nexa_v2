"""
nexa_engine/calculators/cadena_c.py
=====================================
Calculador de costos de Cadena C — Integración IA — Capa 6 del pipeline.

Responsabilidad
---------------
Calcular el costo total mensual de la capa de integración IA del deal:
tarifa del proveedor, costos de integración fijos y variables, equipo
especializado, HITL (Human-in-the-Loop) e inversiones amortizadas.

Estructura de costos Cadena C
------------------------------
  Tarifa proveedor  = volumen × tarifa_por_unidad × factor_ajuste
  OPEX fijo integración = costo_fijo_canal × factor_ajuste
  OPEX variable         = costo_variable_canal × factor_ajuste
  Amortización inversión= (inversión_anual / 12) × (1 + tasa_financiación)
  Equipo especializado  = (personal + herramientas) × factor_ajuste
                          (solo si hay volumen activo en algún canal)
  Escalamiento          = volumen × pct_escalamiento × costo_escalamiento × factor
  HITL                  = (personal_hitl + herramientas_hitl) × factor_ajuste
                          (solo si hay volumen activo)

Consume
-------
  - ParametrosCadenaC: canales, equipo, costos de HITL e inversiones
  - IParametrizationProvider: tasa de financiación para amortización de inversión

Produce
-------
  ResultadoCadenaC con todos los componentes de costo desglosados.
"""

from __future__ import annotations

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator
from nexa_engine.modules.shared.models import (
    CanalCadenaC,
    ParametrosCadenaC,
    ResultadoCadenaC,
)
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.shared.precision import cop_round  # H-05 FIX: Excel-compatible rounding


class CadenaCCalculator:
    """
    Calcula los costos mensuales de Cadena C (integración IA y servicios transversales).
    """

    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        CANALES = "CADENA_C.CANALES"
        EQUIPO_TRANSVERSAL = "CADENA_C.EQUIPO_TRANSVERSAL"
        INVERSION_ANUAL = "CADENA_C.INVERSION_ANUAL"
        OPEX_FIJO_INTEGRACION = "CADENA_C.OPEX_FIJO_INTEGRACION"
        OPEX_VARIABLE_INTEGRACION = "CADENA_C.OPEX_VARIABLE_INTEGRACION"
        ESCALAMIENTO = "CADENA_C.ESCALAMIENTO"
        HITL = "CADENA_C.HITL"
        TOTAL_MENSUAL = "CADENA_C.TOTAL_MENSUAL"

    def __init__(self, parametros: ParametrosCadenaC,
                 parametrizacion: IParametrizationProvider) -> None:
        self._parametros     = parametros
        self._parametrizacion = parametrizacion

    def calcular_para_mes(self, mes: int) -> ResultadoCadenaC:
        """
        Calcula todos los componentes de costo de Cadena C para el mes dado.

        Args:
            mes: Número de mes del contrato (determina el factor de ajuste tecnológico).

        Returns:
            ResultadoCadenaC con cada componente de costo desglosado.
        """
        factor_ajuste  = self._factor_ajuste_tecnologico(mes)
        volumen_total  = sum(c.volumen_mensual for c in self._parametros.canales)

        tarifa_proveedor = self._costo_tarifa_proveedor(factor_ajuste)
        opex_fijo_integ  = self._costo_opex_fijo(factor_ajuste)
        opex_var_integ   = self._costo_opex_variable(factor_ajuste)
        inversiones      = self._costo_amortizacion_inversion()
        equipo_integ     = self._costo_equipo(volumen_total, factor_ajuste)
        escalamiento     = self._costo_escalamiento(factor_ajuste)
        hitl             = self._costo_hitl(volumen_total, factor_ajuste)

        _audit_trace(
            component   = "cadena_c",
            rule        = "CADENA_C.tarifa_proveedor + opex_fijo + opex_var + inversiones + equipo + escalamiento + hitl",
            formula     = (
                "tarifa_proveedor = Σ(vol × tarifa × factor_ajuste); "
                "opex_fijo_integ = Σ(opex_fijo × factor_ajuste); "
                "opex_var_integ = Σ(opex_var × factor_ajuste); "
                "inversiones = (inversion_anual / 12) × (1 + tasa_financiacion); "
                "equipo_integ = (costo_equipo + opex_herramientas) × factor_ajuste; "
                "escalamiento = Σ(vol × pct_esc × costo_esc × factor_ajuste)"
            ),
            inputs      = {
                "n_canales":      len(self._parametros.canales),
                "volumen_total":  volumen_total,
                "factor_ajuste":  factor_ajuste,
                "inversion_anual": self._parametros.inversion_anual,
            },
            intermediate = {
                "tarifa_proveedor": tarifa_proveedor,
                "opex_fijo_integ":  opex_fijo_integ,
                "opex_var_integ":   opex_var_integ,
                "inversiones":      inversiones,
                "equipo_integ":     equipo_integ,
                "escalamiento":     escalamiento,
                "hitl":             hitl,
            },
            result      = tarifa_proveedor + opex_fijo_integ + opex_var_integ + inversiones + equipo_integ + escalamiento + hitl,
            source      = "User-Input (condiciones_cadena_c), OP-Config (tasa_financiacion)",
            mes         = mes,
            formula_ids = [
                self.FORMULA_ID.CANALES,
                self.FORMULA_ID.OPEX_FIJO_INTEGRACION,
                self.FORMULA_ID.OPEX_VARIABLE_INTEGRACION,
                self.FORMULA_ID.INVERSION_ANUAL,
                self.FORMULA_ID.EQUIPO_TRANSVERSAL,
                self.FORMULA_ID.ESCALAMIENTO,
                self.FORMULA_ID.HITL,
                self.FORMULA_ID.TOTAL_MENSUAL,
            ],
        )

        return ResultadoCadenaC(
            tarifa_proveedor = tarifa_proveedor,
            opex_fijo_integ  = opex_fijo_integ,
            opex_var_integ   = opex_var_integ,
            inversiones      = inversiones,
            equipo_integ     = equipo_integ,
            escalamiento     = escalamiento,
            hitl             = hitl,
        )

    # ──────────────────────────────────────────────────────────────
    # Componentes de costo
    # ──────────────────────────────────────────────────────────────

    def _factor_ajuste_tecnologico(self, mes: int) -> float:
        return PayrollCalculator.calcular_factor_aumento(
            mes,
            self._parametros.pct_aumento_tecnologico,
            self._parametros.mes_aplicacion_aumento,
        )

    def _costo_tarifa_proveedor(self, factor: float) -> float:
        """Costo del proveedor de IA: volumen × tarifa unitaria × factor de ajuste.

        H-05 FIX: Round each channel's tarifa before summing for Excel parity.
        """
        return sum(
            cop_round(c.volumen_mensual * c.tarifa_proveedor * factor)
            for c in self._parametros.canales
        )

    def _costo_opex_fijo(self, factor: float) -> float:
        """OPEX fijo de integración por canal activo.

        H-05 FIX: Round each channel's opex before summing.
        """
        return sum(cop_round(c.opex_fijo_integ * factor) for c in self._parametros.canales)

    def _costo_opex_variable(self, factor: float) -> float:
        """OPEX variable de integración proporcional al volumen por canal.

        H-05 FIX: Round each channel's opex before summing.
        """
        return sum(cop_round(c.opex_var_integ * factor) for c in self._parametros.canales)

    def _costo_amortizacion_inversion(self) -> float:
        """
        Amortización mensual de la inversión anual en plataforma.

        EXCEL V2-8: Condiciones Cadena C!J62 = IFERROR((I62/H62)*(1+Panel!$L$11),0)
        Diferencia vs V2-7: incluye factor (1+tasa_interes_mensual) de Panel!L11.
        """
        return self._parametros.inversion_anual / 12 * (1 + self._parametros.tasa_interes_mensual)

    def _costo_equipo(self, volumen_total: float, factor: float) -> float:
        """
        Costo del equipo de integración (personal especializado + herramientas).

        Solo se cobra si hay al menos un canal con volumen activo.

        H-08 FIX: Apply cop_round() for Excel parity.
        """
        if volumen_total == 0:
            return 0.0
        p = self._parametros
        total = (p.costo_equipo_integ + p.opex_herramientas_integ) * factor
        return cop_round(total)  # H-08: Excel-compatible rounding

    def _costo_escalamiento(self, factor: float) -> float:
        """Costo de escalamiento de capacidad por canal activo.

        H-05 FIX: Round each channel's escalamiento before summing for Excel parity.
        """
        return sum(
            cop_round(c.volumen_mensual * c.pct_escalamiento * c.costo_escalamiento * factor)
            for c in self._parametros.canales
        )

    def _costo_hitl(self, volumen_total: float, factor: float) -> float:
        """
        Costo del equipo HITL (Human-in-the-Loop).

        Solo se cobra si hay al menos un canal con volumen activo.

        H-08 FIX: Apply cop_round() for Excel parity.
        """
        if volumen_total == 0:
            return 0.0
        p = self._parametros
        total = (p.costo_personal_hitl + p.opex_herramientas_hitl) * factor
        return cop_round(total)  # H-08: Excel-compatible rounding
