# prompt-token-saver

**Riesgo esperado: bajo** — no modifica código ni datos; genera o evalúa un prompt.

## Propósito

Convertir una tarea técnica en un prompt Claude Code/Cursor/Copilot optimizado: objetivo único, lectura mínima, fases cortas, kill-switches explícitos y modelo recomendado. Evita prompts gigantes que cargan contexto innecesario.

## Cuándo usar

- Antes de iniciar cualquier tarea técnica compleja o transversal.
- Cuando no está claro qué leer, qué modelo usar o qué validación aplicar.
- Cuando un prompt anterior consumió demasiados tokens sin resolver el problema.
- Cuando la tarea tiene más de dos pasos o toca más de un módulo.

## Cuándo NO usar

- Tareas de una sola acción con scope completamente claro (grep, lectura, cambio de una línea).
- Cuando ya tienes un prompt bien estructurado y probado.
- No usar para generar prompts que regeneren baselines o modifiquen golden tests — eso requiere autorización explícita del usuario.

## Lectura mínima

1. `CLAUDE.md` — sección "Coordinación técnica" (flujo de inicio) y "Reglas críticas".
2. `docs/ai/ROUTING_MATRIX.md` — tabla tarea → worker → modelo.
3. `docs/ai/skills/README.md` — árbol de decisión de skills.

**Solo estos tres archivos.** No leer código hasta que el prompt esté estructurado.

## Archivos que NO debe leer inicialmente

- `modules/` (ningún archivo de código productivo)
- `tests/` (ningún test)
- `storage/`, `reports/`, `docs/refactor/`
- Excel de referencia
- `docs/ai/VALIDATION.md`, `docs/ai/TASK_STATE.md` (histórico)

## Flujo de trabajo

1. **Clasificar la tarea** respondiendo:
   - ¿Cuál es el objetivo único y verificable?
   - ¿Qué tipo de tarea es? (inventario / fix / paridad / refactor / seguridad / docs)
   - ¿Qué archivos mínimos necesita leer el AI para actuar?
   - ¿Qué archivos NO debe leer?
   - ¿Qué worker y modelo corresponden? (ver ROUTING_MATRIX.md)
   - ¿Cuál es el riesgo? (bajo / medio / alto)

2. **Estructurar el prompt** con estas secciones:
   ```
   Skill: <nombre-skill>
   Objetivo: <una sola oración verificable>
   Lectura mínima: <lista corta>
   NO leer: <lista>
   Fases: <máximo 3, cortas>
   Kill-switches: <cuándo parar y reportar sin actuar>
   Validación: <comando o criterio mínimo suficiente>
   Entregable: <formato esperado>
   ```

3. **Verificar el prompt** antes de enviar:
   - [ ] ¿Tiene un solo objetivo?
   - [ ] ¿La lectura mínima es < 5 archivos?
   - [ ] ¿Hay sección "NO leer"?
   - [ ] ¿Hay kill-switches explícitos?
   - [ ] ¿La validación es la mínima suficiente?
   - [ ] ¿El modelo es el más barato que resuelve la tarea?

## Kill-switches

Parar y reportar sin generar el prompt si:
- La tarea requiere leer > 10 archivos para ser entendida — el scope no está claro, pedir al usuario que lo acote.
- La tarea mezcla análisis + implementación + baseline en una sola sesión — separar en prompts distintos.
- Se pide regenerar baselines o modificar golden tests sin autorización explícita — escalar al usuario.
- No se puede identificar un solo objetivo verificable — el prompt no puede ser eficiente sin un objetivo claro.

## Validación mínima

El prompt generado responde afirmativamente a todos los ítems del checklist del paso 3.

## Entregable esperado

```md
## Prompt generado

<prompt listo para copiar-pegar>

## Routing aplicado
- Skill: <skill>
- Worker: <worker>
- Modelo: <modelo>
- Riesgo: <bajo/medio/alto>
- Lectura mínima: <archivos>
- NO leer: <archivos>
```

---

**Modelo Anthropic recomendado:** `claude-sonnet-4-6` (suficiente para estructurar prompts; no requiere capacidad de análisis de negocio)

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/prompt-token-saver.md y aplica sus reglas para:
Tarea: investigar por qué el test v28/test_outputs_v28.py::test_cts_cadena_a falla.
Generar el prompt de routing — no leer código todavía.
```
