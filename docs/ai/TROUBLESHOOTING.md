# Troubleshooting rápido

Problemas comunes y soluciones para desarrollo en NEXA.

---

## Python / Venv

| Problema | Solución |
|---|---|
| `ModuleNotFoundError: No module named 'backend_nexa'` | Ejecutar desde directorio padre de `backend_nexa/` o usar `PYTHONPATH=$(pwd)` |
| `venv no encontrado` | `source backend_nexa/venv/bin/activate` desde el directorio de trabajo |
| `Python version mismatch` | Venv debe crearse con Python 3.14 exacto: `~/.pyenv/versions/3.14.0/bin/python3.14 -m venv venv` |

---

## Tests

| Problema | Solución |
|---|---|
| Tests fallan sin cambios en código | `rm -rf storage/ backend_nexa/__pycache__ tests/__pycache__` y reintentar |
| `pytest: unknown -m <marker>` | Marker no definido. Válidos: `parity`, `baseline`, `slow`, `legacy`, `cosmos_integration` |
| Tests `cosmos_integration` se saltan | Esperado si `DB_PROVIDER=json` (default). Solo ejecutar con `DB_PROVIDER=cosmos` y credenciales |

---

## API / Desarrollo

| Problema | Solución |
|---|---|
| Swagger en `/docs` no aparece | Verificar `APP_ENV=development` (nunca en producción) |
| API no responde en localhost:8000 | Verificar que esté levantada: `uvicorn backend_nexa.app:create_app --factory --reload` |
| `Port 8000 already in use` | `lsof -i :8000` para encontrar proceso, luego `kill -9 <PID>` |

---

## Git / Commits

| Problema | Solución |
|---|---|
| `git not a repository` | Trabajar desde `backend_nexa/` (git repo raíz es aquí) |
| Pre-commit hook fallos | Leer error, arreglarlo, `git add`, crear **nuevo commit** (nunca amend) |
| Archivos staged accidentalmente | `git reset <archivo>` para desescenificar |

---

## Parametrización / Excel

| Problema | Solución |
|---|---|
| `OP-Poliza` upload falla | Verificar que estructura sea `[Poliza, Porcentaje, PorcentajeExigido]` (V2-8) |
| `HR-EquipoHITL` no encontrado | Estructura es ahora `[EquipoHITL]` sin columna `ratio` |
| `GN-LV` falta columna | Debe tener 23 columnas con `Divisa` al final |
| ICA Tasa > 5% bloquea upload | Verificar valores en Excel; Armenia debe ser 0.006 (no 0.6) |

---

## Paridad Excel

| Problema | Solución |
|---|---|
| `make validate-excel` falla | Ejecutar desde `backend_nexa/` y verificar que Excel V2-8 existe en `excel/` |
| Drift numérico vs Excel | Revisar `docs/refactor/excel_v28/findings.csv` para deltas conocidos |
| Test de paridad falla | No cambiar test ni fixture; investigar fórmula antes |

---

## Persistencia

| Problema | Solución |
|---|---|
| Arquivos storage corruptos | `rm -rf storage/` y reiniciar app (storage se regenera automáticamente) |
| Cosmos DB timeout | Verificar credenciales en `.env` si `DB_PROVIDER=cosmos` |
| `JSON_STORAGE_PATH` error | Verificar variable en `.env` o usar default `storage/` |

---

## Modelo de datos

| Problema | Solución |
|---|---|
| `IParametrizationProvider` no encontrado | Importar desde `nexa_engine.modules.shared.ports.parametrization_provider` |
| Import circular detectado | Verificar que modulos en `modules/` no importan entre sí (solo desde `shared/`) |
| DTO contract mismatch | Verificar que DTOs en routers coincidan con modelos de dominio en use cases |

---

## Performance

| Problema | Solución |
|---|---|
| Tests lentos | Marcar con `@pytest.mark.slow` si tardan > 5s; ejecutar con `-m "not slow"` para desarrollo rápido |
| API lenta | Verificar `make audit` para lineage/tracing; puede ralentizar |
| Consumo de memoria alto | `rm -rf .parity_backup/` y `storage/` (puede crecer con backups) |

---

## Seguridad

| Problema | Solución |
|---|---|
| Secrets en logs | Nunca loguear `Authorization`, `X-API-Key`, `Cookie`. Ver `request_utils.py` |
| Path traversal riesgo | Siempre validar paths contra allowlist de `settings.allowed_*_roots` |
| Cosmos credentials leak | Usar `AppSettings` de pydantic-settings, nunca hardcodear en código |

---

## Azure / Infra

| Problema | Solución |
|---|---|
| `DB_PROVIDER=cosmos` error | Verificar que `azure-cosmos` esté instalado: `pip install azure-cosmos>=4.5,<5` |
| App Service deployment falla | Verificar `APP_ENV=production`, credenciales Cosmos, Key Vault secrets |
| CORS error | Verificar `CORS_ALLOWED_ORIGINS` en `.env`; default es `localhost:3000,5173` |

---

## Makefile

| Comando | Cuándo usar | Salida esperada |
|---|---|---|
| `make test` | Después de cambios de código | pytest output, 1249 pass / 57 fail |
| `make verify` | Detectar regresiones | baseline comparison OK |
| `make validate-excel` | Validar paridad numérica | Excel match report |
| `make baseline` | Solo después de cambios validados | baseline.json regenerado |
| `make audit` | Debugging / forensics | snapshots/ y lineage/ con traces |
| `make all` | Pre-merge / pre-release | test + verify + validate-excel |

---

## Debugging rápido

```bash
# Ver último error en tests
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -x --tb=short 2>&1 | tail -50

# Buscar función específica
grep -r "def mi_funcion" modules tests

# Ver diferencia contra baseline
git diff storage/baselines/

# Ejecutar un test específico
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test.py::test_name -vvs

# Ver Excel diff
python -c "import openpyxl; ws = openpyxl.load_workbook('excel/OP_productiva.xlsx')['OP-Poliza']; print([cell.value for cell in ws[1]])"
```

---

## Escalación

| Problema | Escalar a | Cómo |
|---|---|---|
| Fórmula incorrect vs Excel | business-rules-agent (opus) | Proporcionar: findings.csv, hoja/celda, diferencia vs V2-7 |
| Arquitectura/diseño | architecture-agent (opus) | Proporcionar: contexto, impacto estimado, alternativas consideradas |
| Seguridad / producción | security-agent (opus) | Proporcionar: descripción de riesgo, impacto, mitigación propuesta |
| Regresión numérica | qa-agent (sonnet) | Proporcionar: test fallido, resultado actual vs esperado |
