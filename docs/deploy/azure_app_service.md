# Despliegue en Azure App Service (Linux, Python)

Checklist para desplegar el backend NEXA en un App Service. Resume lo
**adicional** a lo que ya está en el repo.

## 0. Lo que YA está listo

- `requirements.txt` cubre todo el runtime (FastAPI, uvicorn, pydantic,
  python-multipart, openpyxl, python-dateutil, python-dotenv, azure-cosmos).
  **No** se necesita gunicorn.
- `.python-version = 3.12.0` (App Service soporta 3.12).
- `.env` está en `.gitignore`: los secretos **no** se suben; van en Application Settings.
- `startup.sh` (en la raíz) resuelve el arranque y el import del paquete.

## 1. Startup Command

App Service → **Configuration → General settings → Startup Command**:

```
bash /home/site/wwwroot/startup.sh
```

Por qué hace falta: el repositorio **es** el paquete `backend_nexa` (su contenido
queda directo en `wwwroot`), pero el código importa `backend_nexa`/`nexa_engine`.
`startup.sh` expone el paquete en `PYTHONPATH` (symlink si `wwwroot` es el paquete,
o detecta un subdirectorio `backend_nexa/` si el artefacto viene anidado) y lanza:

```
python -m uvicorn backend_nexa.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 2
```

## 2. Application Settings (variables de entorno)

App Service → **Configuration → Application settings**. Estas reemplazan al `.env`:

| Setting | Valor | Notas |
|---|---|---|
| `APP_ENV` | `production` | Obligatorio para usar Cosmos (guard de seguridad). Desactiva `/docs`. |
| `CORS_ALLOWED_ORIGINS` | `https://tu-frontend...` | **Obligatorio** en production. Sin `*`. Coma-separado. |
| `DB_PROVIDER` | `cosmos` | |
| `COSMOS_ENDPOINT` | `https://<cuenta>.documents.azure.com:443/` | |
| `COSMOS_KEY` | `<key>` | **Ideal: Key Vault reference**, no texto plano. |
| `COSMOS_DATABASE` | `nexa_pricing_db` | |
| `COSMOS_CONTAINER` | `parametrization` | |
| `JSON_STORAGE_PATH` | `storage` | Inocuo con cosmos; evita validaciones de path. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Hace que Oryx ejecute `pip install -r requirements.txt`. |
| `WEBSITES_PORT` | `8000` | Puerto en que escucha el contenedor (coincide con startup.sh). |
| `WEB_CONCURRENCY` | `2` | Opcional: nº de workers uvicorn. |

No definas `APP_RELOAD=true` en production (el guard lo rechaza; default ya es false).

## 3. Datos en Cosmos (seed)

El App Service leerá la parametrización desde Cosmos. Asegúrate de que la base
apuntada por `COSMOS_DATABASE` tenga los datos sembrados:

```bash
python scripts/migrations/seed_cosmos_parametrization.py --provision --execute
```

(Si el App Service usa la misma cuenta/DB que ya sembraste localmente, ya están.)

## 4. Despliegue

Cualquiera de estos métodos sirve (el artefacto debe incluir `startup.sh`,
`requirements.txt` y todo el código):

- **GitHub Actions** (Deployment Center → GitHub): App Service genera el workflow.
- **VS Code** (extensión Azure App Service): "Deploy to Web App".
- **Zip Deploy / `az webapp up`**.

No incluyas `.env` ni `venv/` en el artefacto (ya están en `.gitignore`).

## 5. Verificación post-deploy

- **Log stream** (App Service → Log stream): debe verse
  `Persistence container ready (provider=CosmosDocumentStore)` y
  `Application startup complete`.
- `GET https://<app>.azurewebsites.net/api/v1/parametrization/hr/versions` → 200 con `v2-7`.
- `GET /docs` → **404** (esperado: Swagger desactivado en production).

## 6. Swagger en un entorno desplegado (opcional, con cuidado)

En production `/docs` está desactivado a propósito. Si necesitas Swagger en un
entorno **no público** (p. ej. un slot privado), puedes poner
`APP_ENV=development` + `ALLOW_COSMOS_NON_PRODUCTION=true`. No lo hagas en un
App Service expuesto a internet.

## Notas

- El contrato OpenAPI versionado sigue disponible en
  [contracts/openapi/api-v1.json](../../contracts/openapi/api-v1.json) aunque
  `/docs` esté apagado.
- Persistencia: con `DB_PROVIDER=cosmos`, tanto la parametrización como los
  resultados de simulación usan Cosmos. El filesystem de App Service es efímero
  fuera de `/home`; no dependas de escritura local.
