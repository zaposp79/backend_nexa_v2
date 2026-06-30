#!/usr/bin/env bash
# scripts/run_core_tests.sh
# -----------------------------------------------------------------------------
# Ejecuta la suite *core* de tests (WAVE 7+).
#
# Incluye:
#   - tests/parity (39 tests Excel V2-7)
#   - tests/baselines (16 tests regression V2-7-certified)
#   - tests/unit + tests/integration vivos (sin marker `legacy`)
#
# Excluye:
#   - Tests marcados @pytest.mark.legacy (ver docs/v27/WAVE7_TRIAGE.md)
#   - tests/test_parametrization_phase_1_2.py (ImportError nexa_engine)
#
# Uso:
#   ./scripts/run_core_tests.sh                 # quiet mode
#   ./scripts/run_core_tests.sh -v              # verbose
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [[ -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

exec python -m pytest --tb=short "$@"
