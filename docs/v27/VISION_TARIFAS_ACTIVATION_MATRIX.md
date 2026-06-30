# Visión Tarifas — Matriz de Activación

## Casos de escenarios

| Escenario | matched_perfiles | Resultado |
|-----------|-----------------|-----------|
| Inbound + perfil existe | 1+ | TarifaCanal creado ✓ |
| Outbound + sin perfil outbound | 0 | `continue` → escenario omitido (sin ingreso ficticio) |
| Canal sin FTE | 0 | omitido |
| strict_mode=True + sin perfil | 0 | StrictExcelModeError raised |

## Cálculo de costo_cad_a_total (C40 Oracle)

```python
# Con canal Voz:
voz_payroll = sum(ch.payroll_ch * 12 for ch in canales if ch.producto == "voz")
# Sin canal Voz (WhatsApp, Correo, etc.):
voz_payroll = sum(ch.payroll_ch * 12 for ch in canales)  # fallback a todos
```

## Caso: todos los escenarios sin perfil
- `canales = []`
- `costo_cad_a_total = 0`
- `ingreso_mensual = 0`
- `validate_visions_complete` falla → VISION_INCOMPLETE

## Caso normal (≥1 escenario con perfil)
- Al menos 1 TarifaCanal producido
- `costo_cad_a_total > 0`
- `ingreso_mensual > 0`
- `kpis_deal.ingreso_mensual = ingreso_mensual` (sobrescrito en engine.py:317)
