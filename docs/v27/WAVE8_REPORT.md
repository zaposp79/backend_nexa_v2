> **⚠️ POST-W17 CONTEXT**: Claims of certified parity in this report
> were based on circular tests. W17 oracle validation showed the actual
> parity gap is structural. The infrastructure built in this wave is
> still valid, but the parity certification claim is rescinded until
> the Semantic Reconstruction Program completes.

# WAVE 8 — Freeze del contrato API (FASE 3)

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Fase**: FASE 3 — Formalizar el contrato API como ciudadano de primera clase

---

## 1. Resumen ejecutivo

WAVE 8 convierte el contrato de la API NEXA en un artefacto explícito,
versionado, validado y testeado. Antes de WAVE 8 el contrato vivía
implícitamente en `simulation/request_dto.py` y en lo que aceptaba la
suite de baselines V2-7; ahora vive en `contracts/api_v1/` como un set
de DTOs Pydantic v2 *frozen + strict*, su JSONSchema, ejemplos y
documentación.

### Antes / después

| Dimensión                                  | Pre-WAVE-8 | Post-WAVE-8 |
|--------------------------------------------|-----------|-------------|
| Contrato API formalizado                   | No        | Sí (`api-v1`) |
| DTOs `extra="forbid"` + `frozen=True`      | Parcial   | Total       |
| JSONSchema commiteado                      | No        | Sí (13 archivos) |
| OpenAPI persistido (yaml + json)           | No        | Sí          |
| Tests de contrato                          | 0         | **49**      |
| Resolución de W7-OBS-3 (`cadenas_activas`) | Bug abierto | **Resuelto** |
| Backward-compat con baselines V2-7         | n/a       | 12/12 cases |
| Parity + Baselines                         | 39 + 16   | 39 + 16 (sin cambios) |
| Default `pytest` — passed                  | 746       | 795 (+49)   |
| Default `pytest` — failed/errors           | 0 / 0     | **0 / 0**   |

---

## 2. Estructura creada

```
contracts/
├── __init__.py
├── README.md                          ← política de versionado
├── api_v1/
│   ├── __init__.py                    ← re-exports públicos
│   ├── README.md                      ← contenido del contrato
│   ├── adapter.py                     ← v1 ↔ legacy
│   ├── request/
│   │   ├── __init__.py
│   │   ├── entry_data.py              ← EntryDataV1 (root)
│   │   ├── panel.py                   ← PanelDeControlRequestV1
│   │   ├── cadena_a.py                ← CadenaARequestV1, PerfilCadenaAV1
│   │   ├── cadena_b.py                ← CadenaBRequestV1, CanalCadenaBV1, …
│   │   ├── cadena_c.py                ← CadenaCRequestV1, CanalCadenaCV1
│   │   ├── escenarios.py              ← EscenarioComercialV1
│   │   └── validators.py              ← infer_cadenas_activas + lift helper
│   ├── response/
│   │   ├── __init__.py
│   │   ├── visions.py                 ← VisionsBundleV1 + 4 visiones
│   │   ├── kpis.py                    ← KpisV1
│   │   ├── pricing.py                 ← PricingV1 (reserved)
│   │   └── simulation_result.py       ← SimulationResultV1 (envelope)
│   ├── schema/
│   │   ├── entry_data.schema.json
│   │   ├── panel.schema.json
│   │   ├── cadena_{a,b,c}.schema.json
│   │   ├── escenario.schema.json
│   │   ├── vision_{tarifas,pyg}.schema.json
│   │   ├── cost_to_serve.schema.json
│   │   ├── waterfall.schema.json
│   │   ├── visions_bundle.schema.json
│   │   ├── kpis.schema.json
│   │   └── simulation_result.schema.json
│   └── examples/
│       ├── bancamia_request.json      ← copia certificada
│       ├── bancamia_kpis.json
│       └── bancamia_vision_tarifas.json
└── openapi/
    ├── api-v1.yaml
    └── api-v1.json

scripts/contracts/
├── __init__.py
├── generate_schemas.py                ← regen JSONSchema (idempotente)
└── generate_openapi.py                ← regen OpenAPI (vivo o contract-only)

tests/contracts/
├── conftest.py                        ← path setup
├── test_contract_schema_stable.py     ← 13 casos: drift detection
├── test_contract_examples_valid.py    ← 15 casos: examples + 12 baselines
├── test_contract_backward_compat.py   ← 13 casos: round-trip a SimulationRequest
└── test_contract_cross_field_validation.py  ← 8 casos negativos
```

---

## 3. Decisiones técnicas

### 3.1 Pydantic v2 strict + frozen

