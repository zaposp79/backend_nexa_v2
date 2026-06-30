#!/usr/bin/env bash
# scripts/run_full_tests.sh
# -----------------------------------------------------------------------------
# Ejecuta la suite *completa* — core + legacy.
#
# Atención: la suite legacy tiene fails+errors esperados (deuda heredada
# pre-V2-7). El reporte se utiliza para tracking, no para gate de CI.
# Ver docs/v27/WAVE7_TRIAGE.md.
#
# Uso:
#   ./scripts/run_full_tests.sh
#   ./scripts/run_full_tests.sh --legacy-only   # sólo deuda legacy
# -----------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [[ -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

if [[ "${1:-}" == "--legacy-only" ]]; then
    shift
    python -m pytest -m legacy --tb=no -q "$@"
    exit $?
fi

# Override del default `-m "not legacy"` con `-m ""` para incluir todo.
python -m pytest -m "" --tb=short "$@"
