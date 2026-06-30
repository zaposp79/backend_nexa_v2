# Skill: nexa-golden-validation

## When to use

Tareas relacionadas con golden tests, snapshots, CTS, Vision Tarifas, P&G, paridad Excel, baseline de reproducibilidad, o validación contra outputs esperados. Aplica cuando un test falla y debes determinar si es un bug real, un fixture desactualizado, deuda conocida o un cambio funcional intencional.

**Riesgo esperado: alto** — una decisión incorrecta puede ocultar regresiones o invalidar evidencia de reproducibilidad.

## When not to use

- Cambios funcionales en fórmulas (usa `nexa-excel-migration`).
- Tareas de refactor sin relación a golden values.
- Exploración del repo sin relación a tests de validación.

## Context to read first

1. `CLAUDE.md` — sección "Tests" y "Política de migración Excel V2-7 → V2-8".
2. Test fallido y su fixture asociada en `tests/golden/` o `tests/parity/`.
3. `docs/refactor/excel_v28/findings.csv` — si la discrepancia puede ser un gap documentado de V2-8.
4. Calculador o función relacionada con el valor que diverge.

**No leer por defecto:** toda la suite de tests, VALIDATION.md histórico, hojas Excel no relacionadas.

## Operating rules

1. **No regenerar snapshots ni baselines sin autorización explícita** del usuario, aunque el test falle.
2. Clasificar el tipo de discrepancia antes de actuar:
   - **Mismatch real**: el código calcula diferente al expected del fixture (bug).
   - **Fixture stale**: el fixture no refleja un cambio intencional ya aprobado.
   - **Deuda conocida**: gap documentado en `findings.csv` con `@pytest.mark.known_delta`.
   - **Cambio funcional**: el comportamiento cambió intencionalmente y el fixture debe actualizarse con autorización.
3. Reportar delta numérico, archivo afectado, y posible causa raíz antes de editar código.
4. Priorizar RCA (Root Cause Analysis) antes de proponer cualquier cambio.
5. Si el mismatch es en paridad Excel, citar hoja y celda antes de modificar el calculador.
6. Validar con tests golden relacionados después de cualquier corrección.
7. Markers registrados en `conftest.py`: `parity`, `baseline`, `slow`, `legacy`, `cosmos_integration`. El marker `known_delta` es una convención de documentación interna (en `findings.csv`) — si se quiere usar como marker pytest, verificar que está declarado en `conftest.py` antes de usarlo.

## Forbidden actions

- Actualizar fixtures o snapshots para que el test pase sin entender la causa.
- Eliminar `@pytest.mark.known_delta` sin investigar si el gap fue resuelto.
- Regenerar `storage/baselines/official.json` sin pasar `make validate-excel` antes.
- Modificar golden values sin evidencia del Excel canónico (`Nexa - Pricing - Simulador - V2-8.xlsx`).
- Cambiar el expected de un test parity para que matchee el output actual sin análisis previo.

## Validation

```bash
# Ejecutar test puntual con máximo detalle
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_test>::<nombre_test> -v --tb=long -s

# Suite parity
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v

# Suite baseline
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v

# Comparar backend vs Excel
cd backend_nexa && make validate-excel

# Audit completo con trazabilidad
cd backend_nexa && make audit
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
Usando la skill nexa-golden-validation:
El test tests/parity/v28/test_outputs_v28.py::test_vision_tarifas_canal_digital falla.
Delta observado: backend=1250.00, expected=1280.00.
Tarea: clasificar el mismatch (bug/stale/deuda/funcional).
No regenerar snapshot. Reportar causa raíz y archivo afectado.
Leer findings.csv antes de proponer cualquier cambio.
```
