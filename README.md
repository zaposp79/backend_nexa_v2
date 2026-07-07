# NEXA Simulator

Motor de pricing + API REST para parametrización y simulación de deals. Versión `1.0.0`.

El proyecto tiene dos caras complementarias:

1. **Motor de cálculo (`backend_nexa.engine.NexaPricingEngine`)** — un pipeline de 10 capas que convierte un `PricingRequest` (Panel + Cadenas A/B/C + datos maestros) en un `PricingResult` con P&G mensual y KPIs del deal.
2. **API REST (FastAPI)** — expone endpoints de parametrización (HR, GN, OP), simulación (Panel, Cadena A/B/C) y consulta de masters sobre el motor.

---

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Cómo se ejecuta](#cómo-se-ejecuta)
- [Arquitectura](#arquitectura)
- [Estructura del repositorio](#estructura-del-repositorio)
- [API REST](#api-rest)
- [Almacenamiento](#almacenamiento)
- [Pruebas](#pruebas)
- [Colección Postman](#colección-postman)

---

## Requisitos

- **Python 3.12** (probado con `3.12.0` instalado vía `pyenv`).
  > `requirements.txt` exige `fastapi>=0.100`, lo que descarta Python 3.7. Si tienes 3.12 o 3.13 disponibles, úsalos.
- Dependencias declaradas en [requirements.txt](requirements.txt):
  - `fastapi`, `uvicorn`, `python-multipart`, `pydantic`, `openpyxl`, `python-dateutil`.
  - `azure-cosmos>=4.5,<5` está declarado para el provider Cosmos, pero se importa de forma diferida y no es necesario para operar con `DB_PROVIDER=json`.

---

## Instalación

Desde la raíz `backend_nexa/`:

```bash
# 1) Crear venv con Python 3.12 (ajusta la ruta de tu intérprete)
~/.pyenv/versions/3.12.0/bin/python3.12 -m venv venv

# 2) Activar el venv
source venv/bin/activate

# 3) Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Cómo se ejecuta

Script en la raíz:

| Script | Qué hace |
|---|---|
| [run_api.sh](run_api.sh) | Levanta la API FastAPI en modo desarrollo (`APP_ENV=development`, reload activo). |
| [run_tests.sh](run_tests.sh) | Ejecuta `functional_test.py` (comparación contra valores de `NexaPricing_Simulador.xlsx`). |

Equivalente manual (desde el directorio padre `NEXA/`, para que `backend_nexa` sea un paquete importable):

```bash
# API (flujo oficial)
APP_ENV=development APP_RELOAD=true python -m backend_nexa.app

# Tests (reproducibilidad garantizada)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v

# Test funcional (compara vs Excel)
python -m backend_nexa.functional_test
```

Una vez la API esté arriba en desarrollo: `http://localhost:8000/docs` (Swagger) y `http://localhost:8000/health`.
En producción, `/docs`, `/redoc` y `/openapi.json` quedan deshabilitados.

**Para simular casos de prueba:** usa `POST /api/v1/simulation/calculate` endpoint con entry_data (ver [NEXA_Simulator.postman_collection.json](NEXA_Simulator.postman_collection.json)).

---

## Arquitectura

### Pipeline del motor (10 capas)

`NexaPricingEngine.calcular()` orquesta los siguientes calculadores (ver [engine.py](engine.py)):

```
PricingRequest
    │
    ├─ NominaCalculator              (Capa 2) — nómina cargada
    ├─ NoPayrollCalculator           (Capa 3) — infraestructura y TI
    ├─ CadenaBCalculator             (Capas 4-5) — plataforma digital
    ├─ CadenaCCalculator             (Capa 6) — integración IA
    ├─ CostosTotalesCalculator       (Capa 7) — costos agregados
    ├─ CostosFinancierosCalculator   (Capa 8) — ICA, GMF, pólizas, financiación
    ├─ PyGCalculator                 (Capa 9) — Estado de Resultados mensual
    └─ KPIsCalculator                (Capa 10) — KPIs del deal
        │
        ├─ CostToServeCalculator
        └─ VisionTarifasCalculator
            ▼
    PricingResult { kpis, pyg_por_mes, panel, cost_to_serve, vision_tarifas }
```

El motor no conoce el origen de los datos (JSON, API, frontend) ni el destino del resultado. El método `_construir_calculadores()` es el **Composition Root** — inyecta dependencias y no contiene lógica de negocio.

La persistencia conserva ese resultado técnico completo. La respuesta pública de
`GET /api/v1/simulation/{simulation_id}/results` se proyecta exclusivamente como
`data.vision_imprimible`, con las siete secciones visibles de la hoja canónica
V2-8. Las visiones técnicas continúan disponibles en sus endpoints especializados.

### Capas lógicas

- **`domain/`** — modelos y servicios de dominio puros (sin I/O).
- **`calculators/`** — cada capa del pipeline (nómina, no-payroll, cadenas B/C, P&G, KPIs, …).
- **`adapters/`** — entrada/salida: `JsonCaseLoader`, `UserInputLoader`, `SimulationContextBuilder`, `ConsoleReporter`, `FrontendAdapter`, `InputValidator`.
- **`repositories/`** — `MasterDataRepository` para datos maestros precargados.
- **`parametrization/{hr,gn,op}/`** — carga de Excel, persistencia por versión, activación de versiones.
- **`simulation/{panel,chain_a,chain_b,chain_c}/`** — DTOs, validadores, servicios y repositorios de inputs de simulación.
- **`infrastructure/`** — `config.py` (paths y constantes), parsing Excel, almacenamiento en disco.
- **`api/v1/`** — routers FastAPI organizados por dominio.
- **`shared/`** — `ApiResponse`, excepciones (`DomainError`, `NotFoundError`, `ValidationError`, `UploadError`), tipos comunes.

---

## Estructura del repositorio

```
backend_nexa/
├── app.py                       # Punto de entrada FastAPI
├── __init__.py                  # Expone NexaPricingEngine, __version__
├── requirements.txt
├── run_api.sh / run_tests.sh
├── NEXA_Simulator.postman_collection.json
├── adapters/                    # Loaders, builders, reporter, frontend adapter
├── api/v1/                      # Routers REST (parametrization, simulation, masters)
├── calculators/                 # Capas del pipeline
├── config/reference_data.json   # Datos de referencia del sistema
├── domain/                      # Modelos y servicios de dominio
├── infrastructure/              # Config, parsing Excel, storage
├── master_data/                 # Datos maestros precargados
├── parametrization/{hr,gn,op}/  # Carga + versionado de Excel (HR, GN, OP)
├── repositories/                # MasterDataRepository
├── shared/                      # ApiResponse, excepciones, tipos
├── simulation/{panel,chain_a,chain_b,chain_c}/   # DTOs + servicios de inputs
└── test_cases/                  # Casos JSON de ejemplo
```

---

## API REST

Prefijo de versión: **`/api/v1`**. Los endpoints públicos usan el envelope
[`ApiResponse`](modules/shared/responses.py):

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": null
}
```

| Grupo | Endpoint | Descripción |
|---|---|---|
| Health | `GET /health` | Liveness probe. |
| Simulations | `POST /api/v1/simulation/calculate` | Ejecuta y persiste una simulación. |
| Simulations | `GET /api/v1/simulation/{simulation_id}/results` | Devuelve el resultado imprimible general. |
| Simulations | `GET /api/v1/simulation/{simulation_id}/traceability` | Devuelve trazabilidad de la simulación. |
| Inputs | `GET /api/v1/simulation/input/panel/parametros` | Catálogo de parámetros de panel. |
| Inputs | `GET /api/v1/simulation/input/chain-a/parametros` | Catálogo de parámetros de Cadena A. |
| Inputs | `GET /api/v1/simulation/input/chain-b/parametros` | Catálogo de parámetros de Cadena B. |
| Inputs | `GET /api/v1/simulation/input/chain-c/parametros` | Catálogo de parámetros de Cadena C. |
| Parametrization | `POST /api/v1/parametrization/hr/upload` | Carga archivo HR. |
| Parametrization | `GET /api/v1/parametrization/hr/versions` | Lista versiones HR. |
| Parametrization | `PATCH /api/v1/parametrization/hr/{id}/activate` | Activa versión HR. |
| Parametrization | `DELETE /api/v1/parametrization/hr/{id}` | Elimina versión HR. |
| Parametrization | `POST /api/v1/parametrization/gn/upload` | Carga archivo GN. |
| Parametrization | `GET /api/v1/parametrization/gn/versions` | Lista versiones GN. |
| Parametrization | `PATCH /api/v1/parametrization/gn/{id}/activate` | Activa versión GN. |
| Parametrization | `DELETE /api/v1/parametrization/gn/{id}` | Elimina versión GN. |
| Parametrization | `POST /api/v1/parametrization/op/upload` | Carga archivo OP. |
| Parametrization | `GET /api/v1/parametrization/op/versions` | Lista versiones OP. |
| Parametrization | `PATCH /api/v1/parametrization/op/{id}/activate` | Activa versión OP. |
| Parametrization | `DELETE /api/v1/parametrization/op/{id}` | Elimina versión OP. |
| Vision Imprimible | `GET /api/v1/simulation/{simulation_id}/results/vision-imprimible` | Contrato imprimible screen-ready. |
| Vision PYG | `GET /api/v1/simulation/{simulation_id}/results/vision-pyg` | Contrato PYG screen-ready. |
| Vision Cost To Serve | `GET /api/v1/simulation/{simulation_id}/results/cost-to-serve` | Contrato CTS screen-ready. |
| Vision Tarifas | `GET /api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro` | Modelo de cobro público. |
| Vision Tarifas | `POST /api/v1/simulation/{simulation_id}/results/vision-tarifas/modelo-cobro/recalculate` | Preview stateless de modelo de cobro. |

Códigos de error normalizados: `VALIDATION_ERROR`, `NOT_FOUND`,
`DOMAIN_ERROR`, `UPLOAD_ERROR` y errores específicos por módulo.

**Subidas de archivos:** solo se aceptan extensiones declaradas por la
configuración compartida de uploads.

---

## Almacenamiento

El backend usa una capa transversal `DocumentStore` con provider seleccionable por entorno:

| Variable | Default | Valores |
|---|---|---|
| `DB_PROVIDER` | `json` | `json`, `cosmos` |
| `JSON_STORAGE_PATH` | `storage` | ruta filesystem para el provider JSON |
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` | vacío | requeridas solo con `DB_PROVIDER=cosmos` |

`json` sigue siendo el provider por defecto. Con `DB_PROVIDER=json` la aplicación no conecta a Cosmos, no requiere credenciales y no importa el SDK durante el flujo normal.

En modo JSON, los datos se persisten en disco bajo `storage/`:

```
storage/
├── parametrization/
│   ├── hr/                  # Versiones HR subidas
│   ├── gn/                  # Versiones GN subidas
│   └── op/                  # Versiones OP subidas
└── simulation_inputs/
    ├── panel/
    ├── chain_a/
    ├── chain_b/
    └── chain_c/
```

El lifespan de la API llama a `ensure_storage_dirs()` que crea los directorios si no existen.

### Uploads de parametrización

Los uploads GN, HR y OP ya están migrados/certificados sobre `DocumentStore`:

- El payload lógico `{version_id}.json` conserva su forma de negocio y no recibe `id` técnico.
- `versions.json` conserva el formato histórico de lista.
- Los duplicados mantienen el comportamiento histórico: entradas duplicadas y última versión activa.
- Si el store soporta `AtomicDocumentStore`, payload e índice se guardan en un batch atómico.
- Si el store no soporta atomicidad, JSON mantiene compensación best effort: elimina payload nuevo o restaura payload previo si falla el índice.

### Cosmos DB

Cosmos está preparado, pero no activo por defecto. El diseño DB.7 usa documentos técnicos con `payload` separado de metadata (`id`, `_pk`, `_etag`) para preservar los JSON de negocio.

Estado actual:

- DB.7.0: diseño y skeleton Cosmos sin conexión real.
- DB.7.1: escritura atómica opcional para GN/HR/OP.
- DB.7.2: ETag opcional sobre `versions` y `DbConcurrencyError`.
- DB.7.3: contrato SDK preparado con tests sin red.
- DB.7.3.1: bloqueado en este entorno porque `azure-cosmos` no está instalado y no hay resolución DNS hacia PyPI.

Detalles: [docs/db7/](docs/db7/) y [db/README.md](db/README.md).

---

## Pruebas

- **Test funcional:** `./run_tests.sh` corre `functional_test.py`, que ejecuta el motor sobre datos reales extraídos de `NexaPricing_Simulador.xlsx` y compara contra valores de referencia. Genera `functional_test_report.txt` y `functional_test_inputs.txt`.
- **Casos de prueba:** [test_cases/seguros_adl_cobranzas.json](test_cases/seguros_adl_cobranzas.json), [test_cases/bancamia_cobranzas.json](test_cases/bancamia_cobranzas.json).
- **DB/upload/Cosmos:** los contratos de persistencia viven en `tests/db/` y `tests/parametrizacion/uploads/`. Los tests reales del SDK Cosmos requieren instalar `azure-cosmos>=4.5,<5`; sin el paquete se omiten explícitamente.

---

## Colección Postman

[NEXA_Simulator.postman_collection.json](NEXA_Simulator.postman_collection.json) — colección Postman v2.1.0 con todas las rutas (29 requests, 9 carpetas), variable `baseUrl` configurable (default `http://localhost:8000`), bodies JSON de ejemplo para los `POST` de simulación basados en los DTOs reales, y `form-data` configurado para los `POST /upload`.

Importar: Postman → *Import* → seleccionar el archivo.

---

## Uso de `.env` y `.gitignore`

- **Archivo `.env`:** contiene variables de entorno locales (por ejemplo `APP_ENV`, `APP_PORT`, `APP_RELOAD`, `CORS_ALLOWED_ORIGINS`, `DB_PROVIDER`). No añadas secretos reales al repositorio.
- **Archivo `.gitignore`:** el proyecto ya incluye `.env` en la lista de ignorados para evitar filtraciones accidentales. También están excluidos entornos virtuales (`venv/`), archivos temporales y la base de datos local `nexa.db`.
- **Qué guardar en `.env`:** claves de API, credenciales locales, URL de la base de datos de desarrollo y flags de configuración (`APP_ENV=development`).
- **Ejecutar con variables locales:** puedes exportar variables manualmente o usar una herramienta como `direnv` o `python-dotenv`. Ejemplo rápido:

```bash
# exportar variables para la sesión actual
export APP_ENV="development"
export APP_PORT="8000"
export APP_RELOAD="true"
export CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
python -m backend_nexa.app
```

- **No commitear `.env`:** si por accidente añadiste secretos, rota las claves y evita subir ese commit. Si quieres, puedo añadir un ejemplo `env.example` sin valores sensibles para documentar las variables necesarias.
