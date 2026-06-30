# F6 — Drift Heatmap (Oracle Validation Mesh)

- Total checkpoints: **161**
- Tolerancia técnica: rel < 1e-6 (objetivo conceptual 0.00%)
- Request: `tests/parity/fixtures/excel_v2_7_real_request.json` (V2-7 preloaded)
- Oracle source: `tests/parity/excel_oracle_v2_7_mesh.json` (V2-7)

## Resumen global

| Verdict | Count | Pct |
|---|---:|---:|
| PASS | 20 | 12.4% |
| FAIL | 124 | 77.0% |
| BACKEND_MISSING | 5 | 3.1% |
| NO_ORACLE | 12 | 7.5% |

## Heatmap por stage

| Stage | Total | PASS | FAIL | MISSING | Min drift | Max drift | Median drift |
|---|---:|---:|---:|---:|---:|---:|---:|
| COSTOS_FINANCIEROS | 28 | 0 | 28 | 0 | 86.6983% | 100.0000% | 96.6608% |
| COSTO_A | 7 | 0 | 7 | 0 | 1.7529% | 2.0933% | 1.7529% |
| COSTO_B | 7 | 7 | 0 | 0 | - | - | - |
| COSTO_C | 7 | 0 | 7 | 0 | 100.0000% | 100.0000% | 100.0000% |
| COSTO_TOTAL | 7 | 0 | 7 | 0 | 88.0587% | 88.0637% | 88.0587% |
| INGRESO | 14 | 0 | 14 | 0 | 87.9044% | 87.9095% | 87.9044% |
| KPI | 3 | 0 | 3 | 0 | 99.4281% | 99.4352% | 99.4281% |
| NOMINA | 5 | 0 | 0 | 2 | - | - | - |
| NOMINA_LOADED | 16 | 0 | 15 | 0 | 15.0105% | 16.3216% | 16.3216% |
| NO_PAYROLL_A | 7 | 0 | 7 | 0 | 67.5521% | 68.1155% | 67.5521% |
| PANEL | 15 | 6 | 3 | 1 | 96.6000% | 100.0000% | 100.0000% |
| PAYROLL_A | 7 | 0 | 7 | 0 | 14.3663% | 14.3663% | 14.3663% |
| PYG | 14 | 0 | 14 | 0 | 86.6954% | 87.2925% | 87.2925% |
| RAMPUP | 7 | 7 | 0 | 0 | - | - | - |
| VISION_CTS | 9 | 0 | 9 | 0 | 6.6667% | 250.6804% | 99.9626% |
| VISION_TARIFAS | 8 | 0 | 3 | 2 | 87.5829% | 100.0000% | 99.4352% |

## Top 10 checkpoints con mayor drift

| Stage | Checkpoint | Excel cell | Excel value | Backend value | Drift |
|---|---|---|---:|---:|---:|
| VISION_CTS | `cts.participacion_b` | `Vision Cost To Serve!G31` | 0.2851 | 0.9999 | 250.6804% |
| PANEL | `panel.tarifa_capacitacion_diaria` | `Panel de Control General!C16` | 20,000.0000 | 0.0000 | 100.0000% |
| PANEL | `panel.horas_formacion_mensual` | `Panel de Control General!C18` | 8.0000 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM1` | `Visión P&G!H55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM2` | `Visión P&G!I55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM3` | `Visión P&G!J55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM4` | `Visión P&G!K55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM5` | `Visión P&G!L55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM6` | `Visión P&G!M55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |
| COSTO_C | `pyg.costo_c.contractM7` | `Visión P&G!N55` | 1,267,443,481.7244 | 0.0000 | 100.0000% |

## Stages limpios (todos PASS o drift <0.01%)

- **COSTO_B** — 7/7 PASS
- **NOMINA** — 0/5 PASS
- **RAMPUP** — 7/7 PASS

## Top 5 stages con mayor concentración de fallos

| Stage | FAIL+MISSING | Total | Pct |
|---|---:|---:|---:|
| COSTOS_FINANCIEROS | 28 | 28 | 100.0% |
| INGRESO | 14 | 14 | 100.0% |
| PYG | 14 | 14 | 100.0% |
| VISION_CTS | 9 | 9 | 100.0% |
| PAYROLL_A | 7 | 7 | 100.0% |