Todos los DTOs usan:

```python
model_config = ConfigDict(extra="forbid", frozen=True)
```

Esto significa:

- Campos no declarados → `ValidationError` en parse.
- Instancias inmutables tras construcción (cubierto por
  `test_frozen_models_are_immutable`).

Excepción: `EscenarioComercialV1` usa `extra="allow"` porque el motor
acepta escenarios heterogéneos cuyo subset canónico aún no está cerrado.
La estructura mínima (`nombre`, `canal`, `modalidad`, …) sí es estricta
para cross-field validation.

### 3.2 Cross-field validators

Cuatro reglas en `EntryDataV1`:

1. **`_lift_panel_cadenas_activas`** (mode="before"):
   acepta el formato nested `panel.cadenas_activas = {cadena_a: bool, ...}`
   y lo levanta a un `Set[Literal["A","B","C"]]` en la raíz. Strip el
   campo del panel para mantener strict-mode.

2. **`_populate_and_check_active_chains`** (mode="after"):
   si `cadenas_activas` está vacío después del lift, lo infiere desde los
   contenidos de cadena_a/b/c (resuelve **W7-OBS-3**). Si no hay datos,
   se asume `{"A"}` para evitar crashes en fixtures mínimos.

3. **Escenarios consistentes**: cada `EscenarioComercialV1` con `canal`
   y `modalidad` no vacíos debe referenciar un `(canal, modalidad)`
   declarado en `cadena_a.perfiles`. Sin cadena_a → no se enforza.

4. **Ranges numéricos vía `Field`**: porcentajes `0..1`, meses
   `1..120`/`1..12`, fechas como string libre.

### 3.3 Backward compatibility

`EntryDataV1.to_legacy_dict()` produce el dict que consume
`UserInputLoader.cargar_desde_dict()`. Reinserta el nested
`panel.cadenas_activas = {cadena_a: bool, ...}` para que el loader actual
funcione sin modificación.

`entry_data_v1_to_simulation_request()` adicionalmente strip ese mismo
campo del panel porque `simulation.request_dto.PanelDeControlRequest`
sigue siendo `extra="forbid"` y no declara `cadenas_activas`.

Resultado: los **12 `request.json` certificados de WAVE 6** validan
contra `EntryDataV1` y round-trip-ean correctamente a `SimulationRequest`.

### 3.4 W7-OBS-3 — `cadenas_activas` inferido

Antes: las fixtures legacy sin `cadenas_activas` rompían `volume_resolution`
en TASK_3 cuando entraban al motor. Ahora:

```python
def infer_cadenas_activas(cadena_a, cadena_b, cadena_c, explicit=None):
    if explicit:
        return {c.upper() for c in explicit if c}
    active = set()
    if _has_data(cadena_a, "perfiles"):
        active.add("A")
    if _has_data(cadena_b, "canales", "opex_consumo_variable", "equipo_sm"):
        active.add("B")
    if _has_data(cadena_c, "canales", "equipo_transversal"):
        active.add("C")
    return active or {"A"}
```

Esto vive en `contracts/api_v1/request/validators.py` y se invoca desde
`EntryDataV1` en `mode="after"`. Documentado en `api_v1/README.md`.

### 3.5 Schema stability como gate de PR

`test_contract_schema_stable.py` compara cada JSONSchema commiteado en
`schema/` con el generado por la versión actual de los DTOs:

```python
assert fresh == committed_norm, (
    f"JSONSchema drift for {name}. "
    f"Re-run `python scripts/contracts/generate_schemas.py` if intentional, "
    f"or bump to api-v2 if this is a breaking change."
)
```

Cualquier cambio inadvertido en un campo (rename, range, default,
removal) falla este test y obliga al autor a:

- regenerar a propósito (cambio additivo) **o**
- crear `api_v2` (cambio breaking).

### 3.6 OpenAPI

Dos pistas:

1. **Vivo**: FastAPI sigue sirviendo `/openapi.json` en runtime con todos
   los routers actuales.
2. **Frozen**: `scripts/contracts/generate_openapi.py` toma ese spec y lo
   persiste en `contracts/openapi/api-v1.{yaml,json}`. Si la app no carga
   (e.g., entorno sin parametrización), genera un spec *contract-only*
   construido directamente desde `EntryDataV1` + `SimulationResultV1`.

---

## 4. Lo que NO se tocó

Por restricción explícita:

- `calculators/`, `domain/models/`, `engine.py` — sin cambios.
- `simulation/request_dto.py` — sin cambios; sigue siendo la DTO interna.
- `api/v1/simulation/calculate_router.py` — sin cambios; sigue aceptando
  el formato actual exactamente como antes.
