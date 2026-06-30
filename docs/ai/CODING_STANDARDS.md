# Estándares de Código — NEXA Backend

Convenciones de código, naming, patrones y reglas de calidad para el proyecto.

**Cuándo leer:** Solo si la tarea toca código nuevo, refactor, naming, comentarios o estilo. No es necesario para tareas de configuración, documentación o investigación.

---

## 1. Arquitectura — capas y responsabilidades

```
Router → Use Case → Repository → Store (JSON / Cosmos)
```

- **Routers**: solo parsean input, llaman al use case, mapean a DTO y lanzan `HTTPException`. Sin lógica de negocio.
- **Use cases**: orquestan lógica de dominio. Nunca importan desde routers. Nunca lanzan `HTTPException`.
- **Repositories**: único punto de acceso a persistencia (JSON o Cosmos). Sin lógica de negocio.
- **DTOs**: solo en la capa de router. Dentro de use cases y repos: dataclasses o modelos Pydantic de dominio.
- **`shared/`**: código compartido entre dominios. Los módulos de dominio importan desde `shared/`, nunca entre sí.
- Sin imports circulares. Sin saltar capas.

---

## 2. Inyección de dependencias — siempre `Depends()`

```python
# ❌ Nunca instanciar dependencias manualmente dentro de un endpoint
def get_audit(sim_id: str) -> AuditResponseV1:
    use_case = AuditSimulationUseCase(repo=_lineage_repo)

# ✅ Siempre Depends()
def get_audit(
    sim_id: str,
    use_case: AuditSimulationUseCase = Depends(get_audit_use_case),
) -> AuditResponseV1:
```

- Las factories de dependencias van en `db/dependencies.py` o en `modules/shared/dependencies.py`.
- Nunca importar símbolos con prefijo `_` desde otro módulo o dominio.

```python
# ❌
from nexa_engine.modules.calculator.api.calculate_dependencies import _lineage_repo
# ✅
from nexa_engine.modules.shared.dependencies import get_lineage_repo
```

---

## 3. Nomenclatura

**Python:**

| Elemento | Convención | Ejemplo |
|---|---|---|
| Variables y funciones | `snake_case` descriptivo | `simulation_audit`, `build_lineage_ref` |
| Booleanos | `is_`, `has_`, `can_`, `should_` | `is_active`, `has_lineage` |
| Clases | `PascalCase` sustantivo | `AuditSimulationUseCase` |
| Constantes de módulo | `UPPER_SNAKE_CASE` con `Final` | `MAX_AUDIT_LIMIT: Final[int] = 500` |
| Atributos de instancia | `_snake_case` con `Final` si son inmutables | `self._smmlv: Final[float]` |
| Prefijo `_` | Solo dentro del mismo módulo | Nunca exportar ni importar desde fuera |

**Prohibido sin contexto**: `data`, `result`, `tmp`, `obj`, `info`, `item`, `val`, `resp`, `tc`, `ant`, `rot`, `n`, `reg`, `umb`.

---

## 4. Tipos — sin `Any`, sin `dict` crudo en dominio

```python
# ❌ dict crudo sin tipo — KeyError silencioso en runtime
diff = use_case.diff_vs_baseline(...)
return AuditResponseV1(baseline_id=diff["baseline_id"])

# ✅ dataclass o Pydantic model — contrato explícito
diff: BaselineComparisonResult = use_case.diff_vs_baseline(...)
return AuditResponseV1(baseline_id=diff.baseline_id)
```

- Toda función pública con type hints completos: parámetros + retorno.
- **Use cases y repositories**: nunca retornan `dict` crudo. Retornan dataclasses o modelos Pydantic de dominio.
- **Bordes I/O** (parseo JSON, respuestas API, fixtures): `dict[str, Any]` es permitido si está **validado** (Pydantic schema) o **tipado** completamente (`dict[str, float]`, `dict[str, list[str]]`).
- Sin `Any` implícito en dominio. En bordes de I/O, permitido si el contexto lo justifica (documentar con comentario).

---

## 5. Manejo de errores

**Jerarquía de excepciones:**

```
DomainError (base)
├── NotFoundError
├── ValidationError
└── ParametrizationError
```

- **Use cases**: lanzan excepciones de dominio (`NotFoundError`, `DomainError`, etc.).
- **Routers**: capturan excepciones de dominio y las mapean a `HTTPException`.
- **Exception handlers globales**: en `modules/shared/infrastructure/exception_handlers.py`.