## Recomendación F3.B / F4 / F5 priority

La concentración de fallos por stage es la mejor señal:

1. **PAYROLL_A** (factor de indexación + composición SENA) → F3.B sub-wave
2. **COSTOS_FINANCIEROS** (GMF base + ICA base + comisión admin + pólizas) → F4
3. **COSTO_C / VISION_TARIFAS Cadena C** (HITL no modelado) → F5
4. **VISION_CTS** (depende de cadenas A+B+C correctos) — gated por 1-3

## Tabla completa de checkpoints

<details><summary>Click para expandir</summary>

| Stage | Checkpoint | Excel | Excel value | Backend value | Drift | Verdict |
|---|---|---|---:|---:|---:|---|
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM1` | `Visión P&G!H68` | 53,762,544.5427 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM2` | `Visión P&G!I68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM3` | `Visión P&G!J68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM4` | `Visión P&G!K68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM5` | `Visión P&G!L68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM6` | `Visión P&G!M68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.financiacion.contractM7` | `Visión P&G!N68` | 53,749,817.6443 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM1` | `Visión P&G!H67` | 10,318,771.7027 | 689,131.9155 | 93.3216% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM2` | `Visión P&G!I67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM3` | `Visión P&G!J67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM4` | `Visión P&G!K67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM5` | `Visión P&G!L67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM6` | `Visión P&G!M67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.gmf.contractM7` | `Visión P&G!N67` | 10,316,356.9339 | 689,131.9155 | 93.3200% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM1` | `Visión P&G!H66` | 32,239,879.6741 | 4,287,447.2968 | 86.7014% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM2` | `Visión P&G!I66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM3` | `Visión P&G!J66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM4` | `Visión P&G!K66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM5` | `Visión P&G!L66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM6` | `Visión P&G!M66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.ica.contractM7` | `Visión P&G!N66` | 32,232,247.7125 | 4,287,447.2968 | 86.6983% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM1` | `Visión P&G!H65` | 158,051,509.9629 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM2` | `Visión P&G!I65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM3` | `Visión P&G!J65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM4` | `Visión P&G!K65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM5` | `Visión P&G!L65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM6` | `Visión P&G!M65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTOS_FINANCIEROS | `pyg.polizas.contractM7` | `Visión P&G!N65` | 158,002,309.3046 | 0.0000 | 100.0000% | FAIL |
| COSTO_A | `pyg.costo_a.contractM1` | `Visión P&G!H31` | 173,162,876.5640 | 169,537,978.8648 | 2.0933% | FAIL |
| COSTO_A | `pyg.costo_a.contractM2` | `Visión P&G!I31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_A | `pyg.costo_a.contractM3` | `Visión P&G!J31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_A | `pyg.costo_a.contractM4` | `Visión P&G!K31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_A | `pyg.costo_a.contractM5` | `Visión P&G!L31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_A | `pyg.costo_a.contractM6` | `Visión P&G!M31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_A | `pyg.costo_a.contractM7` | `Visión P&G!N31` | 172,562,837.7843 | 169,537,978.8648 | 1.7529% | FAIL |
| COSTO_B | `pyg.costo_b.contractM1` | `Visión P&G!H45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM2` | `Visión P&G!I45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM3` | `Visión P&G!J45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM4` | `Visión P&G!K45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM5` | `Visión P&G!L45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM6` | `Visión P&G!M45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_B | `pyg.costo_b.contractM7` | `Visión P&G!N45` | 2,745,000.0000 | 2,745,000.0000 | 0.0000% | PASS |
| COSTO_C | `pyg.costo_c.contractM1` | `Visión P&G!H55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM2` | `Visión P&G!I55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM3` | `Visión P&G!J55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM4` | `Visión P&G!K55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM5` | `Visión P&G!L55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM6` | `Visión P&G!M55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_C | `pyg.costo_c.contractM7` | `Visión P&G!N55` | 1,267,443,481.7244 | 0.0000 | 100.0000% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM1` | `Visión P&G!H30` | 1,443,351,358.2884 | 172,282,978.8648 | 88.0637% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM2` | `Visión P&G!I30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM3` | `Visión P&G!J30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM4` | `Visión P&G!K30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM5` | `Visión P&G!L30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM6` | `Visión P&G!M30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| COSTO_TOTAL | `pyg.costo_total.contractM7` | `Visión P&G!N30` | 1,442,751,319.5086 | 172,282,978.8648 | 88.0587% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM1` | `Visión P&G!H18` | 1,626,677,365.8284 | 196,673,818.5983 | 87.9095% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM2` | `Visión P&G!I18` | 1,716,326,764.9754 | 207,600,141.8537 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM3` | `Visión P&G!J18` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM4` | `Visión P&G!K18` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM5` | `Visión P&G!L18` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM6` | `Visión P&G!M18` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_bruto.contractM7` | `Visión P&G!N18` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM1` | `Visión P&G!H27` | 1,626,677,365.8284 | 196,673,818.5983 | 87.9095% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM2` | `Visión P&G!I27` | 1,716,326,764.9754 | 207,600,141.8537 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM3` | `Visión P&G!J27` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM4` | `Visión P&G!K27` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM5` | `Visión P&G!L27` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM6` | `Visión P&G!M27` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| INGRESO | `pyg.ingreso_neto.contractM7` | `Visión P&G!N27` | 1,806,659,752.6057 | 218,526,465.1092 | 87.9044% | FAIL |
| KPI | `kpi.costo_mensual_promedio` | `Vision Cost To Serve!H19` | 30,500,882,693.6216 | 172,282,978.8648 | 99.4352% | FAIL |
| KPI | `kpi.facturacion_mensual_proyectada` | `Vision Tarifas_Modelo_Cobro!C72` | 38,608,712,270.4071 | 220,804,133.9223 | 99.4281% | FAIL |
| KPI | `kpi.ingreso_mensual` | `Vision Cost To Serve!B19` | 38,608,712,270.4071 | 220,804,133.9223 | 99.4281% | FAIL |
| NOMINA | `nomina.W39_costo_empresa_inbound25_perfil` | `Inputs de Nomina!W39` | 2,900,432.6183 | - | - | BACKEND_MISSING |
| NOMINA | `nomina.W40` | `Inputs de Nomina!W40` | 2,900,432.6183 | - | - | BACKEND_MISSING |
| NOMINA | `nomina.W41` | `Inputs de Nomina!W41` | - | - | - | NO_ORACLE |
| NOMINA | `nomina.W42` | `Inputs de Nomina!W42` | - | - | - | NO_ORACLE |
| NOMINA | `nomina.W43` | `Inputs de Nomina!W43` | - | - | - | NO_ORACLE |
| NOMINA_LOADED | `nomina_loaded.nomina_total_m6_calendar` | `Nomina Loaded!I89` | - | 157,807,073.2235 | - | NO_ORACLE |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_total_m1` | `Nomina Loaded!I100` | 131,549,939.6465 | 152,374,196.3813 | 15.8299% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM1` | `Nomina Loaded!I93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM10` | `Nomina Loaded!R93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM11` | `Nomina Loaded!S93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM12` | `Nomina Loaded!T93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM2` | `Nomina Loaded!J93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM3` | `Nomina Loaded!K93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM4` | `Nomina Loaded!L93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM5` | `Nomina Loaded!M93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM6` | `Nomina Loaded!N93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM7` | `Nomina Loaded!O93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM8` | `Nomina Loaded!P93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_contractM9` | `Nomina Loaded!Q93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_voz_m1` | `Nomina Loaded!I93` | 82,218,712.2791 | 95,638,112.5915 | 16.3216% | FAIL |
| NOMINA_LOADED | `nomina_loaded.salario_fijo_whatsapp_m1` | `Nomina Loaded!I97` | 49,331,227.3674 | 56,736,083.7898 | 15.0105% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM1` | `Visión P&G!H41` | 34,555,560.2097 | 11,017,864.6600 | 68.1155% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM2` | `Visión P&G!I41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM3` | `Visión P&G!J41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM4` | `Visión P&G!K41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM5` | `Visión P&G!L41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM6` | `Visión P&G!M41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| NO_PAYROLL_A | `pyg.no_payroll_a.contractM7` | `Visión P&G!N41` | 33,955,521.4299 | 11,017,864.6600 | 67.5521% | FAIL |
| PANEL | `panel.com_cont` | `Panel de Control General!C67` | - | 0.0000 | - | NO_ORACLE |
| PANEL | `panel.crucero` | `Panel de Control General!C17` | 8,408.0000 | - | - | BACKEND_MISSING |
| PANEL | `panel.descuento` | `Panel de Control General!C65` | - | 0.0000 | - | NO_ORACLE |
| PANEL | `panel.horas_formacion_mensual` | `Panel de Control General!C18` | 8.0000 | 0.0000 | 100.0000% | FAIL |
| PANEL | `panel.imprevistos` | `Panel de Control General!C68` | - | 0.0000 | - | NO_ORACLE |
| PANEL | `panel.margen_a` | `Panel de Control General!C63` | 0.2100 | 0.2100 | 0.0000% | PASS |
| PANEL | `panel.margen_b` | `Panel de Control General!D63` | 0.3000 | 0.3000 | 0.0000% | PASS |
| PANEL | `panel.markup` | `Panel de Control General!C64` | - | 0.0000 | - | NO_ORACLE |
| PANEL | `panel.meses_contrato` | `Panel de Control General!C11` | 12.0000 | 12.0000 | 0.0000% | PASS |
| PANEL | `panel.op_cont` | `Panel de Control General!C66` | - | 0.0000 | - | NO_ORACLE |
| PANEL | `panel.pct_ausentismo` | `Panel de Control General!C19` | 0.0650 | 0.0650 | 0.0000% | PASS |
| PANEL | `panel.periodo_pago` | `Panel de Control General!C9` | 30.0000 | 30.0000 | 0.0000% | PASS |
| PANEL | `panel.tarifa_capacitacion_diaria` | `Panel de Control General!C16` | 20,000.0000 | 0.0000 | 100.0000% | FAIL |
| PANEL | `panel.tasa_gmf` | `Panel de Control General!C35` | 0.0040 | 0.0040 | 0.0000% | PASS |
| PANEL | `panel.tasa_ica` | `Panel de Control General!C34` | 0.0100 | 0.0197 | 96.6000% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM1` | `Visión P&G!H32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM2` | `Visión P&G!I32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM3` | `Visión P&G!J32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM4` | `Visión P&G!K32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM5` | `Visión P&G!L32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM6` | `Visión P&G!M32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PAYROLL_A | `pyg.payroll_a.contractM7` | `Visión P&G!N32` | 138,607,316.3544 | 158,520,114.2049 | 14.3663% | FAIL |
| PYG | `pyg.contribucion.contractM1` | `Visión P&G!H74` | 183,326,007.5400 | 24,390,839.7334 | 86.6954% | FAIL |
| PYG | `pyg.contribucion.contractM2` | `Visión P&G!I74` | 273,575,445.4668 | 35,317,162.9889 | 87.0905% | FAIL |
| PYG | `pyg.contribucion.contractM3` | `Visión P&G!J74` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.contribucion.contractM4` | `Visión P&G!K74` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.contribucion.contractM5` | `Visión P&G!L74` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.contribucion.contractM6` | `Visión P&G!M74` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.contribucion.contractM7` | `Visión P&G!N74` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.utilidad_neta.contractM1` | `Visión P&G!H79` | 183,326,007.5400 | 24,390,839.7334 | 86.6954% | FAIL |
| PYG | `pyg.utilidad_neta.contractM2` | `Visión P&G!I79` | 273,575,445.4668 | 35,317,162.9889 | 87.0905% | FAIL |
| PYG | `pyg.utilidad_neta.contractM3` | `Visión P&G!J79` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.utilidad_neta.contractM4` | `Visión P&G!K79` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.utilidad_neta.contractM5` | `Visión P&G!L79` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.utilidad_neta.contractM6` | `Visión P&G!M79` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| PYG | `pyg.utilidad_neta.contractM7` | `Visión P&G!N79` | 363,908,433.0971 | 46,243,486.2444 | 87.2925% | FAIL |
| RAMPUP | `pyg.rampup.contractM1` | `Visión P&G!H15` | 0.9000 | 0.9000 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM2` | `Visión P&G!I15` | 0.9500 | 0.9500 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM3` | `Visión P&G!J15` | 1.0000 | 1.0000 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM4` | `Visión P&G!K15` | 1.0000 | 1.0000 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM5` | `Visión P&G!L15` | 1.0000 | 1.0000 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM6` | `Visión P&G!M15` | 1.0000 | 1.0000 | 0.0000% | PASS |
| RAMPUP | `pyg.rampup.contractM7` | `Visión P&G!N15` | 1.0000 | 1.0000 | 0.0000% | PASS |
| VISION_CTS | `cts.cadena_a` | `Vision Cost To Serve!C34` | 5,732.2462 | 0.0000 | 100.0000% | FAIL |
| VISION_CTS | `cts.cadena_b` | `Vision Cost To Serve!G34` | 171.5625 | 183.0000 | 6.6667% | FAIL |
| VISION_CTS | `cts.cadena_c` | `Vision Cost To Serve!K34` | 238,835.1900 | 0.0000 | 100.0000% | FAIL |
| VISION_CTS | `cts.costo_total_acumulado` | `Vision Cost To Serve!H19` | 30,500,882,693.6216 | 2,067,395,746.3782 | 93.2218% | FAIL |
| VISION_CTS | `cts.ingreso_mensual_acumulado` | `Vision Cost To Serve!B19` | 38,608,712,270.4071 | 218,079,720.0821 | 99.4352% | FAIL |
| VISION_CTS | `cts.participacion_a` | `Vision Cost To Serve!C31` | 0.5366 | 0.0000 | 100.0000% | FAIL |
| VISION_CTS | `cts.participacion_b` | `Vision Cost To Serve!G31` | 0.2851 | 0.9999 | 250.6804% | FAIL |
| VISION_CTS | `cts.participacion_c` | `Vision Cost To Serve!K31` | 0.1782 | 0.0001 | 99.9626% | FAIL |
| VISION_CTS | `cts.ponderado` | `Vision Cost To Serve!G49` | 45,688.6638 | 182.9878 | 99.5995% | FAIL |
| VISION_TARIFAS | `vt.costo_cadena_a_total` | `Vision Tarifas_Modelo_Cobro!C40` | 1,365,353,738.0299 | 169,537,978.8648 | 87.5829% | FAIL |
| VISION_TARIFAS | `vt.costo_cadena_b_total` | `Vision Tarifas_Modelo_Cobro!C50` | - | 2,745,000.0000 | - | NO_ORACLE |
| VISION_TARIFAS | `vt.costo_cadena_c_total` | `Vision Tarifas_Modelo_Cobro!C60` | 29,135,528,955.5917 | 0.0000 | 100.0000% | FAIL |
| VISION_TARIFAS | `vt.costo_total` | `Vision Tarifas_Modelo_Cobro!C65` | - | 172,282,978.8648 | - | NO_ORACLE |
| VISION_TARIFAS | `vt.ingreso_cadena_a` | `Vision Tarifas_Modelo_Cobro!C47` | 1,728,295,870.9239 | - | - | BACKEND_MISSING |
| VISION_TARIFAS | `vt.ingreso_cadena_b` | `Vision Tarifas_Modelo_Cobro!C57` | - | - | - | NO_ORACLE |
| VISION_TARIFAS | `vt.ingreso_cadena_c` | `Vision Tarifas_Modelo_Cobro!C67` | 36,880,416,399.4831 | - | - | BACKEND_MISSING |
| VISION_TARIFAS | `vt.ingreso_mensual` | `Vision Tarifas_Modelo_Cobro!C72` | 38,608,712,270.4071 | 218,079,720.0821 | 99.4352% | FAIL |

</details>
