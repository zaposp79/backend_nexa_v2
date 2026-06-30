# FASE A — Auditoría Contractual: Matriz JSON → Formula → Vision

**Fecha:** 2026-05-25  
**Rama:** `refactor/engine-v2`  
**Objetivo:** Trazar cada campo del contrato `entry_data` a través de toda la cadena:  
`JSON Field → UserInputLoader → UserInput → ContextBuilder → PricingRequest → Calculator → Formula → Vision`

**Leyenda de estado:**
- ✅ `MAPEADO` — campo llega sin pérdida al calculador que lo consume
- ⚠️ `PARCIAL` — campo llega, pero con transformación que puede causar pérdida o default silencioso
- ❌ `IGNORADO` — campo presente en JSON, nunca llega a ningún calculador
- 🔴 `CRÍTICO` — gap que produce resultados incorrectos (costo = 0 o valor erróneo)

---

## 1. `datos_operativos`

| Campo JSON | Normalizador | UserInput | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `cliente` | `panel_de_control.cliente` | `PanelDeControlInput.cliente` | `_construir_panel()` | `PanelDeControl.cliente` | PyGCalculator (label) | display only | Imprimible | ✅ |
| `tipo_cliente` | `panel_de_control.tipo_cliente` | `PanelDeControlInput.tipo_cliente` | `_construir_panel()` | `PanelDeControl.tipo_cliente` | — | display only | Imprimible | ✅ |
| `servicio` | `panel_de_control.linea_negocio` | `PanelDeControlInput.linea_negocio` | `_construir_panel()` | `PanelDeControl.linea_negocio` | PyGCalculator (ramp-up lookup), ParametrosCalculo | ramp-up(mes, linea) | PyG | ✅ |
| `ciudad` | `panel_de_control.ciudad` | `PanelDeControlInput.ciudad` | `_construir_panel()` → `get_ica()` / `_construir_parametros_nomina()` → `get_examen_medico()` | `PanelDeControl.tasa_ica`, `ParametrosNomina.costo_examen_medico` | CostosFinancierosCalculator, NominaCalculator | `ica = costo_total × tasa_ica`, `examenes = fte_examenes × costo_examen` | PyG, CTS | ✅ |
| `sede` | `panel_de_control.sede` | `PanelDeControlInput.sede` | `_construir_no_payroll()` → `get_costo_no_payroll(sede)` | `ParametrosNoPayroll.*_por_estacion` | NoPayrollCalculator | `costos_fijos = fte × pct_presencia × (arriendo + energia + ...)` | PyG, CTS, Tarifas | ✅ |
| `fecha_inicio` | `panel_de_control.fecha_inicio` | `PanelDeControlInput.fecha_inicio` | `_anio_inicio()` → `get_factor_indexacion()` | `ParametrosNomina.pct_aumento_salarial`, `Indexacion.mes_aplicacion` | NominaCalculator, CadenaBCalculator | `salario_mes = salario_base × factor(mes)` | PyG, CTS, Tarifas | ✅ |
| `duracion_meses` | `panel_de_control.meses_contrato` | `PanelDeControlInput.meses_contrato` | `_construir_panel()`, `_construir_parametros_nomina()` | `PanelDeControl.meses_contrato`, `ParametrosNomina.mes_fin` | NominaCalculator, PyGCalculator | `cap_inicial = dias_cap × tarifa / meses_contrato` | PyG, CTS, Tarifas | ✅ |
| `tasa_ica` | `panel_de_control.tasa_ica` | `PanelDeControlInput.tasa_ica` | `_construir_panel()` (override) | `PanelDeControl.tasa_ica` | CostosFinancierosCalculator | `ica_mes = costo_total_mes × tasa_ica` | PyG | ✅ |
| `tasa_gmf` | `panel_de_control.tasa_gmf` | `PanelDeControlInput.tasa_gmf` | `_construir_panel()` (override) | `PanelDeControl.tasa_gmf` | CostosFinancierosCalculator | `gmf_mes = costo_total_mes × tasa_gmf` | PyG | ✅ |
| `cons_costo_de_financiacion` | `panel_de_control.activa_financiacion` | `PanelDeControlInput.activa_financiacion` | `_construir_panel()` | `PanelDeControl.activa_financiacion` | CostosFinancierosCalculator | `financ = if activa: costo × tasa_financ × dias/360` | PyG | ✅ |
| `pct_rotacion` | `panel_de_control.pct_rotacion` | `PanelDeControlInput.pct_rotacion` | `_construir_perfiles_a()`, `_construir_parametros_calculo()` | `ParametrosCalculo.pct_rotacion` | NominaCalculator | `cap_rot = dias_cap_rot × tarifa × fte × pct_rot` | PyG, CTS | ✅ |
| `pct_ausentismo` | `panel_de_control.pct_ausentismo` | `PanelDeControlInput.pct_ausentismo` | `_construir_panel()` | `PanelDeControl.pct_ausentismo` | **NINGUNO** — campo llega a PanelDeControl pero ningún calculator lo lee | — | — | ❌ **IGNORADO** |
| `cufin` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `horas_formacion_mes` | ❌ no mapeado | — | — | — | `PanelDeControl.horas_formacion_mensual` hardcoded `= 0` en context_builder | — | — | ❌ **IGNORADO** |
| `tarifa_diaria_capacitacion` | ❌ no mapeado | — | — | — | `ParametrosNomina.tarifa_dia_cap` = `get_costo_operativo("tarifa_dia_cap")` (parametrización) | `cap = dias × tarifa_dia_cap × fte` | PyG, CTS | ❌ **IGNORADO** (usa parametrización, ignora user override) |
| `sede_combinada_costo_formacion` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `ciudades_recurso[]` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |

