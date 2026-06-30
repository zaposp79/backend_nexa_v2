"""
modules.calculator.formulas.no_payroll.calculator
==================================================
Calculador de costos No Payroll de Cadena A — Capa 3 del pipeline.

Responsabilidad
---------------
Calcular los costos de infraestructura y tecnología asociados a las
estaciones de trabajo activas en sede: OPEX de TI, CAPEX amortizado
y costos fijos de infraestructura (arriendo, energía, vigilancia, aseo).

Estos costos son proporcionales al número de estaciones presenciales,
es decir, al total de FTE de agentes operativos (no de staff de soporte).

Estructura de costos No Payroll
---------------------------------
  OPEX TI     = opex_ti_por_estacion × estaciones × factor_ajuste_tecnológico
  CAPEX        = capex_por_estacion   × estaciones × factor_ajuste_tecnológico
  Infraestructura = (arriendo + energía + vigilancia + aseo + otros) × estaciones × factor

El factor de ajuste tecnológico refleja el incremento anual de costos
de tecnología e infraestructura a partir del mes configurado.

Consume
-------
  - ParametrosNoPayroll: costos unitarios por estación y parámetros de ajuste
  - Lista de PerfilCadenaA: para calcular el total de estaciones activas

Produce
-------
  ResultadoNoPayroll con los tres componentes de costo para el mes dado.
"""

from __future__ import annotations

from typing import List

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.shared.models import (
    ParametrosNoPayroll,
    PerfilCadenaA,
    ResultadoNoPayroll,
)


