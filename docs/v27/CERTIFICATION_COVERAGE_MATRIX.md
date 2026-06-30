# Workbook Economic Coverage Matrix — V2-7

| Escenario | Estado | Evidencia | Tests |
|-----------|--------|-----------|-------|
| **Captura de Datos** | CERTIFIED | 208 oracle checkpoints @ REL_TOL=1e-6 | test_oracle_mesh.py (169 pass) + test_excel_oracle_v2_7_real.py (39 pass) |
| **SACO** | CERTIFIED | rampup=[1.0,1.0,...] from Rot!B41; special billing = DISPLAY_ONLY (VT!C77→0 consumers) | test_w18_f5e_closure.py::TestSacoBillingDerivation |
| **Cobranzas** | CERTIFIED | rampup=[0.85,0.92,1.0] from Rot!B38; Panel!C182→VT!C77→0 consumers = DISPLAY_ONLY | test_w18_f5d_coverage.py + audit W18.F5.F |
| **Sac** | CERTIFIED | rampup=[0.90,0.95,1.0] from Rot!B39 | test_w18_f5d_coverage.py |
| **Ventas multicanal** | CERTIFIED | rampup=[0.80,0.87,0.95] from Rot!B40; Panel!C120 gate ✓ | test_w18_f5e_closure.py::test_service_behavior_all_gates |
| **Plataformas** | CERTIFIED | rampup=[1.0,1.0,1.0] from Rot!B42 | test_w18_f5d_coverage.py |
| **Inbound** | CERTIFIED | V2-7 canonical fixture — Voz + WhatsApp Inbound | Oracle mesh 208 checkpoints |
| **Outbound** | CERTIFIED | PyG!C19 formula identical for Outbound; same code path verified | test_w18_f5e_closure.py::TestOutboundCertification |
| **FTE (70% + 30% Transacción)** | CERTIFIED | Panel!D84=0.7; VT!C15=0.7; oracle mesh ✓ | test_w18_f5e_closure.py::TestBillingModelCertification |
| **FTE 100%** | CERTIFIED | Panel!D98=1.0; VT!E15=1.0; tarifa_variable=0 ✓ | test_w18_f5e_closure.py |
| **Tiempo** | CERTIFIED | VT!G47=G43/E124; E124=272790 min for FTE=40; tarifa_hora_pagada derivable | test_w18_f5e_closure.py::test_tiempo_tarifa_hora_pagada_computable |
| **Transacción** | CERTIFIED | pct_variable=1.0; internal consistency verified; VT!D21 semantic gap documented | test_w18_f5e_closure.py::test_variable_tarifa_internal_consistency |
| **Resultados** | DISPLAY_ONLY | VT!C21=HMS!G33; P&G does NOT reference Vision Tarifas (0 references, scan confirmed) | W18.F5.F audit |
| **Honorarios** | DISPLAY_ONLY | Same as Resultados; VT!C130 gate only | W18.F5.F audit |
| **ICA** | CERTIFIED | Panel!C34=0.01; PyG fila 66; oracle mesh checkpoints ✓ | oracle_mesh.py |
| **GMF** | CERTIFIED | Panel!C35=0.004; PyG fila 67; oracle mesh checkpoints ✓ | oracle_mesh.py |
| **Pólizas (Salarios+Calidad)** | CERTIFIED | Panel!C40=True, C41=True; oracle mesh + gap_closure ✓ | oracle_mesh.py + test_vision_gap_closure.py |
| **Financiación inactiva** | CERTIFIED | Panel!C21='No'; P&G H70-N70=0; oracle mesh ✓ | oracle_mesh.py |
| **Financiación activa** | CERTIFIED | formula: factor_periodo×tasa_mensual×costo_mes_anterior; mes1=0, mes2>0 ✓ | test_w18_f5e_closure.py::test_financiacion_active |
| **Comisión de Administración** | CERTIFIED | Panel!C45=True; PyG fila 68; oracle mesh ✓ | oracle_mesh.py |
| **Crucero** | CERTIFIED | ResultadoNomina.crucero; workbook CTS fila 107=8,408 ✓ | test_vision_gap_closure.py::TestGapCtsHier1 |
| **Cadena A (costs, income, CTS)** | CERTIFIED | 50+ oracle checkpoints ✓ | oracle_mesh.py |
| **Cadena B (costs, income)** | CERTIFIED | VT!C50=0 (Voz no B); VT!C60+costo_cadena_b_total ✓ | oracle_mesh.py |
| **Cadena C (costs, income)** | CERTIFIED | VT!C60, C67; oracle mesh ✓ | oracle_mesh.py |
| **KPIs (ingreso, costo, facturación)** | CERTIFIED | VT!C72=38.6B; oracle mesh kpi.* ✓ | oracle_mesh.py |
| **Vision P&G (estructura)** | CERTIFIED | 29 filas; labels alineados con Excel filas 18-80; oracle mesh ✓ | test_vision_pyg_contract.py + oracle_mesh.py |
| **Vision CTS (desglose A/B)** | CERTIFIED | CTS!C34/G34/K34/G49; desglose_a sub-components ✓ | oracle_mesh.py + test_vision_gap_closure.py |
| **Vision Tarifas (core)** | CERTIFIED | C40, C47, C60, C67, C72; escenario 1+3 ✓ | oracle_mesh.py |
| **Service-driven gates (6×5)** | CERTIFIED | 30 combinaciones: Panel!C120/C152/C184, CTS!C58/C87, VT!C77 | test_servicio_driven_behavior.py + test_w18_f5e_closure.py |
| **Contribución por Puesto** | CERTIFIED | estaciones=24 == workbook P&G!C14 ✓ | test_vision_gap_closure.py::TestGapPygHier4 |
| **Sub-componentes Payroll A** | CERTIFIED | 7 filas detalle: salario_fijo, salario_variable, cap_inicial, etc. ✓ | test_vision_gap_closure.py::TestGapPygHier1 |
| **Sub-componentes No Payroll A** | CERTIFIED | 3 filas detalle: opex_fijo, inversiones, costos_fijos ✓ | test_vision_gap_closure.py |
