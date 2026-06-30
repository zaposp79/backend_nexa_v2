# FASE 0 — Auditoría pre-refactor "Modular Pura"

> Análisis only. **NO se ejecuta refactor** hasta aprobación del plan completo.
> Generado 2026-06-02. Estado base: branch `refactor/modular-structure` (Hybrid parcial ya aplicado: 20 archivos en `modules/`).

## 0. Resumen ejecutivo

- El repo tiene **708 .py** (excl. venv). El refactor Hybrid previo ya movió **20** a `modules/` (compute puro).
- La visión "modular pura" colapsa **14 carpetas raíz** (~200 .py) en `modules/<dominio>/` + `modules/shared/`.
- **3 hallazgos que cambian el plan** (detalle en §4):
  1. `domain/models/{panel,results,visions}.py` NO se importan entre sí → **técnicamente divisibles**, pero 68 archivos los consumen y agregados como `PricingResult`/`PyGMensual` cruzan dominios. → **DECISIÓN 1**.
  2. `simulation/chain_a|b|c/{service,dto,validator}.py` tienen **0 importadores → CÓDIGO MUERTO** (implementación paralela abandonada). NO migrar; borrar/cuarentena. → **DECISIÓN 2**.
  3. Solo `simulation/{results,snapshots,traceability}` están vivos (los usan los routers de `api/`).
- **Coordinación Cadenas B/C:** sin conflicto. No hay ramas de equipo activas (solo `main` viejo + mis ramas `engine-v2`/`modular-structure`). Los archivos cadena_b/c solo los toca mi refactor.

## 1. Inventario de carpetas raíz (a eliminar/distribuir)

| Carpeta | .py | Naturaleza | Destino dominante |
|---|--:|---|---|
| `domain/` | 39 | modelos monolíticos + subpkgs DDD | shared/models + por dominio |
| `simulation/` | 28 | persistencia (live) + chain services (MUERTO) | shared/persistence + (borrar) |
| `application/` | 26 | use_cases + ports/lineage/versioning/certification | por dominio + shared |
| `parametrization/` | 21 | gn/hr/op (upload Excel) | parametrizacion |
| `infrastructure/` | 21 | config/storage/lineage/logging + parametrization | shared + parametrizacion |
| `api/` | 20 | routers FastAPI | por dominio (router.py) + shared |
| `contracts/` | 18 | schemas request/response Pydantic | por dominio + shared |
| `adapters/` | 10 | normalización/IO de input | calculator (+ data_provenance→shared) |
| `repositories/` | 8 | repos de parametrización + interface | parametrizacion (+ interface→shared) |
| `interfaces/` | 5 | placeholders vacíos (azure/excel/cli/http) | borrar o reservar |
| `validators/` | 4 | validadores cross-cutting | shared/validation |
| `audit/` | 3 | tracer thread-safe (live, 10+ imports) | shared/audit |
| `serialization/` | 2 | shim → calculator/serializer | borrar (shim) |
| `input/` | 2 | shim → calculator/user_input_loader | borrar (shim) |
| `shared/` | 9 | utils transversales (YA es el target) | modules/shared (mover) |
| `config/` | 1 | business_rules loader | shared/config |
| raíz: 3 scripts doc | 3 | FASE_8/convert_pdf/generate_arch | scripts/ o borrar |

## 2. Mapeo origen → destino (consolidado)

### 2.1 → `modules/shared/` (transversal, alto blast-radius)
- `shared/*` (exceptions, responses, types, precision, decimal_normalizer, value_normalizer, canonicalization, validator_utils) — **40+ importadores**.
- `audit/{trace,trace_integration}.py` → `shared/audit/` — **10+ importadores** (todos los calculators).
- `validators/{contract,parametrization_completeness,simulation_request}_validator.py` → `shared/validation/`.
- `infrastructure/{config.py (43 imp), storage/{base_repository (26), json_store (24)}, lineage/*, logging/*}` → `shared/infrastructure/`.
- `repositories/i_parametrization_provider.py` (interface, 10+ imp) → `shared/repositories/`.
- `application/ports/*`, `application/services/canonicalization_service.py`, `application/lineage/*`, `application/versioning/*`, `application/certification/*` → `shared/{ports,services,lineage,versioning,certification}/`.
- `application/use_cases/{audit_simulation,certified_calculation}.py` → `shared/use_cases/`.
- `config/business_rules/loader.py` → `shared/config/`.
- `adapters/data_provenance.py` → `shared/`.
- `simulation/{results,snapshots}/repository.py` → `shared/persistence/`; `simulation/traceability/*` → `shared/audit/`.
- `domain/{constants.py, shared/constants.py, shared/exceptions.py}` → `shared/` (merge).
- **`modules/shared_calc/utils.py` → fusionar en `modules/shared/`** (ya movido en Hybrid).

### 2.2 → `modules/parametrizacion/`
- `repositories/{financial,payroll,profitability,infrastructure}_parametrization_repository.py`, `frozen_parametrization_{repository,adapter}.py`.
- `infrastructure/{parametrization_resolver,parametrization_loader}.py`, `infrastructure/{excel,certification,parametrization}/*`.
- `parametrization/{gn,hr,op}/*` (6 archivos c/u: dto/mapper/models/repository/service/validator).
- `domain/frozen_parametrization.py`.
- `api/v1/parametrization/{hr,gn,op}_router.py` → `parametrizacion/router.py`.

