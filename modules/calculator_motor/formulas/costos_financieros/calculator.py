"""
nexa_engine/calculators/costos_financieros.py
===============================================
Calculador de costos financieros y fiscales — Capa 8 del pipeline.

Responsabilidad
---------------
Calcular los cuatro componentes financieros que se aplican sobre el costo
operativo del mes: ICA, GMF, pólizas y financiación.

Cada componente tiene una base de cálculo diferente y deben calcularse
en el orden correcto por sus dependencias:

  1. Financiación  → base: costo operativo
  2. Pólizas       → base: costo + financiación (normalizado por factor de márgenes)
  3. ICA           → base: costo/factor_márgenes + pólizas + financiación  [con gross-up]
  4. GMF           → base: costo + pólizas + financiación                  [sin gross-up]

El gross-up del ICA refleja que el impuesto recae sobre el ingreso neto
equivalente, no directamente sobre el costo.

Consume
-------
  - PanelDeControl: tasas ICA, GMF, tasa de financiación, período de pago,
                    márgenes del deal
  - IParametrizationProvider: tabla de pólizas por mes, factor de período de pago

Produce
-------
  CostosFinancierosMes con los cuatro componentes calculados para el mes dado.
"""

from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
from nexa_engine.modules.shared.models import CostosFinancierosMes, PanelDeControl, PolizaContractual
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider


