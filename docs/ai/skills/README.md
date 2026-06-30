# Skills NEXA — Índice operativo

Las skills son fragmentos de contexto reutilizable para Claude Code, Cursor y Copilot. Su objetivo es **reducir el consumo de tokens** cargando solo el contexto relevante para el tipo de tarea, en lugar de volcar todo `CLAUDE.md` y `docs/ai/` en cada sesión.

---

## ¿Qué son estas skills?

Cada skill es un archivo Markdown que describe:
- **Cuándo usar** esa forma de trabajar.
- **Qué archivos leer mínimo** antes de actuar.
- **Reglas operativas** para esa tarea.
- **Acciones prohibidas** para evitar errores costosos.
- **Validación** recomendada al finalizar.
- **Formato de respuesta** esperado.

No son ejecutables automáticamente — son instrucciones que pegas (o referencias) en tu prompt para que el AI tenga el contexto operativo correcto desde el inicio.

---

## Diferencia entre estos recursos

| Recurso | Propósito | Cuándo leer |
|---|---|---|
| **Esta skill** (`docs/ai/skills/<nombre>.md`) | Contexto operativo mínimo para un tipo de tarea: qué leer, qué no hacer, validación esperada | Al inicio de una tarea de ese tipo |
| **`docs/ai/skills/README.md`** (este archivo) | Índice: qué skills existen, árbol de decisión, ejemplos de invocación | Cuando no sabes qué skill usar |
| **`CLAUDE.md`** | Reglas globales del proyecto: arquitectura, comandos, convenciones estables | Siempre, como contexto base |
| **`docs/ai/ROUTING_MATRIX.md`** | Tabla completa tarea → worker → modelo → contexto mínimo | Para confirmar qué worker/modelo usar y si hay una skill mejor |

Las skills **no reemplazan** `CLAUDE.md` — lo complementan. Cada skill asume que `CLAUDE.md` ya fue leído (o al menos sus secciones relevantes).

---

## Skills disponibles

### Skills de contexto general

| Skill | Cuándo usar | Worker | Modelo | Riesgo |
|---|---|---|---|---|
| [nexa-backend-context](nexa-backend-context.md) | Cualquier tarea backend (endpoints, servicios, DTOs, repos) | backend-agent | sonnet | medio |
| [nexa-refactor-controlled](nexa-refactor-controlled.md) | Refactors seguros sin cambios funcionales | backend-agent / cleanup-agent | sonnet / haiku | bajo–medio |
| [nexa-golden-validation](nexa-golden-validation.md) | Golden tests, snapshots, paridad Excel, RCA de fallos | qa-agent / business-rules-agent | sonnet / opus | alto |
| [nexa-excel-migration](nexa-excel-migration.md) | Comparar versiones Excel (V2-7 → V2-8), analizar cambios de fórmulas | business-rules-agent | opus | medio |
| [nexa-security-review](nexa-security-review.md) | Seguridad FastAPI, production readiness, CORS, logging | security-agent | opus | alto |
| [nexa-cosmos-integration](nexa-cosmos-integration.md) | Cosmos DB: configuración, smoke tests, certificación | infra-agent / backend-agent | sonnet / opus | alto |
| [nexa-prompt-routing](nexa-prompt-routing.md) | Generar prompts eficientes, elegir worker/modelo/contexto | coordinator-agent | sonnet | bajo |

### Skills de flujos V2-8 y operaciones guarded

| Skill | Cuándo usar | Modelo | Riesgo |
|---|---|---|---|
| [prompt-token-saver](prompt-token-saver.md) | Convertir tarea técnica en prompt eficiente | sonnet | bajo |
| [v28-parity-rca](v28-parity-rca.md) | Auditar deltas Excel V2-8 vs backend sin tocar código | opus | alto |
| [backend-safe-fix](backend-safe-fix.md) | Aplicar fix mínimo con RCA existente y validación progresiva | sonnet / opus | medio |
| [baseline-refresh-guarded](baseline-refresh-guarded.md) | Regenerar baseline con drift documentado y aprobado | sonnet | alto |
| [v28-provider-patch](v28-provider-patch.md) | Parchear provider/fixture V2-8 con valor trazado desde Excel | sonnet / opus | medio |

