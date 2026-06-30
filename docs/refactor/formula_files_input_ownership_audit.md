# Auditoría de Fórmulas, Inputs y Ownership de Archivos — NEXA Pricing (V2-7)

> Auditoría EXHAUSTIVA sin refactor. Solo mapeo + propuesta. No se movió código, no se cambiaron tests ni contratos.
> Fuente canónica de negocio: `excel/Nexa - Pricing - Simulador - V2-7.xlsx`.
> Request de referencia: `request/request.json` (Bancamia / Cobranzas / 24 meses).

---

## 1. Resumen ejecutivo

### Hallazgos clave

1. **Las clases calculadoras NO viven en `modules/calculator/`**. El directorio `modules/calculator/` contiene únicamente orquestación (engine.py = Composition Root), DTOs, adapters, serializers, audit y persistence. Las **fórmulas reales** están dispersas en módulos verticales: `cadena_a/`, `cadena_b/`, `cadena_c/`, `costos_financieros/`, `pyg/`, `vision_tarifas/`, `vision_cost_to_serve/`. La propuesta `modules/calculator/formulas/` **no existe hoy**; crearla implicaría re-centralizar contra la arquitectura de slices verticales (FASE Y, ver MEMORY).
2. **Duplicado muerto detectado**: `modules/vision_pyg/{kpis.py, costos_totales.py, reglas.py}` contienen clases `KPIsCalculator`, `CostosTotalesCalculator`, `PyGCalculator` y `CadenaBCalculator`/`CadenaCCalculator` con los MISMOS nombres que las activas en `modules/pyg/` y `modules/cadena_b|c/`. **Ningún import del repo (ni código ni tests) las consume**. El único símbolo vivo de `vision_pyg` es `vision_pyg.builders.vision_pyg_builder` que en realidad reside en `modules/pyg/builders/`. Acción: marcar `vision_pyg/{kpis,costos_totales,reglas}.py` como legacy/dead-code candidato a borrado (FASE separada).
3. **El Excel V2-7 tiene caché válido** (workbook guardado con valores cacheados). Solo "Condiciones Cadena A" muestra ~50% de celdas-fórmula con caché `None`, pero son celdas de input opcional vacías, no fórmulas de salida. El resto de hojas (Pólizas, Costos Totales, Panel, Vision*) tienen caché completo y usable como oracle.
4. **Pólizas: divergencia INPUT esperada y documentada**. El `request.json` trae 10 pólizas con `pct_poliza`/`pct_atribuible` por deal (incluida "Comisión de Administración 1.18%" y "Responsabilidad Civil Protección de Datos"). El Excel Panel!C38:E50 trae el mismo set como input de usuario. La parametrización storage (`Tasas, TRM, Polizas`) trae las tasas BASE (r21-r31). El backend usa `polizas_usuario` del request cuando existe (distinción contractual None vs [] vs [...] en `CostosFinancierosCalculator`). Esto es by-design: las pólizas son INPUT del deal, no parametrización.
5. **Anomalía intencional Excel V2-7 (DEC #5 WAVE 0)**: Vision Tarifas usa `margen_a` para el precio de Cadena C; P&G usa `margen_c`. Replicada deliberadamente en backend. NO es bug.
6. **Comisión de Administración**: tasa efectiva = `pct_poliza × 1.42` (Excel Pólizas D188). Implementada en `costos_financieros_calculator.py`. Es el único "factor mágico" 1.42 y proviene del Excel — no inventar otros.
7. **El snapshot persistido (`PricingResult`) ya es suficiente**: incluye `kpis`, `pyg_por_mes`, `cost_to_serve`, `vision_tarifas`, `vision_pyg`, `vision_imprimible`, `datasets_vision`. Las visiones se construyen DURANTE el pipeline y se serializan; los endpoints de visión leen del JSON persistido, no recalculan. Riesgo bajo de drift por recálculo.

### Recomendaciones

- **No re-centralizar fórmulas en `modules/calculator/formulas/`** salvo decisión explícita de arquitectura. La estructura vertical actual es coherente con FASE Y. Si se quiere un punto único de fórmulas puras, la opción de menor riesgo es extraer funciones puras a `modules/<cadena>/formulas.py` DENTRO de cada slice, no en un paquete global.
- **Eliminar `modules/vision_pyg/{kpis,costos_totales,reglas,vision_pyg_60m}.py`** tras confirmar 0 imports (ya confirmado en esta auditoría) — fase de cleanup independiente.
- **Mantener `polizas_usuario` como INPUT** (no migrar a parametrización).
- **Centralizar el estándar de trazabilidad** ya existente (`shared/audit/trace.py` `_audit_trace`) — ya está bien estructurado; solo falta normalizar `formula_id` y `excel_ref`.

---

## 2. Tabla 1 — JSON de entrada (`request/request.json`)

| Sección JSON | Campo | Tipo | Concepto negocio | Consumidor esperado |
|---|---|---|---|---|
| datos_operativos | servicio | str | Línea de negocio (Cobranzas/SAC...) → ramp-up, margen mín | PyG (rampup), KPIs (margen_minimo), CostToServe |
| datos_operativos | cliente / tipo_cliente | str | Identidad y segmento (Grupo Aval / No) | Riesgo, Panel header |
| datos_operativos | fecha_inicio | date | Año base de indexación, mes inicio | Nomina (factor_indexacion), VisionTarifas (mes_inicio_contrato) |
| datos_operativos | duracion_meses | int | Nº meses contrato (24) | PyG.calcular_contrato, KPIs (promedios), Nomina (amortización) |
| datos_operativos | ciudad / sede | str | ICA por ciudad, costos fijos por sede | CostosFinancieros (ICA), NoPayroll (infra) |
| datos_operativos | tarifa_diaria_capacitacion | float | Tarifa día capacitación | Nomina (_cap_inicial, _cap_rotacion) |
| datos_operativos | crucero | float | Costo crucero/agente (Panel!C17) | Nomina (_crucero) |
| datos_operativos | horas_formacion_mes | float | Horas formación mensual | Context builder (tarifa hora) |
| datos_operativos | pct_ausentismo / pct_rotacion | float | % ausentismo/rotación (0.065/0.085) | Nomina (cap_rotacion, examenes), context |
| datos_operativos | cons_costo_de_financiacion | bool | Activa financiación (Panel!C21) | CostosFinancieros (_calcular_financiacion) |
| datos_operativos | tasa_ica / tasa_gmf | float | Tasas impositivas (0.0097/0.004) | CostosFinancieros (ICA, GMF) |
| datos_operativos | ciudades_recurso[] | list | Distribución ciudad → ICA ponderado | Context builder (ICA efectiva) |
| polizas[] | nombre, activa, pct_poliza, pct_atribuible | mixed | Primas de seguros del deal (10 pólizas) | CostosFinancieros (polizas_usuario), VisionTarifas (extensión) |
| polizas[] | aplica_extension, meses_extension | bool/int | Pólizas que extienden post-contrato (Calidad=36m) | VisionTarifas (C45 extension), CostosFinancieros (vigencia) |
| reglas_negocio | margen_objetivo | float | Margen objetivo (0.18) — Panel!C63 | PyG (factor_billing), KPIs |
| reglas_negocio | contingencia_operativa/comercial | obj{valor,min,max} | op_cont/com_cont (Panel!C67/C68) | PyG, CostosFinancieros (factor) |
| reglas_negocio | markup | obj | Markup complejidad (Panel!C69) | PyG (factor_billing) |
| reglas_negocio | imprevistos | float | Imprevistos sobre ingreso (Panel!C73) | PyG (imprevistos = pct × ingreso_bruto) |
| reglas_negocio | porcentaje_acumulado | obj | Descuento volumen acumulado (Panel!C75) | PyG (descuento) |
| volumetria | indexacion | obj | Componente humano/tecnológico, frecuencia, tasa_interes_mensual | Nomina/CadenaB/C (factor_aumento), CostosFin (tasa_mensual_financ) |
| volumetria | inbound/outbound.cadenas_activas | obj bool | Qué cadenas activas por modalidad | engine (_calcular_pipeline gate), adapters |
| volumetria | inbound/outbound.canales[] | list | Canal × cadena (unidad FTE/VOLUMEN, valor, participacion) | Adapters → perfiles_cadena_a, ParametrosCadenaB/C |
| escenarios_comerciales[] | escenario, modalidad, canal, modelo_cobro | mixed | Escenarios de tarifa (Panel!A81:D113) | VisionTarifas (iteración por escenario) |
| escenarios_comerciales[] | componente_fijo/variable, proporcion_* | str/float | pct_fijo/pct_variable por escenario | VisionTarifas (tarifa_fijo/variable) |
| condiciones_cadena_a | Calculo_conversion_fte_interacciones | obj | TMO, tmo_promedio_seg, horas → conversión FTE↔interacciones | Adapters (vol_cadena_a_mensual) |
| condiciones_cadena_a | perfiles[] | list | Perfiles agente: fte, salario_base, comision_pct, pct_presencia, estaciones | Nomina, NoPayroll (todos los componentes) |
| condiciones_cadena_a | perfiles[].roles_operativos[] | list | Roles staff con ratio (X Agentes) e incluye_en_deal | Context builder (perfiles soporte derivados) |
| condiciones_cadena_a | perfiles[].capacitacion | obj | dias_cap, %_mes, flags exámenes/seguridad | Nomina (cap_inicial/rotacion, examenes, seguridad) |
| condiciones_cadena_a | perfiles[].opex_fijo | obj | items OPEX TI por estación + staffing | NoPayroll (overrides opex_ti) |
| condiciones_cadena_a | perfiles[].inversiones[] | list | CAPEX por ítem: precio, meses_a_diferir, cantidad, es_precio_total | NoPayroll (inversiones_amortizables term-based) |
| condiciones_cadena_b | opex.items[] | list | Plataformas/licencias/tokens por canal | CadenaB (opex_fijo) |
| condiciones_cadena_b | inversiones_capex[] | list | CAPEX cadena B diferido | CadenaB (inversiones) |
| condiciones_cadena_b | equipo_soporte_mantenimiento | obj | FTE roles S&M + dispositivos | CadenaB (soporte_mantenimiento) |
| condiciones_cadena_b | costo_variable.tarifas_por_canal | obj | Tarifa unitaria por canal in/out | CadenaB (costo_variable), VisionTarifas |
| condiciones_cadena_b | costo_variable.tasa_escalamiento | obj | % escalamiento + tarifa escalamiento por canal | CadenaB (escalamiento) |
| condiciones_cadena_b | hitl | obj | Volumen + equipo + dispositivos HITL | CadenaB (hitl) |
| condiciones_cadena_c | tarifa_proveedor_canal / inversiones_capex | list | Costos proveedor IA + CAPEX (vacíos en este request) | CadenaC (tarifa_proveedor, inversiones) |
| condiciones_cadena_c | recurso_humano_transversal | obj | FTE + roles + opex transversal IA | CadenaC (equipo_integ) |
| condiciones_cadena_c | costo_variable / hitl | obj | Tarifas + escalamiento + HITL IA | CadenaC (opex_var, escalamiento, hitl) |

> Nota: `condiciones_cadena_a` y `condiciones_cadena_b` están doblemente anidadas (`condiciones_cadena_a.condiciones_cadena_a`). Esto lo normalizan los adapters en `modules/calculator/adapters/entry_data_adapter.py`.

---

## 3. Tabla 2 — Parametrización actual (`storage/parametrization/`)

Estructura real en disco:
- `hr/` `gn/` `op/` `business_rules/` → carpetas versionadas con UUID + `v2-7.json` + `versions.json`.
- `v2-7/` → snapshot consolidado (`hr.json`, `gn.json`, `op.json`, `business_rules.json`, `manifest.json` con sha256).
- `frozen/v2-6.json` → baseline congelado plano (reproducibilidad, modo frozen del engine).
- NO existe carpeta `active/`; la versión activa se resuelve por `versions.json` + `ParametrizationProvider.build()`.

| Concepto | Archivo parametrización | Versión | Valor/Rango | Consumidor | ¿Duplicado en input JSON? |
|---|---|---|---|---|---|
| Tasas indexación (IPC/SMLV) | op (Tasas,TRM,Polizas) | v2-7 | IPC=0.0527, SMLV=0.2378 (2026) | Nomina factor_indexacion | NO (request trae tasa_interes_mensual=0.0153 distinta) |
| Factores aumento acumulado | op | v2-7 | 50%SMMLV/50%IPC=1.14525 (2026) | Nomina factor_aumento | NO |
| Tasas pólizas BASE | op (r21-r31) | v2-7 | Seriedad 0.005 … RC 0.0275 | get_tasa_polizas_efectiva (modo sin polizas_usuario) | SÍ (request.polizas[].pct_poliza es el set efectivo) |
| ICA por ciudad | op (r34-r54) | v2-7 | Bogota=0.00966 | get_ica(ciudad) | PARCIAL (request.tasa_ica=0.0097 override) |
| GMF | op (r30) | v2-7 | 0.004 | get_gmf | SÍ (request.tasa_gmf=0.004) |
| Timbre Nacional | op (r31) | v2-7 | 0.01 | (no usado en cálculo principal) | NO |
| SMMLV | hr (salarios) | v2-7 | 1_750_905 (2026) | get_smmlv (RiesgoCalculator) | NO (canónico HR) |
| Margen mínimo por línea | hr (rentabilidad) | v2-7 | ej. 0.17-0.21 | get_margen_minimo (KPIs) | PARCIAL (request.margen_objetivo=0.18 es el INPUT del deal) |
| Ramp-up por línea (60m) | hr (campana) | v2-7 | [0..1] por mes | get_rampup (PyG) | NO |
| % rotación/ausentismo por línea | hr (rotacion_ausentismo) | v2-7 | defaults por servicio | get_pct_rotacion/ausentismo | PARCIAL (request trae pct_rotacion=0.085 override) |
| Salarios por rol | hr (nomina, salarios) | v2-7 | por rol | get_salario_rol (context builder) | PARCIAL (request perfiles[].salario_base override) |
| Costo examen médico / estudio seguridad | hr (med_seg) | v2-7 | por ciudad | get_examen_medico (Nomina) | NO |
| Costos fijos no-payroll por sede | hr (costo_fijo) | v2-7 | arriendo/energía/etc | get_costo_no_payroll (NoPayroll) | PARCIAL (request opex_fijo.items override por canal) |
| Ratios staff (cargo→agentes) | hr (ratios) | v2-7 | ej. Supervisor=20 | get_ratios_staff (context) | SÍ (request perfiles[].roles_operativos[].ratio) |
| reglas_negocio (políticas comerciales min/max) | business_rules | v2-7 | rangos op/com/markup | get_politicas_comerciales | SÍ (request.reglas_negocio min/max) |
| riesgo_config | business_rules | v2-7 | pesos, umbrales, criterios | RiesgoCalculator | NO |
| comisión administración factor 1.42 | (NO en storage) | — | hardcoded en costos_financieros desde Excel D188 | CostosFinancieros | implícito en request (pct_poliza 0.0118) |

---

## 4. Tabla 3 — Calculator actual (código existente)

| Concepto/Fórmula | Archivo actual | Función | Inputs | Output | Consumidores directos |
|---|---|---|---|---|---|
| Composition Root | modules/calculator/engine.py | NexaPricingEngine._construir_calculadores | PricingRequest | dict calculadores | _calcular_pipeline |
| Pipeline 10 capas | modules/calculator/engine.py | _calcular_pipeline | PricingRequest, tracer | PricingResult | calcular() |
| Nómina (salario, comisiones, cap, exámenes, seguridad, crucero) | modules/cadena_a/nomina.py | NominaCalculator.calcular_para_mes | ParametrosNomina, ParametrosCalculo, PerfilCadenaA[] | ResultadoNomina | CostosTotales, CostToServe, VisionTarifas |
| Factor indexación/aumento | modules/cadena_a/payroll/calculators.py + shared_calc/utils.py | PayrollCalculator.calcular_factor_aumento | mes, pct, mes_aplicacion | float | Nomina, CadenaB, CadenaC |
| No Payroll (opex_ti, capex term-based, infra) | modules/cadena_a/no_payroll.py | NoPayrollCalculator.calcular_para_mes | ParametrosNoPayroll, PerfilCadenaA[] | ResultadoNoPayroll | CostosTotales, CostToServe, VisionTarifas |
| Cadena B (opex, inversiones, S&M, variable, escalamiento, HITL) | modules/cadena_b/reglas.py | CadenaBCalculator.calcular_para_mes | ParametrosCadenaB | ResultadoCadenaB | CostosTotales, CostToServe |
| Cadena C (tarifa proveedor, opex, inversiones, equipo, escalamiento, HITL) | modules/cadena_c/reglas.py | CadenaCCalculator.calcular_para_mes | ParametrosCadenaC, IParametrizationProvider | ResultadoCadenaC | CostosTotales |
| Costos totales (agregación A+B+C) | modules/pyg/services/costos_totales_calculator.py | CostosTotalesCalculator.calcular_para_mes | 4 calculadores, PerfilCadenaA[] | CostosTotalesMes | PyGCalculator |
| Costos financieros (financiación, pólizas, ICA, GMF, comAdm) per-cadena | modules/costos_financieros/calculators/costos_financieros_calculator.py | CostosFinancierosCalculator.calcular | PanelDeControl, IParametrizationProvider, polizas_usuario | CostosFinancierosMes | PyGCalculator, KPIsCalculator |
| Factor billing / ingreso desde costo | modules/shared/profitability/calculators.py | ProfitabilityCalculator | margen, op_cont, com_cont, markup, descuento | float | PyG, CostosFinancieros, VisionTarifas |
| Factor márgenes / período / tasa pólizas / rampup | modules/shared_calc/utils.py | calcular_factor_margenes/periodo/tasa_polizas/rampup | panel, provider | float/int | múltiples |
| P&G mensual (ingreso, costo, utilidad, imprevistos) | modules/pyg/services/pyg_calculator.py | PyGCalculator.calcular_mes / calcular_contrato | panel, CostosTotales, CostosFinancieros, provider, PerfilCadenaA[] | PyGMensual[] | engine, KPIs, CostToServe, VisionTarifas, VisionPyG |
| KPIs deal (tarifa, facturación, rentabilidad) | modules/pyg/services/kpis_calculator.py | KPIsCalculator.calcular | panel, CostosFinancieros, provider, PyGMensual[] | KPIsDeal | engine, VisionPyG, Riesgo, serializer |
| Cost To Serve (CTS por cadena + desglose + canales) | modules/vision_cost_to_serve/services/cost_to_serve_calculator.py | CostToServeCalculator.calcular | PerfilCadenaA[], ParametrosCadenaB/C, calcs, PyGMensual[] | ResultadoCostToServe | engine, VisionImprimible |
| Vision Tarifas (tarifa por canal/escenario, C40/C50/C60/C72) | modules/vision_tarifas/reglas.py (+ mixins/reglas_methods) | VisionTarifasCalculator.calcular | PerfilCadenaA[], ParametrosCadenaB, panel, calcs, escenarios, polizas_usuario | ResultadoVisionTarifas | engine, VisionImprimible, serializer |
| Vision P&G builder | modules/pyg/builders/vision_pyg_builder.py | VisionPyGBuilder.construir | PyGMensual[], KPIs, calcs, panel | VisionPyG | engine |
| Riesgo | modules/riesgo/reglas.py | RiesgoCalculator.calcular | riesgo_config, smmlv, panel, kpis, pyg | EvaluacionRiesgo | engine, VisionImprimible |
| Vision Imprimible (9 secciones) | modules/vision_imprimible/builders/vision_imprimible_builder.py | VisionImprimibleBuilder.construir | panel, kpis, pyg, vision_tarifas, waterfall, reglas, riesgo, cost_to_serve | VisionImprimible | engine |
| Waterfall / reglas negocio | modules/calculator/helpers/engine_helpers.py | _calcular_waterfall / _calcular_reglas_negocio | PyGMensual[], panel, provider | WaterfallPromedio / ReglaNegocios[] | engine |
| DEAD/duplicado | modules/vision_pyg/{kpis,costos_totales,reglas,vision_pyg_60m}.py | (mismas clases) | — | — | NINGUNO (0 imports) |

---

## 5. Tabla 4 — Excel V2-7 (fórmulas/valores)

Cache validado: workbook guardado con valores cacheados. Hojas de salida 100% cacheadas.

| Concepto | Sheet | Rango Excel | Fórmula/Valor | ¿Cacheado válido? |
|---|---|---|---|---|
| Servicio / línea | Panel de Control General | C5 | "Captura de Datos" (input) | Sí |
| Periodo pago / Duración | Panel | C9 / C11 | 30 / 12 | Sí |
| Crucero | Panel | C17 | 8408 | Sí |
| % Ausentismo / Rotación | Panel | C19 / C20 | 0.065 / 0.085 | Sí |
| Considera financiación | Panel | C21 | "No" | Sí |
| ICA / GMF | Panel | C34 / C35 | 0.01 / 0.004 | Sí |
| Pólizas (activada, %prima, %exigido) | Panel | C38:E50 | bool / 0.005-0.0275 / 0.1-1.0 | Sí |
| Margen A/B/C | Panel | C63/D63/E63 | 0.21 / 0.30 / 0.20 | Sí |
| Contingencias/markup/descuento (min/max) | Panel | C67:E70 | 0 / rangos | Sí |
| Imprevistos / % acumulado | Panel | C73 / C75 | 0 / 0 | Sí |
| Escenarios comerciales | Panel | A80:D113 | modalidad/canal/modelo/pct | Sí |
| IPC / SMLV anual | Tasas,TRM,Polizas | B4:C5 | IPC=0.0527, SMLV2026=0.2378 | Sí |
| Factor acumulado 50/50 | Tasas,TRM,Polizas | C13 | =B13+(C4*50%+C5*50%) = 1.14525 | Sí |
| Tasas pólizas base | Tasas,TRM,Polizas | B21:B31 | 0.005…0.0275, ICA 0.01966, GMF 0.004, Timbre 0.01 | Sí |
| ICA por municipio | Tasas,TRM,Polizas | A35:B54 | Bogota 0.00966 | Sí |
| Comisión Admin tasa efectiva | Pólizas - Costo Financiacion | D188 | = pct_poliza × 1.42 | Sí |
| Pólizas (H69 agregado, H68 comAdm total) | Pólizas - Costo Financiacion | H68/H69 | per-cadena ICA+GMF+pure_pol+comAdm | Sí |
| Financiación | Pólizas - Costo Financiacion | EDATE chains | período × tasa × costo_mes_anterior | Sí |
| Costo total operativo | Costos Totales | (matriz) | Σ payroll+nopayroll+B+C por mes | Sí |
| Nómina cargada por mes | Nomina Loaded | D-CF (474 filas) | salario×FTE×factor − comisiones | Sí (33 none = inputs vacíos) |
| No payroll por canal | No payroll | (267 filas) | opex_ti / capex / infra por estación | Sí (271 none = inputs opcionales) |
| C40/C50/C60/C72 tarifas | Vision Tarifas_Modelo_Cobro | C40,C50,C60,C72 | costo_a/b/c, ingreso=(C40+C60)/(1-margen) | Sí |
| CTS por cadena | Vision Cost To Serve | C200, C186, rows 35-125 | avg_costo/denominador | Sí |
| Hoja Maestra escenarios | Hoja Maestra Escenarios | G5, C40, C60 | =SUM(...) = 0.21 | Sí |

---

## 6. Tabla 5 — Comparativa (Excel vs JSON vs Parametrización vs Backend)

| Dato/Parámetro | Origen Excel | Valor Excel | JSON request | Storage param | Backend actual | Status |
|---|---|---|---|---|---|---|
| Tasa ICA | Panel!C34 / por ciudad | 0.01 (Bogota 0.00966) | 0.0097 | 0.00966 (op) | usa request.tasa_ica | DIVERGENCIA_INPUT (request override, by-design) |
| Tasa GMF | Panel!C35 | 0.004 | 0.004 | 0.004 | usa request.tasa_gmf | MATCH |
| Margen objetivo A | Panel!C63 | 0.21 | 0.18 | (rentabilidad) | usa panel.margen=request | DIVERGENCIA_INPUT (deal-specific, by-design) |
| Comisión Admin factor | Pólizas!D188 | ×1.42 | pct 0.0118 | NO en storage | hardcoded 1.42 desde Excel | MATCH (evidencia Excel) |
| Pólizas set | Panel!C38:E50 | 9 + 1 nueva | 10 pólizas | tasas base (op) | polizas_usuario (request) | DUPLICADO intencional (input gana) |
| IPC indexación | Tasas!C4 | 0.0527 | tasa_interes_mensual 0.0153 | 0.0527 (op) | factor desde param | MATCH (param canónico; request.tasa_interes_mensual es financiación, no IPC) |
| Factor billing | Hoja Maestra | (1-m)(1-op)(1-com)(1-mk)(1+d) | inputs en reglas_negocio | min/max en BR | ProfitabilityCalculator | MATCH |
| Imprevistos | Panel!C73 | 0 | 0 | — | panel.imprevistos × ingreso | MATCH |
| Ramp-up | HR Campana | curva 60m | — | hr.campana | get_rampup | MATCH |
| SMMLV | HR Salarios | 1_750_905 | — | hr (v2-7) | get_smmlv | MATCH (BR legacy ignorado) |
| Margen C en Vision Tarifas | DEC#5 anomalía | usa margen_a | — | — | replica anomalía (margen_a) | MATCH (anomalía intencional) |
| ICA gross-up | Pólizas sheet | costo/fm + pol + fin | — | — | _calcular_ica | MATCH |
| Crucero | Panel!C17 | 8408 | 8422 | — | nomina._crucero | DIVERGENCIA_INPUT (request override) |
| Comisión Admin C (rows 333-351) | fuera de rango H69 | excluida de H69 | — | — | comadm_c NO en polizas(H69) | MATCH (replica exclusión Excel) |

---

## 7. Tabla 6 — Propuesta ownership de archivos

**ADVERTENCIA**: La estructura propuesta `modules/calculator/formulas/` CONTRADICE la arquitectura vertical actual (FASE Y). Se documentan DOS opciones.

### Opción A (recomendada, bajo riesgo) — Formulas puras DENTRO de cada slice vertical

| Archivo propuesto | Fórmulas/Conceptos | Inputs | Outputs | Consumidores | Fuente Excel |
|---|---|---|---|---|---|
| modules/cadena_a/nomina.py (ya existe) | salario, comisiones, cap, exámenes, seguridad, crucero | ParametrosNomina, PerfilCadenaA | ResultadoNomina | CostosTotales, CTS, VT | Nomina Loaded, HR Med-Seg |
| modules/cadena_a/no_payroll.py (ya existe) | opex_ti, capex term-based, infra | ParametrosNoPayroll, PerfilCadenaA | ResultadoNoPayroll | CostosTotales, CTS, VT | No payroll, Costo Fijo |
| modules/cadena_b/reglas.py (ya existe) | opex, inversiones, S&M, variable, escalamiento, HITL | ParametrosCadenaB | ResultadoCadenaB | CostosTotales, CTS | Condiciones Cadena B, Costo Variable |
| modules/cadena_c/reglas.py (ya existe) | tarifa proveedor, opex, equipo, HITL, inversiones | ParametrosCadenaC, provider | ResultadoCadenaC | CostosTotales | Costo Cadena C |
| modules/pyg/services/costos_totales_calculator.py (ya existe) | agregación A+B+C | 4 calcs | CostosTotalesMes | PyG | Costos Totales |
| modules/costos_financieros/calculators/costos_financieros_calculator.py (ya existe) | ICA, GMF, pólizas, financiación, comAdm | panel, provider, polizas_usuario | CostosFinancierosMes | PyG, KPIs | Pólizas - Costo Financiacion |
| modules/pyg/services/pyg_calculator.py (ya existe) | P&G mensual, ingreso, imprevistos | panel, calcs, provider | PyGMensual[] | engine, KPIs, visiones | Visión P&G |
| modules/vision_tarifas/reglas.py (ya existe) | tarifa por canal/escenario, C40/C50/C60/C72 | perfiles, panel, escenarios | ResultadoVisionTarifas | engine, VisionImprimible | Vision Tarifas_Modelo_Cobro |
| modules/vision_cost_to_serve/services/cost_to_serve_calculator.py (ya existe) | CTS por cadena + desglose | perfiles, params, pyg | ResultadoCostToServe | engine | Vision Cost To Serve |

> Conclusión Opción A: **la mayoría del ownership YA está correcto**. Solo falta extraer funciones puras (sin trace/log) a un submódulo `formulas.py` dentro de cada slice si se desea separar "fórmula pura" de "orquestación+trace".

### Opción B (alto riesgo, NO recomendada) — Centralizar en modules/calculator/formulas/

Crear `modules/calculator/formulas/{nomina,no_payroll,cadena_a,cadena_b,cadena_c,costos_totales,costos_financieros,pyg,vision_tarifas,vision_cost_to_serve,vision_imprimible}.py`. Requiere mover 9+ módulos verticales, romper imports, re-validar 1249 tests y oracle. **Contradice FASE Y. Solo con decisión de arquitectura explícita.**

---

## 8. Tabla 7 — Snapshot requerido

`PricingResult` (modules/shared/models/results.py:260) ya persiste TODO lo necesario. Las visiones se construyen en el pipeline y se serializan; los endpoints NO recalculan.

| Resultado calculado | Lo produce | ¿Debe persistirse? | Lo consume visiones | Razón |
|---|---|---|---|---|
| kpis (KPIsDeal) | KPIsCalculator | SÍ (ya) | Imprimible §02, P&G, Riesgo | evita recálculo, base de tarifa |
| pyg_por_mes (PyGMensual[]) | PyGCalculator | SÍ (ya) | P&G, Imprimible, CTS, VT | núcleo del estado de resultados |
| cost_to_serve | CostToServeCalculator | SÍ (ya) | Imprimible, endpoint CTS | recálculo costoso (itera meses×canales) |
| vision_tarifas | VisionTarifasCalculator | SÍ (ya) | Imprimible, endpoint tarifas | recálculo costoso (escenarios) |
| vision_pyg | VisionPyGBuilder | SÍ (ya) | endpoint P&G | estructura frontend |
| vision_imprimible | VisionImprimibleBuilder | SÍ (ya) | endpoint imprimible | composición 9 secciones |
| waterfall | _calcular_waterfall | SÍ (ya, dentro de result) | Imprimible | promedio P&G |
| reglas_negocio | _calcular_reglas_negocio | SÍ (ya) | Imprimible | políticas |
| evaluacion_riesgo | RiesgoCalculator | SÍ (ya) | Imprimible | score riesgo |
| datasets_vision | VisionDatasetsBuilder | SÍ (ya, obligatorio) | datasets frontend | obligatorio (AuditIntegrityError si falta) |
| audit_trace | export_audit_trace | SÍ (ya) | auditoría | trazabilidad fórmulas |

**Conclusión: el snapshot es SUFICIENTE. No se requiere persistir resultados intermedios adicionales** (ResultadoNomina/NoPayroll por mes) porque las visiones que los necesitan (CTS, VT) los recalculan deterministicamente vía calculadores inyectados — y el resultado de esas visiones SÍ se persiste. Riesgo de drift bajo.

---

## 9. Tabla 8 — Duplicidades detectadas

| Fórmula/Valor | Ubicación 1 | Ubicación 2 | ¿Intencional? | Acción propuesta |
|---|---|---|---|---|
| KPIsCalculator | modules/pyg/services/kpis_calculator.py (VIVO) | modules/vision_pyg/kpis.py (MUERTO) | NO | Borrar vision_pyg/kpis.py (0 imports) — fase cleanup |
| CostosTotalesCalculator | modules/pyg/services/costos_totales_calculator.py (VIVO) | modules/vision_pyg/costos_totales.py (MUERTO) | NO | Borrar vision_pyg/costos_totales.py |
| PyGCalculator + CadenaB/C | modules/pyg/services/pyg_calculator.py + cadena_b/c (VIVO) | modules/vision_pyg/reglas.py (MUERTO) | NO | Borrar vision_pyg/reglas.py |
| Vision P&G 60m | (no vivo) | modules/vision_pyg/vision_pyg_60m.py | NO | Verificar 0 imports y borrar |
| calcular_factor_margenes | shared_calc/utils.py (wrapper) | shared/profitability/calculators.py (real) | SÍ | Mantener — wrapper delega (backward compat) |
| calcular_factor_aumento | shared_calc/utils.py (wrapper) | cadena_a/payroll/calculators.py (real) | SÍ | Mantener — delegación documentada (WAVE 9) |
| factor_billing | calculado en pyg, costos_financieros, vision_tarifas | ProfitabilityCalculator (único real) | SÍ | OK — todos delegan a ProfitabilityCalculator |
| Tasas pólizas | request.polizas[] (input) | storage op (base) + Excel Panel | SÍ | polizas_usuario gana cuando existe (distinción None/[]/[...]) |
| Factor 1.42 comAdm | costos_financieros_calculator.py | Excel Pólizas!D188 | SÍ | Mantener — evidencia Excel directa |
| margen para Cadena C | vision_tarifas usa margen_a; pyg usa margen_c | DEC#5 WAVE 0 | SÍ | Mantener — anomalía Excel intencional |

---

## 10. Tabla 9 — Estándar de trazabilidad/logs

**Ya existe** `_audit_trace` (modules/shared/audit/trace.py) usado por todos los calculadores con `component`, `rule`, `formula`, `inputs`, `intermediate`, `result`, `source`, `mes`. Propuesta de normalización mínima (agregar `formula_id` y `excel_ref` estandarizados):

```json
{
  "formula_id": "nomina.salario_fijo",
  "archivo": "modules/cadena_a/nomina.py",
  "funcion": "_salario_fijo",
  "concepto": "Salario base mensual cargado",
  "excel_ref": "Nomina Loaded!D93:CF99",
  "rule": "(salario_cargado × FTE × factor_indexacion) − comisiones",
  "inputs": {"salario_cargado": 1560000, "fte": 10, "factor_indexacion": 1.14525, "comisiones": 0},
  "intermediate": {"total_cargado": 17865900},
  "output": 17865900,
  "source": "HR-Nomina + HR-SegSocial + HR-Prestaciones",
  "mes": 1,
  "status": "SUCCESS",
  "error": null
}
```

Campos a ESTANDARIZAR (no presentes hoy de forma consistente):
- `formula_id`: identificador estable `<modulo>.<concepto>` (algunos traces ya usan `component` similar).
- `excel_ref`: hoja!rango canónico (hoy va embebido en `source`, normalizar a campo dedicado).
- `status` / `error`: hoy implícito (excepción rompe pipeline). Agregar para tracing no destructivo.

No requiere refactor de cálculo: solo enriquecer la firma de `_audit_trace` con 3 campos opcionales.

---

## 11. Plan de refactor por fases (sin mover código)

> Si el objetivo es ÚNICAMENTE separar fórmula pura de orquestación/trace (Opción A), no re-centralizar (Opción B).

**Fase 0 (cero riesgo, recomendada primero):** Cleanup de duplicados muertos.
- Borrar `modules/vision_pyg/{kpis,costos_totales,reglas,vision_pyg_60m}.py` tras `grep` confirmatorio (ya confirmado: 0 imports vivos).
- Validar suite completa + oracle. Sin cambio numérico esperado.

**Fase 1 (bajo riesgo):** Nómina.
- Extraer fórmulas puras de `nomina.py` a `modules/cadena_a/formulas_nomina.py` (funciones sin estado/trace). `NominaCalculator` las invoca.
- Test de equivalencia: ResultadoNomina idéntico antes/después por mes. Oracle parity intacto.

**Fase 2 (bajo-medio):** No Payroll.
- Igual patrón. Atención al modelo CAPEX term-based (inversiones_amortizables) — quirk SFTP/meses=1 documentado en MEMORY (CAPEX Amortization Model).

**Fase 3 (medio):** Cadena B y C.
- Extraer fórmulas. Validar redondeo cop_round H-05/H-08 (Excel ROUND_HALF_UP).

**Fase 4 (medio-alto):** Costos Financieros.
- El más sensible: ICA gross-up, comAdm 1.42, per-cadena split, exclusión comAdm_c de H69. Tests parity_oracle_real son la red de seguridad.

**Fase 5 (alto):** P&G + KPIs.
- factor_billing per-cadena, anomalía margen_c. No tocar ProfitabilityCalculator.

**Fase 6 (alto):** Vision Tarifas + Vision Cost To Serve + Vision Imprimible.
- VT tiene lógica de extensión de pólizas C45 muy acoplada. Última en migrar.

En cada fase: contrato público sin cambios, golden/parity/baseline verde, drift documentado.

---

## 12. Riesgos identificados

1. **Re-centralizar en `modules/calculator/formulas/` (Opción B) rompe FASE Y** y arriesga 1249 tests + oracle. Riesgo ALTO. Evitar salvo decisión de arquitectura.
2. **CostosFinancieros es el punto más frágil**: per-cadena, gross-up, 1.42, exclusiones de rango. Cualquier extracción debe preservar el orden de dependencia (financiación→pólizas→ICA/GMF).
3. **Anomalía margen_c (DEC#5)**: cualquiera que "corrija" Vision Tarifas a margen_c rompe paridad. Documentado pero frágil.
4. **Doble anidación de condiciones_cadena_a/b** en request: depende de adapters; cambiar la forma del request rompe el contrato de entrada.
5. **Pólizas como input vs parametrización**: confundir None/[]/[...] altera el costo financiero. Distinción crítica de auditoría.
6. **Caché Excel "Condiciones Cadena A"**: ~50% celdas None — NO usar esa hoja como oracle de valores derivados; usar Nomina Loaded / Costos Totales / Vision* que sí están cacheadas.
7. **`vision_pyg` muerto** puede confundir a futuros devs (nombres idénticos a clases vivas). Borrarlo reduce riesgo cognitivo.

---

## 13. Próximos pasos para refactor seguro

1. **Decisión de arquitectura requerida**: confirmar Opción A (formulas puras dentro de slices) vs Opción B (centralizar). Recomendación firme: Opción A.
2. **Ejecutar Fase 0** (borrar `vision_pyg/{kpis,costos_totales,reglas,vision_pyg_60m}.py`) — cleanup sin riesgo numérico, requiere solo confirmación de 0 imports (ya confirmada) y suite verde.
3. **Estandarizar `_audit_trace`** con `formula_id` + `excel_ref` (3 campos opcionales) antes de mover fórmulas, para tener trazabilidad de equivalencia durante la migración.
4. **Congelar baseline oracle** del request actual (`request/request.json`) como golden adicional antes de Fase 1.
5. **Por cada fase**: extraer → test de equivalencia bit-a-bit del Resultado* del calculador → suite parity/baseline/oracle → documentar drift (esperado: cero).

---

## Criterios de aceptación — paridad 100% (Tarea 11)

- Backend ≈ Excel: diferencia ≤ tolerancia COP (cop_round ROUND_HALF_UP) en C40/C50/C60/C72, P&G mensual, CTS, KPIs.
- Inputs == JSON request: todo valor del deal (margen, pólizas, tasas, crucero, perfiles) proviene del request, no de defaults silenciosos.
- Parametrización no duplicada: storage solo aporta lo canónico (ramp-up, SMMLV, factores indexación, costos médicos); el deal aporta overrides.
- Fórmulas sin duplicatas: 0 imports a `vision_pyg/{kpis,costos_totales,reglas}`; factor_billing/margenes/aumento delegan a un único calculador.
- Snapshot suficiente: PricingResult contiene kpis+pyg+todas las visiones; endpoints no recalculan.
- Tests de regresión: `pytest -m parity`, `-m parity_oracle_real`, `-m baseline` en verde; `make verify` y `make validate-excel` sin drift.