---

## 2. `polizas[]`

| Campo JSON | Normalizador | UserInput | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `polizas[]` (array completo) | ❌ `_normalizar_entry_data_format()` **nunca consume `polizas`** | — | — | — | CostosFinancierosCalculator usa `self._prov.get_polizas()` (storage únicamente) | `polizas_mes = Σ(pct_poliza × pct_atribuible × ingreso)` | PyG | 🔴 **CRÍTICO** — configuración del usuario 100% ignorada |
| `nombre` | ❌ | — | — | — | — | — | — | ❌ |
| `activa` | ❌ | — | — | — | — | — | — | ❌ |
| `pct_poliza` | ❌ | — | — | — | — | — | — | ❌ |
| `pct_atribuible` | ❌ | — | — | — | — | — | — | ❌ |
| `aplica_extension` | ❌ | — | — | — | — | — | — | ❌ |
| `meses_extension` | ❌ | — | — | — | — | — | — | ❌ |

**Impacto:** El costo de pólizas se calcula siempre desde `storage/parametrization/op/`, ignorando cuáles pólizas activó el usuario y sus porcentajes atribuibles. Si el cliente tiene pólizas personalizadas, el costo será incorrecto.

---

## 3. `reglas_negocio`

| Campo JSON | Normalizador | UserInput | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `margen_objetivo` | `panel_de_control.margen` | `PanelDeControlInput.margen` | `_construir_panel()` | `PanelDeControl.margen` | PyGCalculator | `ingreso = costo / (1 - margen - op_cont - com_cont - markup)` | PyG, Tarifas | ✅ |
| `contingencia_operativa.valor` | `panel_de_control.op_cont` | `PanelDeControlInput.op_cont` | `_construir_panel()` | `PanelDeControl.op_cont` | PyGCalculator | `cont_op = ingreso_bruto × op_cont` | PyG | ✅ |
| `contingencia_operativa.minimo` | ❌ no mapeado | — | — | — | — | — | Imprimible (display) | ❌ **IGNORADO** (usado solo para display en reglas_negocio output) |
| `contingencia_operativa.maximo` | ❌ no mapeado | — | — | — | — | — | Imprimible (display) | ❌ **IGNORADO** |
| `contingencia_comercial.valor` | ⚠️ `com_cont` hardcoded `= 0.0` en normalizer | `PanelDeControlInput.com_cont = 0.0` | — | `PanelDeControl.com_cont = 0.0` | PyGCalculator | `cont_com = ingreso_bruto × com_cont` | PyG | 🔴 **CRÍTICO** — com_cont siempre 0, ignora valor del JSON |
| `contingencia_comercial.minimo` | ❌ | — | — | — | — | — | — | ❌ |
| `contingencia_comercial.maximo` | ❌ | — | — | — | — | — | — | ❌ |
| `markup.valor` | `panel_de_control.markup` | `PanelDeControlInput.markup` | `_construir_panel()` | `PanelDeControl.markup` | PyGCalculator | `markup_ing = ingreso_bruto × markup` | PyG | ✅ |
| `markup.minimo` | ❌ | — | — | — | — | — | — | ❌ |
| `markup.maximo` | ❌ | — | — | — | — | — | — | ❌ |
| `imprevistos` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `porcentaje_acumulado.actual` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `porcentaje_acumulado.minimo` | ❌ | — | — | — | — | — | — | ❌ |
| `porcentaje_acumulado.maximo` | ❌ | — | — | — | — | — | — | ❌ |

