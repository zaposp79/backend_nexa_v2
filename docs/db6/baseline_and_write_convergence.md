# DB.6 baseline y convergencia de escritura

## Baseline ejecutado

Entorno:

- `DB_PROVIDER=json`
- Errores de colección: `0`
- Backend activo: `json`

Comandos:

- Gate: `DB_PROVIDER=json PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA venv/bin/python -m pytest --tb=no -q`
- Parity/oracle: `DB_PROVIDER=json PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA venv/bin/python -m pytest tests/parity -q --tb=no`

Resultados antes de cambios:

- Gate: `56 failed, 1267 passed, 46 skipped, 450 deselected, 1 xfailed`
- Parity/oracle: `406 passed, 11 skipped, 39 deselected`

Resultados despues de tests de caracterizacion y FASE 2:

- Gate: `56 failed, 1276 passed, 46 skipped, 450 deselected, 1 xfailed`
- Parity/oracle: `406 passed, 11 skipped, 39 deselected`

Los 56 node ids fallidos se mantienen estables contra el baseline DB.5.

## Inventario dirigido

| Componente | Consumidores | Lectura | Escritura | Accion |
| ---------- | ------------ | ------- | --------- | ------ |
| `BaseRepository.save_version` | `GNService`, `HRService`, `OPService` vía repositorios de dominio | No | Si, versión JSON + índice | Migrar por dominio despues de caracterizacion |
| `BaseRepository.set_active/delete_version/get_active` | Repositorios GN/HR/OP usados por servicios | Si | Si | Mantener temporal hasta migrar escrituras |
| `RepositoryFactory` | Sin consumidores activos en runtime; presente en módulo deprecated | No runtime | Potencial | Retirar en fase P.8/DB.6 posterior |
| `get_parametrization_store` | `resolver.py` fallback, `provider_business_rules.py`, `panel_service.py`, factory | Si | No directa | Eliminar fallback fuera de container |
| `ParametrizationRepositoryPort` | P.8 repos JSON/Cosmos y factory | Si/escritura paralela | Si | Clasificar: duplica `DocumentStore` |
| `json_parametrization_repository` | `RepositoryFactory` | Si | Si | Retirar o convertir si queda responsabilidad de dominio |
| `cosmos_parametrization_repository` | `RepositoryFactory` | Si | Si | Retirar duplicidad; no activar Cosmos en DB.6 |
| `VersionIndexRepository` | `BaseRepository`, repositorios activos HR/GN/OP | Si | Si | FASE 2: acepta `CollectionConfig`; path legacy temporal |
| `HR_DIR/GN_DIR/OP_DIR` | repositorios de carga, path overrides en repos activos | Si | Si | Reemplazo parcial en repositorios activos; mantener temporal en cargas |
| `BUSINESS_RULES_DIR` | `BusinessRulesRepository`, provider mixin metadata | Si | No confirmada | Revisar en fase Business Rules; posible `READ_ONLY` |

## VersionIndexRepository

| Dominio | Ruta fisica actual | Uso real | CollectionConfig posible | Accion |
| ------- | ------------------ | -------- | ------------------------ | ------ |
| HR | `storage/parametrization/hr` | `versions.json`, data path override legacy | `CollectionConfig(name="hr")` | `REPLACE_WITH_COLLECTION_CONFIG` en repo activo; carga temporal |
| GN | `storage/parametrization/gn` | `versions.json`, data path override legacy | `CollectionConfig(name="gn")` | `REPLACE_WITH_COLLECTION_CONFIG` en repo activo; carga temporal |
| OP | `storage/parametrization/op` | `versions.json`, data path override legacy | `CollectionConfig(name="op")` | `REPLACE_WITH_COLLECTION_CONFIG` en repo activo; carga temporal |
| Business Rules | `storage/parametrization/business_rules` | indice con esquema dict propio | `CollectionConfig(name="business_rules")` | `POSTPONE_WITH_REASON`: esquema diferente, repo propio |

Decision implementada:

- `VersionIndexRepository(store, collection=CollectionConfig(...))` queda soportado.
- `domain_dir` sigue soportado para compatibilidad temporal de uploads.
- Los repositorios activos GN/HR/OP ya pasan `collection`.
- No se cambio el esquema de `versions.json`.

## Preservacion de esquema JSON

| Dominio | Payload actual | Metadata tecnica requerida | Cambia JSON | Decision |
| ------- | -------------- | -------------------------- | ----------- | -------- |
| GN | `{version_id, lv, sheets}` | `id` para `DocumentStore.upsert` si se usara directo | No permitido | Crear mapper/codec antes de migrar escritura |
| HR | `{version_id, niveles, salarios, ...}` | `id` para `DocumentStore.upsert` si se usara directo | No permitido | Crear mapper/codec antes de migrar escritura |
| OP | `{version_id, sheets}` | `id` para `DocumentStore.upsert` si se usara directo | No permitido | Crear mapper/codec antes de migrar escritura |
| versions.json HR/GN/OP | lista de summaries sin `id` | `id` si se modela como documento | No permitido | Mantener formato legacy encapsulado hasta migracion explicita |

Riesgo central:

`DocumentStore.upsert()` exige documentos dict con `id`, pero los JSON actuales no pueden ganar campos tecnicos. La escritura por `DocumentStore` requiere un mapper o codec de repositorio que separe metadata tecnica del payload logico antes de migrar GN/HR/OP.

## Tests de caracterizacion agregados

- `tests/parametrizacion/uploads/test_gn_upload_characterization.py`
- `tests/parametrizacion/uploads/test_hr_upload_characterization.py`
- `tests/parametrizacion/uploads/test_op_upload_characterization.py`

Cobertura:

- archivo `{version_id}.json` creado;
- nombre exacto de archivo;
- contenido JSON exacto;
- estructura exacta de `versions.json`;
- version activa;
- listado de versiones;
- respuesta HTTP y codigo HTTP;
- duplicado de `version_id` actual;
- extension invalida;
- libro Excel invalido;
- ausencia de campo tecnico `id`.

Resultado: `9 passed`.
