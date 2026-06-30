# Skill: nexa-prompt-routing

## When to use

Generar prompts eficientes para Claude Code, Cursor o Copilot cuando la tarea es compleja o transversal y necesitas asegurarte de elegir el worker, modelo y contexto correcto antes de actuar. Aplica especialmente cuando el scope no está claro o hay riesgo de gastar tokens innecesariamente.

**Riesgo esperado: bajo** — no modifica código ni datos; solo genera o evalúa un prompt.

## When not to use

- Tareas simples con scope claro (leer un archivo, grep, cambio de una línea).
- Cuando ya sabes el worker y el modelo y tienes el contexto mínimo.
- Cuando la tarea ya está en curso y el routing ya se hizo.

## Context to read first

1. `CLAUDE.md` — routing policy, workers disponibles, reglas críticas.
2. `docs/ai/ROUTING_MATRIX.md` — tabla de tarea → worker → modelo → contexto mínimo.
3. `docs/ai/CONTEXT_SAVING_POLICY.md` — qué NO leer por tipo de tarea.

**Solo estos tres archivos.** No leer código, calculadores, tests ni Excel antes de hacer el routing.

## Operating rules

1. Antes de actuar, responder las cuatro preguntas de routing:
   - ¿Qué tipo de tarea es? (inventario / refactor / paridad / backend / seguridad / docs)
   - ¿Qué worker y modelo corresponden? (ver ROUTING_MATRIX.md)
   - ¿Cuál es el riesgo? (bajo / medio / alto)
   - ¿Cuáles son los archivos mínimos a leer para esta tarea?
2. Incluir en el prompt:
   - Skill a usar (de `docs/ai/skills/`).
   - Archivos mínimos a leer.
   - Qué NO hacer (acciones prohibidas según la skill).
   - Validación esperada al finalizar.
3. Preferir prompts cortos y concretos. Un prompt de 5 líneas bien estructurado supera a uno de 50 líneas genérico.
4. No usar `/agents` ni otros slash commands — generan prompts que dependen del entorno de quien los ejecuta.
5. Si la tarea toca fórmulas de negocio → escalar a `business-rules-agent` + opus + citar hoja/celda Excel.
7. Si la tarea toca arquitectura o módulos transversales → escalar a `architecture-agent` + opus.
8. Si la tarea es documentación pura → usar `docs-agent` + haiku para ahorrar tokens.

## Forbidden actions

- Generar prompts que lean todo `CLAUDE.md` + todos los `docs/ai/` + el módulo completo para una tarea simple.
- Usar `/agents` en prompts generados.
- Escalar a opus para tareas que un haiku o sonnet puede resolver.
- Incluir archivos históricos (`VALIDATION.md`, `TASK_STATE.md`) en el contexto mínimo salvo necesidad explícita.
- Generar prompts que regeneren baselines o modifiquen golden tests sin instrucción explícita del usuario.

## Validation

El prompt generado debe responder afirmativamente a:

- [ ] ¿Especifica el worker y modelo?
- [ ] ¿Lista solo los archivos mínimos necesarios?
- [ ] ¿Incluye una sección "qué NO hacer"?
- [ ] ¿Incluye validación esperada?
- [ ] ¿Evita instrucciones que carguen contexto innecesario?
- [ ] ¿Usa la skill adecuada de `docs/ai/skills/`?

## Final response format

```md
## Prompt generado

<prompt listo para usar>

## Routing aplicado
- Tarea: <tipo>
- Worker: <worker>
- Modelo: <modelo>
- Riesgo: <bajo/medio/alto>
- Contexto mínimo: <archivos>
- Skills usadas: <lista>
```

---

**Ejemplo de invocación:**

```
Usando la skill nexa-prompt-routing:
Necesito un prompt para investigar por qué el test
tests/parity/v28/test_outputs_v28.py::test_cts_cadena_a falla.
Elige worker, modelo, contexto mínimo y skill adecuada.
No leer código todavía — solo generar el prompt de routing.
```