---

## 4. `volumetria`

| Campo JSON | Normalizador | UserInput | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `indexacion.componente_humano` | ⚠️ no mapeado en normalizer | `componente_indexacion_humano` default `"IPC"` en `_panel()` | `_construir_parametros_nomina()` → `get_factor_indexacion("IPC", ...)` | `ParametrosNomina.pct_aumento_salarial` | NominaCalculator | `salario(mes) = base × (1 + pct_aum) si mes >= mes_ajuste` | PyG | ⚠️ **PARCIAL** — siempre usa "IPC", ignora selección del usuario |
| `indexacion.componente_tecnologico` | ⚠️ no mapeado | `componente_indexacion_tecnologico` default `"IPC"` | `_construir_cadena_b()` → `get_factor_indexacion()` | `ParametrosCadenaB.pct_aumento_personal` | CadenaBCalculator | `costo_sm(mes) = base × (1 + pct_aum)^n` | PyG | ⚠️ **PARCIAL** |
| `indexacion.frecuencia` | ❌ no mapeado | — | Hardcoded `"Anual"` en Indexacion | `PanelDeControl.indexacion.frecuencia` | NominaCalculator | — | — | ❌ **IGNORADO** |
| `indexacion.mes_aplicacion` | ❌ no mapeado | — | `get_costo_operativo("mes_inicio_ajuste_anual")` | `ParametrosNomina.mes_aplicacion_aumento` | NominaCalculator | `if mes >= mes_ajuste: aplica factor` | PyG | ❌ **IGNORADO** (parametrización, no usuario) |
| `indexacion.tasa_interes_mensual` | `panel_de_control.tasa_mensual_financ` | `PanelDeControlInput.tasa_mensual_financ` | `_construir_panel()` (override) | `PanelDeControl.tasa_mensual_financ` | CostosFinancierosCalculator | `financ = costo × tasa_mensual × (dias_pago/30)` | PyG | ✅ |
| `inbound.cadenas_activas.*` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `inbound.canales[].cadena_a.valor` | ⚠️ solo en fallback (cuando `condiciones_cadena_a` no está explícita) → `fte` en perfil auto-generado | `PerfilCadenaAInput.fte` | `_construir_perfil_a()` | `PerfilCadenaA.fte` | NominaCalculator | `salario_fijo = salario_cargado × fte × factor(mes)` | PyG, CTS | ⚠️ **PARCIAL** (solo fallback) |
| `inbound.canales[].cadena_b.valor` | ⚠️ solo en fallback → `volumen_mensual` en CanalCadenaBInput auto-generado | `CanalCadenaBInput.volumen_mensual` | `_construir_cadena_b()` | `CanalCadenaB.volumen_mensual` | CadenaBCalculator | `costo_var = vol × tarifa` | PyG, CTS | ⚠️ **PARCIAL** (solo fallback) |
| `inbound.canales[].cadena_c.valor` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `inbound.canales[].cadena_a.participacion` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `outbound.cadenas_activas.*` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `outbound.canales[].cadena_a.valor` | ⚠️ solo en fallback → `fte` outbound | `PerfilCadenaAInput.fte` | `_construir_perfil_a()` | `PerfilCadenaA.fte` | NominaCalculator | — | PyG | ⚠️ **PARCIAL** |
| `outbound.canales[].cadena_b.valor` | ❌ no mapeado en normalizer | — | — | — | — | — | — | ❌ **IGNORADO** |
| `outbound.canales[].cadena_c.valor` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |

