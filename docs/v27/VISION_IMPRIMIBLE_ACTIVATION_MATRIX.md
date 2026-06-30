# Visión Imprimible — Matriz de Activación

Esta vista no tiene reglas de activación propias. Todas sus celdas referencian
otras hojas. Los únicos condicionales son:

## Condicionales identificados

| Elemento | Fórmula | Condición | Comportamiento |
|----------|---------|-----------|----------------|
| Nombre cliente | =IF(Panel!C7="Cliente Nuevo", D6, C6) | tipo_cliente | Nombre nuevo vs existente |
| Componente fijo | =IFERROR(Vision Tarifas!C34 & ..., "-") | canal existe | "-" si no hay canal |
| Modelo cobro | =IFERROR(Vision Tarifas!C33, "-") | canal existe | "-" si Vision Tarifas vacío |
| Ingreso mensual | =IFERROR(Vision Tarifas!C72, 0) | Vision Tarifas calculada | 0 si no hay tarifas |
| Escenarios 1-5 | Panel!B80/B87/B94/B101/B108 | escenario definido | vacío si escenario no configurado |

## Casos de activación

| Caso | Resultado esperado |
|------|--------------------|
| Sin escenarios comerciales | Section 05 vacía (todos los campos en blanco) |
| Sin Vision Tarifas | ingreso_mensual = 0, modelo_cobro = "-" |
| Sin RiesgoCalculator | Section 06 con scores = 0 |
| Cliente nuevo | nombre = Panel!D6 (nombre cliente nuevo) |
| Cliente existente | nombre = Panel!C6 (nombre cliente existente) |
