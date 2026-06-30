# Formula IDs propuestos — FORMULA_REFACTOR_BASELINE_0 (TAREA 3)

Propuesta de identificadores estables `LAYER.COMPONENT_CALCULATION`. NO se
implementa tracing aún. Los IDs deben sobrevivir al refactor (no cambian aunque
la implementación se reorganice). Mapeo: ID → ubicación actual → tipo de cálculo.

> Composition Root: `modules/calculator/engine.py::_construir_calculadores` (L433+).

## Capa 2 — NominaCalculator  (`modules/cadena_a/nomina/`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| NOMINA.SALARIO_BASE | NominaCalculator (salario por perfil) | base salarial |
| NOMINA.SALARIO_VARIABLE | NominaCalculator (comisiones/variable) | variable |
| NOMINA.PRESTACIONES | hr.prestaciones (cesantías/primas/int/vac) | factor legal |
| NOMINA.SEGURIDAD_SOCIAL | hr.seg_social (salud/pensión/ARL/caja/sena) | factor legal |
| NOMINA.SALARIO_CARGADO | NominaCalculator (loaded = base*factores) | agregado |
| NOMINA.RAMP_UP | hr.rentabilidad ramp por servicio (Cobranzas 0.85/0.92/1.0) | curva |
| NOMINA.ROLES_OPERATIVOS | NominaCalculator (roles por ratio agentes) | staffing |
| NOMINA.CAPACITACION | NominaCalculator (inicial + rotación) | costo periódico |

## Capa 3 — NoPayrollCalculator  (`modules/cadena_a/no_payroll/`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| NO_PAYROLL.OPEX_FIJO | NoPayrollCalculator (items opex_fijo) | costo fijo |
| NO_PAYROLL.INFRAESTRUCTURA | NoPayrollCalculator (internet/VPN/backup) | TI |
| NO_PAYROLL.TI_LICENCIAS | NoPayrollCalculator (CCaaS/antivirus/office) | TI |
| NO_PAYROLL.INVERSIONES_CAPEX | NoPayrollCalculator (amortización diferida) | CAPEX |
| NO_PAYROLL.COSTO_FIJO_SEDE | hr.costo_fijo (sede combinada) | costo fijo |

## Capas 4-5 — CadenaBCalculator  (`modules/cadena_b/reglas.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| CADENA_B.PLATAFORMA_DIGITAL | CadenaBCalculator (inversion_plataforma) | CAPEX |
| CADENA_B.OPEX_CONSUMO_VARIABLE | CadenaBCalculator (opex items por canal) | costo variable |
| CADENA_B.EQUIPO_SOPORTE_MANT | CadenaBCalculator (equipo_sm + dispositivos) | RRHH soporte |
| CADENA_B.HITL | CadenaBCalculator (human-in-the-loop) | RRHH |
| CADENA_B.TARIFA_CANAL | CadenaBCalculator (tarifa_unitaria por canal/modalidad) | tarifa |
| CADENA_B.ESCALAMIENTO | CadenaBCalculator (pct/costo escalamiento) | costo variable |

## Capa 6 — CadenaCCalculator  (`modules/cadena_c/reglas.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| CADENA_C.IA_INTEGRACION | CadenaCCalculator (tarifa_proveedor por canal) | costo IA |
| CADENA_C.INVERSION_ANUAL | CadenaCCalculator (capex amortizado) | CAPEX |
| CADENA_C.RECURSO_TRANSVERSAL | CadenaCCalculator (equipo_transversal) | RRHH |
| CADENA_C.HITL | CadenaCCalculator (costo_personal_hitl) | RRHH |

## Capa 7 — CostosTotalesCalculator  (`modules/pyg/services/costos_totales_calculator.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| COSTOS_TOTALES.COSTO_OPERATIVO | CostosTotalesCalculator (A+B+C operativo) | agregado |
| COSTOS_TOTALES.CONTINGENCIA_OP | reglas_negocio.contingencia_operativa | sobrecosto |
| COSTOS_TOTALES.CONTINGENCIA_COM | reglas_negocio.contingencia_comercial | sobrecosto |
| COSTOS_TOTALES.MARKUP | reglas_negocio.markup | sobrecosto |
| COSTOS_TOTALES.IMPREVISTOS | reglas_negocio.imprevistos | sobrecosto |