---

## 5. `escenarios_comerciales[]`

| Campo JSON | Normalizador | UserInput | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `escenarios_comerciales[]` (array completo) | ❌ **NUNCA consumido** en `_normalizar_entry_data_format()` | — | — | — | VisionTarifasCalculator usa `modelo_cobro` y `pct_fijo` de `PerfilCadenaAInput` — que tienen default `"Fijo FTE"` / `1.0` | `facturacion = ingreso × pct_fijo` | Tarifas | 🔴 **CRÍTICO** |
| `escenario` | ❌ | — | — | — | — | — | — | ❌ |
| `modalidad` | ❌ | — | — | — | — | — | — | ❌ |
| `canal` | ❌ | — | — | — | — | — | — | ❌ |
| `modelo_cobro` | ❌ | — | — | — | `PerfilCadenaAInput.modelo_cobro` = `"Fijo FTE"` (default) | — | Tarifas | 🔴 |
| `componente_fijo` | ❌ | — | — | — | — | — | — | ❌ |
| `proporcion_componente_fijo` | ❌ | — | — | — | `PerfilCadenaAInput.pct_fijo` = `1.0` (default) | — | Tarifas | 🔴 |
| `componente_variable` | ❌ | — | — | — | — | — | — | ❌ |
| `proporcion_componente_variable` | ❌ | — | — | — | — | — | — | ❌ |

**Impacto:** La Vision Tarifas siempre calcula como modelo `"Fijo FTE"` con `pct_fijo=1.0`, ignorando completamente si el deal es Híbrido o Variable. Las tarifas resultantes son incorrectas para cualquier deal no-FTE.

---

## 6. `condiciones_cadena_a`