---

## Cómo usarlas en un prompt

### Opción 1 — Referencia directa

```
Usando la skill nexa-backend-context:
[descripción de tu tarea]
```

El AI debe leer el archivo de skill correspondiente (o tenerlo como contexto) y aplicar sus reglas.

### Opción 2 — Incluir contenido completo

Copia el contenido de la skill al inicio de tu prompt cuando no hay referencia automática al repo (ej. Cursor sin contexto de archivo).

### Opción 3 — En Claude Code (este repo)

```
Lee docs/ai/skills/nexa-backend-context.md y aplica sus reglas para:
[descripción de tu tarea]
```

---

## Cómo evitar gasto innecesario de tokens

1. **Elige la skill más específica** — no uses `nexa-backend-context` para una tarea de seguridad.
2. **Lee solo el módulo afectado** — las skills especifican qué leer; no abras `modules/` completo.
3. **Usa el modelo más barato que resuelva la tarea** — ver columna "Modelo" de la tabla.
4. **No cargues histórico** — `VALIDATION.md`, `TASK_STATE.md`, reportes en `reports/` solo cuando sean estrictamente necesarios.
5. **Para búsquedas** — usa `scanner-agent` con haiku antes de abrir archivos.
6. **Para paridad Excel** — lee primero `findings.csv`, no todo el Excel.

Ahorro estimado por skill (orden de magnitud — varía según la tarea concreta):

| Skill | Contexto con skill | Sin skill (carga masiva) | Ahorro aprox. |
|---|---|---|---|
| nexa-backend-context | ~30 KB | ~170 KB | ~82% |
| nexa-refactor-controlled | ~25 KB | ~150 KB | ~83% |
| nexa-golden-validation | ~40 KB | ~170 KB | ~76% |
| nexa-excel-migration | ~50 KB | ~200 KB | ~75% |
| nexa-security-review | ~20 KB | ~170 KB | ~88% |
| nexa-cosmos-integration | ~15 KB | ~170 KB | ~91% |
| nexa-prompt-routing | ~10 KB | ~170 KB | ~94% |

> Los números asumen que sin skill se carga `CLAUDE.md` completo + todos los `docs/ai/` + el módulo completo. Con skill, solo se carga lo mínimo indicado en "Context to read first".

---

## Ejemplos de invocación por skill

### nexa-backend-context
```
Lee docs/ai/skills/nexa-backend-context.md.
Módulo: modules/calculator_motor/formulas/billing.py
Tarea: agregar campo `factor_descuento` al resultado de `calcular_factor_billing`.
No tocar parametrizaciones ni baselines.
```

### nexa-refactor-controlled
```
Lee docs/ai/skills/nexa-refactor-controlled.md.
Mover función `_calcular_cts_cadena_a` de
  modules/calculator_motor/formulas/cts.py
  a modules/calculator_motor/formulas/cts_cadenas.py (nuevo archivo).
No cambiar firma ni lógica. Ejecutar pytest tests/calculator_motor/ al finalizar.
```

### nexa-golden-validation
```
Lee docs/ai/skills/nexa-golden-validation.md.
El test tests/parity/v28/test_outputs_v28.py::test_vision_tarifas falla.
Delta: backend=1250.00, expected=1280.00.
Clasificar el tipo de mismatch. No regenerar snapshot.
Leer findings.csv antes de actuar.
```

### nexa-excel-migration
```
Lee docs/ai/skills/nexa-excel-migration.md.
Analizar cambios en la hoja 'CTS' entre V2-7 y V2-8.
Generar reporte técnico de impacto backend.
No implementar cambios — solo análisis y tabla de gaps.
```

