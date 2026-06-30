# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Coordinación técnica

Actúa como coordinador técnico del proyecto.
**Flujo de inicio (reduce contexto innecesario):**

1. Lee este archivo (CLAUDE.md) — índice operativo
2. Clasifica la tarea usando `docs/ai/ROUTING_MATRIX.md`
3. Lee **solo** los documentos específicos para tu tarea según:
   - `docs/ai/CONTEXT_SAVING_POLICY.md` — qué documentos leer/no leer por tarea
   - `docs/ai/TROUBLESHOOTING.md` — problemas comunes (si lo necesitas)
4. Lee documentos opcionalmente:
   - `docs/ai/PROJECT_CONTEXT.md` — contexto general (primera vez)
   - `docs/ai/DECISIONS.md` — decisiones arquitectónicas (si la tarea las toca)
   - `docs/ai/TASK_STATE.md` — histórico de fases (solo si necesitas entender cambios previos)
   - **`docs/ai/skills/README.md`** — skills reutilizables por tipo de tarea (contexto mínimo, reglas, validación)

**⚠️ NO leas automáticamente:** `VALIDATION.md` (histórico completo), `CODE_REVIEW_WORKFLOW.md` (solo si revisar código), `QUICK_START.md` (solo primera vez)

### Estado actual: rama `refactor/modular-pure`

Esta rama contiene el estado actualizado del proyecto después de las fases de refactoring modular (FASE 8B). El estado es:
- ✅ **153 shims eliminados** — imports legacy completamente removidos.
- ✅ **0 imports circulares** — arquitectura de módulos limpia.
- ✅ **Contracts preservados** — contratos públicos intactos (sin breaking changes).
- ✅ **Baseline intacto** — reproducibilidad garantizada (test suite 1249 pass / 57 fail estable).
- ✅ **FASE 8B: module boundary rename completo** — engine/formulas → `calculator_motor/`; HTTP → `calculator/api/`; repos → `calculator/persistence/`.
- ✅ **IParametrizationProvider** — interface movida a `modules/shared/ports/parametrization_provider.py` (shim legacy eliminado).

**Implicaciones para desarrollo:**
- Motor de cálculo vive en `modules/calculator_motor/` (engine, formulas, adapters, dto, mixins).
- Endpoints HTTP de cálculo en `modules/calculator/api/`. Repositorios en `modules/calculator/persistence/`.
- No usar rutas legacy `nexa_engine.modules.calculator.engine` — usar `nexa_engine.modules.calculator_motor.engine`.
- `IParametrizationProvider` se importa desde `nexa_engine.modules.shared.ports.parametrization_provider`.
- Inyección de dependencias centralizada en `db/dependencies.py` y `db/container.py`.
- Si ves un import de un módulo fuera de `nexa_engine.modules.*`, es un error (investiga).

### Workers disponibles
12 workers especializados están configurados en `.claude/agents/`:
`coordinator-agent`, `scanner-agent`, `cleanup-agent`, `backend-agent`, `qa-agent`, `architecture-agent`, `security-agent`, `infra-agent`, `business-rules-agent`, `frontend-agent`, `docs-agent`, `reviewer-agent`.

**Usa siempre un worker especializado si la tarea coincide con su descripción.** Fallback: `design.md`, `explore.md`, `implement.md` (genéricos, sin especialidad).
Ver `docs/ai/ROUTING_MATRIX.md` para routing automático.

---

## Política de ahorro de contexto

**Objetivo:** Reducir tokens consumidos (~170 KB → 20-100 KB según tarea).

**Principios:**
- Lectura selectiva según tipo de tarea (ver `docs/ai/CONTEXT_SAVING_POLICY.md`)
- No cargar documentación histórica salvo necesidad explícita
- Ejecutar validación mínima suficiente para la tarea

**Ahorro estimado por tarea:**
- Inventario/grep: 88% (20 KB contexto mínimo)
- Refactor módulo: 53% (80 KB)
- Paridad puntual: 41% (100 KB)
- Documentación: 71% (50 KB)

**Línea de comandos baratos:**
```bash
# Inventario (haiku, 5-10 min)
claude --model haiku "Haz grep de X. Reporta archivos"

# Refactor (sonnet, 15-30 min)
claude --model sonnet --permission-mode plan "Refactoriza foo en módulo Y"

# Paridad (opus, 30-60 min)
claude --model opus --permission-mode plan "Investiga drift en fórmula X"

# Consulta corta (sin sesión larga)
claude -p --max-turns 3 "Qué hace función X?"
```

