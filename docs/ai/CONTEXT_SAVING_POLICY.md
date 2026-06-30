# Política de ahorro de contexto en Claude Code

**Objetivo:** Reducir tokens consumidos por sesión evitando lectura de documentación innecesaria.

---

## Principios

1. **Lectura selectiva:** Lee solo lo necesario para la tarea específica.
2. **Clasificación previa:** Usa `ROUTING_MATRIX.md` antes de empezar.
3. **No cargar completo:** Filtra logs, reportes, histórico según la tarea.
4. **Verificación mínima:** Ejecuta solo validaciones relevantes a la tarea.

---

## Qué SIEMPRE leer

| Archivo | Cuándo | Líneas |
|---|---|---|
| CLAUDE.md | Inicio de cualquier sesión | 500 |
| ROUTING_MATRIX.md | Para clasificar la tarea | 69 |

**Total mínimo: ~570 líneas (~18 KB)**

---

## Qué leer SEGÚN LA TAREA

### Tarea: Inventario / grep / búsqueda de referencias
- **Leer:** archivos encontrados por grep solamente
- **NO leer:** backend completo, todos los módulos, Excel
- **Validación:** grep + resumen textual
- **Worker:** scanner-agent (haiku)
- **Tiempo estimado:** 5-10 min

Ejemplo:
```bash
# En lugar de leer todo, ejecuta:
grep -r "pattern" modules tests --include="*.py"
# Luego lee solo los 2-3 archivos mostrados
```

---

### Tarea: Refactor mecánico (renombrado, limpieza, orden)
- **Leer:** módulo afectado + tests directos del módulo
- **NO leer:** Excel completo, reportes antiguos, VALIDATION.md histórico
- **Validación:** pytest del módulo afectado únicamente
- **Worker:** backend-agent o cleanup-agent (sonnet)
- **Tiempo estimado:** 15-30 min
- **Ahorro:** Evitar TASK_STATE.md histórico, CODE_REVIEW_WORKFLOW.md

Ejemplo:
```bash
# Lectura:
# 1. Leer modules/foo/bar.py (archivo a refactorizar)
# 2. Leer tests/test_bar.py (tests del módulo)

# Validación:
PYTHONPATH=$(pwd) pytest backend_nexa/tests/test_bar.py -q
```

---

### Tarea: Paridad Excel V2-8 / cambios de fórmulas
- **Leer:** 
  - `docs/refactor/excel_v28/findings.csv` (fuente de verdad)
  - Hoja/mapa específico del Excel
  - Módulo calculador afectado (ej. `payroll_calculator.py`)
- **NO leer:** todo el Excel, todo el backend, histórico de validaciones
- **Validación:** test de paridad específico solamente
- **Worker:** business-rules-agent (opus)
- **Tiempo estimado:** 30-60 min
- **Ahorro:** Evitar leer VALIDATION.md completo

Ejemplo:
```bash
# Lectura:
# 1. Leer docs/refactor/excel_v28/findings.csv (primer 50 filas)
# 2. Leer una hoja específica del Excel (no todas)
# 3. Leer función específica del calculador

# Validación:
PYTHONPATH=$(pwd) pytest backend_nexa/tests/parity/test_nomina_v28.py::test_specific -q
```

---

### Tarea: Traducción puntual de fórmula Excel → código
- **Leer:**
  - Celda específica / rango del Excel
  - Función destino en código
  - Test asociado a la función
- **NO leer:** hojas no relacionadas, módulos no relacionados
- **Validación:** test puntual de la función
- **Worker:** backend-agent (sonnet)
- **Tiempo estimado:** 10-20 min
- **Ahorro:** Máximo (enfoque quirúrgico)

Ejemplo:
```bash
# Lectura:
# 1. Excel: Hoja "Nomina" celda K45
# 2. Código: modules/payroll/calculator.py línea 123
# 3. Test: tests/test_payroll.py::test_k45_formula

# Validación:
PYTHONPATH=$(pwd) pytest backend_nexa/tests/test_payroll.py::test_k45_formula -q
```

---

### Tarea: Seguridad / auditoría de main/app
- **Leer:** 
  - backend_nexa/app.py
  - modules/shared/infrastructure/ (security-related)
  - Dependencias críticas (ej. `db/container.py`)
