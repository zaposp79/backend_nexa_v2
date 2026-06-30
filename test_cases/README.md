# test_cases/input — Cobertura de fixtures

Cada fixture es un `entry_data` que el motor (`NexaPricingEngine`) debe ejecutar sin error.
Activación de cadenas: en formato `panel_de_control` la activación se declara en
`panel_de_control.cadenas_activas`; en formato `datos_operativos`/`volumetria` se deriva
de los volúmenes por canal.

## Estado (verificado ejecutando el motor)

| Fixture | Formato | Cadenas activas | Estado |
|---------|---------|------------------|--------|
| `solo_cadena_a.json` | panel_de_control | A | ✅ ejecuta (cobertura Cadena A aislada) |
| `bancamia_whatsapp_only.json` | panel_de_control | A, B | ✅ ejecuta |
| `bancamia_correo_only.json` | panel_de_control | A, B | ✅ ejecuta |
| `bancamia_webchat_only.json` | panel_de_control | A, B | ✅ ejecuta |
| `bancamia_canonical_k50.json` | panel_de_control | A, B | ✅ ejecuta |
| `bancamia_excel_match.json` | panel_de_control | A, B | ✅ ejecuta |
| `excel_v24_canonical_bancamia.json` | panel_de_control | A, B | ✅ ejecuta |
| `bancamia_cobranzas.json` | panel_de_control | A, B | ❌ **roto (dato)**: `Locality '' not found` — `sede`/localidad vacía |
| `seguros_adl_cobranzas.json` | panel_de_control | A, B | ❌ **roto (dato)**: rol `Agente Basico`/`Empleado` ausente en HR-Nómina (master data) |

## Fixtures rotos — decisión pendiente

`bancamia_cobranzas.json` y `seguros_adl_cobranzas.json` fallan por **datos inválidos**
(localidad vacía / rol inexistente en parametrización), no por activación. No se corrigieron
para **no inventar** datos maestros (localidad/rol). Acción pendiente de decisión:
corregir el dato con un valor válido del catálogo, o eliminar el fixture.

## Nota de contrato

Existen dos formatos de `entry_data` aceptados por `UserInputLoader.cargar_desde_dict`:
`panel_de_control` + `condiciones_cadena_*` (estos fixtures) y `datos_operativos` + `volumetria`
(ver `request/request.json`). Ambos son válidos; la activación de cadenas se resuelve distinto
en cada uno (ver arriba).