Ver detalles completos en `docs/ai/CONTEXT_SAVING_POLICY.md`.

---

## Instalación y setup

1. **Python 3.14 requerido** (FastAPI necesita `>=3.10`, pero venv debe ser 3.14 para consistencia)
2. Desde dentro de `backend_nexa/`:
   ```bash
   ~/.pyenv/versions/3.14.0/bin/python3.14 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip && pip install -r requirements.txt
   ```
3. Copia `env.example` a `.env` (variables de entorno locales)

**Nota:** El venv debe crearse con Python 3.14 exacto (no 3.12 ni versión del sistema). Esto garantiza reproducibilidad entre máquinas.

---

## Comandos de desarrollo

Todos los comandos se ejecutan desde el directorio **padre** de `backend_nexa/` (donde `backend_nexa` es importable como paquete), o desde dentro con `PYTHONPATH` ajustado al padre.

```bash
# Activar venv (Python 3.14)
source backend_nexa/venv/bin/activate

# Levantar API (modo desarrollo — hot reload)
python -m backend_nexa.app
# o desde el directorio padre:
APP_ENV=development APP_RELOAD=true uvicorn backend_nexa.app:create_app --factory --reload

# Simular un caso (via API endpoint)
curl -X POST http://localhost:8000/api/v1/simulation/calculate \
  -H "Content-Type: application/json" \
  -d @backend_nexa/test_cases/request.json

# Consultar resultado
curl http://localhost:8000/api/v1/simulation/{simulation_id}/results/vision-imprimible

# Swagger: http://localhost:8000/docs  (solo APP_ENV=development)
# Health:  http://localhost:8000/health

# Script shell (alternativa para API)
backend_nexa/run_api.sh

# Tests (reproducibilidad garantizada, baseline/parity)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short
```

### Tests

```bash
# Suite principal (desde el directorio padre de backend_nexa/)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short

# Test único
PYTHONPATH=$(pwd) pytest backend_nexa/tests/path/to/test_file.py::test_name -v

# Solo tests de paridad Excel (críticos — golden values)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v

# Solo tests de baseline/regresión (valores congelados entre cambios)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v

# Incluir tests legacy (excluidos por defecto — módulos desaparecidos)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m legacy -v

# Pipeline completo de validación Make
cd backend_nexa && make test        # Ejecuta pytest determinístico
cd backend_nexa && make verify      # Verifica outputs vs baseline congelado
cd backend_nexa && make validate-excel  # Compara backend vs Excel Nexa - Pricing - Simulador - V2-8.xlsx
cd backend_nexa && make baseline    # Regenera baseline oficial (snapshot congelado)
cd backend_nexa && make audit       # Ejecuta engine con tracing y exporta lineage/snapshots
cd backend_nexa && make all         # test + verify + validate-excel (pipeline completo)
```

### Targets Makefile en detalle

| Target | Qué hace | Cuándo usarlo |
|---|---|---|
| `make test` | Corre `pytest tests/` sin markers especiales | Verificación rápida después de cambios |
| `make verify` | Compara output actual vs baseline congelado en `storage/baselines/` | Detectar regresiones de reproducibilidad |
| `make validate-excel` | Compara calculadores backend vs Excel `Nexa - Pricing - Simulador - V2-8.xlsx` | Validar paridad de negocio (crítico) |
| `make baseline` | Regenera el snapshot congelado (`storage/baselines/official.json`) | Solo después de cambios validados |
| `make audit` | Ejecuta motor con tracing completo y exporta JSON + CSV de lineage | Debugging, auditoría, forensics |
| `make all` | `test` + `verify` + `validate-excel` en secuencia | Pre-merge/pre-release |

**Nota sobre `make baseline`:** Regenerar baseline es una operación delicada. Solo ejecutarla cuando:
1. Los cambios han pasado `validate-excel` (paridad Excel confirmada).
2. El cambio es intencional (refactor, feature aprobado, etc.).
3. Se commitea el nuevo baseline con el código en el mismo PR.