### 2.3 → `modules/calculator/`
- `adapters/{console_reporter,input_normalizer,input_validator,json_loader,unified_input_adapter,vision_pyg_60m,volume_resolution}.py`.
- `domain/{normalized_input,snapshot,user_inputs,visions}.py` (datasets/input DTOs), `domain/pricing/*`.
- `simulation/request_dto.py`, `simulation/panel/{dto,service,validator}.py`.
- `application/use_cases/{build_pricing,build_visions,calculate_simulation}.py`, `application/orchestrators/pricing_pipeline.py`.
- `api/v1/simulation/{calculate_router,results_router}.py` → `calculator/router.py`. `app.py` queda como bootstrap (raíz o `calculator/`).
- `contracts/api_v1/response/simulation_result.py`, `contracts/api_v1/adapter.py` (puente entry_data↔legacy).

### 2.4 → módulos de dominio (cadena_a/b/c, pyg, costos_financieros, vision_*, cost_to_serve, riesgo)
- **cadena_a**: `domain/payroll/*`, `domain/staffing/*`, `domain/services/{nomina_cargada,servicio_catalogo,special_roles_calculator}.py`, `application/use_cases/{build_payroll,build_staffing}.py`, `api/v1/simulation/chain_a_router.py`, `contracts/.../cadena_a.py`.
- **cadena_b / cadena_c**: `api/v1/simulation/chain_{b,c}_router.py` + `_chain_bc_parametros.py` (→ shared util), `contracts/.../cadena_{b,c}.py`.
- **pyg**: `domain/profitability/*`, `api/v1/simulation/vision_router.py`, `contracts/.../response/visions.py::VisionPyGV1`.
- **costos_financieros**: `domain/financial/*`.
- **vision_tarifas**: `application/use_cases/build_scenarios.py`, `contracts/.../request/escenarios.py`, `response/{pricing,visions::VisionTarifasV1}.py`.
- **cost_to_serve / vision_imprimible / riesgo**: porciones de `contracts/.../response/visions.py` + `domain/models/visions.py` (según DECISIÓN 1).

## 3. Archivos a PARTIR (y cómo)

| Archivo | Líneas | Partición propuesta |
|---|--:|---|
| `domain/models/panel.py` | 446 | Por dominio: base (PricingRequest/PanelDeControl/Poliza*/Escenario)→shared; PerfilCadenaA/ParametrosNomina/NoPayroll/Indexacion→cadena_a; CanalCadenaB/ParametrosCadenaB/ItemOpex/Miembro/Dispositivo→cadena_b; CanalCadenaC/ParametrosCadenaC→cadena_c; ParametrosCalculo→calculator. **(condicionado a DECISIÓN 1)** |
| `domain/models/results.py` | 272 | Agregados (CostosTotalesMes/CostosFinancierosMes/PyGMensual/KPIsDeal/PricingResult)→shared; ResultadoNomina/NoPayroll→cadena_a; ResultadoCadenaB→cadena_b; ResultadoCadenaC→cadena_c. |
| `domain/models/visions.py` | 818 | CTS→cost_to_serve; Tarifas→vision_tarifas; PyG/Waterfall→pyg; Imprimible→vision_imprimible; Riesgo→riesgo. |
| `contracts/api_v1/response/visions.py` | 428 | VisionTarifasV1→vision_tarifas; VisionPyGV1→pyg; CostToServeV1→cost_to_serve; WaterfallV1→vision_imprimible; VisionsBundleV1→shared. |
| `api/v1/simulation/_chain_bc_parametros.py` | 51 | Compartido B/C → `shared` util (no duplicar). |

> **Nota de riesgo:** aunque panel/results/visions no se importan entre sí, **68 archivos** los consumen y los agregados cruzan dominios. Partirlos crea imports cross-módulo (pyg→cadena_a, etc.) que deben respetar el DAG de dependencias. Ver DECISIÓN 1.

## 4. Conflictos / hallazgos que requieren decisión

### DECISIÓN 1 — domain/models: ¿partir por módulo o `modules/shared/models`?
- **A (shared, recomendado, bajo riesgo):** `modules/shared/models/{panel,results,visions}.py` unificado; todos importan de shared. Desvía levemente de "cada módulo su models.py" pero evita 68 reescrituras frágiles y acoplamiento cross-módulo.
- **B (split puro):** cada módulo su `models.py`; imports cross-módulo siguiendo el DAG. Máxima pureza, alto churn y riesgo de ciclos.

### DECISIÓN 2 — `simulation/chain_a|b|c/` (dto+service+validator): CÓDIGO MUERTO (0 importadores)
- **A (recomendado):** borrar (commit separado "remove dead chain services") — no migrar basura a módulos limpios.
- **B:** cuarentena en `_legacy/` y migrar después.
- **C:** investigar si hay un consumidor externo (API futura) antes de borrar.

