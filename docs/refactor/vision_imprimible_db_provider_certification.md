# Visión Imprimible — DB Provider Certification

**Fecha:** 2026-06-05
**Rama:** `refactor/modular-pure`
**Auditoría:** VISION_IMPRIMIBLE_DB_PROVIDER_CERTIFICATION

---

## Veredicto

**CERTIFICADO — Provider JSON activo. Cosmos documentado como gap de entorno.**

`modules/vision_imprimible` obtiene todos sus datos exclusivamente a través del puerto
`DocumentStore` abstracto. No accede directamente a ningún provider, ruta de filesystem,
ni instancia de Cosmos SDK.

---

## Flujo validado

```
GET /api/v1/simulation/{simulation_id}/results/vision-imprimible
    │
    ├── router.py
    │     └── repo: ResultsRepository = Depends(get_results_repository)
    │
    ├── db/dependencies.py
    │     └── get_results_repository(container) → container.results_repository
    │
    ├── db/container.py — ApplicationContainer
    │     └── results_repository = ResultsRepository(store)
    │                                               │
    │                                    store = build_provider(db_config)
    │
    └── db/factory.py — build_provider()
          ├── DB_PROVIDER=json   → JsonDocumentStore(json_storage_path)
          └── DB_PROVIDER=cosmos → CosmosDocumentStore(cosmos_settings)
```

El módulo `vision_imprimible` no participa en la selección del provider.
La resolución ocurre 100% en la raíz de composición (`db/container.py`).

---

## Repository usado

| Capa | Clase | Archivo |
|---|---|---|
| Port (interfaz) | `DocumentStore` (ABC) | `db/ports/document_store.py` |
| Repository de dominio | `ResultsRepository` | `modules/calculator/persistence/results_repository.py` |
| DI provider | `get_results_repository` | `db/dependencies.py` |
| Composition root | `ApplicationContainer.results_repository` | `db/container.py` |

`ResultsRepository` recibe `DocumentStore` por constructor.
El router recibe `ResultsRepository` por `Depends()`.
`modules/vision_imprimible` no instancia ni importa ninguno de ellos directamente.

---

## DocumentStore usado

```python
# db/factory.py
def build_provider(config: DbConfig) -> DocumentStore:
    if config.provider == PROVIDER_JSON:
        return JsonDocumentStore(config.json_storage_path)
    if config.provider == PROVIDER_COSMOS:
        return CosmosDocumentStore(config.cosmos)
```

`JsonDocumentStore` y `CosmosDocumentStore` son implementaciones del puerto `DocumentStore`.
Ambas implementan exactamente el mismo contrato: `get()`, `upsert()`, `list()`, `query()`, `delete()`.

---

## Provider activo

| Variable de entorno | Valor en `.env` | Estado |
|---|---|---|
| `DB_PROVIDER` | `json` | **Activo** |
| `COSMOS_ENDPOINT` | no configurado | Ausente |
| `COSMOS_KEY` | no configurado | Ausente |
| `COSMOS_DATABASE` | no configurado | Ausente |
| `COSMOS_CONTAINER` | no configurado | Ausente |

**Provider activo: JSON**
Ruta de storage: `storage/simulation_results/{simulation_id}.json` (default `_DEFAULT_JSON_STORAGE_PATH`).

---

## Garantías certificadas

| ID | Garantía | Resultado |
|---|---|---|
| P1 | `ResultsRepository` solo importa `DocumentStore` (port), no providers concretos | ✅ PASS |
| P2 | `modules/vision_imprimible` no importa `JsonDocumentStore` ni `CosmosDocumentStore` | ✅ PASS |
| P3 | `modules/vision_imprimible` no tiene rutas de storage hardcodeadas | ✅ PASS |
| P4 | `ResultsRepository.save()` → `get()` preserva los 15 campos canónicos de VI | ✅ PASS |
| P5 | El router GET usa `Depends(get_results_repository)`, no instancia el repo directamente | ✅ PASS |
| P6 | `FakeDocumentStore` inyectado vía `dependency_overrides` → HTTP 200 con los 15 campos | ✅ PASS |
| P7 | El GET lee el documento persistido exactamente, sin recalcular el motor | ✅ PASS |
| P8 | HTTP 404 cuando `simulation_id` no existe en el store | ✅ PASS |
| P9 | Cosmos: SKIP — credenciales no configuradas (documentado como gap) | ⏭ SKIP |
| P10 | Ciclo completo: engine → serializer → `save()` → `get()` → 15 campos + coherencia | ✅ PASS |

