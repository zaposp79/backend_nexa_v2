"""
scripts/excel_map_common.py
===========================
Campos y mapeos compartidos entre múltiples hojas del Excel V2-8.

Fuente de verdad de paridad: excel/Nexa - Pricing - Simulador - V2-8.xlsx
Request base:               request/request.json

Stage 1 (harness + delta): este módulo solo declara constantes y helpers de
comparación. NO contiene lógica de negocio ni evalúa fórmulas Excel.
"""
from __future__ import annotations

from pathlib import Path

# Raíz de backend_nexa (parent del directorio scripts/)
BACKEND_ROOT = Path(__file__).resolve().parent.parent

EXCEL_V28_PATH = BACKEND_ROOT / "excel" / "Nexa - Pricing - Simulador - V2-8.xlsx"
EXCEL_V27_PATH = BACKEND_ROOT / "excel" / "Nexa - Pricing - Simulador - V2-7.xlsx"
REQUEST_PATH = BACKEND_ROOT / "request" / "request.json"

# Hash del workbook V2-7 con el que se certificó la paridad del backend.
# Fuente: tests/parity/excel_oracle_v2_7_full.json::workbook_sha256
# Gate: si el V2-7 actual no coincide -> KILL_SWITCH V27_DRIFT_DETECTED.
EXPECTED_V27_SHA256 = (
    "5fb7174f998356c1fdc92315d391cd1f09294a058e4916e9c03f0cb0f10e4db0"
)

# --- Clasificación de hojas: motor vs vista (poblar en Fase 1) ---
# motor  = cálculo base que el motor produce y persiste
# vista  = agregación/transformación/presentación leída por un endpoint
SHEET_TYPE: dict[str, str] = {
    # Inputs / parametrización (consumidos por el motor)
    "Panel de Control General": "motor",
    "Condiciones Cadena A": "motor",
    "Condiciones Cadena B": "motor",
    "Condiciones Cadena C": "motor",
    "Inputs de Nomina": "motor",
    "Listas Desplegables": "motor",
    "Hoja Maestra Escenarios": "motor",
    # Cálculo base
    "Nomina Loaded": "motor",
    "Tasas, TRM, Polizas": "motor",
    "Rot, Ausent y Rentabilidad": "motor",
    "No payroll": "motor",
    "Costo Fijo": "motor",
    "Costo Variable": "motor",
    "Costo Cadena C": "motor",
    "Costos Totales": "motor",
    "Pólizas - Costo Financiacion": "motor",
    "Riesgo": "motor",
    # Vistas (salida)
    "Visión P&G": "vista",
    "Visión Imprimible": "vista",
    "Vision Cost To Serve": "vista",
    "Vision Tarifas_Modelo_Cobro": "vista",
    "Visiones": "vista",
    "Graficos": "vista",
}

# --- Inputs request -> celda Excel (poblar incrementalmente) ---
COMMON_INPUT_MAP: dict[str, dict] = {}

# --- Named ranges (poblar en Fase 1) ---
NAMED_RANGES: dict[str, str] = {}

# --- Inventario de archivos de configuración / parametrización ---
# NOTA: business rules NO viven en config/business_rules/ sino en
# modules/shared/config/business_rules/ (desviación vs prompt rev7).
CONFIG_FILES_INVENTORY: list[str] = [
    "modules/shared/config/business_rules/riesgo.yaml",
    "modules/shared/config/business_rules/margenes.yaml",
    "modules/shared/config/business_rules/politicas_comerciales.yaml",
    "modules/shared/config/business_rules/operaciones.yaml",
    "modules/calculator_motor/constants/global_constants.py",
]

# --- Mapeo config path -> celda Excel (poblar en Fase 3) ---
CONFIG_TO_EXCEL_MAP: dict[str, dict] = {}

# --- Política por archivo de configuración ---
CONFIG_FILE_POLICY: dict[str, str] = {}

# --- Tolerancias ---
TOL_MONETARY = 0.01
TOL_RATE = 1e-6
TOL_COUNT = 0
TOL_SCALE_PCT = 1e-4

# --- Detección de SCALE_MISMATCH por potencia de 10 ---
SCALE_FACTORS = [1e-4, 1e-3, 1e-2, 1e-1, 1e1, 1e2, 1e3, 1e4]

# --- Prefijos de error Excel (cacheados) ---
EXCEL_ERROR_PREFIXES = (
    "#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!",
)


def is_scale_mismatch(
    valor_backend: float, valor_excel: float, tol: float = TOL_RATE,
) -> tuple[bool, float | None]:
    """Detecta si backend y excel difieren solo por un factor potencia de 10."""
    if valor_excel == 0:
        return (False, None)
    for f in SCALE_FACTORS:
        if abs(valor_backend - valor_excel * f) <= tol * max(1.0, abs(valor_excel * f)):
            return (True, f)
    return (False, None)


def sha256_of(path: Path) -> str:
    """SHA256 hex de un archivo (para el gate de drift V2-7)."""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
