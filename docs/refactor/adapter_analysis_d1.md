# Adapter Analysis for D-1

## Método _es_formato_entry_data_b
- Ubicación: `modules/calculator/adapters/entry_data_adapter.py:88`
- Lógica actual:
```python
@staticmethod
def _es_formato_entry_data_b(d: Dict) -> bool:
    entry_data_keys = {"opex", "equipo_soporte_mantenimiento", "costo_variable",
                       "inversiones_capex", "hitl"}
    internal_keys   = {"canales", "opex_consumo_variable", "equipo_sm"}
    has_entry  = bool(entry_data_keys & set(d.keys()))
    has_intern = bool(internal_keys & set(d.keys()))
    return has_entry and not has_intern
```
- ¿Detecta `condiciones_cadena_b.condiciones_cadena_b`? **NO**
- Razón: cuando `d = {"condiciones_cadena_b": {...}}`, `set(d.keys())` = `{"condiciones_cadena_b"}`.
  Intersección con `entry_data_keys` = vacío. `has_entry = False`. Retorna False.

## Método _normalizar_cadena_b (renombrado _adaptar_cadena_b en adapter)
- ¿Desenvuelve? **NO** — no hay lógica recursiva ni de unwrap.
- El adapter es correcto para datos planos; el problema estaba un nivel arriba.

## Lugar real del fix
El fix se aplicó en `user_input_loader.py`, método `_normalizar_entry_data_format`,
sección cadena_b (líneas ~389-410). Antes de pasar `condiciones_b` al adapter,
se detecta el doble anidamiento y se desenvuelve in-place:

```python
# Guard NUEVO (análogo al guard de cadena_a en línea 346)
if (
    isinstance(condiciones_b, dict)
    and "condiciones_cadena_b" in condiciones_b
    and "canales" not in condiciones_b
    and "opex" not in condiciones_b
):
    inner = condiciones_b["condiciones_cadena_b"]
    if isinstance(inner, dict):
        # log warning + unwrap
        condiciones_b = inner
```

## Cadena C
- ¿Tiene mismo problema? **NO** — `condiciones_cadena_c` en request.json es plano.
- `_es_formato_entry_data_c` busca `tarifa_proveedor_canal` o `recurso_humano_transversal`,
  que están presentes en el nivel externo de cadena_c.
- No requiere cambio.

## Corrección aplicada
- Un solo guard de unwrap en `user_input_loader.py` sección cadena_b.
- Adapter `entry_data_adapter.py`: **sin cambios** (correcto para datos planos).
- DTOs públicos: **sin cambios**.
- Calculadores y fórmulas: **sin cambios**.