### nexa-security-review
```
Lee docs/ai/skills/nexa-security-review.md.
Revisar: app.py, modules/shared/responses.py, db/container.py.
Verificar exposición de str(exc), CORS, APP_ENV gate.
No cambiar comportamiento funcional. Reportar hallazgos con severidad.
```

### nexa-cosmos-integration
```
Lee docs/ai/skills/nexa-cosmos-integration.md.
Ejecutar smoke tests cosmos_integration contra staging.
Reportar si la integración queda como "preparada" o "certificada".
```

### nexa-prompt-routing
```
Lee docs/ai/skills/nexa-prompt-routing.md.
Generar prompt para investigar por qué falla
  tests/parity/v28/test_outputs_v28.py::test_cts_cadena_a.
Elegir worker, modelo, contexto mínimo y skill. No leer código todavía.
```

### prompt-token-saver
```
Lee docs/ai/skills/prompt-token-saver.md y aplica sus reglas para:
Tarea: el test test_vision_tarifas_canal_digital falla con delta -30 COP/tx.
Generar el prompt de routing — no leer código todavía.
```

### v28-parity-rca
```
Lee docs/ai/skills/v28-parity-rca.md y aplica sus reglas para:
Delta test_cts_cadena_a: backend=6155.30, expected=6224.58 (-69.27 COP/tx).
Trazar celdas 'Condiciones Cadena A'!E135 y 'Nomina Loaded'!C329.
No aplicar fix — solo RCA y matriz de fixability.
```

### backend-safe-fix
```
Lee docs/ai/skills/backend-safe-fix.md y aplica sus reglas para:
RCA existente: FORMULA_BUG en fte_supervisor (findings.csv línea 42).
Localizar con rg en modules/calculator_motor/formulas/nomina.py.
Solo el bloque afectado. Ejecutar pytest tests/parity/v28/test_outputs_v28.py primero.
```

### baseline-refresh-guarded
```
Lee docs/ai/skills/baseline-refresh-guarded.md y aplica sus reglas para:
Fix de med_seg aprobado. make validate-excel PASS.
Documentar drift antes de ejecutar make baseline.
Confirmar con make all al final.
```

### v28-provider-patch
```
Lee docs/ai/skills/v28-provider-patch.md y aplica sus reglas para:
PROVIDER_MISMATCH: med_seg[Bogota].valor en _v28_deal_provider.py.
Excel 'Nomina Loaded'!C329 = 60800 (provider tiene 60.8).
Confirmar con openpyxl antes de editar. Solo tests/refactor/.
```

---

## Cuándo usar cada skill — árbol de decisión

```
¿Qué tipo de tarea es?
├─ No sé por dónde empezar / scope difuso      → prompt-token-saver
├─ Buscar/inventario/grep                      → scanner-agent + haiku (sin skill)
├─ Backend (endpoint/servicio/DTO)             → nexa-backend-context
├─ Refactor sin cambio funcional               → nexa-refactor-controlled
│
├─ Test parity V2-8 falla / delta sin RCA      → v28-parity-rca
├─ RCA listo, aplicar fix en módulo            → backend-safe-fix
├─ PROVIDER_MISMATCH, parchear fixture         → v28-provider-patch
├─ Fix aprobado, baseline desactualizado       → baseline-refresh-guarded
│
├─ Test fallido / golden / snapshot / RCA      → nexa-golden-validation
├─ Análisis Excel V2-7 → V2-8                 → nexa-excel-migration
├─ Seguridad / production readiness            → nexa-security-review
├─ Cosmos DB                                   → nexa-cosmos-integration
└─ No sé qué worker/modelo usar                → nexa-prompt-routing
```

---

## Referencias

- [CLAUDE.md](../../../CLAUDE.md) — reglas globales del proyecto
- [ROUTING_MATRIX.md](../ROUTING_MATRIX.md) — tabla completa de tarea → worker → modelo
- [CONTEXT_SAVING_POLICY.md](../CONTEXT_SAVING_POLICY.md) — política de ahorro de tokens