**Marcadores pytest — semántica:**
- `parity` — tests que validan paridad contra Excel `Nexa - Pricing - Simulador - V2-8.xlsx` (golden values, nunca actualizar)
- `parity_oracle_real` — subset de parity con datos reales del oráculo Excel
- `baseline` — tests que validan reproducibilidad (snapshot congelado, nunca actualizar)
- `slow` — tests lentos (parametrización completa, Cosmos, etc.)
- `cosmos_integration` — requiere `azure-cosmos` y credenciales Azure; **excluido del default run**

**Excluidos por defecto:** `legacy` (módulos desaparecidos), `legacy_circular`, `cosmos_integration`.
- `tests/test_parametrization_phase_1_2.py` — ignorado permanentemente (ImportError: módulo legacy `circular_dependencies` no existe). Eliminar si es seguro después de auditoría.
- Tests `cosmos_integration` excluidos porque requieren SDK y credenciales; activate solo si `DB_PROVIDER=cosmos`.

### Variables de entorno relevantes

| Variable | Default | Descripción |
|---|---|---|
| `APP_ENV` | `development` | `development` / `production` / `test` |
| `DB_PROVIDER` | `json` | `json` (local) o `cosmos` (Azure) |
| `JSON_STORAGE_PATH` | `storage` | Raíz del storage JSON |
| `CORS_ALLOWED_ORIGINS` | localhost:3000,5173 | Origins permitidos |
| `ALLOW_COSMOS_NON_PRODUCTION` | `false` | Permite Cosmos fuera de prod |

Copia `env.example` a `.env` para configuración local.

---

## Arquitectura

### Alias de módulo

`backend_nexa` registra el alias `nexa_engine` en `sys.modules` al importarse (`__init__.py`). Todo el código interno usa `from nexa_engine.modules.xxx import ...` aunque el directorio en disco sea `backend_nexa/modules/`. El módulo canónico para uvicorn es siempre `backend_nexa.app:create_app`.

### Pipeline del motor (10 capas)

`NexaPricingEngine.calcular()` en `modules/calculator_motor/engine.py` es el único punto de entrada al sistema de cálculo. Recibe `PricingRequest` y produce `PricingResult`. No conoce HTTP ni persistencia.

```
PricingRequest
  ├─ NominaCalculator              (Capa 2)
  ├─ NoPayrollCalculator           (Capa 3)
  ├─ CadenaBCalculator             (Capas 4-5)
  ├─ CadenaCCalculator             (Capa 6)
  ├─ CostosTotalesCalculator       (Capa 7)
  ├─ CostosFinancierosCalculator   (Capa 8)
  ├─ PyGCalculator                 (Capa 9)
  └─ KPIsCalculator                (Capa 10)
       ├─ CostToServeCalculator
       └─ VisionTarifasCalculator
            ▼
  PricingResult { kpis, pyg_por_mes, panel, cost_to_serve, vision_tarifas }
```

`_construir_calculadores()` en el engine es el **Composition Root**: inyecta dependencias, no contiene lógica de negocio. Los calculadores dependen de `IParametrizationProvider` (Protocol), nunca de implementaciones concretas.

### Módulos verticales (`modules/`)

Cada módulo sigue la estructura: `api/` → `services/` → `repositories/` → `dto/` → `models/`.

| Módulo | Responsabilidad |
|---|---|
| `calculator_motor/` | Engine principal (`NexaPricingEngine`), pipeline de 10 capas, formulas, adapters, dto, mixins |
| `calculator/api/` | Endpoints HTTP de cálculo (`calculate_router`, handlers, DTOs) |
| `calculator/persistence/` | `ResultsRepository`, `TraceabilityRepository` (DocumentStore) |
| `parametrizacion/hr/gn/op/` | Carga de Excel, versionado, activación de versiones |
| `panel/` | Input del Panel de Control General (simulación) |
| `cadena_a/b/c/` | Inputs de las tres cadenas (A=Backoffice, B=Digital, C=IA) |
| `vision_imprimible/` | Vista de 9 secciones del resultado final |
| `vision_cost_to_serve/` | Vista Cost-to-Serve |
| `vision_tarifas/` | Vista de tarifas por canal |
| `pyg/` | Vista del Estado de Resultados (P&G) |
| `lineage/` | Bounded context de trazabilidad: domain models, builder, JSON emitter, null emitter, snapshot repository |
| `audit/` | Registry de auditoría, integration hooks, writer de trazas; expone API de audit trail |
| `shared/` | Excepciones (`DomainError`, `NotFoundError`, `ValidationError`), `ApiResponse`, contratos, auditoría, certificación |
| `shared/ports/` | Interfaces Protocol: `IParametrizationProvider`, `ILogger`, `ITraceEmitter` |

