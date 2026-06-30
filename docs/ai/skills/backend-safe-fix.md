# backend-safe-fix

**Riesgo esperado: medio** — modifica código productivo en un punto mínimo; el riesgo sube a alto si el campo afectado es parte del pipeline de nómina core o paridad crítica.

## Propósito

Aplicar fixes mínimos en el backend con riesgo controlado, partiendo siempre de un RCA existente. Localiza el archivo exacto, modifica solo el punto necesario, preserva comportamiento legacy, agrega tests focalizados y valida progresivamente.

## Cuándo usar

- Cuando existe un RCA documentado (en `findings.csv`, `TASK_STATE.md` o una sesión anterior) y el fix está acotado a un punto específico.
- Para corregir `FORMULA_BUG`, `PROVIDER_MISMATCH` o `INPUT_MISMATCH` con causa raíz confirmada.
- Cuando el cambio no requiere modificar contratos de API, DTOs públicos ni estructura del pipeline.

## Cuándo NO usar

- Sin RCA previo — primero ejecutar `v28-parity-rca`.
- Para cambios arquitectónicos, movimiento de módulos o refactors oportunistas — usar `nexa-refactor-controlled` o escalar a `architecture-agent`.
- Si el fix requiere cambiar `request.json`, contratos de entrada o la estructura del pipeline — escalar al usuario antes de actuar.
- Si el campo afectado es golden value sin evidencia del Excel canónico.

## Lectura mínima

1. RCA existente: fragmento de `docs/refactor/excel_v28/findings.csv` o nota del TASK_STATE.md.
2. Archivo específico del backend donde está el bug (localizado con `rg`).
3. Test puntual asociado al campo afectado.

**No leer:** todo el módulo, toda la suite de tests, VALIDATION.md histórico, Excel completo.

## Archivos que NO debe leer inicialmente

- `modules/` completo (solo el archivo específico del fix)
- `storage/`, `reports/`, `docs/refactor/` (salvo findings.csv del RCA)
- `docs/ai/TASK_STATE.md` (el RCA ya fue leído)
- Excel completo (la celda ya fue trazada en el RCA)

## Flujo de trabajo

1. **Confirmar RCA**: leer el gap en findings.csv o en la nota del RCA anterior. Si no existe RCA, parar y ejecutar `v28-parity-rca` primero.

2. **Localizar el archivo exacto**:
   ```bash
   rg "<nombre_campo_o_función>" modules/ --type py -n
   ```

3. **Leer solo el bloque afectado** — no el archivo completo si es largo. Usar offset+limit en Read.

4. **Aplicar el fix mínimo**:
   - Modificar solo la línea o bloque necesario.
   - Agregar comentario de trazabilidad:
     ```python
     # Excel V2-8 · '<Hoja>'!<Celda> · fórmula: =<original>
     # Traducción: <capa usada>
     ```
   - No limpiar código adyacente ni hacer refactor oportunista.
   - No cambiar firmas de métodos ni contratos Pydantic.

5. **Preservar comportamiento legacy**: si el campo tiene un valor anterior funcional, documentar con `# known_debt:` si el cambio podría afectar tests legacy.

6. **Ejecutar test puntual** (no la suite completa):
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_test>::<test_name> -v --tb=long -s
   ```

7. **Si pasa, ampliar validación progresivamente**:
   ```bash
   # Módulo afectado
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/<modulo>/ -v --tb=short

   # Baseline de no-regresión
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q
   ```

8. **Solo si todo pasa**: considerar `make validate-excel` para confirmar paridad.

## Kill-switches

Parar y reportar sin aplicar el fix si:
- No existe RCA documentado previo — ejecutar `v28-parity-rca` primero.
- El fix requiere modificar más de 1 archivo que no sea un test — el scope creció, escalar al usuario.
- El fix requiere cambiar un contrato Pydantic (DTO de entrada/salida) — necesita análisis de impacto adicional.
- El campo afectado es un valor hardcodeado en el motor productivo — prohibido, documentar como `known_debt`.
- Regenerar baseline es necesario para que el test pase — ejecutar `baseline-refresh-guarded` en sesión separada con autorización.
- El test puntual pasa pero los tests de módulo introducen nuevas regresiones — parar, reportar regresiones nuevas.

## Validación mínima

```bash
# Test puntual del fix
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_test>::<test_name> -v --tb=long

# Módulo afectado
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<modulo>/ -v --tb=short

# Baseline de no-regresión
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q
```

Si el fix es de paridad crítica, agregar:
```bash
cd backend_nexa && make validate-excel
```

## Entregable esperado

```md
## Resultado
<Fix aplicado: archivo, línea, campo corregido>

## Evidencia
- Archivo modificado: <path>:<línea>
- Valor anterior: <valor>
- Valor nuevo: <valor>
- Trazabilidad: Excel '<Hoja>'!<Celda> = <valor>

## Riesgo
<módulos tocados, posibles efectos en tests legacy>

## Validación
<comandos ejecutados y resultado: PASS/FAIL>

## Siguiente paso
<baseline-refresh-guarded si se requiere / cerrar gap en findings.csv>
```

---

**Modelo Anthropic recomendado:** `claude-sonnet-4-6` para fixes de lógica estándar. Escalar a `claude-opus-4-8` si el campo afecta nómina core, paridad de CTS o fórmulas de pricing complejas.

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/backend-safe-fix.md y aplica sus reglas para:
RCA existente: FORMULA_BUG en cálculo de supervisor FTE.
Campo: fte_supervisor en modules/calculator_motor/formulas/nomina.py
Fix: incluir cargos_adicionales en numerador (Excel 'Condiciones Cadena A'!E26).
Ejecutar solo pytest tests/parity/v28/test_outputs_v28.py::test_cts_cadena_a primero.
```