| Campo JSON | Normalizador | UserInput (`_perfil_a`) | ContextBuilder | PricingRequest | Calculator | Fórmula | Vision | Estado |
|---|---|---|---|---|---|---|---|---|
| `Calculo_conversion_fte_interacciones.tmo_promedio_seg` | ❌ no mapeado | `tmo_segundos = 0.0` (default) | — | `PerfilCadenaA.tmo_segundos` | NominaCalculator (no usa) | informativo | — | ❌ **IGNORADO** |
| `perfiles[].nombre` | directo | `PerfilCadenaAInput.nombre` | `_construir_perfil_a()` | `PerfilCadenaA.nombre` | display | display | Tarifas, Imprimible | ✅ |
| `perfiles[].modalidad` | directo | `PerfilCadenaAInput.modalidad` | `_construir_perfil_a()` | `PerfilCadenaA.modalidad` | CostToServeCalculator, VisionTarifas | segmentación | CTS, Tarifas | ✅ |
| `perfiles[].canal` | directo | `PerfilCadenaAInput.canal` | `_construir_perfil_a()` | `PerfilCadenaA.canal` | VisionTarifasCalculator | agrupación por canal | Tarifas | ✅ |
| `perfiles[].fte` | directo | `PerfilCadenaAInput.fte` | `_construir_perfil_a()` | `PerfilCadenaA.fte` | NominaCalculator, NoPayrollCalculator | `nomina = salario_cargado × fte × factor(mes)` | PyG, CTS, Tarifas | ✅ |
| `perfiles[].pct_presencia` | directo | `PerfilCadenaAInput.pct_presencia` | `_construir_perfil_a()` | `PerfilCadenaA.pct_presencia` | NoPayrollCalculator | `estaciones = fte × pct_presencia` | CTS | ✅ |
| `perfiles[].salario_base` | directo (override) | `PerfilCadenaAInput.salario_base` | `_construir_perfil_a()` → override o `get_salario_rol()` | `PerfilCadenaA.salario_base` | NominaCalculator | `salario_cargado = nomina_cargada(salario_base)` | PyG, CTS | ✅ |
| `perfiles[].comision_pct` | directo | `PerfilCadenaAInput.comision_pct` | `_construir_perfil_a()` | `PerfilCadenaA.comision_pct` | NominaCalculator | `comisiones = salario_base × comision_pct × fte × pct_cumplimiento` | PyG, CTS | ✅ |
| `perfiles[].estaciones_presenciales` | ❌ no mapeado | — | — | — | NoPayrollCalculator usa `fte × pct_presencia` | — | CTS | ❌ **IGNORADO** |
| `perfiles[].roles_operativos[]` | ❌ no mapeado | — | — | — | ContextBuilder usa `get_ratios_staff(linea)` (parametrización) | — | — | ❌ **IGNORADO** (overrides por perfil imposibles) |
| `perfiles[].capacitacion.dias_cap_inicial` | `dias_cap_inicial` | `PerfilCadenaAInput.dias_cap_inicial` | `_construir_perfil_a()` | `PerfilCadenaA.dias_cap_inicial` | NominaCalculator | `cap_inicial = dias_cap_inicial × tarifa_dia × fte / meses` | PyG, CTS | ✅ |
| `perfiles[].capacitacion.dias_cap_rotacion` | `dias_cap_rotacion` | `PerfilCadenaAInput.dias_cap_rotacion` | `_construir_perfil_a()` | `PerfilCadenaA.dias_cap_rotacion` | NominaCalculator | `cap_rot = dias_cap_rot × tarifa_dia × fte × pct_rot` | PyG, CTS | ✅ |
| `perfiles[].capacitacion.tarifa_dia_cap` | ❌ no mapeado | — | — | `ParametrosNomina.tarifa_dia_cap` desde parametrización | NominaCalculator | `cap = dias × tarifa_dia_cap` | PyG, CTS | ❌ **IGNORADO** |
| `perfiles[].capacitacion.tarifa_diaria_capacitacion_sede_combinada` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `perfiles[].opex_fijo.opex_ti_por_estacion` | ❌ no mapeado | — | — | `ParametrosNoPayroll.opex_ti_por_estacion` desde parametrización | NoPayrollCalculator | `opex_ti = fte × pct_presencia × opex_ti` | CTS | ❌ **IGNORADO** |
| `perfiles[].opex_fijo.capex_por_estacion` | ❌ no mapeado | — | — | `ParametrosNoPayroll.capex_por_estacion` desde parametrización | NoPayrollCalculator | — | CTS | ❌ **IGNORADO** |
| `perfiles[].inversiones[]` | ❌ no mapeado | — | — | — | — | — | — | ❌ **IGNORADO** |
| `perfiles[].incluye_examenes` | directo | `PerfilCadenaAInput.incluye_examenes` | `_construir_perfil_a()` | `PerfilCadenaA.incluye_examenes` | NominaCalculator | `if incluye_examenes: examenes += fte_examenes × costo_examen` | PyG, CTS | ✅ |
| `perfiles[].incluye_seguridad` | directo | `PerfilCadenaAInput.incluye_seguridad` | `_construir_perfil_a()` | `PerfilCadenaA.incluye_seguridad` | NominaCalculator | — | PyG, CTS | ✅ |
| `perfiles[].incluye_crucero` | directo | `PerfilCadenaAInput.incluye_crucero` | `_construir_perfil_a()` | `PerfilCadenaA.incluye_crucero` | NominaCalculator | `crucero = fte × costo_crucero (mes 1 only)` | PyG, CTS | ✅ |