### Capa de persistencia (`db/`)

`db/container.py` es el **root de inyección** para persistencia. Construye el `DocumentStore` en el `lifespan` de FastAPI (`app.state.container`) y lo pasa a todos los repositorios.

- `DB_PROVIDER=json` (default): persiste en `storage/` bajo el filesystem, sin dependencias externas.
- `DB_PROVIDER=cosmos`: requiere `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` y el paquete `azure-cosmos>=4.5,<5` (importado de forma diferida).

La app nunca conecta a Cosmos si `DB_PROVIDER=json`. Los tests no deben depender de Cosmos; los que sí lo necesitan están marcados `@pytest.mark.cosmos_integration` y excluidos del default run.

### Flujo de cálculo via API

```
POST /api/v1/simulation/calculate
  → CalculationRequest (entry_data del deal)
  → NexaPricingEngine.calcular()
  → PricingResult persisted as storage/simulation_results/{simulation_id}.json
  → returns simulation_id

GET /api/v1/simulation/{simulation_id}/results/vision-imprimible
GET /api/v1/simulation/{simulation_id}/results/vision-pyg
GET /api/v1/simulation/{simulation_id}/results/vision-tarifas
GET /api/v1/simulation/{simulation_id}/results/cost-to-serve
```

### Respuesta estándar

Todos los endpoints devuelven `ApiResponse` de `modules/shared/responses.py`:

```json
{ "success": true, "data": {...}, "error": null, "meta": {...} }
```

Errores normalizados: `NOT_FOUND` (404), `VALIDATION_ERROR` (422), `DOMAIN_ERROR` (400), `INTERNAL_SERVER_ERROR` (500).

### Parametrización

Los Excels HR, GN y OP se suben via `POST /api/v1/parametrization/{hr|gn|op}/upload` y se versionan en `storage/parametrization/`. Solo una versión puede estar activa a la vez. El motor lee siempre la versión activa mediante `ParametrizationProvider.build()`, a menos que se pase `parametrization_version` explícito (modo frozen para reproducibilidad).

### Estructura de almacenamiento (`storage/`)

Generada automáticamente en startup. No commitear; `.gitignore` ya la excluye.

```
storage/
├── parametrization/        # Versiones HR/GN/OP subidas
│   ├── hr/
│   ├── gn/
│   └── op/
├── simulation_results/     # Resultados de simulaciones calculadas
├── simulation_inputs/      # Inputs guardados (Panel, Cadena A/B/C)
├── snapshots/             # Snapshots de cálculo (lineage, traceability)
├── lineage/               # Traces de fórmula (audit trail)
├── certificates/          # Certificados de parity/baseline
└── baselines/             # Snapshots congelados para regresión
```

Limpieza: `rm -rf storage/` regenera en próximo startup (seguro, contiene solo datos transitorios).

### Flujos de ejecución recomendados

| Caso de uso | Flujo | Formato |
|---|---|---|
| **Producción + reproducibilidad** | `POST /api/v1/simulation/calculate` (API) | Entry data plano (Cadena A/B/C) con `parametrization_version` frozen |
| **Testing local + baseline** | `pytest backend_nexa/tests/ -m baseline` | Fixtures JSON en `tests/refactor/` |
| **Parity contra Excel** | `pytest backend_nexa/tests/ -m parity` | Golden values, nunca actualizar snapshots |
| **Exploración/debugging** | `pytest backend_nexa/tests/golden/` | Test cases reales con traces |

**API endpoint oficial:**
- ✅ Único flujo de producción
- ✅ Soporta entry data plano (Cadena A/B/C)
- ✅ Versionado y freezable para reproducibilidad
- ✅ Persistencia DocumentStore (JSON o Cosmos)
- ✅ Integración con Postman collection

### Auditoría y lineage (para debugging y forensics)

