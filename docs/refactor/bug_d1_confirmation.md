# Bug D-1 Confirmation

## Estructura del request

- **Archivo**: `backend_nexa/request/request.json` (Bancamia Cobranzas, 24m)
- **cadenas_activas** (inbound): cadena_a=true, cadena_b=true, cadena_c=false
- **condiciones_cadena_b (nivel 1)**: `{"condiciones_cadena_b": {...}}` — clave única, valor = dict anidado
- **condiciones_cadena_b.condiciones_cadena_b (nivel 2)**: `{opex: {items:[16 items]}, inversiones_capex, equipo_soporte_mantenimiento, costo_variable, hitl}` — payload real

Estructura JSON confirmada:
```json
"condiciones_cadena_b": {
  "condiciones_cadena_b": {
    "opex": { "items": [ ... 16 items ... ] },
    "inversiones_capex": [ ... ],
    "equipo_soporte_mantenimiento": { ... },
    "costo_variable": { "tarifas_por_canal": { ... }, "tasa_escalamiento": { ... } },
    "hitl": { "total_volumen_cadena_b": 2500, "equipo": [ ... ] }
  }
}
```

**condiciones_cadena_c**: plano (sin doble anidamiento) — NO afectado por D-1.

## Síntomas (pre-fix)

- `costo_b`: 0 en los 24 meses (esperado: ~39.5M/mes × indexación)
- `volumen_mensual_cadena_b`: 0 (esperado: 18000/mes según volumetría)
- `canales_activos`: [] en cadena_b (esperado: WhatsApp, Correo, WebChat)

## Causa raíz

En `_normalizar_entry_data_format` (user_input_loader.py, sección cadena_b, línea ~390):
```python
condiciones_b = data["condiciones_cadena_b"]
# condiciones_b = {"condiciones_cadena_b": {opex, hitl, ...}}
```

El dict `condiciones_b` tiene como única clave `"condiciones_cadena_b"` — no tiene
`"opex"`, `"equipo_soporte_mantenimiento"`, ni `"canales"`. Cuando se llama a:
```python
adapter.adaptar(data)  # → _es_formato_entry_data_b(condiciones_b)
```
El detector `_es_formato_entry_data_b` busca entry_data keys (`opex`, `hitl`, etc.)
en el nivel externo — no las encuentra. Retorna `False`. El adapter no transforma.
Luego `_cadena_b({"condiciones_cadena_b": {...}})` construye todo en defaults (canales=[]).

Idéntico patrón existía en `condiciones_cadena_a` y YA estaba resuelto con un guard
explícito (línea 346 del mismo archivo). El guard faltaba para cadena_b.

## Conclusión

**D-1 CONFIRMADO** — Bug técnico pre-existente. No introducido por ningún refactor reciente.
Causa: doble anidamiento en request.json + falta de unwrap guard en el loader para cadena_b.
