"""
nexa_engine/calculators/costos_totales.py
==========================================
Calculador de costos operativos consolidados — Capa 7 del pipeline.

Responsabilidad
---------------
Agregar los costos de todas las cadenas (A, B y C) en un único objeto
de costos operativos totales por mes.

Actúa como coordinador (orquestador): no contiene lógica de negocio propia,
sino que delega en los calculadores especializados de cada cadena y consolida
sus resultados en CostosTotalesMes.

Capas que coordina
------------------
  Capa 2: NominaCalculator     → payroll Cadena A
  Capa 3: NoPayrollCalculator  → infraestructura y TI Cadena A
  Capa 4: CadenaBCalculator    → plataforma digital
  Capa 6: CadenaCCalculator    → integración IA

Consume
-------
  - NominaCalculator, NoPayrollCalculator, CadenaBCalculator, CadenaCCalculator
  - Lista de PerfilCadenaA (para los calculadores de Cadena A)

Produce
-------
  CostosTotalesMes con payroll, no-payroll, costo_b y costo_c del mes dado.
"""

from __future__ import annotations

from typing import List

from nexa_engine.modules.cadena_b.reglas import CadenaBCalculator
from nexa_engine.modules.cadena_c.reglas import CadenaCCalculator
from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
from nexa_engine.modules.calculator_motor.formulas.no_payroll import NoPayrollCalculator
from nexa_engine.modules.shared.models import (
    CostosTotalesMes,
    PerfilCadenaA,
)


class CostosTotalesCalculator:
    """
    Agrega los costos de todas las cadenas para producir el costo operativo total del mes.
    """

    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        PAYROLL_A = "COSTOS_TOTALES.PAYROLL_A"
        NO_PAYROLL_A = "COSTOS_TOTALES.NO_PAYROLL_A"
        COSTO_B = "COSTOS_TOTALES.COSTO_B"
        COSTO_C = "COSTOS_TOTALES.COSTO_C"
        TOTAL_MENSUAL = "COSTOS_TOTALES.TOTAL_MENSUAL"

    def __init__(
        self,
        nomina_calc: NominaCalculator,
        no_payroll_calc: NoPayrollCalculator,
        cadena_b_calc: CadenaBCalculator,
        cadena_c_calc: CadenaCCalculator,
    ) -> None:
        self._nomina      = nomina_calc
        self._no_payroll  = no_payroll_calc
        self._cadena_b    = cadena_b_calc
        self._cadena_c    = cadena_c_calc

    def calcular_para_mes(self, perfiles_a: List[PerfilCadenaA], mes: int) -> CostosTotalesMes:
        """
        Calcula los costos operativos totales de todas las cadenas para el mes dado.

        Args:
            perfiles_a: Lista de perfiles de Cadena A (agentes + staff de soporte).
            mes:        Número de mes del contrato (1-based).

        Returns:
            CostosTotalesMes con payroll, no-payroll, costo B y costo C del mes.
        """
        nomina      = self._nomina.calcular_para_mes(perfiles_a, mes)
        no_payroll  = self._no_payroll.calcular_para_mes(perfiles_a, mes)
        cadena_b    = self._cadena_b.calcular_para_mes(mes)
        cadena_c    = self._cadena_c.calcular_para_mes(mes)

        return CostosTotalesMes(
            mes          = mes,
            payroll_a    = nomina.total,
            no_payroll_a = no_payroll.total,
            costo_b      = cadena_b.total,
            costo_c      = cadena_c.total_pyg,  # P&G display (Vision P&G row 55)
            costo_c_fin  = cadena_c.total,       # financial base (ICA/GMF includes hitl/equipo/opex_var)
        )