`make audit` ejecuta el motor con tracing completo y exporta:
- **JSON snapshots**: `storage/snapshots/{timestamp}.json` — estado completo de cálculo en cada capa.
- **Lineage traces**: `storage/lineage/{timestamp}.csv` — audit trail de fórmulas y valores intermedios.
- **Certificates**: `storage/certificates/` — evidencia de reproducibilidad vs Excel y baseline.

Casos de uso:
- **Debugging**: quieres ver exactamente qué pasó en cada paso del cálculo.
- **Forensics**: investigar por qué un resultado cambió entre versiones.
- **Auditoría regulatoria**: generar evidencia de qué fórmulas y parámetros se usaron.

```bash
cd backend_nexa && make audit
# Genera storage/snapshots/ y storage/lineage/ con traces completos
# Los archivos CSV son importables a Excel para análisis
```

### Postman

[NEXA_Simulator.postman_collection.json](NEXA_Simulator.postman_collection.json) — colección v2.1 con 29 requests (9 carpetas):
- **Parametrization**: HR/GN/OP upload, versions, activate
- **Simulation**: Panel, Cadena A/B/C input + retrieve
- **Masters**: clientes, servicios, tipos-cliente, períodos-pago

Importar: Postman → *Import* → seleccionar archivo. Variable `baseUrl` predefinida (default `http://localhost:8000`).

---

## Política de commits

Cuando hay múltiples cambios sin commit, organiza por categoría según `TASK_STATE.md`:
- **Cambios de configuración/IA** (CLAUDE.md, docs/ai/) → separado
- **Fixes API contract** (routers, respuestas) → separado
- **Cambios de persistencia** (db/, DocumentStore) → separado
- **Cambios de fórmulas** (calculadores, lógica) → separado
- **Tests y fixtures** → separado

Cada categoría debe pasar su suite de tests antes de commit. Prefijo sugerido en mensaje: categoría en mayúsculas o código de fase (ej. `refactor: CADENA_C...`, `test+docs: ...`, `docs: ...`).

---

## Reglas críticas

- **Paridad Excel**: la fuente canónica de business rules es el Excel `Nexa - Pricing - Simulador - V2-8.xlsx`. No cambiar fórmulas, golden values ni parámetros sin evidencia del Excel. Escalar a `business-rules-agent` + opus.
- **Contratos públicos**: no cambiar DTOs, respuestas API ni formatos de `ApiResponse` sin verificar impacto en consumidores.
- **Composition Root**: toda inyección de dependencias ocurre en `engine.py` (`_construir_calculadores`) y `db/container.py`. Los calculadores y repositorios no instancian sus propias dependencias.
- **Tests de paridad y baseline**: nunca actualizarlos para hacer pasar un test. Si divergen, investigar el drift antes de modificar.
- **Cosmos**: no activar por defecto ni importar `azure-cosmos` en el flujo principal. Solo en el provider específico, cargado de forma diferida.
- **APP_ENV**: `docs_enabled=True` solo en `development`/`test`. Producción nunca expone `/docs`, `/redoc` ni `/openapi.json`.

---

## Política de migración Excel V2-7 → V2-8

**Objetivo:** Migrar cambios funcionales desde el Excel de referencia sin romper reproducibilidad ni contratos públicos.

### Fuentes de verdad por tipo de cambio

| Tipo de cambio | Fuente canónica | Tratamiento |
|---|---|---|
| **Estructura de entrada** | `PanelDeControl`, `CondicionesCadena{A,B,C}` (contratos Pydantic) | Crear DTO versionado V2-8; no mutar V2-7 silenciosamente |
| **Visiones (salida)** | `VisionImprimible`, `VisionCostToServe`, `VisionTarifas` | Validar facts intermedios antes de cambiar render; no alterar solo formato |
| **Fórmulas y cálculos** | Excel `Nexa - Pricing - Simulador - V2-8.xlsx` | Citar hoja, celda/rango, diferencia vs V2-7 en docstring |
| **Parámetros de negocio** | HR/GN/OP parametrización activa (versionada) | Frozen snapshot V2-8 en `storage/parametrization/` si es crítico |

### Checklist para cambios funcionales

