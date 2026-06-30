# Input Contract Canonicalization 1

Fecha: 2026-06-06. Branch: refactor/modular-pure.

## Formato Canónico: PLANO

### Cadena A

```json
"condiciones_cadena_a": {
  "Calculo_conversion_fte_interacciones": { ... },
  "perfiles": [ ... ]
}
```

### Cadena B

```json
"condiciones_cadena_b": {
  "opex": { "items": [ ... ] },
  "inversiones_capex": [ ... ],
  "equipo_soporte_mantenimiento": { ... },
  "costo_variable": { ... },
  "hitl": { ... }
}
```

### Cadena C

```json
"condiciones_cadena_c": {
  "tarifa_proveedor_canal": { ... },
  "inversiones_capex": [ ... ],
  "recurso_humano_transversal": { ... },
  "costo_variable": { ... },
  "hitl": { ... }
}
```

## Formato Legacy: ANIDADO (Deprecado — compatibilidad temporal)

El archivo `request/request.json` enviaba cadena_a y cadena_b con doble anidamiento:

```json
"condiciones_cadena_a": {
  "condiciones_cadena_a": { "perfiles": [ ... ] }
}

"condiciones_cadena_b": {
  "condiciones_cadena_b": { "opex": { ... }, "hitl": { ... }, ... }
}
```

Este fue el origen del bug D-1: cadena_b no fluía (costo_b=0) porque el adapter
no reconocía el nivel exterior del dict anidado.

## Cambios aplicados

| Archivo | Cambio |
|---|---|
| `request/request.json` | Eliminado wrapper redundante en `condiciones_cadena_a` y `condiciones_cadena_b` |
| `modules/calculator/user_input_loader.py` | Comentarios explicativos añadidos en los unwrap guards |
| `modules/calculator/validation/contract_validator.py` | Validator extendido para aceptar volumetria-derived canales como escenarios válidos |

## Code Changes Summary

### Modified Files

| File | Type of Change | Business Logic Changed? |
|------|---------------|------------------------|
| `modules/calculator/user_input_loader.py` | Input normalization guards (NOT formulas) | NO |
| `request/request.json` | Canonicalized to flat format (A/B unwrapped) | N/A (test fixture) |
| `modules/calculator/validation/contract_validator.py` | Accept volumetria-derived canales as valid | NO (validation only) |

### user_input_loader.py guards

- Guard cadena_a: ~line 344. Condition: `"condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a`
- Guard cadena_b: ~line 397. Condition: `"condiciones_cadena_b" in condiciones_b and "canales" not in condiciones_b and "opex" not in condiciones_b`

No se tocaron fórmulas ni cálculos. Se modificó SOLO normalización de entrada en
`user_input_loader.py` (método `_normalizar_entry_data_format`) para aceptar ambos
formatos (plano canónico + legacy anidado).

### Unchanged Files

- All formula calculators (layers 2-10 of the pipeline)
- modules/cadena_a/, modules/cadena_b/, modules/cadena_c/ (calculators, adapters)
- modules/vision_cost_to_serve/ (CTS)
- modules/vision_tarifas/, modules/vision_imprimible/, modules/pyg/
- modules/shared/ (DTOs, ApiResponse, contracts)
- storage/parametrization/ (frozen parametrization)
- All HTTP endpoints

## Compatibilidad temporal en backend

Los unwrap guards en `user_input_loader.py` (~líneas 344-353 y ~397-409) siguen activos
para tolerar el formato legacy. Clientes que aún envíen el formato anidado seguirán
funcionando sin error.

- **Cadena A guard:** línea ~344. Condición: `"condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a`
- **Cadena B guard:** línea ~397. Condición: `"condiciones_cadena_b" in condiciones_b and "canales" not in condiciones_b and "opex" not in condiciones_b`

**Plan de deprecación:** Eliminar guards cuando todos los clientes/integraciones
se hayan actualizado al formato canónico plano. Documentar versión en ese momento.

## Decisión: Cadena A, B y C

### Cadena A
- Estado en request.json antes: ANIDADA (`condiciones_cadena_a.condiciones_cadena_a`)
- Guard en backend: SÍ (línea ~344, análogo al de cadena_b)
- Acción aplicada: Normalizado a formato plano en request.json

### Cadena B
- Estado en request.json antes: ANIDADA (`condiciones_cadena_b.condiciones_cadena_b`) — origen del D-1 bug
- Guard en backend: SÍ (línea ~397, añadido en INPUT_CONTRACT_FIX_B1)
- Acción aplicada: Normalizado a formato plano en request.json

### Cadena C
- Estado en request.json antes: PLANA (nunca estuvo anidada)
- Guard en backend: NO necesario
- Acción aplicada: Ninguna (documentado como correcto)

## Impacto en outputs

- `costo_b mes1`: 39,503,127.41 — **idéntico a Baseline 1**
- `payroll_a mes1`: 154,103,322.32 — **sin cambio**
- Todos los KPIs: **idénticos a Baseline 1**

Conclusión: el cambio de formato (plano vs anidado) no altera los cálculos
porque los unwrap guards producen exactamente el mismo input al motor.

## Tests

```bash
# Desde directorio padre NEXA/
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -v
# Resultado: 12/12 PASSED
```

Tests de canonicalization añadidos (markers: `baseline`):
- `test_request_json_cadena_b_is_canonical_flat`
- `test_request_json_cadena_a_is_canonical_flat`
- `test_request_json_cadena_c_is_canonical_flat`
- `test_flat_and_nested_b_produce_same_output`
- `test_flat_and_nested_a_produce_same_output`