---

## 7. `condiciones_cadena_b`

> **⚠️ MISMATCH ESTRUCTURAL CRÍTICO**  
> La estructura del entry_data para cadena_b es completamente diferente a la que espera `_cadena_b()`.  
> `_cadena_b()` busca: `canales[]`, `opex_consumo_variable[]`, `equipo_sm[]`, `dispositivos_sm[]`  
> entry_data provee: `opex.items[]`, `inversiones_capex[]`, `equipo_soporte_mantenimiento{fte, roles[], dispositivos_requeridos[]}`, `costo_variable{tarifas_por_canal{}, tasa_escalamiento{}}`, `hitl{total_volumen_cadena_b, equipo[], dispositivos_requeridos[]}`

| Campo JSON (entry_data) | Campo esperado por `_cadena_b()` | Mapeado? | Impacto |
|---|---|---|---|
| `opex.items[].rubro` | — | ❌ | — |
| `opex.items[].modalidad` | `opex_consumo_variable[].modalidad` | ❌ campo no reconocido | 🔴 todo OPEX = 0 |
| `opex.items[].canal` | `opex_consumo_variable[].canal` | ❌ | — |
| `opex.items[].producto` | `opex_consumo_variable[].producto` | ❌ | — |
| `opex.items[].valor` | `opex_consumo_variable[].valor_unitario` | ❌ nombre distinto | — |
| `opex.items[].cantidad` | `opex_consumo_variable[].cantidad` | ❌ | — |
| `opex.items[].tipo_de_cobro` | `opex_consumo_variable[].tipo_cobro` | ❌ nombre distinto | — |
| `inversiones_capex[].valor` | `inversion_plataforma` (scalar) | ❌ lista vs escalar | 🔴 inversión = 0 |
| `inversiones_capex[].meses_a_diferir_inversion` | `dispositivos_sm[].meses_amortizacion` | ❌ modelo distinto | — |
| `equipo_soporte_mantenimiento.fte` | `fte_equipo_sm` | ❌ anidado | 🔴 fte_sm = 1.0 (default) |
| `equipo_soporte_mantenimiento.roles[].rol` | `equipo_sm[].rol` | ❌ campo distinto (`roles` vs `equipo_sm`) | — |
| `equipo_soporte_mantenimiento.roles[].activado` | `equipo_sm[].activo` | ❌ nombre distinto | — |
| `equipo_soporte_mantenimiento.roles[].dedicacion` | `equipo_sm[].pct_dedicacion` | ❌ semántica distinta (% vs fracción) | — |
| `equipo_soporte_mantenimiento.dispositivos_requeridos[]` | `dispositivos_sm[]` | ❌ campo distinto | 🔴 opex_dispositivos = 0 |
| `costo_variable.tarifas_por_canal.inbound[].tarifa` | `canales[].tarifa_unitaria` | ❌ estructura completamente diferente | 🔴 tarifa_unitaria = 0 |
| `costo_variable.tasa_escalamiento.inbound[].tasa` | `canales[].pct_escalamiento` | ❌ estructura diferente | 🔴 escalamiento = 0 |
| `costo_variable.tasa_escalamiento.tarifa_de_escalamiento_indbound.value` | `canales[].costo_escalamiento` | ❌ estructura diferente | — |
| `hitl.total_volumen_cadena_b` | — | ❌ no existe en modelo | — |
| `hitl.equipo[].rol` | `opex_consumo_variable[].nombre` (HITL) | ❌ modelo completamente diferente | 🔴 HITL personal = 0 |
| `hitl.equipo[].activado` | — | ❌ | — |
| `hitl.equipo[].ratio` | — | ❌ | — |
| `hitl.equipo[].personas` | — | ❌ | — |
| `hitl.dispositivos_requeridos[]` | `dispositivos_sm[]` (HITL) | ❌ | — |

