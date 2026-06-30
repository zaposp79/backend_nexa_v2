# baseline-refresh-guarded

**Riesgo esperado: alto** — regenerar un baseline sin drift documentado oculta regresiones. Esta skill es la última línea de defensa antes de sobrescribir evidencia de reproducibilidad.

## Propósito

Regenerar baselines y snapshots congelados solo cuando el drift esté explicado, documentado y aprobado por el usuario. Ejecuta los gates necesarios, documenta el valor anterior y posterior, y solo entonces ejecuta `make baseline`.

## Cuándo usar

- Después de un fix de paridad validado con `make validate-excel` que produce un nuevo valor correcto y diferente al baseline actual.
- Después de un cambio intencional en lógica de negocio aprobado por el usuario.
- Cuando `pytest -m baseline` falla por un cambio aprobado y no por una regresión.

## Cuándo NO usar

- Para silenciar fallos de baseline sin entender la causa — esto es su uso más peligroso.
- Cuando `make validate-excel` no pasa todavía.
- Cuando el drift no tiene RCA documentado.
- Cuando el usuario no ha aprobado explícitamente el nuevo valor.
- En medio de una sesión de análisis o fix — siempre en sesión separada o como paso final confirmado.

## Lectura mínima

1. `CLAUDE.md` — sección "Nota sobre `make baseline`" (condiciones de regeneración).
2. `git diff --stat` — ver qué cambió desde el último baseline.
3. `git diff` — confirmar que los cambios son los esperados y aprobados.
4. Test de baseline fallido — entender el delta exacto antes de sobrescribir.

**No leer:** módulos no relacionados, Excel completo, toda la suite de tests.

## Archivos que NO debe leer inicialmente

- `modules/` completo (solo si necesitas confirmar la fórmula que cambió)
- `storage/parametrization/` (no es parte del baseline de cálculo)
- `docs/ai/TASK_STATE.md` (histórico — no relevante para esta operación)
- `reports/` (los reportes son outputs, no inputs de esta skill)

## Flujo de trabajo

1. **Confirmar que el cambio es intencional y aprobado**:
   - ¿El usuario aprobó explícitamente el nuevo valor?
   - ¿Hay un RCA documentado (en `findings.csv` o TASK_STATE.md)?
   - ¿`make validate-excel` pasa con el nuevo valor?

   Si alguna de las tres respuestas es NO → **parar, no continuar**.

2. **Ejecutar gates previos**:
   ```bash
   # Gate 1: tests de paridad
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m parity -v

   # Gate 2: validar Excel
   cd backend_nexa && make validate-excel

   # Gate 3: ver qué cambió
   git diff --stat
   git diff -- backend_nexa/modules/ backend_nexa/tests/
   ```

3. **Identificar snapshots y anchors afectados**:
   ```bash
   # Correr baseline en modo dry para ver qué cambiaría
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v --tb=short
   # Anotar qué tests fallan y cuál es el delta
   ```

4. **Documentar el drift ANTES de sobrescribir**:
   ```md
   Campo: <nombre>
   Valor anterior: <valor>
   Valor nuevo: <valor>
   Delta: <numérico> (<porcentaje>%)
   Causa: <RCA de una línea>
   Aprobado por: <usuario/fecha>
   ```

5. **Ejecutar `make baseline`** solo después de completar los pasos 1–4:
   ```bash
   cd backend_nexa && make baseline
   ```

6. **Verificar resultado**:
   ```bash
   PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v
   cd backend_nexa && make all
   ```

7. **Revisar git diff** del nuevo baseline para confirmar que solo cambió lo esperado:
   ```bash
   git diff -- storage/baselines/
   git diff --stat
   ```

## Kill-switches

Parar inmediatamente y reportar sin ejecutar `make baseline` si:
- `make validate-excel` falla — el nuevo valor no está confirmado contra Excel.
- `pytest -m parity` falla — hay regresiones en paridad que deben resolverse primero.
- `git diff` muestra cambios en módulos no relacionados con el fix aprobado.
- El usuario no ha dado aprobación explícita del nuevo valor.
- El drift está en `storage/`, `modules/` o `tests/` de áreas no relacionadas — puede indicar efecto secundario no intencional.
- Se detecta que el baseline está siendo regenerado para ocultar un test que falla por un bug nuevo.

## Validación mínima

```bash
# Después de make baseline
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline -v
cd backend_nexa && make all
git diff --stat
```

Resultado esperado: `make all` pasa, `baseline` pasa, `git diff --stat` solo muestra `storage/baselines/official.json`.

## Entregable esperado

```md
## Resultado
<Baseline regenerado: campo(s) afectado(s)>

## Evidencia
Drift documentado:
| Campo | Valor anterior | Valor nuevo | Delta | Causa |
|---|---|---|---|---|

## Riesgo
<qué pasaría si el drift no era intencional>

## Validación
- make validate-excel: PASS
- pytest -m parity: PASS
- pytest -m baseline (post-regeneración): PASS
- make all: PASS
- git diff --stat: solo storage/baselines/

## Siguiente paso
<commitear baseline con el código del fix en el mismo PR>
```

---

**Modelo Anthropic recomendado:** `claude-sonnet-4-6` — la operación es procedimental; no requiere análisis numérico complejo si el RCA ya está documentado.

---

**Ejemplo de invocación:**

```
Lee docs/ai/skills/baseline-refresh-guarded.md y aplica sus reglas para:
El fix de fte_supervisor fue aprobado y make validate-excel pasa.
Proceder con regeneración de baseline.
Documentar drift antes de ejecutar make baseline.
Confirmar con make all al final.
```
