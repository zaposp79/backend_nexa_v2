# Visión Cost To Serve — Mapa Jerárquico

## Árbol de datos

```
PerfilCadenaA[] + ParametrosCadenaB + ParametrosCadenaC
 └── denominators K50 / L50 / M50

PyGMensual[] (monthly costs)
 ├── costo_a = payroll_a + no_payroll_a
 ├── costo_b
 └── costo_c_fin

NominaCalculator (per perfil, per mes)
 └── DesgloseCTSCadenaA (sub-components)
      ├── nomina_loaded = salario_fijo + salario_variable
      ├── cap_inicial, cap_rotacion
      ├── examenes, estudios_seguridad
      └── opex_fijo, inversiones, costos_fijos_estacion

CadenaBCalculator (per mes)
 └── DesgloseCTSCadenaB
      ├── componente_fijo (opex, inversiones, s_m)
      └── componente_variable (tarifa, escalamiento, hitl)

CostToServeCalculator.calcular()
 └── ResultadoCostToServe
      ├── cts_cadena_a = (payroll + no_payroll) / K50
      ├── cts_cadena_b = costo_b / L50
      ├── cts_cadena_c = costo_c_fin / M50
      ├── cts_ponderado = weighted avg
      ├── desglose_a (DesgloseCTSCadenaA)
      └── desglose_b (DesgloseCTSCadenaB)
```

## Relación con otras vistas

| Vista | Consume de CTS |
|-------|---------------|
| Visión Imprimible (Section 02) | cts_ponderado / meses_contrato = CTS mensual |
| Visión Tarifas | K50 (para fin_ch proporcional) |
| API response | `cost_to_serve` key |
