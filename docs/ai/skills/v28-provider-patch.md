# v28-provider-patch

**Riesgo esperado: medio** — modifica solo fixtures/providers de tests V2-8; no toca código productivo ni baselines, pero un valor incorrecto introduce deuda de paridad.

## Propósito

Aplicar ajustes en providers y fixtures de test V2-8 con valores trazados directamente desde celdas del Excel, sin tocar módulos productivos. Toda modificación debe incluir comentario de trazabilidad con hoja, celda y fórmula original.

## Cuándo usar

- Cuando el RCA identifica un `PROVIDER_MISMATCH`: el provider de test tiene un valor diferente al Excel V2-8 activo.
- Para actualizar `_v28_deal_provider.py` o fixtures en `tests/refactor/` o `tests/golden/` con valores trazados.
- Cuando un campo de HR/GN/OP en el provider de test está usando fallback incorrecto y la corrección es verificable en Excel.

## Cuándo NO usar

- Sin haber confirmado el valor en Excel con openpyxl — nunca parchear a ciegas.
- Si el fix requiere modificar `modules/` (motor productivo) — usar `backend-safe-fix`.
- Si el fix requiere cambiar `storage/parametrization/` (parametrización activa productiva) — escalar al usuario.
- Para regenerar baselines — usar `baseline-refresh-guarded` en sesión separada.
- Si el campo no tiene celda Excel identificada — reportar como `SOURCE_NOT_FOUND` y escalar.

## Lectura mínima

1. RCA del PROVIDER_MISMATCH: gap documentado en `findings.csv` o TASK_STATE.md.
2. Provider de test afectado: `tests/refactor/_v28_deal_provider.py` u otro fixture V2-8.
3. Celda Excel confirmada con openpyxl (valor leído antes de editar).

**No leer:** módulos productivos, storage, toda la suite de tests, Excel completo.

## Archivos que NO debe leer inicialmente

- `modules/` (ningún archivo de código productivo)
- `storage/` (salvo si se confirma que el provider carga desde allí)
- `docs/ai/TASK_STATE.md` completo (solo el fragmento del RCA)
- Hojas Excel no relacionadas con el campo a parchear
- `reports/` (usar findings.csv como fuente)

## Flujo de trabajo

1. **Confirmar valor en Excel** con openpyxl antes de editar cualquier archivo:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook("Nexa - Pricing - Simulador - V2-8.xlsx", data_only=True)
   ws = wb["<Nombre_Hoja>"]
   print(ws["<Celda>"].value)  # debe coincidir con el valor esperado
   ```
   Si el valor no coincide con el RCA → **parar**, el RCA puede ser incorrecto.

2. **Localizar el campo en el provider**:
   ```bash
   rg "<nombre_campo>" tests/refactor/ tests/golden/ --type py -n
   ```

3. **Leer solo el bloque afectado** del provider (no el archivo completo si es largo).

4. **Aplicar el patch con comentario de trazabilidad obligatorio**:
   ```python
   # Excel V2-8 · '<Hoja>'!<Celda> · valor: <valor>
   # Diferencia vs activo: <descripción breve>
   "<nombre_campo>": <valor_excel>,
   ```

5. **Validar el test puntual** asociado al campo:
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_test>::<test_name> -v --tb=long -s
   ```

6. **Si pasa, ejecutar validación de paridad V2-8**:
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/parity/v28/ -v --tb=short
   cd backend_nexa && make validate-excel
   ```

7. **Actualizar findings.csv** con el estado del gap (de `PENDING` a `PATCHED` o `FULL_MATCH`).

## Kill-switches

Parar y reportar sin aplicar el patch si:
- El valor en Excel (openpyxl) no coincide con el valor del RCA — posible error en el RCA.
- El campo no está en el provider de test — puede estar en `modules/` (escalar a `backend-safe-fix`).
- El patch requiere modificar `modules/` o `storage/` — fuera de scope de esta skill.
- El test puntual pasa pero `make validate-excel` introduce nuevas discrepancias — el patch tiene efecto secundario.
- Se intenta parchear un valor sin celda Excel identificada — reportar `SOURCE_NOT_FOUND`.
- `request.json` necesita cambios para que el patch funcione — escalar al usuario, requiere decisión de input.

## Validación mínima

```bash
# Test puntual
PYTHONPATH=$(pwd) pytest backend_nexa/tests/<ruta_test>::<test_name> -v --tb=long

# Suite parity V2-8
PYTHONPATH=$(pwd) pytest backend_nexa/tests/parity/v28/ -v --tb=short

# Validar Excel
cd backend_nexa && make validate-excel

# No-regresión baseline
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q
```

## Entregable esperado

```md
## Resultado
<Provider parcheado: archivo, campo, valor anterior → valor nuevo>

## Evidencia
- Celda Excel confirmada: '<Hoja>'!<Celda> = <valor>
- Archivo modificado: <path>:<línea>
- Comentario de trazabilidad: incluido

## Riesgo
<efecto en otros tests que usen el mismo provider>

## Validación
- pytest puntual: PASS
- pytest parity/v28/: PASS
- make validate-excel: PASS/PARTIAL
- pytest -m baseline: PASS

## Siguiente paso
<actualizar findings.csv / baseline-refresh-guarded si aplica>
```

---

**Modelo Anthropic recomendado:** `claude-sonnet-4-6` — operación procedimental con trazabilidad clara. Escalar a `claude-opus-4-8` si el campo afecta múltiples cadenas o el efecto en paridad es incierto.

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/v28-provider-patch.md y aplica sus reglas para:
RCA: PROVIDER_MISMATCH en med_seg[Bogota].valor.
Excel 'Nomina Loaded'!C329 = 60800 (backend provider tiene 60.8 — escala incorrecta).
Parchear tests/refactor/_v28_deal_provider.py.
Confirmar valor con openpyxl antes de editar.
```