- [ ] **Entrada versionada**: Si `PanelDeControl` o `CondicionesCadena*` cambian de estructura, crear `V2_8` contrato separado en `modules/shared/models/` + tests en `tests/contract/`.
- [ ] **Fórmula documentada**: Toda fórmula nueva/modificada en un calculador incluye:
  ```python
  # EXCEL V2-8: [Nombre_Hoja]![Celda/Rango]
  # Diferencia vs V2-7: [cambio breve]
  ```
- [ ] **Facts validados**: Si una visión requiere hechos nuevos (campos adicionales en `DesgloseCTSCadenaA`, etc.), verificar que los facts se computen antes de modificar render.
- [ ] **Test de paridad**: Agregar caso en `tests/parity/` con valores esperados de Excel V2-8 y evidencia de reproducibilidad.
- [ ] **Golden fixture**: Si es un cambio significativo, crear fixture V2-8 en `tests/golden/` con resultado esperado congelado.
- [ ] **Sin mutación silenciosa**: No cambiar valores en fixtures V2-7 existentes. Crear nuevos si es necesario.

### Flujo recomendado para cambios V2-8

1. **Leer el cambio en Excel** — hoja, celda/rango, fórmula nueva, impacto estimado.
2. **Crear test fallador** — test/golden con valores esperados V2-8 (cita hoja+celda).
3. **Implementar fórmula** — con docstring EXCEL V2-8 + código comentado.
4. **Validar facts** — si visión cambió, asegurar hechos intermedios existen.
5. **Ejecutar `make validate-excel`** — paridad Excel V2-8.
6. **Pasar baseline** — solo si cambio es intencional y aprobado.

### Casos especiales

**Delta pre-existentes vs Excel:**
- Si V2-7 tenía gaps vs Excel (ej. `capacitacion_rotacion` 70% delta), documentar en legacy test con `@pytest.mark.known_delta`. No "arreglar" en V2-8 sin explicación de negocio.

**Parámetros versionados:**
- HR/GN/OP cambios entre V2-7 y V2-8 → generar snapshot `v2.8` en parametrization storage antes de cambiar fórmulas.
- Usar `parametrization_version="v2.8"` en golden tests para reproducibilidad.

### Infraestructura de paridad V2-8

**Scripts de comparación:** `scripts/parity/`
- `utils.py` — funciones puras: `resolve_sheet_name()`, `is_scale_mismatch()`, etc.
- `maps/common.py` — campos compartidos entre hojas
- `maps/<hoja>.py` — campos por hoja (ej. `maps/nomina.py`)
- `runner.py` — comparación unificada Excel vs Backend

**Tests:** `tests/parity/v28/`
- `test_inputs_v28.py` — contrato de entrada (Panel, Cadenas A/B/C)
- `test_business_rules_v28.py` — parámetros HR/GN/OP
- `test_formulas_v28.py` — fórmulas de cálculo
- `test_outputs_v28.py` — visiones finales (P&G, Tarifas, CTS)

**Artefactos:** `docs/refactor/excel_v28/`
- `findings.csv` — estado inter-sesión, **fuente principal para correcciones**
- `parity_report.md` — reporte ejecutivo
- `request_diff.txt` — diferencias de entrada
- `business_rules_diff.txt` — diferencias de parámetros

**Backup pre-cambios:** `.parity_backup/v28/`

**Worker recomendado:**
- `business-rules-agent` (modelo `opus`) para cambios de fórmulas/parámetros
- `backend-agent` (modelo `sonnet`) para traducción puntual Excel→código

**Regla de sesión:** 
- Antes de modificar motor de cálculo, leer `docs/refactor/excel_v28/findings.csv`
- Cada línea corregida debe incluir comentario obligatorio:
  ```python
  # Excel V2-8 · '<Hoja>'!<Celda> · fórmula: =<original abreviada>
  # Traducción: <capa usada>
  ```

---

## Skills recomendadas

Skills locales en `.claude/skills/` (índice) y `docs/ai/skills/` (contenido completo).

Usar solo cuando aplique — una skill es un patrón de trabajo, no una copia de este archivo:

- `prompt-token-saver` — convertir tareas en prompts eficientes antes de actuar.
- `v28-parity-rca` — auditar deltas Excel V2-8 vs backend sin tocar código.
- `backend-safe-fix` — aplicar fixes mínimos con RCA existente y validación progresiva.
- `baseline-refresh-guarded` — regenerar baselines solo con drift documentado y aprobado.
- `v28-provider-patch` — parchear providers/fixtures V2-8 con trazabilidad Excel.

