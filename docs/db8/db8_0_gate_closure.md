# DB.8.0 Gate Closure

Fecha: 2026-06-05
Branch: `refactor/modular-pure`
Commit base: `7660995`

## Alcance

DB.8.0 hizo configurable el `DocumentStore` de parametrizacion desde composicion.
JSON permanece como default y Cosmos no queda activado por defecto.

No se modifico logica de negocio, calculo, contratos HTTP, payloads legacy ni
`versions.json` para cerrar esta comparacion.

## Baseline oficial

El baseline oficial del branch se ejecuto desde una copia temporal de `HEAD`,
conservando el mismo `storage/` local usado por el workspace para evitar errores
artificiales por parametrizacion faltante.

Comando:

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/.db8_gate_compare_20260605_000502/baseline_pkg \
  /Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/venv_py312_backup_20260604_165827/bin/python \
  -m pytest --tb=short -q
```

Resultado:

```text
48 failed, 1623 passed, 54 skipped, 450 deselected, 1 xfailed
```

## Gate actual

Comando:

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  /Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/venv_py312_backup_20260604_165827/bin/python \
  -m pytest --tb=short -q
```

Resultado:

```text
48 failed, 1628 passed, 54 skipped, 450 deselected, 1 xfailed
```

## Comparacion por node id

Extraccion: lineas `FAILED`/`ERROR` de las salidas completas de pytest.

```text
baseline_count=48
current_count=48
new_failures=0
missing_baseline_failures=0
```

`new_failures`:

```text
[]
```

`missing_baseline_failures`:

```text
[]
```

## Veredicto

DB.8.0 queda cerrado frente al baseline oficial por node id: el gate actual no
introduce fallos nuevos y conserva exactamente el mismo conjunto de fallos del
baseline.

La suite completa sigue roja por deuda preexistente del baseline. Esa deuda no
se corrige ni se re-clasifica como parte de DB.8.0.