**Resultado neto para cadena_b cuando se usa formato entry_data:**
- `opex_fijo = 0` (tarifas variables = 0, opex = 0)
- `sm = 0` (costo_personal_sm = 0, opex_herramientas_sm = 0)
- `hitl = 0` (costo_personal_hitl = 0)
- `inversiones = 0`
- `escalamiento = 0`
- **`costo_b = 0` — CRÍTICO**

---

## 8. `condiciones_cadena_c`

> **⚠️ MISMATCH ESTRUCTURAL CRÍTICO**  
> `_cadena_c()` busca: `canales[]`, `equipo_transversal[]`, `inversion_anual`  
> entry_data provee: `tarifa_proveedor_canal.items[]`, `inversiones_capex[]`, `recurso_humano_transversal{fte, roles[], opex[]}`, `costo_variable{...}`, `hitl{...}`  
> **No hay `canales[]` en el entry_data de cadena_c.**

| Campo JSON (entry_data) | Campo esperado por `_cadena_c()` | Mapeado? | Impacto |
|---|---|---|---|
| `tarifa_proveedor_canal.items[]` | `canales[]` (no existe en este entry_data) | ❌ estructura radicalmente diferente | 🔴 canales = [] → tarifa_proveedor = 0 |
| `tarifa_proveedor_canal.items[].servicio` | `canales[].nombre` | ❌ | — |
| `tarifa_proveedor_canal.items[].valor` | `canales[].tarifa_proveedor` | ❌ | 🔴 tarifa proveedor siempre 0 |
| `tarifa_proveedor_canal.items[].cantidad` | `canales[].volumen_mensual` | ❌ semántica diferente | — |
| `inversiones_capex[].valor` | `inversion_anual` (scalar) | ❌ lista vs escalar | 🔴 inversion_anual = 0 |
| `inversiones_capex[].meses_a_diferir` | — | ❌ | — |
| `recurso_humano_transversal.fte` | — (no existe) | ❌ | 🔴 fte transversal ignorado |
| `recurso_humano_transversal.roles[].rol` | `equipo_transversal[].rol` | ❌ campo distinto (`roles` vs `equipo_transversal`) | 🔴 equipo_transversal = [] → costo_equipo_integ = 0 |
| `recurso_humano_transversal.roles[].activado` | `equipo_transversal[].activo` | ❌ nombre distinto | — |
| `recurso_humano_transversal.roles[].dedicacion` | `equipo_transversal[].pct_dedicacion` | ❌ nombre distinto | — |
| `recurso_humano_transversal.opex[]` | — | ❌ no existe en modelo | — |
| `costo_variable.tarifas_por_canal.inbound[]` | `canales[].tarifa_proveedor` | ❌ estructura diferente | 🔴 |
| `costo_variable.tasa_escalamiento.inbound[]` | `canales[].pct_escalamiento` | ❌ | 🔴 escalamiento = 0 |
| `costo_variable.tasa_escalamiento.tarifa_de_escalamiento_indbound.value` | `canales[].costo_escalamiento` | ❌ | — |
| `hitl.total_volumen_cadena_c` | — | ❌ | — |
| `hitl.equipo[].rol` | — (no hay equivalente en CadenaCInput) | ❌ | 🔴 HITL C = 0 |
| `hitl.equipo[].activado` | — | ❌ | — |
| `hitl.equipo[].ratio` | — | ❌ | — |
| `hitl.opex[].precio` | — | ❌ | — |

**Resultado neto para cadena_c cuando se usa formato entry_data:**
- `canales = []` → tarifa_proveedor = 0, opex_integ = 0
- `costo_equipo_integ = 0`
- `inversion_anual = 0`
- **`costo_c = 0` — CRÍTICO**

---

## Resumen de Gaps por Severidad

### 🔴 CRÍTICOS (producen costo incorrecto / visión incorrecta)