### DECISIÓN 3 — punto de partida del refactor
- **A (recomendado):** construir sobre `refactor/modular-structure` (reutiliza los 20 archivos ya movidos y validados).
- **B:** empezar limpio desde `engine-v2` (descarta el Hybrid; rehace todo).

### DECISIÓN 4 — profundidad intra-módulo
- El target del usuario muestra archivos planos (`router.py, engine.py, models.py, serializer.py, utils.py, tests/`).
- Los audits proponen subcarpetas (`api/routers/`, `contracts/`, `domain/`, `services/`, `orchestrators/`).
- **Recomendado:** plano por defecto; subcarpeta solo cuando un módulo tenga >~8 archivos (p.ej. parametrizacion con gn/hr/op).

### DECISIÓN 5 — `interfaces/` (vacío) y scripts doc raíz
- `interfaces/{azure,excel,cli,http}` están vacíos → **borrar** (reservar solo si hay plan WAVE 11 concreto).
- Scripts doc raíz → `scripts/` o borrar.

## 5. Plan de fases propuesto (con dependencias)

> Mismo método que el Hybrid: fases atómicas, shim temporal, gate por fase (1249 pass/57 fail + C40–C47 Δ=0), commit por fase, consolidación de imports al final.

| Fase | Contenido | Depende de | Riesgo |
|---|---|---|---|
| P1 | `modules/shared/` foundation: `shared/*`, `audit/*`, `config/business_rules`, `domain/{constants,shared/*}` | — | Medio (40+ imports) |
| P2 | `shared/infrastructure`: `infrastructure/{config,storage,lineage,logging}` | P1 | **Alto** (config 43, storage 26/24) |
| P3 | `modules/parametrizacion`: repositories/ + infrastructure/parametrization* + parametrization/{gn,hr,op} + interface | P1,P2 | Medio |
| P4 | **DECISIÓN 1**: domain/models → shared o split | P1 | **Alto** (68 imports) |
| P5 | domain subpkgs → dominios (payroll/staffing/services→cadena_a; financial→cf; profitability→pyg; pricing→calculator) | P4 | Medio |
| P6 | `adapters/` → calculator (+ data_provenance→shared) | P1,P4 | Bajo |
| P7 | `contracts/` → split por dominio + shared (incl. visions.py 428) | P4 | Medio |
| P8 | `application/` use_cases→dominios; ports/lineage/versioning/certification→shared | P1–P5 | Medio |
| P9 | `simulation/` persistencia→shared/persistence; **borrar chain_*/ muerto** (DECISIÓN 2) | P1,P2 | Bajo |
| P10 | `api/` routers→`modules/<x>/router.py` + shared; `app.py` re-wire | P1–P9 | **Alto** (wiring HTTP) |
| P11 | `validators/`→shared/validation | P1 | Bajo |
| P12 | Consolidación imports (repoint ~200 archivos) + borrar shims + borrar carpetas raíz vacías + `interfaces/` + scripts | todas | **Alto** |

## 6. Estimación de esfuerzo

- **Volumen:** ~200 .py a mover/partir (vs 20 del Hybrid). Splits de monolíticos (panel/results/visions/visions-contract) son lo más costoso.
- **Fases:** ~12 mayores; varias se subdividen → estimado **25–35 commits atómicos**.
- **Comparación:** ~3× el Hybrid (que tomó esta sesión completa). 
- **Mayor riesgo:** P2 (config/storage 40+ imports), P4 (models 68 imports), P10 (re-wire HTTP). Se mitiga con shims por fase + gate.
- **Pre-requisito de seguridad:** mantener el método de gate (full-suite diff vs baseline + C40–C47) idéntico al Hybrid.

## 7. Decisiones resueltas (2026-06-02)

1. **domain/models → `modules/shared/models/` UNIFICADO** (no split por módulo). Elimina P4-split; P4 pasa a ser "mover los 3 archivos a shared/models".
2. **`simulation/chain_a|b|c/` (muerto) → BORRAR** en commit separado dentro de P9.
3. **Base = `refactor/modular-structure`** (se construye encima; se reutilizan los 20 archivos ya movidos).
4. **Layout PLANO** por módulo; subcarpeta solo si el módulo supera ~8 archivos (p.ej. `parametrizacion/{gn,hr,op}/`).
5. (recomendado, no bloqueante) `interfaces/` vacío → **borrar**; scripts doc raíz → `scripts/`.

### Ajustes al plan por las decisiones
- **P4** se simplifica: `domain/models/{panel,results,visions}.py` → `modules/shared/models/` tal cual (sin partir). Riesgo baja de Alto a Medio.
- **P9** incluye `git rm` de `simulation/chain_a|b|c/{service,dto,validator,__init__}.py` (verificar 0 importadores justo antes).
- `modules/shared_calc/utils.py` se fusiona dentro de `modules/shared/` (deja de existir shared_calc).
- Nueva rama de trabajo: `refactor/modular-pure` cortada desde `refactor/modular-structure`.

**Estado:** plan finalizado. Pendiente únicamente el GO explícito para ejecutar P1.