- `tests/parity/` (39) — pasan, sin cambios.
- `tests/baselines/` (16) — pasan, sin cambios.
- `tests/contract/` (legacy, 290 tests marcados `legacy`) — siguen
  excluidos del default run.

El contrato `api-v1` es estrictamente *aditivo* sobre la API existente.
Ningún cliente necesita migrar; el endpoint sigue aceptando el body
flat o envuelto en `user_input` como hoy.

---

## 5. Validación

```bash
$ python -m pytest tests/contracts --tb=short -v 2>&1 | tail -5
tests/contracts/test_contract_backward_compat.py .............           [ 26%]
tests/contracts/test_contract_cross_field_validation.py ........         [ 42%]
tests/contracts/test_contract_examples_valid.py ...............          [ 73%]
tests/contracts/test_contract_schema_stable.py .............             [100%]
============================== 49 passed in 0.14s ==============================

$ python -m pytest tests/parity tests/baselines --tb=no -q | tail -3
55 passed, 2 warnings in 1.52s

$ python -m pytest --tb=no -q | tail -3
795 passed, 23 skipped, 411 deselected, 1 xfailed, 2 warnings in 2.16s
```

| Suite               | Esperado | Real |
|---------------------|----------|------|
| `tests/contracts`   | ≥ 15     | **49** |
| `tests/parity`      | 39       | 39   |
| `tests/baselines`   | 16       | 16   |
| Default (`pytest`)  | 0 failed / 0 errors | **0 / 0** |

---

## 6. Cómo regenerar todo

```bash
source venv/bin/activate
python scripts/contracts/generate_schemas.py    # idempotente
python scripts/contracts/generate_openapi.py    # idempotente
python -m pytest tests/contracts --tb=short
```

Ejecutar dos veces en seco produce `[=]` en todas las salidas — los
artefactos son byte-equal.

---

## 7. Sample JSONSchema generado

`entry_data.schema.json` (top-level keys, sorted):

```
- $defs                  (todas las sub-DTOs: PanelV1, PerfilCadenaAV1, …)
- additionalProperties   (false — strict)
- properties             (panel, cadena_a, cadena_b, cadena_c,
                          cadenas_activas, escenarios, metadata)
- required               ([panel])
- title                  ("EntryDataV1")
- type                   ("object")
```

`panel.schema.json`:

- Todas las constraints (`minimum`, `maximum`) materializadas en el
  schema (e.g., `meses_contrato: {minimum: 1, maximum: 120, type: int}`,
  `margen_b: {anyOf: [{type: number, minimum: 0, maximum: 1}, {type: null}]}`).

---

## 8. Bloqueos / observaciones para WAVE 9

Ninguno. Las precondiciones para WAVE 9 (Clean Architecture — extraer el
core financiero puro) están todas satisfechas:

1. **Contrato de entrada formalizado** → WAVE 9 puede asumir
   `EntryDataV1` como input fijo del adapter.
2. **Contrato de salida formalizado** → WAVE 9 puede modelar
   `SimulationResultV1` como output del core puro.
3. **`UserInputLoader` aislado** → único seam de adaptación; WAVE 9 lo
   reemplazará por un mapper directo `EntryDataV1 → domain.UserInput`
   sin pasar por dict.
4. **W7-OBS-3 resuelto** → ninguna fixture necesita parchear
   `cadenas_activas` antes de WAVE 9.

### Follow-ups menores (no bloqueantes)

- **W7-FUP-1/2/3/6** del triaje WAVE 7 quedan listos para limpieza: con
  el nuevo `tests/contracts/`, los archivos `tests/contract/test_vision_*`
  legacy ya no aportan cobertura y pueden eliminarse en una limpieza
  cosmética post-WAVE-9.
- `EscenarioComercialV1` está abierto (`extra="allow"`). Cerrarlo a
  estricto requerirá inventariar las formas de escenario en uso real
  por el frontend (tarea pre-WAVE-15 / Certified Mode).
- `PricingV1` (response/pricing.py) está reservado pero no se usa aún;
  se llenará en WAVE 14 (versionado formal) cuando se devuelva un
  resumen pricing en el header.

---

## 9. Comandos de validación rápida

```bash
source venv/bin/activate

# Regenerar artefactos
python scripts/contracts/generate_schemas.py
python scripts/contracts/generate_openapi.py

# Contratos
python -m pytest tests/contracts --tb=short -v

# Críticos
python -m pytest tests/parity tests/baselines --tb=no -q

# Toda la suite default
python -m pytest --tb=no -q
```

— Fin del reporte WAVE 8.