---

## Pruebas ejecutadas

```
tests/db/test_vision_imprimible_db_provider.py::test_p1_results_repository_no_importa_providers_concretos  PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p2_vision_imprimible_no_importa_providers_concretos  PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p3_vision_imprimible_no_hardcoded_paths              PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p4_repository_save_get_produce_campos_canonicos_vi   PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p5_router_usa_depends_get_results_repository         PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p6_fake_store_get_vision_imprimible_200              PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p6_fake_store_no_recalcula_motor                     PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p8_get_returns_404_para_simulation_inexistente       PASSED
tests/db/test_vision_imprimible_db_provider.py::test_p9_cosmos_skip_si_no_configurado                     DESELECTED (marca cosmos_integration)
tests/db/test_vision_imprimible_db_provider.py::test_p10_ciclo_completo_engine_save_get_via_fake_store    PASSED
────────────────────────────────────────────────────────────────────────────────
9 passed, 1 deselected, 0 failed
```

---

## Resultado JSON (round-trip P10)

El ciclo P10 verifica:
- `kpis.ingreso_mensual > 0` — motor ejecutó correctamente
- `configuracion_comercial.modelo_cobro_principal == "Fijo FTE"` — sección 03 presente
- `reglas_negocio.reglas instanceof list` — sección 07 presente
- `len(pyg_por_mes) == 12` — 12 meses preservados
- `"id" not in retrieved` — campo interno del DocumentStore no filtra al consumidor HTTP

---

## Resultado Cosmos

**GAP — Entorno local no tiene credenciales Cosmos configuradas.**

El test `test_p9_cosmos_skip_si_no_configurado` verifica la ausencia de credenciales
y hace `pytest.skip()` con instrucciones explícitas para habilitar la certificación Cosmos.

Para certificar Cosmos, configurar en el entorno:
```bash
export COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
export COSMOS_KEY=<key>
export COSMOS_DATABASE=nexa_pricing_db
export COSMOS_CONTAINER=simulation_results
```
Y ejecutar:
```bash
python -m pytest tests/db/test_vision_imprimible_db_provider.py -m cosmos_integration -v
```

La arquitectura garantiza que el mismo `ResultsRepository` y el mismo contrato HTTP
funcionan con Cosmos sin cambios en `modules/vision_imprimible` — el único cambio es
el `DocumentStore` inyectado en `db/container.py`.

---

## FakeDocumentStore

Para las pruebas de DI (P4, P6, P7, P8, P10) se implementó `_FakeDocumentStore`:
- In-memory (`dict` por colección)
- Implementa el contrato completo de `DocumentStore` (port)
- No accede a filesystem ni a Cosmos SDK
- Inyectado via `app.dependency_overrides[get_results_repository]`

Esto certifica que el módulo es provider-agnostic: funciona con cualquier implementación
del puerto `DocumentStore` sin modificar código de `modules/vision_imprimible`.

---

## Invariantes de arquitectura confirmadas

1. **Vertical slice completo**: `modules/vision_imprimible/api/router.py` es el único punto de entrada HTTP para VI. No hay lógica de VI dispersa en otros routers.
2. **Sin recálculo en GET**: El router llama `repo.get(simulation_id)` y proyecta campos. No instancia el motor de pricing.
3. **Separación port/implementación**: `ResultsRepository` depende de `DocumentStore` (ABC). Los providers son detalles de infraestructura resueltos en la composition root.
4. **DI via FastAPI `Depends()`**: El router no conoce la existencia de `JsonDocumentStore` ni `CosmosDocumentStore`. La sustitución es transparente.
5. **Campo `id` interno no filtrado**: `ResultsRepository.get()` elimina el campo `id` antes de retornar al consumidor HTTP.