| # | Gap | Sección | Impacto en visión |
|---|---|---|---|
| C1 | `condiciones_cadena_b` mismatch estructural completo | cadena_b | `costo_b = 0` en PyG, CTS, Tarifas |
| C2 | `condiciones_cadena_c` mismatch estructural completo | cadena_c | `costo_c = 0` en PyG, CTS, Tarifas |
| C3 | `polizas[]` nunca consumida | polizas | `costo_polizas` siempre de storage, no del deal |
| C4 | `escenarios_comerciales[]` nunca consumida | escenarios | `modelo_cobro = "Fijo FTE"` siempre, Tarifas incorrectas |
| C5 | `contingencia_comercial.valor` hardcoded a 0.0 | reglas_negocio | `ingreso_neto` subestimado si com_cont > 0 |

### ⚠️ PARCIALES (mapeo incompleto o silently defaulted)

| # | Gap | Sección | Impacto |
|---|---|---|---|
| P1 | `indexacion.componente_humano/tecnologico` hardcoded "IPC" | volumetria | Ajuste salarial puede ser incorrecto |
| P2 | `indexacion.mes_aplicacion` viene de parametrización, no del JSON | volumetria | Mes de ajuste no configurable por deal |
| P3 | `roles_operativos[]` en perfiles cadena_a ignorados | cadena_a | Ratios staff siempre de parametrización global |
| P4 | `opex_fijo` y `inversiones[]` en perfiles cadena_a ignorados | cadena_a | Costos tecnológicos por-perfil perdidos |
| P5 | `cadenas_activas` en volumetria ignorado | volumetria | Activación de cadenas sin efecto |

### ❌ IGNORADOS (informativo, no financiero)

| # | Gap | Sección |
|---|---|---|
| I1 | `cufin` | datos_operativos |
| I2 | `horas_formacion_mes` | datos_operativos |
| I3 | `tarifa_diaria_capacitacion` (user override) | datos_operativos |
| I4 | `sede_combinada_costo_formacion` | datos_operativos |
| I5 | `ciudades_recurso[]` | datos_operativos |
| I6 | `pct_ausentismo` llega a PanelDeControl pero ningún calculator lo lee | datos_operativos |
| I7 | `contingencia_operativa/comercial.minimo/maximo` | reglas_negocio |
| I8 | `imprevistos` | reglas_negocio |
| I9 | `porcentaje_acumulado` | reglas_negocio |
| I10 | `Calculo_conversion_fte_interacciones` | cadena_a |
| I11 | `estaciones_presenciales` | cadena_a |
| I12 | `polizas[].aplica_extension`, `meses_extension` | polizas |

---

## Orden de Implementación Propuesto (FASE B en adelante)

Dado este análisis, el orden de resolución que maximiza impacto vs riesgo es:

1. **FASE B — `NewEntryDataAdapter`**: Traducir `condiciones_cadena_b` y `condiciones_cadena_c` del formato entry_data al formato interno esperado por los loaders (gaps C1, C2).  
2. **FASE C — `escenarios_comerciales`**: Mapear modelo_cobro/proporcion a `PerfilCadenaAInput.modelo_cobro/pct_fijo` (gap C4).  
3. **FASE D — `polizas`**: Mapear `polizas[]` a `ParametrosCadenaB/C` o a un nuevo `ParametrosPolizas` consumido por `CostosFinancierosCalculator` (gap C3).  
4. **FASE E — `contingencia_comercial`**: Pasar `com_cont` correctamente desde el normalizer (gap C5).  
5. **FASE F — indexación configurable**: Mapear `componente_humano/tecnologico` desde entry_data al panel (gap P1).  
6. **FASE G — datos menores**: `pct_ausentismo`, `horas_formacion_mes`, `tarifa_diaria_capacitacion` (gaps I2, I3, I6).

---

*Generado por FASE A de la auditoría contractual. Ver `docs/audit/` para los reportes de cada fase subsiguiente.*
