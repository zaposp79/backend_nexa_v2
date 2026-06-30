# Skill: nexa-backend-context

## When to use

Contexto base mínimo para cualquier tarea backend en NEXA: leer código existente, entender flujos, implementar endpoints, modificar servicios, crear o ajustar DTOs, revisar repositorios.

**Riesgo esperado: medio** — modifica código productivo; no toca fórmulas de negocio ni baselines.

## When not to use

- Tareas puramente de documentación (usa `docs-agent` con haiku).
- Tareas de paridad Excel o validación de golden values (usa `nexa-golden-validation`).
- Tareas de seguridad o production readiness (usa `nexa-security-review`).
- Búsquedas de inventario o grep simple (usa `scanner-agent` con haiku).

## Context to read first

Lectura mínima ordenada — leer solo lo que aplica a la tarea concreta:

1. `CLAUDE.md` — reglas globales del proyecto, arquitectura, comandos.
2. `docs/ai/ROUTING_MATRIX.md` — elegir worker y modelo antes de actuar.
3. Módulo afectado en `modules/` (solo el módulo, no todo `modules/`).
4. Tests directamente relacionados con el módulo (no la suite completa).

**No leer por defecto:** `docs/ai/VALIDATION.md` (histórico), `docs/ai/TASK_STATE.md` (solo si necesitas historico de fases), Excel de referencia, reportes en `reports/`.

## Operating rules

1. Identifica el módulo afectado antes de tocar código (`modules/calculator_motor/`, `modules/calculator/`, `modules/parametrizacion/`, etc.).
2. Preferir cambios pequeños y localizados. No modificar módulos adyacentes sin justificación explícita.
3. No tocar parametrizaciones frozen (`storage/parametrization/`).
4. No regenerar baselines sin autorización explícita del usuario.
5. No romper contratos públicos: DTOs Pydantic, respuestas `ApiResponse`, formatos de persistencia.
6. Toda inyección de dependencias ocurre en `engine.py` (`_construir_calculadores`) y `db/container.py`, no en los calculadores.
7. Imports siempre desde `nexa_engine.modules.*`. Nunca usar rutas legacy `nexa_engine.modules.calculator.engine`.
8. `IParametrizationProvider` se importa desde `nexa_engine.modules.shared.ports.parametrization_provider`.
9. Documentar deuda conocida con `# known_debt:` en lugar de arreglarla de forma encubierta.
10. Reportar riesgo y archivos tocados al finalizar.

## Forbidden actions

- Modificar `storage/baselines/`, `storage/parametrization/` o snapshots congelados.
- Cambiar fórmulas de negocio sin evidencia del Excel canónico.
- Importar `azure-cosmos` fuera del provider específico.
- Exponer `/docs`, `/redoc`, `/openapi.json` en producción (`APP_ENV != development`).
- Añadir lógica de negocio fuera de los calculadores del pipeline.
- Usar `from nexa_engine.modules.calculator.engine import ...` (ruta legacy).

## Validation

```bash
# Verificar solo el módulo afectado
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_modulo>/ -v --tb=short

# Verificar contratos no rotos
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v

# Check imports circulares (si se modificaron imports)
cd backend_nexa && python -c "import nexa_engine; print('OK')"
```

## Final response format

```md
## Resultado
## Evidencia
## Riesgo
## Validación
## Siguiente paso
```

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/nexa-backend-context.md y aplica sus reglas para:
Módulo: modules/calculator_motor/formulas/
Tarea: agregar campo X al DTO PricingResult sin romper contratos públicos.
```