- **NO leer:** módulos de negocio, Excel, reportes
- **Validación:** smoke tests de seguridad (CORS, auth, secrets)
- **Worker:** security-agent (opus o sonnet según riesgo)
- **Tiempo estimado:** 20-45 min
- **Ahorro:** Evitar todo el negocio

---

### Tarea: Documentación (crear, actualizar, refactor)
- **Leer:** archivos de documentación afectados solamente
- **NO leer:** código completo, tests, Excel
- **Validación:** diff de markdown
- **Worker:** docs-agent (haiku o sonnet)
- **Tiempo estimado:** 10-30 min
- **Ahorro:** Mínimo contexto técnico

Ejemplo:
```bash
# Lectura:
# 1. docs/ai/FILENAME.md (si existe)
# 2. CLAUDE.md (si se actualiza)

# Validación:
git diff -- docs/ai/FILENAME.md
```

---

## Qué NO leer salvo indicación explícita

| Archivo | Razón | Cuándo SÍ leer |
|---|---|---|
| **VALIDATION.md** | Histórico de validaciones pasadas (1072 líneas) | Solo si debugueas fallos historiales |
| **TASK_STATE.md** | Histórico de fases completadas (507 líneas) | Solo si necesitas entender cambios previos |
| **CODE_REVIEW_WORKFLOW.md** | Workflow detallado (486 líneas) | Si la tarea es revisar código |
| **QUICK_START.md** | Guía de comandos (399 líneas) | Si es tu primera vez en el proyecto |
| **Reportes en `reports/`** | Diffetrials pasados, Excel diffs | Solo si investigas un error específico |
| **`scripts/parity/`** | Scripts de comparación | Solo si escribes nuevos tests de paridad |

---

## Comandos recomendados para sesiones baratas

```bash
# 1. Inventario barato (haiku)
claude --model haiku "Haz grep de X en codebase. Reporta archivos encontrados"

# 2. Refactor controlado (sonnet)
claude --model sonnet --permission-mode plan \
  "Refactoriza foo() para X. Módulo afectado: Y"

# 3. RCA / paridad compleja (opus)
claude --model opus --permission-mode plan \
  "Investiga drift en fórmula X vs Excel. Fuente: findings.csv"

# 4. Consulta corta sin sesión larga (cualquier modelo)
claude -p --max-turns 3 "Qué hace la función X?"

# 5. Documentación simple (haiku)
claude --model haiku \
  "Actualiza docs/ai/FILE.md con: X"
```

---

## Matriz de decisión rápida

| Pregunta | SÍ → | NO → |
|---|---|---|
| ¿Es solo grep/búsqueda? | haiku, lee grep results | sonnet/opus |
| ¿Es refactor de 1 módulo? | sonnet, lee módulo + tests | opus |
| ¿Toca parámetros Excel? | opus, lee findings.csv + hoja | sonnet |
| ¿Es documentación? | haiku, lee docs affected | sonnet/opus |
| ¿Es seguridad? | opus, lee app.py + security | haiku |
| ¿Es nuevo feature? | opus, lee todo necesario | haiku |

---

## Validación mínima por tipo de tarea

| Tarea | Validación mínima |
|---|---|
| Inventario | Grep + manual read of found files |
| Refactor mecánico | pytest del módulo |
| Fórmula puntual | Test específico de la función |
| Paridad Excel | Test parity específico |
| Documentación | git diff de markdown |
| Seguridad | Smoke tests de seguridad |

---

## Ahorro estimado

| Escenario | Contexto mínimo | Contexto actual | Ahorro |
|---|---|---|---|
| Inventario (grep) | 20 KB (findings) | 170 KB | **88%** |
| Refactor (1 módulo) | 80 KB | 170 KB | **53%** |
| Paridad puntual | 100 KB | 170 KB | **41%** |
| Documentación | 50 KB | 170 KB | **71%** |
| Seguridad | 90 KB | 170 KB | **47%** |

---

## Regla de oro

**Antes de leer cualquier archivo, preguntate: ¿Realmente lo necesito para esta tarea específica?**

Si la respuesta es "no", no lo leas.
