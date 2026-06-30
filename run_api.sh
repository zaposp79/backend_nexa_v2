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
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

# Activar entorno virtual
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "✓ Virtual environment activated (Python $(python --version 2>&1 | awk '{print $2}'))"
elif [ -f "$SCRIPT_DIR/venv/Scripts/activate" ]; then
    source "$SCRIPT_DIR/venv/Scripts/activate"
    echo "✓ Virtual environment activated (Python $(python --version 2>&1 | awk '{print $2}'))"
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
python -m backend_nexa.app
