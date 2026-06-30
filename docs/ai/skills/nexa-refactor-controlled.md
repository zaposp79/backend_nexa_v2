# Skill: nexa-refactor-controlled

## When to use

Refactors seguros y acotados: renombrar símbolos, mover módulos, eliminar dead code, reorganizar imports, mejorar estructura interna de un módulo. Aplica cuando el cambio no altera contratos públicos ni lógica de negocio.

**Riesgo esperado: bajo–medio** — no toca lógica de negocio; puede romper imports si no se verifica completamente.

## When not to use

- Cambios funcionales o de fórmulas (usa `nexa-excel-migration` o `nexa-backend-context`).
- Refactors transversales de arquitectura (escalar a `architecture-agent` + opus).
- Cuando hay riesgo de romper golden tests o paridad Excel.
- Limpieza cosmética simple (usa `cleanup-agent` con haiku).

## Context to read first

1. `CLAUDE.md` — sección "Arquitectura" (módulos, alias `nexa_engine`, pipeline).
2. `docs/ai/ROUTING_MATRIX.md` — confirmar que la tarea no escala a opus.
3. Módulo fuente y módulo destino (si hay movimiento).
4. Tests directamente relacionados con los símbolos a refactorizar.

**No leer por defecto:** histórico de fases (`TASK_STATE.md`), Excel, reportes de paridad.

## Operating rules

1. **Cambios mínimos**: modificar solo lo necesario para el objetivo declarado.
2. No cambiar contratos públicos (DTOs, `ApiResponse`, endpoints) salvo instrucción explícita.
3. No mezclar limpieza con cambios funcionales en el mismo commit.
4. No hacer "opportunistic refactor": si ves algo que mejorar fuera del scope, documenta como `# known_debt:` y continúa.
5. Preservar compatibilidad con golden tests: ejecutar tests relacionados antes y después del cambio.
6. Ejecutar tests focalizados primero (`pytest tests/<modulo>/`), no la suite completa salvo que el cambio sea transversal.
7. Si el cambio toca más de 2 módulos, confirmar con el usuario antes de continuar.
8. El alias `nexa_engine` debe mantenerse funcional (`backend_nexa/__init__.py`).
9. Imports siempre desde `nexa_engine.modules.*`.

## Forbidden actions

- Cambiar firmas de métodos públicos sin actualizar todos los consumidores.
- Eliminar shims o aliases sin verificar que no hay consumidores externos.
- Mezclar movimiento de archivos con cambios de lógica en el mismo commit.
- Regenerar baselines como efecto secundario del refactor.
- Modificar `storage/`, `tests/golden/` o `tests/parity/` como parte del refactor.

## Validation

```bash
# Verificar módulo afectado
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<modulo>/ -v --tb=short

# Verificar que no hay imports rotos
cd backend_nexa && python -c "import nexa_engine; print('OK')"

# Si el cambio es transversal, ejecutar gate completo
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -v --tb=short

# Verificar reproducibilidad
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v
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
Usando la skill nexa-refactor-controlled:
Tarea: mover la función `calcular_factor_billing` de
  modules/calculator_motor/formulas/billing.py
  a modules/calculator_motor/formulas/factores.py.
No cambiar la firma ni lógica interna.
No tocar tests golden.
Ejecutar pytest tests/calculator_motor/ después del movimiento.
```
