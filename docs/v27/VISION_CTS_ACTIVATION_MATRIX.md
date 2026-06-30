# Visión Cost To Serve — Matriz de Activación

## Reglas de activación validadas en Excel

| Sección | Condición Excel | Comportamiento | Backend |
|---------|----------------|----------------|---------|
| Visión General por Servicio | siempre | siempre visible | siempre expuesto |
| Visión General por Canal | IF(C27="SAC",...) | "✓ Habilitado" o "— Deshabilitado" | no implementado |
| Detalle por Canal | IF(C27="SAC",...) | igual | no implementado |

## Casos de activación

| Caso | Cadenas activas | K50 | L50 | M50 | CTS_a | CTS_b | CTS_c |
|------|----------------|-----|-----|-----|-------|-------|-------|
| Solo A | A=true | FTE_out + vol_in | 0 | 0 | > 0 | N/A | N/A |
| A + B | A=true, B=true | idem | vol_b | 0 | > 0 | > 0 | N/A |
| A + B + C | todos | idem | idem | vol_c | > 0 | > 0 | > 0 |
| K50 = 0 | A activa, FTE=0, vol=0 | 0 | — | — | DIV/0 riesgo | — | — |
| Sin volumen B | B activa, vol=0 | — | 0 | — | — | DIV/0 riesgo | — |

## Denominador K50 — Lógica de cálculo

```python
# Por perfil de Cadena A:
if perfil.modalidad == "Outbound":
    contribucion = perfil.fte
else:  # Inbound
    contribucion = perfil.vol_cadena_a_mensual  # default 0.0 si no configurado
```

**RIESGO**: Perfiles Inbound sin `vol_cadena_a_mensual` configurado → K50 = sum(FTE_outbound_only)

## Fase 2 — GAP-CTS-ACT-1 cerrado (flag, no node-hiding)

Hallazgo de workbook (data_only=True, request real service="Captura de Datos"):

| Celda | Valor | Significado |
|-------|-------|-------------|
| C27 | "Captura de Datos" | servicio (= Panel!C5) |
| C58 | "— Deshabilitado" | etiqueta cabecera "Visión General por Canal" |
| C87 | "— Deshabilitado" | etiqueta cabecera "Detalle por Canal" |
| C64 (WhatsApp vol) | 26292.23 | **dato SÍ computado pese a "Deshabilitado"** |
| C98 (WhatsApp CTS) | 4,121,564.78 | **dato SÍ computado** |

**Conclusión**: la condición `IF(C27="SAC",...)` controla SOLO el texto de la cabecera.
Los datos por canal se calculan siempre. Por tanto el backend:
- expone `cost_to_serve.canal_view_habilitado = (servicio.upper()=="SAC")`
- NO suprime ni oculta nodos de datos (hacerlo contradiría el workbook)

| Caso | servicio | canal_view_habilitado | desglose emitido |
|------|----------|----------------------|------------------|
| Real V2-7 | Captura de Datos | False | Sí (siempre) |
| SAC | SAC | True | Sí |
| Cualquier otro | Ventas/Cobranzas/Backoffice | False | Sí |
