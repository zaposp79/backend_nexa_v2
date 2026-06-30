# v28-parity-rca

**Riesgo esperado: alto** — una clasificación incorrecta puede llevar a fixes equivocados que rompen paridad o esconden regresiones.

## Propósito

Auditar deltas entre Excel V2-8 y backend sin tocar código. Trazar cada celda Excel a su fuente backend, clasificar el tipo de discrepancia y producir una matriz de fixability. No aplica fixes en la misma sesión salvo autorización explícita del usuario.

## Cuándo usar

- Cuando un test parity V2-8 falla y el delta no tiene causa raíz documentada.
- Cuando hay discrepancia numérica entre `make validate-excel` y el resultado backend.
- Cuando se quiere auditar un conjunto de celdas Excel antes de iniciar un ciclo de correcciones.
- Antes de aplicar un fix de paridad — para asegurar que el RCA es correcto.

## Cuándo NO usar

- Cuando el RCA ya existe y está documentado en `docs/refactor/excel_v28/findings.csv` — ir directamente a `backend-safe-fix` o `v28-provider-patch`.
- Para implementar fixes (esta skill es solo diagnóstico).
- Para tareas sin relación con paridad Excel V2-8.

## Lectura mínima

1. `CLAUDE.md` — sección "Política de migración Excel V2-7 → V2-8".
2. `docs/refactor/excel_v28/findings.csv` — estado inter-sesión de gaps ya documentados.
3. Test fallido y su fixture en `tests/parity/v28/` o `tests/golden/`.
4. Calculador o función backend relacionada con el valor que diverge.

**No leer por defecto:** toda la suite de tests, VALIDATION.md histórico, hojas Excel no relacionadas con el delta investigado.

## Archivos que NO debe leer inicialmente

- `modules/` completo (solo el calculador específico del delta)
- `storage/` (salvo snapshot puntual si aplica)
- `docs/ai/TASK_STATE.md` (histórico de fases)
- Hojas Excel no relacionadas con el delta analizado
- `reports/` (usar findings.csv como fuente inter-sesión)

## Flujo de trabajo

1. **Leer findings.csv** — verificar si el delta ya está clasificado como `known_delta`, `BLOCKED` o pendiente.

2. **Trazar la celda Excel** usando openpyxl:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook("Nexa - Pricing - Simulador - V2-8.xlsx", data_only=True)
   ws = wb["<Nombre_Hoja>"]
   print(ws["<Celda>"].value)  # valor calculado
   ```
   Citar siempre: `'<Hoja>'!<Celda> = <valor>`.

3. **Trazar la fuente backend** — ubicar con `rg` el campo o fórmula correspondiente:
   ```bash
   rg "<nombre_campo>" modules/ --type py -l
   ```

4. **Clasificar el delta** en una de estas categorías:
   - `INPUT_MISMATCH`: el valor de entrada en `request.json` o deal provider difiere del Excel.
   - `PROVIDER_MISMATCH`: el provider de test (HR/GN/OP) tiene un valor diferente al Excel activo.
   - `FORMULA_BUG`: la fórmula backend es structuralmente diferente a la Excel.
   - `TIMING_MISMATCH`: el valor depende de un orden de cálculo diferente (ej. redondeo, acumulación).
   - `KNOWN_DELTA`: gap documentado, aceptado o en espera de decisión de negocio.

5. **Construir la matriz de fixability**:

   | Campo | Celda Excel | Valor Excel | Valor Backend | Delta | Tipo | Fixable | Scope |
   |---|---|---|---|---|---|---|---|
   | `nombre_campo` | `'Hoja'!C45` | 123.45 | 118.20 | -5.25 | FORMULA_BUG | sí | `backend-safe-fix` |

6. **Documentar en findings.csv** antes de cerrar la sesión — actualizar estado de cada gap analizado.

## Kill-switches

Parar y reportar sin intentar fix si:
- No se puede abrir o leer el Excel con openpyxl — reportar `EXCEL_UNREADABLE`.
- No se puede ubicar la fuente backend con `rg` — reportar `SOURCE_NOT_FOUND`.
- El fix requería cambiar el scope de la sesión (ej. cambia contrato de API) — reportar `SCOPE_CHANGE_REQUIRED`.
- Se detecta intención de hardcodear un dato en el motor productivo — parar inmediatamente, reportar `HARDCODE_FORBIDDEN`.
- El delta tiene múltiples causas simultáneas sin poder aislar la dominante — reportar `MULTI_CAUSE_RCA_REQUIRED`.

## Validación mínima

```bash
# Verificar que findings.csv fue actualizado
head -5 docs/refactor/excel_v28/findings.csv

# Verificar que el test sigue en el estado conocido (sin regresiones nuevas)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/parity/v28/<test_file>.py::<test_name> -v --tb=short

# Smoke check de no-regresión
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -q
```

## Entregable esperado

```md
## Resultado
Resumen del RCA: qué tipo de delta, qué fuente backend.

## Evidencia
- Celda Excel: '<Hoja>'!<Celda> = <valor>
- Fuente backend: <archivo>:<línea> = <valor>
- Delta: <numérico> (<porcentaje>%)

## Matriz de fixability
| Campo | Celda Excel | Valor Excel | Valor Backend | Delta | Tipo | Fixable | Scope |
|---|---|---|---|---|---|---|---|

## Riesgo
<si se aplica el fix sugerido>

## Validación
<comandos ejecutados>

## Siguiente paso
<skill sugerida + instrucción accionable>
```

---

**Modelo Anthropic recomendado:** `claude-opus-4-8` — requiere análisis numérico detallado y razonamiento sobre fórmulas Excel complejas.

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/v28-parity-rca.md y aplica sus reglas para:
Delta en test_cts_cadena_a: backend=6155.30, expected=6224.58 (-69.27 COP/tx).
Trazar celdas Excel 'Condiciones Cadena A'!E135 y 'Nomina Loaded'!C329.
Clasificar el tipo de mismatch. No aplicar fix — solo RCA y matriz de fixability.
Leer findings.csv antes de comenzar.
```