**HTTP status codes precisos:**

| Código | Cuándo |
|---|---|
| `404` | Recurso no encontrado |
| `422` | Error de validación (FastAPI automático) |
| `400` | Input inválido que pasa Pydantic |
| `403` | Sin permisos sobre el recurso |
| `409` | Conflicto (duplicado) |
| `500` | Error inesperado — loguear full exception, devolver mensaje genérico |

**Reglas de logging en errores:**

```python
# ❌ Expone internos al cliente
raise HTTPException(500, detail=str(exc))

# ✅ Loguear completo server-side, mensaje genérico al cliente
logger.exception("[módulo] Error en operación sim_id=%s", simulation_id)
raise HTTPException(500, detail="Error inesperado. Contactar soporte.")
```

- `logger.exception()` para errores inesperados (incluye stack trace automático).
- `logger.error()` para errores de dominio esperados con contexto.
- `logger.warning()` para validaciones fallidas.
- `logger.info()` para not found y flujo normal.
- Nunca `except Exception: pass` — siempre loguear y/o reraise.

---

## 6. Seguridad

**Paths del filesystem:**

```python
# ❌ Path traversal — input del usuario entra directo a Path()
baseline_root = Path.cwd() / "storage" / baseline_version / "cases"

# ✅ Validar contra allowlist + usar settings
if baseline_version not in settings.allowed_baseline_versions:
    raise HTTPException(400, "Invalid baseline version")
baseline_root = settings.baselines_root / baseline_version / "cases"
```

- Nunca usar `Path.cwd()` en código de aplicación. Usar `settings.*_root` o paths relativos a `__file__`.
- Todo path construido con input del usuario debe validarse contra una allowlist o regex estricto.

**Logging seguro:**

```python
# ❌ Input del usuario directo en el log
logger.info("processing %s", user_input)

# ✅ Truncar y sanitizar
logger.info("sim_id=%s", simulation_id[:64])
logger.info("filename=%s", filename[:100].replace("\x00", ""))
```

**Secrets:**

- Cero secrets en código fuente. Todo desde env vars vía `AppSettings` (pydantic-settings).
- Nunca loguear valores de headers `Authorization`, `Cookie`, `X-API-Key` — ver `request_utils.py`.

**Cosmos DB (Azure):**

- Nunca construir queries concatenando strings de input del usuario.
- Siempre usar parametrización y validación antes de enviar a Cosmos.
- Use `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` desde `AppSettings` (nunca hardcodear).
- Recordar que `DB_PROVIDER=json` es el default (desarrollo local), `DB_PROVIDER=cosmos` requiere credenciales Azure.

---

## 7. Business rules y configuración

- Los umbrales, pesos y constantes de negocio van en `config/business_rules/{calculadora}.yaml`.
- Nunca hardcodear valores de negocio como dicts o listas en Python.
- Usar `load_business_rules_cached(rule_name)` de `modules/shared/infrastructure/business_rules_loader.py`.
- El parámetro de configuración del calculador sigue siendo inyectable (para tests), pero el fallback es siempre el YAML.

```python
# ❌ Defaults hardcodeados en Python
_DEFAULT_CONFIG = {"umbral_aprobacion_smmlv": 1000.0, ...}

# ✅ Fallback desde YAML
if riesgo_config is None:
    riesgo_config = load_business_rules_cached("riesgo")
```

---

## 8. FastAPI — patrones establecidos

**Middleware y exception handlers:**

- Middlewares: `modules/shared/infrastructure/middlewares.py` → `register_middlewares(app)`
- Exception handlers: `modules/shared/infrastructure/exception_handlers.py` → `register_exception_handlers(app)`
- Helpers HTTP (sanitización, correlation ID): `modules/shared/infrastructure/request_utils.py`
- En `app.py` solo viven: `_load_env_file()`, `_make_lifespan()`, `create_app()`, `__main__`.

**Query params:**

- Siempre definir `ge`, `le`, `min_length`, `max_length` en todo `Query(...)` que acepte input del usuario.

```python
limit: int = Query(50, ge=1, le=500)
```

**Type hints en endpoints:**

```python
# ❌ Sin tipos
async def log_requests(request, call_next):

# ✅ Completo
async def log_requests(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
```

**`health` endpoint:**

```python
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nexa-simulator-api"}
```

---

## 9. Testing — patrones de integración

