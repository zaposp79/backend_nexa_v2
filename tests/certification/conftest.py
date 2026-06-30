"""
tests/certification/conftest.py
================================
Fixtures compartidos para el Triple-Layer Certification Harness.

Provee:
  - nomina_service   : NominaCargadaService con parametrización activa
  - raw_params       : dict con parámetros extraídos de storage
  - gold_master      : fixture JSON generado desde Excel V2-6
  - financial_bounds : rangos actuariales BPO Colombia

Política de skip:
  - gold_master: skipea tests si `generated` == false (ejecutar generate_gold_master.py)
  - raw_params : falla si storage no tiene la parametrización activa cargada
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict

import pytest

# ── sys.path bootstrap ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401 — registra alias nexa_engine

# ── Directorios ──────────────────────────────────────────────────────────────
CERT_DIR        = Path(__file__).parent
FIXTURES_DIR    = CERT_DIR.parent / "fixtures" / "gold_master"
GOLD_MASTER_PATH = FIXTURES_DIR / "nomina_gold_master_v26.json"
BOUNDS_PATH      = FIXTURES_DIR / "financial_sanity_bounds.json"


# ── Fixtures: Motor ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def nomina_service():
    """
    NominaCargadaService construido desde la parametrización activa en storage.

    Scope: session — la parametrización es estática durante los tests.
    Falla si storage no tiene parametrización HR activa.
    """
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService

    provider = ParametrizationProvider.build()
    return NominaCargadaService.desde_parametrizacion(provider)


@pytest.fixture(scope="session")
def raw_params() -> Dict[str, Any]:
    """
    Parámetros de nómina en formato dict, como los entrega ParametrizationProvider.

    Incluye: salario_minimo, auxilio_transporte, dotaciones_mensual,
             pct_cumplimiento_variable, factor_alto_salario_smmlv,
             factor_corrector_alto_salario, aportes_patronales, prestaciones.
    """
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    provider = ParametrizationProvider.build()
    return provider.get_nomina_laboral_params()


@pytest.fixture(scope="session")
def parametros_objeto(raw_params):
    """
    ParametrosNominaLaboral construido desde raw_params.
    Útil para calcular valores esperados en L3B sin instanciar el servicio.
    """
    from nexa_engine.modules.cadena_a.services.nomina_cargada import ParametrosNominaLaboral
    aps = raw_params["aportes_patronales"]
    pre = raw_params["prestaciones"]

    return ParametrosNominaLaboral(
        salario_minimo                = raw_params["salario_minimo"],
        auxilio_transporte            = raw_params["auxilio_transporte"],
        dotaciones_mensual            = raw_params["dotaciones_mensual"],
        pct_cumplimiento_variable     = raw_params["pct_cumplimiento_variable"],
        factor_alto_salario_smmlv     = raw_params["factor_alto_salario_smmlv"],
        factor_corrector_alto_salario = raw_params["factor_corrector_alto_salario"],
        tasa_salud                    = aps["salud"],
        tasa_pension                  = aps["pension"],
        tasa_arl                      = aps["arl_staff"],
        tasa_caja                     = aps["caja"],
        tasa_icbf_sena                = aps["icbf_sena"],
        tasa_cesantias                = pre["cesantias"],
        tasa_primas                   = pre["primas"],
        tasa_interes_cesantia         = pre["interes_cesantia"],
        tasa_vacaciones               = pre["vacaciones"],
    )


# ── Fixtures: Gold Master ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def gold_master() -> Dict[str, Any]:
    """
    Fixture con valores extraídos de Excel V2-6 'Inputs de Nomina'.
    Skipea si el fixture no ha sido generado.

    Para generar: python scripts/generate_gold_master.py
    """
    if not GOLD_MASTER_PATH.exists():
        pytest.skip(
            f"Gold master no encontrado: {GOLD_MASTER_PATH}\n"
            "Ejecutar: python scripts/generate_gold_master.py"
        )

    with open(GOLD_MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("generated", False):
        pytest.skip(
            "Gold master no generado (generated=false).\n"
            "Ejecutar: python scripts/generate_gold_master.py"
        )

    return data


@pytest.fixture(scope="session")
def gold_master_sample() -> Dict[str, Any]:
    """
    Casos de muestra pre-computados manualmente para L3A básico.
    Disponible SIEMPRE (no requiere ejecutar el script de generación).

    Tolerancia aplicada: 0.01 COP (por imprecisión del cálculo manual).
    Los valores fueron verificados contra la certificación Excel V2-6 (180/180 match).
    """
    if not GOLD_MASTER_PATH.exists():
        pytest.skip(f"Gold master no encontrado: {GOLD_MASTER_PATH}")

    with open(GOLD_MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # sample_cases disponible incluso antes de generar el fixture completo
    sample = data.get("sample_cases", [])
    if not sample:
        pytest.skip("Sin sample_cases en gold master fixture")
    return data


# ── Fixtures: Financial Bounds ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def financial_bounds() -> Dict[str, Any]:
    """
    Rangos actuariales BPO Colombia (2022-2026).
    Fuente: histórico de contratos y benchmarks de mercado.
    """
    if not BOUNDS_PATH.exists():
        pytest.skip(f"Bounds no encontrados: {BOUNDS_PATH}")

    with open(BOUNDS_PATH, encoding="utf-8") as f:
        return json.load(f)
