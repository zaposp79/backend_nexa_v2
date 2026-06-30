# Visión Tarifas — Mapa Jerárquico

## Árbol de datos

```
Panel.escenarios_comerciales (A81:D113)
 └── EscenarioComercial[] {escenario#, modalidad, canal, modelo_cobro, pct_fijo}

PerfilCadenaA[] (filtrado por canal+modalidad de cada escenario)
PyGMensual[] (financial costs: ica, gmf, polizas, financiacion)
ParametrosCadenaB (para cadena_b_mensual)

VisionTarifasCalculator.calcular(pyg_por_mes)
 ├── Per EscenarioComercial:
 │    ├── filter perfiles by (canal, modalidad)
 │    ├── _calcular_tarifa_canal() → TarifaCanal
 │    │    ├── costo_op = payroll_ch + no_payroll_ch
 │    │    ├── fin_ch = avg_fin_total × (op_ch / avg_costo_a)
 │    │    ├── costo_ch = op_ch + fin_ch + cadena_b_ch
 │    │    ├── ingreso = costo_ch / factor_billing
 │    │    ├── facturacion = ingreso × pct_fijo
 │    │    └── tarifa_fte = facturacion / fte
 │    └── total_cad_a += TarifaCanal.costo_cadena_a_ch
 └── Totals:
      ├── costo_cad_a_total = payroll_annual + nop_annual + fin_a × voz_frac
      ├── costo_b_total = avg_costo_b × 12
      ├── costo_c_total = sum(costo_c_fin + ica_c + gmf_c)
      └── ingreso_mensual = ingreso_a + ingreso_c
```

## engine.py override (línea 317)

```python
kpis_deal.ingreso_mensual = vision_tarifas.ingreso_mensual
```

Si `vision_tarifas.ingreso_mensual = 0` → `kpis.ingreso_mensual = 0` → VISION_INCOMPLETE.

## Relación con otras vistas

| Vista | Consume de Tarifas |
|-------|-------------------|
| Visión Imprimible (Section 02) | ingreso_mensual |
| Visión Imprimible (Section 03) | canales[0].modelo_cobro, tarifa_fija, tarifa_variable |
| Vision Cost To Serve (fila 19) | ingreso_mensual (C72) |
| KPIs | kpis_deal.ingreso_mensual (sobrescrito) |