class CostosFinancierosCalculator:
    """
    Calcula los cuatro componentes financieros sobre el costo operativo del mes.

    Orden de dependencia entre componentes:
      1. Financiacion es independiente -> se calcula primero.
      2. Polizas dependen de la financiacion.
      3. ICA depende de polizas y financiacion (gross-up).
      4. GMF depende de polizas y financiacion (sin gross-up).

    FASE D / Gap C3 + TASK 2 -- Polizas del usuario (distincion contractual):
      - polizas_usuario = None  -> usuario NO configuro; usar storage/parametrization
      - polizas_usuario = []    -> usuario EXPLICITAMENTE pidio cero polizas; costo = 0
      - polizas_usuario = [...] -> usuario EXPLICITAMENTE pidio estas polizas; usarlas

    Esta distincion es critica para auditoria financiera: no podemos confundir
    "el usuario no eligio" con "el usuario eligio vacio".

    @excel_lineage:
      version: V2-8
      sheet: Polizas - Costo Financiacion
      cells: [H69 (polizas total), H68 (comision_admin total),
              E222 (comision_administracion formula: costo_a/factor_margenes x tasa),
              rows 12:163 (pure per_canal insurance premiums),
              rows 173:185 (per_canal polizas marked per_canal=True),
              row 188 (comAdm: pct_poliza x 1.42),
              rows 198:327 (activado polizas per cadena)]
      concept: costos_financieros_mes
    @runtime_sources:
      - request/request.json -> PanelDeControl (tasa_ica, tasa_gmf, tasa_mensual_financ,
        periodo_pago_dias, activa_financiacion, margen, margen_b, margen_c,
        op_cont, com_cont, markup, descuento, tasa_comision_administracion)
      - storage/parametrization/op -> IParametrizationProvider.get_factor_periodo()
        (factor for payment period: maps Polizas - Costo Financiacion period table)
      - storage/parametrization/op -> IParametrizationProvider.get_tasa_polizas_efectiva()
        (insurance rate for legacy/fallback path)
      - request/request.json -> PolizaContractual[] (user-provided polizas override)
    @confidence: HIGH
    @forbidden:
      - hardcoded_excel_values (all rates come from Panel or OP parametrization)
    """

    # ──────────────────────────────────────────────────────────────
    # Formula identifiers for audit trail and reproducibility
    # ──────────────────────────────────────────────────────────────
    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        FINANCIACION = "COSTOS_FINANCIEROS.FINANCIACION"  # Costo de financiación (período adelantado)
        POLIZAS = "COSTOS_FINANCIEROS.POLIZAS"  # Prima de pólizas de seguros
        ICA = "COSTOS_FINANCIEROS.ICA"  # Impuesto Industria y Comercio (gross-up)
        GMF = "COSTOS_FINANCIEROS.GMF"  # Gravamen Movimientos Financieros (sin gross-up)
        COMISION_ADMINISTRACION = "COSTOS_FINANCIEROS.COMISION_ADMINISTRACION"  # Solo Cadena A
        POLIZAS_PER_CADENA = "COSTOS_FINANCIEROS.POLIZAS_PER_CADENA"  # Distribución A/B/C (contractual)
        ICA_PER_CADENA = "COSTOS_FINANCIEROS.ICA_PER_CADENA"  # Distribución A/B/C
        GMF_PER_CADENA = "COSTOS_FINANCIEROS.GMF_PER_CADENA"  # Distribución A/B/C

    def __init__(
        self,
        panel: PanelDeControl,
        parametrizacion: IParametrizationProvider,
        polizas_usuario: Optional[List[PolizaContractual]] = None,
    ) -> None:
        self._panel           = panel
        self._parametrizacion = parametrizacion
        # TASK 2: Mantener la distinción contractual en el calculador.
        # Nunca convertir None → [] o [] → None. Solo almacenar tal como viene.
        self._polizas_usuario: Optional[List[PolizaContractual]] = (
            None if polizas_usuario is None else list(polizas_usuario)
        )

    def calcular(  # noqa: C901 — instrumented with audit trace
        self,
        costo_operativo: float,
        mes: int,
        costo_operativo_mes_anterior: float | None = None,
        costo_a: float | None = None,
        costo_b: float | None = None,
        costo_c: float | None = None,
    ) -> CostosFinancierosMes:
        """
        Calcula todos los costos financieros para el costo operativo del mes dado.

        Args:
            costo_operativo: Suma de costos de Cadena A + B + C para el mes actual.
            mes:             Número de mes del contrato (activa pólizas correspondientes).
            costo_operativo_mes_anterior: Costo del mes anterior. Si se proporciona,
                                           la financiación se calcula sobre este (convención
                                           Excel V2-4: TC adelanta capital del mes pasado
                                           que cliente paga ahora). Si es None, se usa
                                           el costo del mes actual (convención legacy).
                                           Para mes=1, debe pasarse 0.0 para alinear con Excel.
            costo_a:         Costo de Cadena A (solo) para el mes actual.
                             Base de cálculo de Comisión de Administración (Panel!C45=True,
                             D45=blank, E45=False). Si es None, se usa costo_operativo total
                             (backward-compat con versiones anteriores a V2-5).

        Returns:
            CostosFinancierosMes con financiación, pólizas, ICA, GMF y comisión adm calculados.
        """
        factor_margenes   = ProfitabilityCalculator.calcular_factor_margenes(self._panel)
        factor_periodo    = self._parametrizacion.get_factor_periodo(self._panel.periodo_pago_dias)

        base_financiacion = (
            costo_operativo_mes_anterior
            if costo_operativo_mes_anterior is not None
            else costo_operativo
        )
        financiacion = self._calcular_financiacion(base_financiacion, factor_periodo)
        base_a = costo_a if costo_a is not None else costo_operativo
        base_b = costo_b if costo_b is not None else 0.0
        base_c = costo_c if costo_c is not None else 0.0

        if self._polizas_usuario is not None:
            meses_contrato = self._panel.meses_contrato
            polizas_vigentes = [
                p for p in self._polizas_usuario
                if not (mes > meses_contrato and not p.aplica_extension)
            ]

            # Separate per-canal polizas (insurance premiums) from comAdm.
            # Per-canal: marked per_canal=True (Pólizas sheet rows 173-185).
            # ComAdm: marked is_comision_administracion=True (Pólizas sheet row 188).
            # tasa_comAdm = pct_poliza × 1.42 (Excel D188 formula).
            comadm_poliza = next(
                (p for p in polizas_vigentes if p.is_comision_administracion and p.activa),
                None
            )
            tasa_comadm = comadm_poliza.pct_poliza * 1.42 if comadm_poliza else 0.0

            pure_pol = [
                p for p in polizas_vigentes
                if p.per_canal and not p.is_comision_administracion
            ]
            tasa_pure_a = sum(p.tasa_efectiva for p in pure_pol if p.aplica_a)
            tasa_pure_b = sum(p.tasa_efectiva for p in pure_pol if p.aplica_b)
            tasa_pure_c = sum(p.tasa_efectiva for p in pure_pol if p.aplica_c)

            # Per-cadena factor_billing (gross-up denominators).
            fm_a = ProfitabilityCalculator.calcular_factor_billing(
                self._panel.margen,   self._panel.op_cont, self._panel.com_cont,
                self._panel.markup,   self._panel.descuento,
            )
            fm_b = ProfitabilityCalculator.calcular_factor_billing(
                self._panel.margen_b, self._panel.op_cont, self._panel.com_cont,
                self._panel.markup,   self._panel.descuento,
            )
            fm_c = ProfitabilityCalculator.calcular_factor_billing(
                self._panel.margen_c, self._panel.op_cont, self._panel.com_cont,
                self._panel.markup,   self._panel.descuento,
            )

            # Proportional financing split per cadena.
            total_base_fin = max(base_a + base_b + base_c, 0.0)
            fin_a = financiacion * (base_a / total_base_fin) if total_base_fin > 0 else 0.0
            fin_b = financiacion * (base_b / total_base_fin) if total_base_fin > 0 else 0.0
            fin_c = financiacion * (base_c / total_base_fin) if total_base_fin > 0 else 0.0

            # Pure insurance premiums per cadena: tasa × (costo + fin) / fm.
            pure_pol_a = self._calcular_polizas(base_a, fin_a, tasa_pure_a, fm_a)
            pure_pol_b = self._calcular_polizas(base_b, fin_b, tasa_pure_b, fm_b)
            pure_pol_c = self._calcular_polizas(base_c, fin_c, tasa_pure_c, fm_c)
            pure_pol_total = pure_pol_a + pure_pol_b + pure_pol_c

            # Comisión de Administración per cadena: (costo + fin) / fm × tasa_comAdm.
            # Pólizas sheet D188: tasa = pct_poliza × 1.42.
            comision_admin_a = (base_a + fin_a) / fm_a * tasa_comadm if fm_a > 0 else 0.0
            comadm_b = (base_b + fin_b) / fm_b * tasa_comadm if fm_b > 0 else 0.0
            comadm_c = (base_c + fin_c) / fm_c * tasa_comadm if fm_c > 0 else 0.0
            comision_adm = comision_admin_a + comadm_b + comadm_c

            # ICA per cadena: (costo/fm + pure_pol + fin) × tasa_ica.
            ica_a = self._calcular_ica(base_a, pure_pol_a, fin_a, fm_a)
            ica_b = self._calcular_ica(base_b, pure_pol_b, fin_b, fm_b)
            ica_c = self._calcular_ica(base_c, pure_pol_c, fin_c, fm_c)
            ica = ica_a + ica_b + ica_c

            # GMF per cadena: (costo + pure_pol + fin) × tasa_gmf.
            gmf_a = self._calcular_gmf(base_a, pure_pol_a, fin_a)
            gmf_b = self._calcular_gmf(base_b, pure_pol_b, fin_b)
            gmf_c = self._calcular_gmf(base_c, pure_pol_c, fin_c)
            gmf = gmf_a + gmf_b + gmf_c

            # polizas (H69) = ICA + GMF + pure_pol_a + comAdm_a + pure_pol_b + comAdm_b + pure_pol_c.
            # Matches Excel Pólizas sheet rows 12:163 + 198:327 ("Activado").
            # Note: comAdm_c (rows 333:351) is outside range 198:327, so NOT included here.
            polizas = ica + gmf + pure_pol_a + comision_admin_a + pure_pol_b + comadm_b + pure_pol_c
            polizas_a = pure_pol_a
            polizas_b = pure_pol_b
            polizas_c = pure_pol_c

            # VT cadena-A financials: regular ICA + GMF + pure per_canal polizas.
            # Extended months (aplica_extension=True) are handled in vision_tarifas.py.
            costo_financiero_vt_cadena_a = ica_a + gmf_a + pure_pol_a

        else:
            tasa_polizas = self._parametrizacion.get_tasa_polizas_efectiva(mes)
            polizas = self._calcular_polizas(costo_operativo, financiacion,
                                             tasa_polizas, factor_margenes)
            polizas_a = polizas_b = polizas_c = 0.0
            ica = self._calcular_ica(costo_operativo, polizas, financiacion, factor_margenes)
            gmf = self._calcular_gmf(costo_operativo, polizas, financiacion)
            base_comision = costo_a if costo_a is not None else costo_operativo
            comision_adm = self._calcular_comision_administracion(base_comision, factor_margenes)
            costo_financiero_vt_cadena_a = 0.0

        _audit_trace(
            component="costos_financieros",
            rule="V2-7.per_cadena: ICA+GMF+pure_pol+comAdm_a+comAdm_b=H69; comAdm_total=H68",
            formula=("financiacion = costo_mes_anterior × tasa × factor_periodo;"
                     " pure_pol_X = tasa_pure × (costo_X+fin_X)/fm_X;"
                     " ica_X = (costo_X/fm_X + pure_pol_X + fin_X) × tasa_ica;"
                     " gmf_X = (costo_X + pure_pol_X + fin_X) × tasa_gmf;"
                     " comAdm_X = (costo_X+fin_X)/fm_X × (pct_poliza_comAdm × 1.42);"
                     " polizas(H69) = ica+gmf+pure_pol_a+comAdm_a+pure_pol_b+comAdm_b+pure_pol_c;"
                     " comAdm_total(H68) = comAdm_a+comAdm_b+comAdm_c"),
            inputs={
                "costo_operativo": costo_operativo,
                "costo_a": costo_a, "costo_b": costo_b, "costo_c": costo_c,
                "costo_mes_anterior": costo_operativo_mes_anterior,
                "tasa_ica": self._panel.tasa_ica,
                "tasa_gmf": self._panel.tasa_gmf,
            },
            intermediate={
                "financiacion": financiacion,
                "polizas": polizas,
                "ica": ica,
                "gmf": gmf,
                "comision_administracion": comision_adm,
            },
            result=financiacion + polizas + ica + gmf + comision_adm,
            source="OP-Poliza (per_canal/is_comAdm flags), Panel.tasa_ica/gmf/financ",
            mes=mes,
            formula_ids=[
                self.FORMULA_ID.FINANCIACION,
                self.FORMULA_ID.POLIZAS,
                self.FORMULA_ID.ICA,
                self.FORMULA_ID.GMF,
                self.FORMULA_ID.COMISION_ADMINISTRACION,
                self.FORMULA_ID.POLIZAS_PER_CADENA,
                self.FORMULA_ID.ICA_PER_CADENA,
                self.FORMULA_ID.GMF_PER_CADENA,
            ],
        )
        _has_user_polizas = self._polizas_usuario is not None
        _comision_admin_a = comision_admin_a if _has_user_polizas else 0.0
        _costo_financiero_vt_cadena_a = costo_financiero_vt_cadena_a if _has_user_polizas else 0.0
        return CostosFinancierosMes(
            financiacion            = financiacion,
            polizas                 = polizas,
            polizas_a               = polizas_a,
            polizas_b               = polizas_b,
            polizas_c               = polizas_c,
            ica                     = ica,
            ica_a                   = ica_a if _has_user_polizas else 0.0,
            ica_b                   = ica_b if _has_user_polizas else 0.0,
            ica_c                   = ica_c if _has_user_polizas else 0.0,
            gmf                     = gmf,
            gmf_a                   = gmf_a if _has_user_polizas else 0.0,
            gmf_b                   = gmf_b if _has_user_polizas else 0.0,
            gmf_c                   = gmf_c if _has_user_polizas else 0.0,
            comision_administracion  = comision_adm,
            comision_admin_cadena_a  = _comision_admin_a,
            comision_admin_cadena_b  = comadm_b if _has_user_polizas else 0.0,
            comision_admin_cadena_c  = comadm_c if _has_user_polizas else 0.0,
            costo_financiero_vt_cadena_a = _costo_financiero_vt_cadena_a,
            # EXCEL V2-8: per-cadena proportional financing split for HME ingreso base.
            fin_a                   = fin_a if _has_user_polizas else 0.0,
            fin_b                   = fin_b if _has_user_polizas else 0.0,
            fin_c                   = fin_c if _has_user_polizas else 0.0,
        )

    # ──────────────────────────────────────────────────────────────
    # Componentes financieros — un método por componente
    # ──────────────────────────────────────────────────────────────

    def _calcular_financiacion(self, costo_operativo: float,
                                factor_periodo: int) -> float:
        """
        Costo de financiación del período de crédito al cliente.

        Financiación = período_meses × tasa_mensual × costo_operativo.
        Solo aplica si el deal tiene financiación activa.
        """
        if not self._panel.activa_financiacion:
            return 0.0
        return factor_periodo * self._panel.tasa_mensual_financ * costo_operativo

    def _calcular_polizas(self, costo_operativo: float, financiacion: float,
                           tasa_polizas: float, factor_margenes: float) -> float:
        """
        Prima de pólizas de seguros del período.

        Las pólizas se calculan sobre el ingreso bruto equivalente (costo +
        financiación normalizado por factor de márgenes), no sobre el costo directo.
        """
        return (
            tasa_polizas
            * (costo_operativo + financiacion)
            / factor_margenes
        )

    def _calcular_ica(self, costo_operativo: float, polizas: float,
                       financiacion: float, factor_margenes: float) -> float:
        """
        Impuesto de Industria y Comercio (ICA).

        El ICA aplica gross-up: la base es el ingreso neto equivalente
        (costo/factor_márgenes) más los costos financieros ya calculados.
        Esto refleja que el impuesto recae sobre el ingreso, no el costo.
        """
        base_ingreso_neto = (
            (costo_operativo / factor_margenes)
            + polizas
            + financiacion
        )
        return base_ingreso_neto * self._panel.tasa_ica

    def _calcular_gmf(self, costo_operativo: float, polizas: float,
                       financiacion: float) -> float:
        """
        Gravamen a los Movimientos Financieros (GMF / 4×1000).

        El GMF no tiene gross-up: aplica directamente sobre el flujo de caja
        total (costo operativo + costos financieros ya calculados).
        """
        return (costo_operativo + polizas + financiacion) * self._panel.tasa_gmf

    def _calcular_comision_administracion(
        self, costo_a: float, factor_margenes: float
    ) -> float:
        """
        GAP-PYG-3 / BUG-1 FIX: Comisión de Administración (Panel!C45=True, G45 = 1.18%).

        Aplica EXCLUSIVAMENTE a Cadena A (Panel!C45=True, D45=blank/False, E45=False).
        Fórmula Excel Pólizas E222:
            base = costo_a / factor_margenes  (ingreso bruto equivalente de Cadena A)
            comision = base × tasa_comision_administracion

        Args:
            costo_a: Costo operativo de Cadena A únicamente (payroll_a + no_payroll_a).
            factor_margenes: (1-margen)×(1-op_cont)×(1-com_cont)×(1-markup)×(1+descuento).

        H-07 FIX: Apply cop_round() for Excel parity.
        """
        from nexa_engine.modules.shared.precision import cop_round

        if self._panel.tasa_comision_administracion <= 0:
            return 0.0
        ingreso_bruto_a = costo_a / factor_margenes if factor_margenes > 0 else 0.0
        result = ingreso_bruto_a * self._panel.tasa_comision_administracion
        return cop_round(result)  # H-07: Excel-compatible rounding


__all__ = ["CostosFinancierosCalculator"]
