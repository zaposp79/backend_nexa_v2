#!/bin/bash
# Ejecuta la API del simulador NEXA (application factory mode).
# Uso: ./run_api.sh
#
# Variables de entorno relevantes:
#   APP_ENV      — development (default) | test | production
#   APP_HOST     — 0.0.0.0 (default)
#   APP_PORT     — 8000 (default)
#   APP_RELOAD   — true (default en development) | false
#   DB_PROVIDER  — json (default) | cosmos
#   CORS_ALLOWED_ORIGINS — obligatorio si APP_ENV=production

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_NAME="$(basename "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Activar entorno virtual.
# Orden: si Oryx ya activó antenv (VIRTUAL_ENV set), no hace falta nada.
# Si no, buscar: antenv en PROJECT_ROOT (Azure/Oryx), luego venv local.
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ -f "$PROJECT_ROOT/antenv/bin/activate" ]; then
        source "$PROJECT_ROOT/antenv/bin/activate"
        echo "✓ antenv activated (Oryx) — Python $(python --version 2>&1)"
    elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
        source "$SCRIPT_DIR/venv/bin/activate"
        echo "✓ venv activated (local) — Python $(python --version 2>&1)"
    elif [ -f "$SCRIPT_DIR/venv/Scripts/activate" ]; then
        source "$SCRIPT_DIR/venv/Scripts/activate"
        echo "✓ venv activated (Windows) — Python $(python --version 2>&1)"
    else
        echo "⚠ No virtualenv found — using system Python $(python --version 2>&1)"
    fi
else
    echo "✓ Virtual env already active: $VIRTUAL_ENV — Python $(python --version 2>&1)"
fi

# La configuración (APP_ENV, APP_RELOAD, DB_PROVIDER, COSMOS_*) la carga la
# aplicación desde backend_nexa/.env al arrancar (ver env_loader.py).
# NO exportamos defaults aquí: hacerlo pisaría el .env (la carga usa
# override=False, por lo que una variable ya presente en el entorno gana).
# Para sobrescribir puntualmente, exporta la variable antes de invocar el script:
#   APP_ENV=development DB_PROVIDER=json ./run_api.sh

# Iniciar via __main__ del módulo, que usa uvicorn factory mode internamente.
# Equivalente a:
#   uvicorn backend_nexa.app:create_app --factory --host 0.0.0.0 --port 8000 [--reload]
python -m "${PACKAGE_NAME}.app"