Ver índice completo: [`docs/ai/skills/README.md`](docs/ai/skills/README.md)

---

## Política de contexto (archivos AI)

Mantén actualizados (no llenes con logs largos, no dupliques):
- `docs/ai/PROJECT_CONTEXT.md` — arquitectura, stack, convenciones estables.
- `docs/ai/TASK_STATE.md` — fase actual, pendientes, riesgos.
- `docs/ai/DECISIONS.md` — decisiones técnicas y alternativas descartadas.
- `docs/ai/VALIDATION.md` — comandos de test, gates, fallos conocidos.
- `docs/ai/ROUTING_MATRIX.md` — matriz tarea → worker → modelo.

**Integración con auto-memory:**

Además de `docs/ai/`, Claude Code mantiene un sistema de auto-memory persistente en `.claude/projects/-Users-darwin-minota-quinto-Projects-NEXA-backend-nexa/memory/`. Este sistema almacena:

- **User memories** — preferencias de trabajo, expertise, rol dentro del proyecto.
- **Feedback memories** — correcciones y confirmaciones de enfoques que funcionaron.
- **Project memories** — estado actual, deadlines, iniciativas en progreso.
- **Reference memories** — ubicación de información externa (Linear, Grafana, etc.).

**Cuándo actualizar auto-memory:**
- Si aprendes algo sobre el usuario que debería persistir (ej. "usuario prefiere minimal verbosity").
- Si descubres un patrón que funcionó bien o un patrón que falló (ej. "no hacer X porque causó Y").
- Si hay cambios en scope, deadlines, o prioridades del proyecto.

**Diferencia entre `docs/ai/` y auto-memory:**
- `docs/ai/` — decisiones arquitectónicas, roadmap público, decisiones técnicas que todos deben leer.
- Auto-memory — preferencias personales, contexto histórico, patrones aprendidos en conversaciones previas.

---

## Política de economía de tokens

- Usa contexto curado antes que lectura masiva.
- Usa Grep/Glob antes que abrir archivos largos.
- Lee solo archivos directamente relacionados.
- Delega búsquedas extensas al `scanner-agent`.
- Delega revisiones finales al `reviewer-agent`.
- Usa el modelo más barato que pueda resolver bien la tarea.

---

## Política de ejecución

Antes de modificar código, determina: tipo de tarea, worker, modelo, archivos relevantes, riesgo, tests esperados y cambios prohibidos.

Si hay riesgo de arquitectura, seguridad, producción, contratos públicos, persistencia crítica, cálculos de negocio o paridad numérica: escalar a modelo fuerte (opus).

---

## Convenciones de código

**Ver `docs/ai/CODING_STANDARDS.md`** para convenciones detalladas.

Leer solo si la tarea toca **código nuevo, refactor, naming, comentarios o estilo**. 

Aplica **todas** las reglas: arquitectura en capas, inyección de dependencias, nomenclatura, tipos, errores, seguridad, business rules, FastAPI patterns, testing, calidad y checklist pre-entrega.

---

## Troubleshooting rápido

| Problema | Solución |
|---|---|
| `ModuleNotFoundError: No module named 'backend_nexa'` | Ejecutar desde directorio padre de `backend_nexa/` o usar `PYTHONPATH=$(pwd)` |
| `venv no encontrado` | `source backend_nexa/venv/bin/activate` desde el directorio de trabajo |
| Tests fallan sin cambios en código | `rm -rf storage/ backend_nexa/__pycache__ tests/__pycache__` y reintentar |
| Swagger en `/docs` no aparece | Verificar `APP_ENV=development` (nunca en producción) |
| Tests `cosmos_integration` se saltan | Esperado si `DB_PROVIDER=json` (default). Solo ejecutar con `DB_PROVIDER=cosmos` y credenciales. |
| `pytest: unknown -m <marker>` | Marker no definido en `conftest.py`. Markers válidos: `parity`, `baseline`, `slow`, `legacy`, `cosmos_integration` |

---

## Formato final obligatorio

Toda respuesta final debe incluir:

```md
## Resultado
## Evidencia
## Riesgo
## Validación
## Siguiente paso
```

El siguiente paso debe ser una instrucción accionable.
