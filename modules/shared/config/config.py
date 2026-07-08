"""Application configuration: resolved paths and environment settings."""

import os
from pathlib import Path

# refactor modular-pure: backend_nexa/modules/shared/infrastructure/config.py → backend_nexa/
# (pasó de infrastructure/ a modules/shared/infrastructure/ = +2 niveles; .parent x4)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
STORAGE_BASE = PROJECT_ROOT / "storage"

# Parametrization directories
PARAMETRIZATION_DIR = STORAGE_BASE / "parametrization"
HR_DIR = PARAMETRIZATION_DIR / "hr"
GN_DIR = PARAMETRIZATION_DIR / "gn"
OP_DIR = PARAMETRIZATION_DIR / "op"
FROZEN_PARAMETRIZATION_DIR = PARAMETRIZATION_DIR / "frozen"
PARAMETRIZATION_V27_DIR = PARAMETRIZATION_DIR / "v2-7"

# Certification baseline directory
BASELINES_DIR = STORAGE_BASE / "baselines" / "v2-7-certified"

# Simulation input directories
SIMULATION_INPUTS_DIR = STORAGE_BASE / "simulation_inputs"
PANEL_DIR = SIMULATION_INPUTS_DIR / "panel"
CHAIN_A_DIR = SIMULATION_INPUTS_DIR / "chain_a"
CHAIN_B_DIR = SIMULATION_INPUTS_DIR / "chain_b"
CHAIN_C_DIR = SIMULATION_INPUTS_DIR / "chain_c"

# Calculation results directory (legacy flat JSON — mantiene compatibilidad GET)
RESULTS_DIR = STORAGE_BASE / "simulation_results"

# FASE G — Directorio con estructura de traceabilidad por simulación
SIMULATIONS_DIR = STORAGE_BASE / "simulations"

ALL_STORAGE_DIRS = [
    OP_DIR,
    GN_DIR,
    HR_DIR,
    PANEL_DIR,
    CHAIN_A_DIR,
    CHAIN_B_DIR,
    CHAIN_C_DIR,
    RESULTS_DIR,
    SIMULATIONS_DIR,
]

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}

# ---------------------------------------------------------------------------
# Excel upload security limits — all configurable via environment variables.
# ---------------------------------------------------------------------------
MAX_EXCEL_UPLOAD_BYTES: int = int(os.getenv("MAX_EXCEL_UPLOAD_BYTES", str(5 * 1024 * 1024)))        # 5 MB
MAX_EXCEL_UNCOMPRESSED_BYTES: int = int(os.getenv("MAX_EXCEL_UNCOMPRESSED_BYTES", str(100 * 1024 * 1024)))  # 100 MB
MAX_EXCEL_COMPRESSION_RATIO: float = float(os.getenv("MAX_EXCEL_COMPRESSION_RATIO", "50"))
MAX_EXCEL_SHEETS: int = int(os.getenv("MAX_EXCEL_SHEETS", "30"))
MAX_EXCEL_ROWS_PER_SHEET: int = int(os.getenv("MAX_EXCEL_ROWS_PER_SHEET", "20000"))
MAX_EXCEL_COLUMNS_PER_SHEET: int = int(os.getenv("MAX_EXCEL_COLUMNS_PER_SHEET", "200"))
MAX_EXCEL_CELLS: int = int(os.getenv("MAX_EXCEL_CELLS", "500000"))
MAX_EXCEL_CELL_LENGTH: int = int(os.getenv("MAX_EXCEL_CELL_LENGTH", "2048"))

# ---------------------------------------------------------------------------
# OP parametrization — ICA rate anomaly detection threshold
# ---------------------------------------------------------------------------
# MAX_TASA_ICA_DECIMAL es un TECHO TÉCNICO para detectar anomalías extremas.
# NO es el rango normal de tasas ICA, ni el límite legal.
#
# Rango de negocio esperado (referencia):
#   ~0.004 – 0.014  (0.4 % – 1.4 %)   ← tasas municipales típicas en Colombia
#
# Umbral bloqueante (este parámetro):
#   0.05  (5 %)                          ← muy superior al rango normal;
#                                          cualquier valor mayor indica error
#                                          de unidades en el Excel fuente.
#
# Comportamiento:
#   ICA == "Tasa"   AND valor > umbral  →  error  (bloquea el upload)
#   ICA != "Tasa"   AND valor > umbral  →  warning (subcategorías como Bomberos)
#
# Un valor como 0.6 (= 60 %) es imposible como tasa ICA municipal y es rechazado.
MAX_TASA_ICA_DECIMAL: float = float(os.getenv("MAX_TASA_ICA_DECIMAL", "0.05"))


def ensure_storage_dirs():
    for d in ALL_STORAGE_DIRS:
        d.mkdir(parents=True, exist_ok=True)