**Test unitarios:** calculadores y use cases sin dependencias externas. Inyectar mocks de `IParametrizationProvider`.

**Test de integración (E2E sobre API):**

```python
# tests/integration/test_simulation_api.py
import pytest
from fastapi.testclient import TestClient
from nexa_engine.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_simulation_calculate_happy_path(client):
    """Flujo completo: POST calculate → GET results."""
    request_body = {
        "panel": {...},
        "cadena_a": {...},
        "cadena_b": {...},
        "cadena_c": {...},
        "parametrization_version": "v1.0"
    }
    resp = client.post("/api/v1/simulation/calculate", json=request_body)
    assert resp.status_code == 200
    
    data = resp.json()["data"]
    simulation_id = data["simulation_id"]
    
    # Consultar resultado
    result_resp = client.get(f"/api/v1/simulation/{simulation_id}/results/vision-imprimible")
    assert result_resp.status_code == 200
    vision = result_resp.json()["data"]
    assert vision["total_costo_mes"] > 0
```

- Usa `TestClient` de FastAPI (no necesita servidor real).
- Tests de integración viven en `tests/integration/` separados de unitarios.
- Siempre usar `DB_PROVIDER=json` en tests (default, sin dependencias externas).
- Marcar tests lentos con `@pytest.mark.slow` si tardan > 5s.

---

## 10. Calidad general

- **Funciones**: máximo ~30 líneas. Una función = una responsabilidad.
- **Early returns**: preferir guard clauses sobre `if/else` anidados.
- **Sin mutable default arguments**: `def fn(items: list = [])` → `def fn(items: list | None = None)`.
- **f-strings** en código general. `%` solo en llamadas de logging (lazy evaluation).
- **Sin magic numbers**: extraer a constantes con nombre y `Final`.
- **Sin bare `except`**: capturar siempre tipos específicos.
- **Sin imports no usados**.
- **Docstrings**: clases públicas y métodos de use case con al menos una línea.
- **`frozenset`** para colecciones de lookup inmutables (en lugar de `set`).

**NamedTuple para retornos multi-valor:**

```python
# ❌ Tupla anónima — contrato invisible
return f"{dias} días", "Alto", 3

# ✅ NamedTuple — contrato explícito
class CriterioEvaluado(NamedTuple):
    valor_evaluado: str
    calificacion: str
    puntaje: int
return CriterioEvaluado(f"{dias} días", "Alto", PUNTAJE_ALTO)
```

---

## 11. Estructura de archivos del proyecto

```
backend_nexa/
  app.py                          ← solo factory + lifespan + __main__
  db/
    container.py
    dependencies.py               ← factories de DI para todos los repos y use cases
  modules/
    api_v1/router.py              ← agrega todos los sub-routers
    shared/
      exceptions.py               ← jerarquía de excepciones de dominio
      infrastructure/
        app_settings.py
        business_rules_loader.py  ← load_business_rules() + load_business_rules_cached()
        config.py
        exception_handlers.py     ← handlers como funciones puras + register_exception_handlers()
        middlewares.py            ← log_requests + register_middlewares()
        request_utils.py          ← constantes HTTP + helpers de sanitización
    {dominio}/
      api/router.py               ← endpoints del dominio
      use_cases/                  ← lógica de negocio
      repositories/               ← acceso a datos
  modules/calculator/             ← engine de cálculo (10 capas)
config/
  business_rules/
    riesgo.yaml                   ← umbrales y pesos del RiesgoCalculator
    {otros}.yaml
```

---

## 12. Checklist antes de entregar código

- [ ] Todas las funciones públicas tienen type hints completos (params + retorno)
- [ ] Sin `dict` crudo como retorno de use cases o repos
- [ ] Sin instanciación manual de dependencias en endpoints
- [ ] Sin imports de símbolos `_privados` desde otro módulo
- [ ] Sin `Path.cwd()` ni paths hardcodeados
- [ ] Sin secrets en código
- [ ] Sin `str(exc)` expuesto al cliente en HTTPException
- [ ] Sin magic numbers — usar constantes con nombre
- [ ] Sin `UPPER_SNAKE_CASE` en atributos de instancia
- [ ] Sin mutable default arguments
- [ ] Variables con nombres descriptivos (sin abreviaciones opacas)
- [ ] Business rules en YAML, no hardcodeadas en Python
- [ ] `logger.exception()` en errores inesperados, `logger.error()` en errores de dominio
