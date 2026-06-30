# Display-Only Formula Registry — V2-7

Elementos formalmente excluidos del scope económico con evidencia.

| ID | Celda | Fórmula | Evidencia de exclusión |
|----|-------|---------|----------------------|
| DO-01 | VT!C77 | `IF(C5="SACO", TRANSPOSE(C143:G143), IF(C5="Cobranzas", TRANSPOSE(C182:P182), ""))` | Scan: 0 downstream consumers. VT!C72≠f(C77). P&G no referencia VT. |
| DO-02 | Panel!C182 | `SUMPRODUCT(F158:F165, C171:C178, VT!J136:J143)` | Solo consumido por VT!C77 (DO-01). Chain termina en dead end. |
| DO-03 | VT!C133 | `IF(C5="SACO", C124, IF(C5="Cobranzas", C155, 0))` | Solo usado en VT!G57 (col G = display summary column). |
| DO-04 | VT!G57 | `IF(C35="Transacción", (C40+C50+C60)×D35/G55, (G53+G55)/C133/C11)` | Columna G = summary display. No es consumida por P&G ni CTS económico. |
| DO-05 | VT!C21 | `IF(C16="Transacción", HMS!G31, IF(OR(C16="Resultados","Honorarios"), HMS!G33, 0))` | P&G 0 referencias a VT. Tarifa display row solamente. |
| DO-06 | VT!G45 | `IF(C34="FTE", G43/C37/12, G43/E126)` | Columna G = deal-level summary. No alimenta P&G. |
| DO-07 | VT!G47 | `IF(C34="Tiempo", G43/E124, 0)` | Columna G = deal-level summary. No alimenta P&G. |
| DO-08 | VT rows 75-85 | Tabla mensual "Ingreso Variable" para SACO/Cobranzas | Solo referenciada desde VT!C77 (DO-01). |
| DO-09 | VT!C130 | `IF(OR(C35="Honorarios","Resultados"), "✓ Habilitado", "—")` | Gate de visibilidad en VT display. No afecta cálculos. |
| DO-10 | HMS!G31/G33 | Tasas de transacción/honorarios | Sólo usadas en VT!C21 (DO-05). |

## Proof of display-only classification

Condición para DISPLAY_ONLY: el elemento no puede estar en la ruta causal de ninguna de estas celdas económicas:

- P&G!H27 (Ingreso Neto)
- P&G!H30 (Costo Total)  
- P&G!H74 (Contribución)
- CTS!C34 (CTS Cadena A)
- CTS!G49 (CTS Ponderado)
- VT!C72 (Facturación Total deal)
- KPI ingreso_mensual, costo_mensual

Verificación: trazado de dependencias exhaustivo (scan de fórmulas en todas las 23 hojas).
Ningún elemento DO-01 a DO-10 aparece en la ruta a ninguna de las celdas económicas listadas.