## Capa 8 — CostosFinancierosCalculator  (`modules/costos_financieros/`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| COSTOS_FINANCIEROS.ICA | CostosFinancierosCalculator (tasa_ica * base) | impuesto |
| COSTOS_FINANCIEROS.GMF | CostosFinancierosCalculator (tasa_gmf * base) | impuesto |
| COSTOS_FINANCIEROS.POLIZAS | CostosFinancierosCalculator (10 pólizas * pct_atribuible) | seguros |
| COSTOS_FINANCIEROS.COMISION_ADMIN | póliza Comisión Admón 1.18% sobre ventas | comisión |
| COSTOS_FINANCIEROS.FINANCIACION | CostosFinancierosCalculator (tasa_mensual período pago) | financiero |
| COSTOS_FINANCIEROS.TASA_MENSUAL | indexacion.tasa_interes_mensual (0.0153) | financiero |
| COSTOS_FINANCIEROS.COMPONENTE_FINANCIERO | agregado financiero mensual | agregado |

## Capa 9 — PyGCalculator  (`modules/pyg/services/pyg_calculator.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| PYG.INGRESO_BRUTO | PyGCalculator (ingreso bruto A/B/C por mes) | ingreso |
| PYG.INGRESO_NETO | PyGCalculator (bruto + contingencias + markup - desc) | ingreso |
| PYG.COSTO_TOTAL | PyGCalculator (operativo + financiero) | costo |
| PYG.CONTRIBUCION | PyGCalculator (neto - costo total) | margen |
| PYG.PCT_UTILIDAD_NETA | PyGCalculator (contribución / ingreso neto) | KPI mensual |
| PYG.INDEXACION | PyGCalculator (IPC anual mes_aplicacion) | ajuste |
| PYG.RAMP_UP_APLICADO | PyGCalculator (ramp * ingreso/costo) | curva |

## Capa 10 — KPIsCalculator  (`modules/pyg/services/kpis_calculator.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| KPIS.INGRESO_MENSUAL | KPIsCalculator (promedio mensual) | KPI |
| KPIS.COSTO_TOTAL_CONTRATO | KPIsCalculator (suma 24m) | KPI |
| KPIS.UTILIDAD_NETA_TOTAL | KPIsCalculator (contribución total) | KPI |
| KPIS.PCT_UTILIDAD_NETA_TOTAL | KPIsCalculator (util/ingreso neto total) | KPI |
| KPIS.MARGEN_MINIMO | hr.rentabilidad (Cobranzas 0.21) | gate negocio |
| KPIS.CUMPLE_MARGEN | KPIsCalculator (pct >= mínimo) | gate negocio |

## Visión Cost-to-Serve  (`modules/vision_cost_to_serve/`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| CTS.COST_TO_SERVE_TOTAL | CostToServeCalculator | KPI servicio |
| CTS.CTS_PONDERADO | CostToServeCalculator (por canal/cadena) | KPI |
| CTS.COSTO_POR_CADENA | CostToServeCalculator (A/B/C breakdown) | desglose |

## Visión Tarifas  (`modules/vision_tarifas/reglas.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| VISION_TARIFAS.CANAL_TARIFA | VisionTarifasCalculator (tarifa por canal) | tarifa |
| VISION_TARIFAS.COMPONENTE_FIJO | VisionTarifasCalculator (modelo cobro fijo) | tarifa |
| VISION_TARIFAS.COMPONENTE_VARIABLE | VisionTarifasCalculator (transacción) | tarifa |
| VISION_TARIFAS.MARGEN_FINANCIERO | VisionTarifasCalculator | margen |

## Visión Imprimible  (`modules/vision_imprimible/`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| VISION_IMPRIMIBLE.SECCION_01_FICHA_DEAL | serializer 9 secciones | presentación |
| VISION_IMPRIMIBLE.SECCION_02_ECONOMICS | ingreso/costo/margen | presentación |
| VISION_IMPRIMIBLE.SECCION_03_ESTRUCTURA_EQUIPO | FTE/roles | presentación |
| VISION_IMPRIMIBLE.SECCION_04_PYG | resumen P&G | presentación |

## Riesgo  (`modules/riesgo/reglas.py`)
| Formula ID | Ubicación | Tipo |
|---|---|---|
| RIESGO.EVALUACION | RiesgoCalculator (riesgo_config) | gate |
| RIESGO.SMMLV_REFERENCIA | parametrizacion.get_smmlv | constante |

Total: 50+ IDs propuestos cubriendo capas 2-10 + visiones + riesgo.