class NoPayrollCalculator:
    """
    Calcula los costos de infraestructura y tecnología de las estaciones activas.

    Las estaciones activas son los FTE de agentes que ocupan puesto físico
    en la sede. El staff de soporte (es_soporte=True) no genera costo de estación.

    @excel_lineage:
      version: V2-8
      sheet: No payroll
      cells: [R107 (OPEX TI por estación), E167/K167/K168 (CAPEX amortizable),
              R248 (Costos Fijos por estación), D13:BK13 (date headers)]
      concept: costos_no_payroll_estaciones_activas
    @runtime_sources:
      - storage/parametrization/op → ParametrosNoPayroll (opex_ti_por_estacion,
        capex_por_estacion, capex_inicial_por_estacion, arriendo_por_estacion,
        energia_por_estacion, vigilancia_por_estacion, aseo_por_estacion,
        otros_fijos_por_estacion, inversiones_amortizables)
      - request/request.json → PerfilCadenaA[].no_payroll_mensual (OPEX override per canal)
      - request/request.json → PerfilCadenaA[].inversiones_mensual (CAPEX override per canal)
      - request/request.json → PerfilCadenaA[].costos_fijos_mensual (infra override per canal)
    @confidence: HIGH
    @forbidden:
      - hardcoded_excel_values (all per-station costs come from OP parametrization)
    """

    # ──────────────────────────────────────────────────────────────
    # Formula identifiers for audit trail and reproducibility
    # ──────────────────────────────────────────────────────────────
    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        OPEX_TI = "NO_PAYROLL.OPEX_TI"  # Excel No Payroll R107
        CAPEX = "NO_PAYROLL.CAPEX"  # Excel No Payroll R186, V2-7 term-based K167/K168
        INFRAESTRUCTURA = "NO_PAYROLL.INFRAESTRUCTURA"  # arriendo+energía+vigilancia+aseo+otros
        OPEX_FIJO_ANUAL = "NO_PAYROLL.OPEX_FIJO_ANUAL"  # Excel No Payroll R107 paramétrico
        INVERSIONES_CAPEX = "NO_PAYROLL.INVERSIONES_CAPEX"  # Excel No Payroll R186
        COSTOS_FIJOS = "NO_PAYROLL.COSTOS_FIJOS"  # Excel No Payroll R248

    def __init__(self, parametros: ParametrosNoPayroll) -> None:
        self._parametros = parametros

    def calcular_para_mes(self, perfiles: List[PerfilCadenaA], mes: int) -> ResultadoNoPayroll:
        """
        Consolida los tres componentes No Payroll para el mes dado.

        Lógica de cálculo:
        - Si CUALQUIER perfil-agente tiene `no_payroll_mensual > 0` (override
          explícito del usuario, típicamente OPEX por canal del Excel V2-4),
          se usa la SUMA de overrides como OPEX TI y se mantienen capex e infra
          basados en estaciones × parámetros maestros.
        - Si NINGÚN perfil tiene override, se usa el cálculo basado en
          opex_ti_por_estacion × estaciones (modo agregado/legacy).

        Esto permite alinear el OPEX-TI con valores específicos por canal del
        Excel V2-4 (que varían mucho: WhatsApp~6M, Correo~68M, WebChat~133M)
        sin perder retrocompatibilidad con casos donde el usuario no provee override.

        Args:
            perfiles: Lista completa de perfiles (agentes + soporte).
            mes:      Número de mes del contrato.

        Returns:
            ResultadoNoPayroll con OPEX TI, CAPEX e infraestructura fija.
        """
        estaciones_capex = self._calcular_estaciones_capex(perfiles)
        estaciones_infra = self._calcular_estaciones_infra(perfiles)
        overrides_opex   = self._opex_overrides_por_canal(perfiles)
        overrides_inv    = self._inversiones_overrides_por_canal(perfiles)
        overrides_cf     = self._costos_fijos_overrides_por_canal(perfiles)

        opex_ti = (
            overrides_opex
            if overrides_opex > 0
            else self._costo_opex_ti(estaciones_infra)
        )

        # Si el usuario provee inversiones_mensual / costos_fijos_mensual por perfil
        # (Excel No payroll R186/R248), usarlos en lugar del cálculo paramétrico.
        capex = (
            overrides_inv
            if overrides_inv > 0
            else self._costo_capex(estaciones_capex, mes)
        )
        costos_fijos = (
            overrides_cf
            if overrides_cf > 0
            else self._costo_infraestructura(estaciones_infra)
        )

        _audit_trace(
            component   = "no_payroll",
            rule        = "NO_PAYROLL.opex_ti + capex + infraestructura",
            formula     = (
                "opex_ti = Σ(no_payroll_mensual) si override, "
                "else opex_ti_por_estacion × estaciones_infra; "
                "capex = capex_por_estacion × estaciones_capex (+ capex_inicial si mes=1); "
                "costos_fijos = (arriendo + energia + vigilancia + aseo + otros) × estaciones_infra"
            ),
            inputs      = {
                "estaciones_capex":      estaciones_capex,
                "estaciones_infra":      estaciones_infra,
                "overrides_opex":        overrides_opex,
                "overrides_inv":         overrides_inv,
                "overrides_cf":          overrides_cf,
                "opex_ti_por_estacion":  self._parametros.opex_ti_por_estacion,
                "capex_por_estacion":    self._parametros.capex_por_estacion,
            },
            intermediate = {
                "opex_ti":      opex_ti,
                "capex":        capex,
                "costos_fijos": costos_fijos,
            },
            result      = opex_ti + capex + costos_fijos,
            source      = "OP-NoPayroll (parametros_no_payroll), User-Input (no_payroll_mensual)",
            mes         = mes,
            formula_ids = [
                self.FORMULA_ID.OPEX_TI,
                self.FORMULA_ID.CAPEX,
                self.FORMULA_ID.INFRAESTRUCTURA,
            ],
        )

        return ResultadoNoPayroll(
            opex_ti      = opex_ti,
            capex        = capex,
            costos_fijos = costos_fijos,
        )

    def _opex_overrides_por_canal(self, perfiles: List[PerfilCadenaA]) -> float:
        """
        Suma los overrides de OPEX TI (Excel No payroll R107) por canal.

        Si el usuario provee `no_payroll_mensual` en algún perfil-agente,
        reemplaza el cálculo paramétrico. Solo perfiles es_soporte=False.
        """
        return sum(
            p.no_payroll_mensual
            for p in perfiles
            if (not p.es_soporte) and p.no_payroll_mensual > 0
        )

    def _inversiones_overrides_por_canal(self, perfiles: List[PerfilCadenaA]) -> float:
        """
        Suma los overrides de Inversiones (Excel No payroll R186) por canal.

        Usa `inversiones_mensual` del perfil-agente como override del CAPEX
        paramétrico. Solo activo cuando el usuario provee valores > 0.
        """
        return sum(
            getattr(p, "inversiones_mensual", 0.0) or 0.0
            for p in perfiles
            if (not p.es_soporte) and (getattr(p, "inversiones_mensual", 0.0) or 0.0) > 0
        )

    def _costos_fijos_overrides_por_canal(self, perfiles: List[PerfilCadenaA]) -> float:
        """
        Suma los overrides de Costos Fijos x Estación (Excel No payroll R248) por canal.

        Usa `costos_fijos_mensual` del perfil-agente como override del cálculo
        paramétrico de infraestructura. Solo activo cuando el usuario provee valores > 0.
        """
        return sum(
            getattr(p, "costos_fijos_mensual", 0.0) or 0.0
            for p in perfiles
            if (not p.es_soporte) and (getattr(p, "costos_fijos_mensual", 0.0) or 0.0) > 0
        )

    # ──────────────────────────────────────────────────────────────
    # Componentes de costo
    # ──────────────────────────────────────────────────────────────

    def _calcular_estaciones_capex(self, perfiles: List[PerfilCadenaA]) -> float:
        """Station count for CAPEX: raw FTE (Excel uses FTE for hardware)."""
        return sum(p.fte for p in perfiles if not p.es_soporte)

    def _calcular_estaciones_infra(self, perfiles: List[PerfilCadenaA]) -> float:
        """Station count for infrastructure/OPEX: FTE × pct_presencia (Excel fila 19)."""
        return sum(p.fte * p.pct_presencia for p in perfiles if not p.es_soporte)

    def _costo_opex_ti(self, estaciones: float) -> float:
        """OPEX de tecnología de la información por estación activa."""
        return self._parametros.opex_ti_por_estacion * estaciones

    def _costo_capex(self, estaciones: float, mes: int) -> float:
        """
        CAPEX de equipos y hardware.

        Modelo V2-7 (preferente): amortización term-based por ítem.
        CAPEX(mes) = Σ_items[precio_mensual × cantidad × factor] para los ítems
        cuyo plazo de diferimiento cubre el mes (mes ≤ meses). Los ítems con
        meses=1 sólo aportan en el mes 1 (origen del salto no_payroll mes1 vs mes2+).

        Modelo legacy (fallback): capex_por_estacion × estaciones, con componente
        inicial sólo en el mes 1.
        """
        items = self._parametros.inversiones_amortizables
        if items:
            return sum(
                it["precio_mensual"] * it["cantidad"] * it.get("factor", 1.0)
                for it in items
                if mes <= it["meses"]
            )

        base = self._parametros.capex_por_estacion * estaciones
        if mes == 1:
            base += self._parametros.capex_inicial_por_estacion * estaciones
        return base

    def _costo_infraestructura(self, estaciones: float) -> float:
        """
        Costos fijos de infraestructura física por estación activa.

        Incluye: arriendo de área, energía, vigilancia, aseo y otros servicios fijos.
        """
        p = self._parametros
        costo_unitario = (
            p.arriendo_por_estacion
            + p.energia_por_estacion
            + p.vigilancia_por_estacion
            + p.aseo_por_estacion
            + p.otros_fijos_por_estacion
        )
        return costo_unitario * estaciones


__all__ = ["NoPayrollCalculator"]
