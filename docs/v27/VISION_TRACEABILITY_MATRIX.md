# Matriz de Trazabilidad Visiones → API (Excel V2-7 ↔ Backend)

> FASE 5. Inventario fundado en el JSON real de `pricing_result_to_dict` ejecutado sobre
> `test_cases/input/solo_cadena_a.json` (motor real, parametrización real). Evidencia literal:
> `archivo:función` backend + celda/rango Excel. **Sin propuestas de cambio.**
>
> Clasificación: **MATCH** (Excel y API, misma semántica) · **MISSING** (Excel sí, API no) ·
> **EXTRA** (API sí, Excel no) · **DRIFT** (ambos, semántica distinta).
> Builders/serializers en `calculators/*` y `adapters/pricing_serializer.py` (PS).

## Sección 1 — Tabla maestra

### ficha_deal — `PS::_ficha_deal_to_dict(panel)` · origen: Visión Imprimible §01 + Panel
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| cliente | Panel!C6/D6 (VI!B11) | MATCH | — |
| tipo_cliente / antiguedad_cliente | Panel!C8 / C7 (VI!T11) | MATCH | — |
| ciudad / sede | Panel!C12 / C13 (VI!N11) | MATCH | — |
| linea_negocio | Panel!C5 (VI!H11) | MATCH | — |
| fecha_inicio / fecha_fin / duracion_contrato / meses_contrato / mes_finalizacion | Panel!C10/C11 (VI!B13/H13) | MATCH | — |
| periodo_pago_dias | Panel!C9 (VI!N13) | MATCH | — |
| ajuste_precio_tipo/_tecnologico/_frecuencia / mes_ajuste_indexacion | Panel!L7/L8 (VI!T13) | MATCH | — |
| tasa_ica / tasa_gmf | Panel!C34 / C35 | MATCH (ICA: drift menor 0,00966 vs 0,01, Fase 4) | — |
| pct_ausentismo / horas_formacion_mensual / tarifa_diaria_capacitacion / tarifa_crucero / complejidad_especialista | Panel!C19/C18/C16/C17/… | MATCH (crucero: DRIFT menor, GAP-TAR/C17) | — |
| activa_financiacion / cadenas_activas / divisa | Panel inputs | MATCH | — |

### kpis — `KPIsCalculator.calcular` → `asdict(kpis)` · origen: VI §02 Economics
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| ingreso_mensual | nativo pyg (NO Tarifas C72 tras Opción A) | MATCH (base nativa) | GAP-IMP (P2 resuelto) |
| facturacion_mensual_proyectada | nativo pyg | MATCH | — |
| costo_mensual_promedio | nativo pyg | MATCH | — |
| costo_total_contrato | Σ P&G costo_total (sin financiero) | MATCH | — |
| valor_total_deal | Σ P&G ingreso_neto (≈CTS!C200) | MATCH | — |
| contribucion_total / utilidad_neta_total / pct_utilidad_neta_total | P&G filas 74/79/80 | MATCH | — |
| ingreso_bruto_total / ingreso_neto_total / costo_cadena_a_promedio | P&G filas 18/27/31 | MATCH | — |
| **margen_minimo_requerido** | `get_margen_minimo(servicio)` = Rot!B29:B34 / Panel!C63 (=0,21) | MATCH (storage) | GAP-CADENA-A-FASE4 |
| cumple_margen_minimo | derivado (margen ≥ mínimo) | MATCH | — |

### configuracion_comercial — `PS::_configuracion_comercial` · origen: VI §03
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| modelo_cobro_principal | Tarifas!C33 (VI!B36) | MATCH | — |
| pct_fijo_global / pct_variable_global | Tarifas!D34 / D35 (VI!I36/P36) | MATCH (sin label compuesto) | GAP-IMP-05 |
| tarifa_fija | Tarifas!G47 (VI!B38) — pero G47=0 para FTE (la real es G45) | **DRIFT** | GAP-TAR-03 |
| tarifa_variable | Tarifas!G55 (VI!D38) | MATCH | — |
| descuento / margen_objetivo | Panel!C70 / C63 (VI!I38/T38) | MATCH | — |
| volumen_base_mensual | Panel!L52 (VI!N38) vs cost_to_serve.vol_cadena_b | DRIFT (fuente distinta) | GAP-IMP-06 |
| ingreso_mensual / costo_mensual_total | Tarifas C72 / (C40+C60) — leídos de vision_tarifas (Opción A) | MATCH (escenario) | — |
| valor_total_deal | kpis (nativo) | MATCH | — |

