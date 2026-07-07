#!/bin/bash
# Startup alternativo para Azure App Service (Linux, Python).
#
# NOTA: el método recomendado es el Startup Command INLINE (ver
# docs/deploy/ENV_PRODUCCION.md), porque Oryx COMPRIME la salida del build y
# /home/site/wwwroot no contiene archivos reales sino un artefacto comprimido
# que Azure extrae a /tmp/<guid>. Por eso `bash /home/site/wwwroot/startup.sh`
# puede no existir en runtime.
#
# Este script SOLO es válido si la salida NO está comprimida (o si lo invocas
# por su ruta real extraída). Es auto-localizable: descubre su propio directorio,
# así funciona tanto en /home/site/wwwroot como en el /tmp/<guid> extraído.
#
# Layout esperado (anidado): este script vive junto a backend_nexa_v2/ y venv/.
set -euo pipefail

echo "[startup] ===== NEXA startup.sh ====="

# Directorio real de la app (donde están backend_nexa_v2/ y venv/), sin rutas fijas.
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_ROOT"
echo "[startup] APP_ROOT=$APP_ROOT  PWD=$PWD"

# Activar el virtualenv de Oryx (venv) si la plataforma no lo activó ya.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$APP_ROOT/venv/bin/activate" ]; then
    echo "[startup] Activando virtualenv: $APP_ROOT/venv"
    # shellcheck disable=SC1091
    source "$APP_ROOT/venv/bin/activate"
fi

# El paquete backend_nexa_v2/ está bajo APP_ROOT → su padre (APP_ROOT) en PYTHONPATH.
export PYTHONPATH="$APP_ROOT:${PYTHONPATH:-}"

# Puerto: App Service inyecta PORT. Orden: PORT > WEBSITES_PORT > APP_PORT > 8000.
PORT="${PORT:-${WEBSITES_PORT:-${APP_PORT:-8000}}}"

echo "[startup] python=$(command -v python)  ($(python --version 2>&1))  PORT=$PORT"
python -c "import uvicorn, backend_nexa_v2; print('[startup] imports OK: uvicorn + backend_nexa_v2')"

# Preflight de configuración: si APP_ENV/CORS/COSMOS_* están mal, falla aquí con
# mensaje claro en lugar de que cada worker muera en silencio (causa de 503).
python -c "import backend_nexa_v2; \
from nexa_engine.modules.shared.config.app_settings import load_app_settings; \
from nexa_engine.db.config import load_config; \
s = load_app_settings(); c = load_config(); \
print(f'[startup] config OK: env={s.app_env} provider={c.provider} cors={len(s.cors_allowed_origins)} origins')"

exec python -m uvicorn backend_nexa_v2.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --no-access-log
