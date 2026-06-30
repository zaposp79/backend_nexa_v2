# Visión P&G — Mapa Jerárquico

## Árbol de dependencias de datos

```
Panel de Control General
 ├── C63/D63/E63 → márgenes por cadena (divisores en ingresos)
 ├── C67-C70     → contingencias, markup, descuento
 ├── C73         → imprevistos %
 └── C11         → duración contrato (meses)

Rot, Ausent y Rentabilidad
 └── B38:BI43    → tabla ramp-up (cadena × mes)

NominaCalculator → PyGMensual.payroll_a (aggregate)
  └── [Sub-componentes pendientes: GAP-PYG-HIER-1]

NoPayrollCalculator → PyGMensual.no_payroll_a (aggregate)
  └── [Sub-componentes pendientes: GAP-PYG-HIER-1]

CadenaBCalculator → PyGMensual.costo_b (aggregate)
  └── [Sub-componentes pendientes: GAP-PYG-HIER-2]

CadenaCCalculator → PyGMensual.costo_c (aggregate)
  └── [Sub-componentes pendientes: GAP-PYG-HIER-3]

CostosFinancierosCalculator
 ├── PyGMensual.ica
 ├── PyGMensual.gmf
 ├── PyGMensual.polizas
 ├── PyGMensual.financiacion
 └── PyGMensual.comision_administracion

PyGCalculator → List[PyGMensual]
  └── VisionPyGBuilder.construir() → VisionPyG.filas[]
```

## Orden de cálculo (Excel)

1. Costos → cost base (Nómina, NoPayroll, CadenaB, CadenaC)
2. Ingresos → costo / (1 - margen) × rampup (bottom-up)
3. Componente Financiero → sobre costo operativo
4. Ingreso Neto → Ingreso Bruto + ajustes - descuentos - imprevistos
5. Contribución = Ingreso Neto - Costo Total - Componente Financiero

## Relación con otras vistas

| Vista | Consume de P&G |
|-------|---------------|
| Visión Cost To Serve | PyGMensual.costo_a/b/c para denominadores K50/L50/M50 |
| Visión Imprimible (Section 04) | PyGMensual[] para waterfall y evolución mensual |
| KPIs | PyGMensual[] para contribucion_total, ingreso_neto_total |
| Vision Tarifas | PyGMensual.ica/gmf/polizas para atribución financiera por canal |