### waterfall_promedio — `engine::_calcular_waterfall` → `PS::_waterfall_to_dict` · origen: VI §04.01 (chartEx1, `Graficos!N56:X57`)
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| payroll_a, no_payroll_a, costo_b, costo_c, financiacion, polizas, ica, gmf, costo_total, ingreso_bruto, contingencias, markup_descuento, ingreso_neto, contribucion, meses_activos | P&G filas 32/43/45/55/70/69/66/67/30/18/22-24/24-25/27/74 (promedios) | MATCH | — |

### pyg_por_mes — `PyGCalculator` → `PS::_pyg_to_dict` · origen: Visión P&G (C:BJ)
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| (≈25 campos/mes: ingreso_bruto/neto, costo_a/b/c, payroll_a, no_payroll_a, ica/gmf/polizas, contribucion, utilidad_neta, pct_*) | P&G filas 18-80 por mes | MATCH (acumulado BK: DRIFT financiero) | GAP-PYG-01 |

### vision_pyg — `VisionPyGBuilder` → `PS::_vision_pyg_to_dict` · origen: Visión P&G jerárquico
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| resumen, secciones[], filas+detalle (excel_row/formula), puestos_trabajo, fechas_meses | Visión P&G filas 14-80 | MATCH | — |
| +C71 (ingreso bruto término extra) | P&G!C18 incluye +C71 | MISSING (omitido) | GAP-PYG-03 |
| Comisión Adm / periodo pago header | P&G!C68 / I5 | DRIFT (fuente) | GAP-PYG-04 / 05 |
| tipo_servicio (Call Center/Fuerza Ventas) | P&G!G6 | MISSING | GAP-PYG-06 |

### cost_to_serve — `CostToServeCalculator` → `PS::_cost_to_serve_to_dict` · origen: Vision Cost To Serve
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| cts_cadena_a/b/c, cts_ponderado | CTS!C34/G34/K34/G49 | MATCH | — |
| participacion_a/b/c | CTS!C31/G31/K31 | MATCH | — |
| costo_total_acumulado | nativo Σ P&G mensual A+B+C (NO H19 tras Opción A) | MATCH (escenario H19 → vision_tarifas.costo_total_scenario) | GAP-A-01 (resuelto) |
| desglose_a/b, canales_detalle, canal_view_habilitado | CTS rows 34-48/62-113 | MATCH (canal único Excel vs lista backend) | GAP-CTS-04/05 |

### vision_tarifas — `VisionTarifasCalculator` → `PS::_vision_tarifas_to_dict` · origen: Vision Tarifas
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| canales[], costo_cadena_a/b/c_total, ingreso_cadena_a/b/c | Tarifas C40-C67 | MATCH | — |
| ingreso_mensual (C72) | Tarifas!C72 = C47+C57+C67 | DRIFT (backend excluye Cadena B C57) | GAP-TAR-01 |
| costo_total_scenario (@property, H19=C40+C60) | Tarifas C40+C60 | MATCH (añadido P2) | — |
| Cadena C base (C60/C62 filas 67-85) | Tarifas filas 67-85 vs P&G filas 95-457 | DRIFT (1,88×, base distinta) | GAP-TAR-08 (crítico) |
| escenarios_detalle (matriz C20:G21 por escenario) | Tarifas!C20:G21 | MISSING en composite VI | GAP-IMP-01 |

### evaluacion_riesgo — `RiesgoCalculator` → `PS::_evaluacion_riesgo_to_dict` · origen: VI §06 / Riesgo
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| score_cliente / score_operativo / score_total | Riesgo!E17 / E16 / E18 (VI!B87/B90/B92) | MATCH | — |
| clasificacion_total | Riesgo clasificación | MATCH | — |
| criterios[] (10) | Riesgo!E3:E12, D3:D12, N3:N12 (VI!P/U/W) | MATCH | — |
| requiere_aprobacion (1 bool, 1000·SMMLV) | VI!M91/M92/M93 (3 niveles: 100M/200M/1.000M) | **DRIFT** | GAP-IMP-04 |

### reglas_negocio — `engine::_calcular_reglas_negocio` → `PS::_reglas_negocio_to_dict` · origen: VI §07
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| reglas[] (nombre, label, aplicado, min, max, status, monto) | VI filas 101-105 (Panel!C63:E70) | MATCH | — |
| monto (base costo_total) | Σ P&G mensual (4.868 B) vs cts (VT) | DRIFT (base distinta a cts) | GAP-A-01 / nota |
| alerta, costo_total, valor_total_deal | derivados | MATCH | — |

