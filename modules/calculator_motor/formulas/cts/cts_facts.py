"""
Read-model interno para CostToServeCalculator.

Contiene los resultados finos de Nomina/NoPayroll/CadenaB pre-computados
por el engine, eliminando la necesidad de que CostToServeCalculator
instancie o llame a calculadoras core.

No es un contrato público de API — solo transporte interno engine→CTS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from nexa_engine.modules.shared.models.results import (
    ResultadoCadenaB,
    ResultadoNomina,
    ResultadoNoPayroll,
)


@dataclass
class CanalCTSFacts:
    """Resultados pre-computados para un canal específico de Cadena A.

    nomina_por_mes: todos los perfiles del canal (agentes + soporte).
    no_payroll_por_mes: solo perfiles agente del canal (sin soporte).
    Coincide con la semántica del workbook (Nomina Loaded rows 93-99 vs No Payroll rows 107-113).
    """
    canal: str
    modalidad: str
    fte_del_canal: float
    nomina_por_mes: List[ResultadoNomina] = field(default_factory=list)
    no_payroll_por_mes: List[ResultadoNoPayroll] = field(default_factory=list)


@dataclass
class CostToServeFacts:
    """Read-model interno: resultados finos pre-computados por el engine.

    Transporte de datos del engine al CostToServeCalculator.
    El engine computa estos valores una sola vez usando las calculadoras core;
    CostToServeCalculator los consume sin re-calcular.

    nomina_por_mes[i]: ResultadoNomina para todos los perfiles, mes i+1.
    no_payroll_por_mes[i]: ResultadoNoPayroll para todos los perfiles, mes i+1.
    cadena_b_por_mes[i]: ResultadoCadenaB, mes i+1.
    canales: facts por canal (canal, modalidad, fte, nomina/no_payroll mensuales).
    """
    nomina_por_mes: List[ResultadoNomina] = field(default_factory=list)
    no_payroll_por_mes: List[ResultadoNoPayroll] = field(default_factory=list)
    cadena_b_por_mes: List[ResultadoCadenaB] = field(default_factory=list)
    canales: List[CanalCTSFacts] = field(default_factory=list)


__all__ = ["CanalCTSFacts", "CostToServeFacts"]
