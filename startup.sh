#!/bin/bash
# Startup command para Azure App Service (Linux, Python).
#
# Problema que resuelve: el repositorio ES el paquete `backend_nexa` (su
# contenido queda directamente en /home/site/wwwroot). El código importa
# `backend_nexa` / `nexa_engine`, lo que exige que exista un directorio LLAMADO
# `backend_nexa` cuyo PADRE esté en PYTHONPATH. Aquí lo garantizamos.
#
# Configúralo en: App Service → Configuration → General settings → Startup Command:
#   bash /home/site/wwwroot/startup.sh
set -euo pipefail

WWWROOT="${WWWROOT_OVERRIDE:-/home/site/wwwroot}"

if [ -d "$WWWROOT/backend_nexa" ]; then
    # El artefacto ya trae un subdirectorio backend_nexa/ (deploy anidado).
    ROOT="$WWWROOT"
else
    # wwwroot ES el contenido de backend_nexa: exponerlo como paquete vía symlink.
    ln -sfn "$WWWROOT" /home/site/backend_nexa
    ROOT="/home/site"
fi

cd "$ROOT"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

# Puerto: Azure App Service inyecta WEBSITES_PORT; también se puede sobrescribir con APP_PORT.
PORT="${APP_PORT:-${WEBSITES_PORT:-8000}}"

# Arranque ASGI con la application factory. APP_ENV/COSMOS_*/CORS_ALLOWED_ORIGINS
# se leen desde las Application Settings del App Service (NO desde .env).
exec python -m uvicorn backend_nexa.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --no-access-log
