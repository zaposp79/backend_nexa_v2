# Visión Imprimible — Mapa Jerárquico

## Árbol de dependencias

```
Panel de Control General
 ├── ficha: cliente, fecha_inicio, duracion_meses, linea_negocio
 ├── reglas_negocio: margen, op_cont, com_cont, markup, descuento, imprevistos
 └── escenarios_comerciales: List[EscenarioComercial]

Vision Tarifas_Modelo_Cobro (ya calculada)
 ├── Section 02: ingreso_mensual (C72)
 └── Section 03: modelo_cobro, tarifa_fija, tarifa_variable, componente_fijo

Visión P&G (PyGMensual[])
 ├── Section 02: cts_mensual (BK30/E6)
 └── Section 04: waterfall + evolución mensual

Cost To Serve
 └── Section 02: cts_mensual alternativo (cts_ponderado/meses)

KPIs (KPIsDeal)
 └── contribucion_total, pct_utilidad

Riesgo (EvaluacionRiesgo)
 └── Section 06: score_cliente, score_operativo, score_total

VisionImprimibleBuilder.construir(...)
 └── VisionImprimible
      ├── ficha: FichaDelDeal
      ├── economics: EconomicsDeal
      ├── configuracion_comercial: ConfiguracionComercial
      ├── evolucion_mensual: EvolucionMensual
      ├── waterfall: WaterfallPromedio
      ├── reglas_negocio: List[ReglaNegocios]
      ├── evaluacion_riesgo: EvaluacionRiesgo
      ├── escenarios: List[EscenarioComercial]
      └── comparativo_escenarios: List[ComparativoEscenario]
```

## Orden de dependencias para construcción

```
1. PyGCalculator        → PyGMensual[]
2. KPIsCalculator       → KPIsDeal
3. CostToServeCalc      → ResultadoCostToServe
4. VisionTarifasCalc    → ResultadoVisionTarifas  ← depende de PyGMensual
5. RiesgoCalculator     → EvaluacionRiesgo
6. WaterfallBuilder     → WaterfallPromedio        ← depende de PyGMensual
7. VisionPyGBuilder     → VisionPyG               ← depende de PyGMensual
8. VisionImprimibleBuilder → VisionImprimible      ← depende de TODO lo anterior
```

La **Visión Imprimible** es la vista de más alto nivel. Solo puede construirse
después de que todas las demás vistas hayan sido calculadas.