### vision_por_servicio / vision_por_canal / detalle_por_canal / estructura_equipo — `VisionImprimibleBuilder` → `PS::_vision_ejecutiva_sections`
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| vision_por_servicio[] (servicio, ingreso_mensual, cts_ponderado, costo_mensual, margen, fte_total, volumen_mensual, cadenas_activas) | CTS "Visión General por Servicio" filas 25-48 | MATCH (parcial) | — |
| vision_por_canal[] (canal, modalidad, modelo_cobro, estado, fte, participacion, facturacion, inbound/outbound) | CTS "Por Canal" filas 62-83 | MATCH (parcial) | — |
| detalle_por_canal[] (desglose CTS + nomina_loaded/salario/capacitacion/…/inbound/outbound) | CTS detalle por canal filas 90+ | MATCH (parcial; canal único Excel) | GAP-CTS-04 |
| estructura_equipo (roles, por_cargo, fte_total/agentes/soporte, costo_total_mensual) | Condiciones Cadena A / staffing (sin sección dedicada VI) | EXTRA (sin hoja Excel directa) | — |

### panel — `PanelDeControl` → `asdict` · origen: inputs Panel
| Campo API | Excel origen | Clasificación | GAP-ID |
|-----------|--------------|---------------|--------|
| margen / margen_b / margen_c | Panel!C63 / D63 / E63 | MATCH (margen A: fuente input vs servicio) | GAP-CADENA-A-FASE4 |
| op_cont/com_cont/markup/descuento/imprevistos | Panel!C67-C70/C73 | MATCH | — |
| tasa_comision_administracion / aplica_ley_1819 / tasa_mensual_financ | Panel / config | MATCH | — |
| (resto inputs: cliente, fechas, tasas, indexacion, cadenas_activas) | Panel | MATCH | — |

### EXTRA sin contraparte Excel
| Campo API | Builder | Clasificación |
|-----------|---------|---------------|
| simulation_id, scenario, calculated_at | serializer (metadata ejecución) | EXTRA |
| datasets_vision (staffing, polizas, indexacion, volumetria) | `VisionDatasetsBuilder` | EXTRA (datasets internos) |
| audit_trace (generated_at, entries, summary) | `export_audit_trace` | EXTRA (auditoría backend) |
| polizas (cadena_a/b/c) | `_polizas_por_cadena` | EXTRA (desglose interno) |

### MISSING (en composite del endpoint, builder produce pero no se serializa)
| Visión solicitada | Estado | GAP-ID |
|-------------------|--------|--------|
| comparativo_escenarios | **MISSING** (builder lo crea, no serializado) | GAP-IMP-11 |
| economics | **MISSING** (builder lo crea, no serializado) | GAP-IMP-10 |
| evolucion_mensual | **MISSING / derivable de pyg_por_mes** | GAP-IMP-12 |
| estado_margen (VI!N20) | **MISSING** | GAP-IMP-03 |

## Sección 2 — Cobertura agregada

| Visión | Total campos | MATCH | MISSING | EXTRA | DRIFT | % cobertura (MATCH/total) |
|--------|--------------|-------|---------|-------|-------|----------------------------|
| ficha_deal | 26 | 26 | 0 | 0 | 0 | 100% |
| kpis | 13 | 13 | 0 | 0 | 0 | 100% |
| configuracion_comercial | 11 | 8 | 0 | 0 | 3 (tarifa_fija, volumen_base, +pct labels parc.) | 73% |
| waterfall_promedio | 15 | 15 | 0 | 0 | 0 | 100% |
| pyg_por_mes | ~25 | ~24 | 1 (+C71) | 0 | acum (BK financiero) | ~96% |
| vision_pyg | 6 secciones | 4 | 2 (tipo_servicio, +C71) | 0 | 2 (comAdm, periodo) | ~67% |
| cost_to_serve | 15 | 13 | 0 | 0 | 2 (canal único, gate) | 87% |
| vision_tarifas | 11 | 8 | 1 (matriz escenarios) | 0 | 2 (C72 Cadena B, Cadena C base) | 73% |
| evaluacion_riesgo | 6 | 5 | 0 | 0 | 1 (3 niveles aprob.) | 83% |
| reglas_negocio | 4 | 3 | 0 | 0 | 1 (base monto) | 75% |
| vision_por_servicio | 10 | 10 | 0 | 0 | 0 | 100% |
| vision_por_canal | 14 | 14 | 0 | 0 | 0 | 100% |
| detalle_por_canal | 27 | 26 | 0 | 0 | 1 (canal único) | 96% |
| estructura_equipo | 6 | 0 | 0 | 6 | 0 | EXTRA (sin Excel) |
| panel | 32 | 31 | 0 | 0 | 1 (margen fuente) | 97% |
| **comparativo_escenarios** | (8 esc.) | 0 | 8 | 0 | 0 | **0% (MISSING)** |
| **economics** | 5 | 0 | 5 | 0 | 0 | **0% (MISSING)** |
| **evolucion_mensual** | 5 | 0 | 5 | 0 | 0 | **0% (MISSING/derivable)** |

