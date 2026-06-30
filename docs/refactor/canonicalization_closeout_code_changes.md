# Code Changes for Canonicalization

Fecha: 2026-06-06. Branch: refactor/modular-pure.

## Modified: modules/calculator/user_input_loader.py

### _normalizar_entry_data_format()

#### Cadena A guard (~lines 344-357)

```python
# Guard: detect accidental double-nesting not caught by InputNormalizer
# (e.g. legacy/format-legacy path that skips InputNormalizer)
# request/request.json fue normalizado al formato canónico (2026-06-06).
# Este guard es compatibilidad temporal. Eliminar cuando todos los clientes se actualicen.
if "condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a:
    inner = condiciones_a["condiciones_cadena_a"]
    if isinstance(inner, dict) and "perfiles" in inner:
        import logging as _log
        _log.getLogger("nexa_engine.loader").warning(
            "[NORMALIZER] condiciones_cadena_a double-nesting detected and unwrapped"
        )
        condiciones_a = inner
```

Condición: `"condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a`
Acción: unwrap al nivel interior que contiene `perfiles`.

#### Cadena B guard (~lines 397-416)

```python
# Guard: detect accidental double-nesting (same pattern as cadena_a above).
# El adapter _es_formato_entry_data_b ve el dict exterior {condiciones_cadena_b}
# que no tiene las claves internas esperadas → omite traducción → costo_b=0 (D-1 bug).
# Unwrap here so the adapter receives the actual payload.
# request/request.json fue normalizado al formato canónico (2026-06-06).
# Este guard es compatibilidad temporal. Eliminar cuando todos los clientes se actualicen.
if (
    isinstance(condiciones_b, dict)
    and "condiciones_cadena_b" in condiciones_b
    and "canales" not in condiciones_b
    and "opex" not in condiciones_b
):
    inner = condiciones_b["condiciones_cadena_b"]
    if isinstance(inner, dict):
        import logging as _log
        _log.getLogger("nexa_engine.loader").warning(
            "[NORMALIZER] condiciones_cadena_b double-nesting detected and unwrapped"
        )
        condiciones_b = inner
```

Condición: `"condiciones_cadena_b" in condiciones_b and "canales" not in condiciones_b and "opex" not in condiciones_b`
Acción: unwrap al nivel interior que contiene `opex`, `hitl`, etc.

### Naturaleza del cambio

- Este es un normalizador de entrada (NO una fórmula ni un cálculo de negocio).
- Objetivo: aceptar ambos formatos (plano canónico + legacy anidado) sin errores.
- Impacto en outputs: CERO (ambos formatos producen exactamente el mismo resultado).
- Impacto en contratos públicos: NINGUNO (DTOs sin cambios, ApiResponse sin cambios).
- La lógica de negocio (calculadores, fórmulas, PyG, KPIs, visiones) no fue tocada.

## Modified: request/request.json

El archivo fue normalizado del formato legacy anidado al formato canónico plano:

- `condiciones_cadena_a`: eliminado el wrapper redundante `condiciones_cadena_a.condiciones_cadena_a`
- `condiciones_cadena_b`: eliminado el wrapper redundante `condiciones_cadena_b.condiciones_cadena_b`
- `condiciones_cadena_c`: sin cambios (ya estaba en formato plano)

Este es el "contrato de entrada canónico" oficial para Bancamia Cobranzas.

## Modified: modules/calculator/validation/contract_validator.py

Validator extendido para aceptar volumetria-derived canales como escenarios válidos.
Outbound cadena_a activo en volumetria es válido aunque no haya escenarios_comerciales explícitos.

## Conclusion

- No se tocaron fórmulas de negocio.
- No se tocaron calculadores (cadena_a, cadena_b, cadena_c, costos_financieros, pyg, vision_*).
- No se tocó frozen (parametrización).
- No se tocó vision_cost_to_serve.
- No se tocaron DTOs ni contratos públicos.
- Se modificó SOLO: normalización de entrada (user_input_loader.py), contrato de test (request.json),
  y validación de escenarios (contract_validator.py).

## Files Unchanged

- Todos los calculadores del pipeline (capas 2-10)
- modules/cadena_a/, modules/cadena_b/, modules/cadena_c/ (calculadores, adapters)
- modules/vision_cost_to_serve/
- modules/vision_tarifas/
- modules/vision_imprimible/
- modules/pyg/
- modules/shared/ (DTOs, ApiResponse, contratos)
- storage/parametrization/ (frozen)
- Todos los endpoints HTTP