## Sección 3 — Gaps no documentados previamente (nuevos en Fase 5)

1. **`kpis.margen_minimo_requerido` SÍ expone el margen-por-servicio de storage** (= `get_margen_minimo` = Rot!B29:B34 = 0,21). Es decir, el valor "correcto Excel" del margen **ya está en el API** (en `kpis.margen_minimo_requerido`), separado del margen de cálculo (`panel.margen`, input). Refuerza GAP-CADENA-A-FASE4: el dato existe expuesto; lo que falta es cablearlo al ingreso. Clasificación: MATCH (dato presente) + wiring pendiente.
2. **`estructura_equipo` es EXTRA**: no tiene hoja/sección Excel V2-7 dedicada (deriva de Condiciones Cadena A + staffing). No es gap de paridad, pero es un campo API sin oracle Excel → no certificable contra Excel.
3. **`reglas_negocio.monto` usa base `Σ P&G mensual` (4.868 B)** mientras `cost_to_serve.costo_total_acumulado` es nativo y `vision_tarifas.costo_total_scenario` es escenario → **tres bases de "costo total" coexisten** en el JSON. Registrar (no re-auditar): consistente con GAP-A-01; el consumidor debe elegir la base correcta por contexto.
4. **`panel` (asdict) duplica ~15 campos de `ficha_deal`** (cliente, fechas, tasas, cadenas_activas) con posibles formatos distintos (panel crudo vs ficha formateada) → riesgo de doble fuente de verdad para el frontend.

## Sección 4 — Riesgos de migración Azure (por DRIFT)

| DRIFT | Tipo de divergencia | Riesgo de migración |
|-------|---------------------|---------------------|
| GAP-IMP-04 (3 niveles aprobación) | **Modelo** (1 bool vs 3 niveles + umbrales distintos) | Alto: la lógica de aprobación debe rediseñarse; afecta workflow de negocio, no solo display |
| GAP-TAR-08 (Cadena C base 1,88×) | **Cálculo** (Tarifas filas 67-85 vs P&G 95-457) | Alto: divergencia de valor en ingreso headline; bloquea certificación de paridad |
| GAP-PYG-01 (costo acum con/sin financiero) | **Cálculo** (BK30 incluye financiero, backend no) | Medio: afecta acumulados P&G; aislado a la columna BK |
| GAP-TAR-01 (C72 excluye Cadena B) | **Cálculo** (C47+C57+C67 vs C47+C67) | Medio: nulo si Cadena B inactiva; material si activa |
| GAP-TAR-03 (tarifa fija G47 vs G45) | **Presentación/modelo** (celda fuente incorrecta para FTE) | Bajo-Medio: enlace de campo; el dato correcto (G45) existe |
| GAP-CADENA-A-FASE4 (margen fuente) | **Modelo** (input vs tabla servicio) | Medio: decisión de negocio; warning ya instrumentado; +9,63% si se conmuta |
| GAP-IMP-06 (volumen base) | **Modelo** (Panel!L52 vs cost_to_serve.vol_cadena_b) | Bajo: campo informativo |
| GAP-PYG-04/05 (comAdm, periodo pago) | **Cálculo/fuente** | Bajo: componentes menores |

**Resumen de riesgo:** los DRIFT de **cálculo** (GAP-TAR-08, GAP-PYG-01, GAP-TAR-01) y de **modelo** (GAP-IMP-04, GAP-CADENA-A-FASE4) son los que bloquean paridad/decisiones; los de **presentación** (GAP-TAR-03, IMP-05/06) son de bajo riesgo. Las visiones **MISSING** (comparativo_escenarios, economics, evolucion_mensual) requieren exponer estructuras que el builder ya produce — riesgo de contrato, no de cálculo.

---
*Sin propuestas de cambio. Sin refactor jerárquico (Fase 5C). Campos no trazables marcados explícitamente (EXTRA / Origen desconocido). Gaps previos solo registrados por referencia.*
