# V2-8 — Mapa maestro de inputs (Excel → request → contrato → loader/provider → backend)

Fecha: 2026-06-11 · Rama: `refactor/modular-pure` · Modo: **READ-ONLY / DOCS-ONLY**
(sin tocar `modules/`, `request/request.json`, `storage/`, tests ni baselines).
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`.
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m, denominador Panel!W31 = 221,000 tx/mes.

> **Propósito:** sustituir la corrección reactiva delta-por-delta por un mapa completo de inputs V2-8.
> Cada dato Excel se clasifica como input real vs hoja intermedia, y se traza extremo-a-extremo hasta el
> valor efectivamente consumido por el backend, marcando explícitamente defaults, overrides de provider
> y campos presentes-pero-no-consumidos.

---

## 0. Convenciones

**Tipo de fuente Excel:**
`REAL_INPUT` · `DERIVED_INPUT` · `INTERMEDIATE_FORMULA` · `OUTPUT_ONLY` · `LOOKUP_OR_PARAMETRIZATION` · `AMBIGUOUS_SOURCE`

**Estado de consumo backend:**
`CONSUMED_AS_IS` · `CONSUMED_WITH_TRANSFORM` · `CONSUMED_WITH_DEFAULT` · `PRESENT_NOT_CONSUMED` ·
`CONSUMED_FROM_PROVIDER_NOT_REQUEST` · `MISSING_IN_CONTRACT` · `MAPPING_AMBIGUOUS`

**Estado de mapping Excel→request:**
`MATCH` · `VALUE_MISMATCH` · `MISSING_IN_REQUEST` · `MISSING_IN_BACKEND_CONSUMPTION` ·
`MISSING_IN_EXCEL` · `MAPPING_AMBIGUOUS` · `DERIVED_VALUE` · `NOT_USED_BY_BACKEND` · `OUTPUT_ONLY_NOT_INPUT`

**Regla aplicada:** sólo `REAL_INPUT` / `DERIVED_INPUT` justifican un mapping directo a request.
Hojas intermedias (`Nomina Loaded`, `No payroll`, `Inputs de Nomina`, `Vision *`) se usan para validar/rastrear,
nunca para inventar campos de request. Sin valores hardcodeados nuevos en motor.

**Hojas de input real Excel V2-8:** `Panel de Control General`, `Condiciones Cadena A/B/C`.
**Hojas intermedias / output:** `Inputs de Nomina`, `Nomina Loaded`, `No payroll`, `HME`, `Vision *`.

---

## 1. Inventario request / contrato / backend (Fase 1)

Contrato público V1: `modules/shared/contracts/api_v1/request/`. El request real (`request/request.json`)
está en formato **entry_data** (`datos_operativos`, `volumetria`, `condiciones_cadena_*`), normalizado por
`user_input_loader.py:_normalizar_entry_data_format` a la forma legacy (`panel_de_control`, etc.) antes de
construir los DTOs internos (`modules/calculator_motor/dto/user_inputs.py`).

> **Hallazgo estructural:** muchos campos del deal **no existen en el contrato público V1** (es estricto,
> `extra="forbid"` en Panel). Llegan como dict crudo del formato entry_data y se materializan en DTOs
> internos (`PerfilCadenaAInput`, `PolizaInput`, etc.). Esto explica por qué `opex_fijo.items`,
> `inversiones[]`, `no_payroll_mensual`, `roles_operativos[]`, `polizas[]` "funcionan" sin estar en
> `PerfilCadenaAV1` / `EntryDataV1`.

| Request path | Contrato V1 (file:line) | DTO interno | Loader/builder (file:line) | Consumidor backend | Estado consumo | Observación |
|---|---|---|---|---|---|---|
| `datos_operativos.crucero` | ✗ (no en panel.py) | `PanelDeControlInput.tarifa_crucero` | `user_input_loader.py:323` | `nomina.py:297-308` | CONSUMED_WITH_TRANSFORM | mapea `crucero`→`tarifa_crucero` |
| `condiciones_cadena_a.perfiles[].incluye_crucero` | `cadena_a.py:36` (`=False`) | `PerfilCadenaAInput.incluye_crucero` | `user_input_builders_cadena_a.py:159` | `nomina.py:304` | CONSUMED_AS_IS | gate del crucero |
| `…perfiles[].no_payroll_mensual` | `cadena_a.py:37` (`=0.0`) | `PerfilCadenaAInput.no_payroll_mensual` | `user_input_builders_cadena_a.py:165` | `costs.py:98-103` | CONSUMED_AS_IS | override; bypasea `opex_fijo.items` |
| `…perfiles[].opex_fijo.items[]` | ✗ (interno) | `PerfilCadenaAInput.opex_fijo` | `user_input_builders_cadena_a.py:172` | `context_builder_perfiles_soporte_mixin.py:296-340` → `costs.py:101` | CONSUMED_WITH_DEFAULT | **ignorado si `no_payroll_mensual>0`** |
| `…perfiles[].inversiones[]` | ✗ (interno) | `PerfilCadenaAInput.inversiones` | `user_input_builders_cadena_a.py:173` | `context_builder_perfiles_soporte_mixin.py:342-375` → `costs.py:222-233` | CONSUMED_AS_IS | CAPEX term-based |
| `…perfiles[].fte` | `cadena_a.py:30` | `PerfilCadenaAInput.fte` | `user_input_builders_cadena_a.py:153` | `context_builder_perfiles_soporte_mixin.py:122`, `costs.py:200` | CONSUMED_AS_IS | numerador soporte + estaciones |
| `…perfiles[].salario_base` | `cadena_a.py:33` (`=None`) | `PerfilCadenaAInput.salario_base` | `user_input_builders_cadena_a.py:156` | `context_builder_perfiles_light_mixin.py:95-107` | CONSUMED_WITH_DEFAULT | `None`→`get_salario_rol` |
| `…perfiles[].comision_pct` | `cadena_a.py:32` | `PerfilCadenaAInput.comision_pct` | `user_input_builders_cadena_a.py:155` | `nomina.py:200-227` | CONSUMED_AS_IS | comisión agente |
| `…perfiles[].roles_operativos[].comision_rol` | ✗ | (no se persiste como comisión de rol) | — | `comision_rol` soporte = `get_comision_pct_rol` provider | CONSUMED_FROM_PROVIDER_NOT_REQUEST | request lleva `0.0`; soporte usa provider HR |
| `…perfiles[].roles_operativos[].ratio` ("20 Agentes") | ✗ → `staff_config[].ratio_override` | `StaffRolInput.ratio_override` | `user_input_builders_cadena_a.py:128-134` | `context_builder_perfiles_soporte_mixin.py:64-75` | MAPPING_AMBIGUOUS | el backend consume `staff_config`, **no** `roles_operativos`; string "N Agentes" no se parsea |
| `…perfiles[].roles_operativos[].incluye_en_deal` | ✗ → `staff_config[].activo` | `StaffRolInput.activo` | `user_input_builders_cadena_a.py:131` | `context_builder_perfiles_soporte_mixin.py:64-70` | MAPPING_AMBIGUOUS | igual: vía `staff_config`, no `roles_operativos` |
| `…perfiles[].capacitacion.dias_capacitacion_perfil` | `cadena_a.py:38-39` | `PerfilCadenaAInput.dias_cap_*` | `input_normalizer_cadena_a.py:99-121` | `nomina.py:229-257` | CONSUMED_WITH_DEFAULT | default 10 |
| `…capacitacion.incluye_costo_examenes_ingreso` | `cadena_a.py:34` (`=True`) | `incluye_examenes` | `input_normalizer_cadena_a.py` | `nomina.py:259-289` | CONSUMED_AS_IS | gate exámenes |
| `…capacitacion.incluye_estudio_seguridad_*` | `cadena_a.py:35` (`=False`) | `incluye_seguridad` | `input_normalizer_cadena_a.py` | `nomina.py:291-295` | CONSUMED_AS_IS | gate seguridad |
| `datos_operativos.pct_rotacion` | `panel.py:40` (`=None`) | `PanelDeControlInput.pct_rotacion` | `user_input_loader.py:314` | `nomina.py:251,280`, soporte mixin:140 | CONSUMED_WITH_DEFAULT | `None`→`get_pct_rotacion` |
| `datos_operativos.pct_ausentismo` | `panel.py:41` (`=None`) | `PanelDeControlInput.pct_ausentismo` | `user_input_loader.py:315` | `context_builder_panel_mixin.py:55` | **PRESENT_NOT_CONSUMED** | no alimenta fórmula de costo verificable (solo contexto/output) |
| `datos_operativos.pct_examen_anual` (opcional) | ✗ | `PanelDeControlInput.pct_examen_anual` | `user_input_loader.py:324` | `context_builder_panel_bc_mixin.py:378` | CONSUMED_WITH_DEFAULT | `None`→`get_pct_examen_anual` |
| `volumetria.indexacion.componente_humano` | `panel.py:35` (`="IPC"`) | `PanelDeControlInput` | `user_input_loader.py:285+` | `nomina.py:149-161`, `pyg_calculator.py:213` | CONSUMED_AS_IS | factor indexación payroll + P&G |
| `volumetria.indexacion.componente_tecnologico` | `panel.py:36` | `PanelDeControlInput` | `user_input_loader.py:285+` | `cadena_c/reglas.py:144`, `pyg_calculator.py:216` | CONSUMED_AS_IS | factor Cadena C + P&G B/C |
| `volumetria.indexacion.tasa_interes_mensual` | `panel.py:48` (`=None`) | `tasa_mensual_financ` | `user_input_loader.py:313` | `costs.py` factor_capex, `cadena_c/reglas.py:182` | CONSUMED_WITH_DEFAULT | `None`→`0.0153` v27 default |
| `volumetria.indexacion.mes_aplicacion` | `panel.py:47` (`=None`) | `mes_ajuste_indexacion` | `user_input_loader.py:331` | `context_builder_panel_bc_mixin.py:447-466` | CONSUMED_WITH_TRANSFORM | calendario→mes contrato |
| `volumetria.{inbound,outbound}.canales[].cadena_a.valor` | ✗ (dict crudo) | `VolumeResolutionService` | `volume_resolution.py:27-80` | `user_input_loader.py:473-485` (fallback) | CONSUMED_WITH_DEFAULT | fallback si `vol_cadena_a_mensual=0` |
| `…perfiles[].vol_cadena_a_mensual` | `cadena_a.py:43` | `PerfilCadenaAInput.vol_cadena_a_mensual` | `user_input_loader.py:475` | `cost_to_serve_calculator.py:214-240` | CONSUMED_AS_IS | denominador CTS Cadena A |
| `volumetria.{}.cadenas_activas.{a,b,c}` | ✗ | `cadenas_activas` | `volume_resolution.py` | engine pipeline | CONSUMED_AS_IS | activación cadenas |
| `reglas_negocio.margen_objetivo` | `panel.py:27` (`margen`) | `PanelDeControlInput.margen` | `user_input_loader.py:304` (requerido) | `pyg_calculator.py:160`, `costos_financieros/calculator.py:158` | CONSUMED_AS_IS | margen Cadena A |
| `reglas_negocio.margen_objetivo_cadena_b` | `panel.py:45` (`margen_b`) | `margen_b` | builder panel | `pyg_calculator.py`, `costos_financieros` | CONSUMED_WITH_DEFAULT | `None`→0.30 |
| `reglas_negocio.contingencia_operativa/comercial`, `markup`, `descuento_volumen`, `imprevistos`, `porcentaje_acumulado` | parcial (`panel.py:28-31,49`) | `PanelDeControlInput` | builder panel | `pyg`/factor billing | CONSUMED_WITH_DEFAULT | ver §3 (porcentaje_acumulado VALUE_MISMATCH) |
| `polizas[]` (`activa`,`pct_poliza`,`pct_atribuible`) | ✗ (dict crudo) | `PolizaInput` | `user_input_loader.py:239-261` | `costos_financieros/calculator.py:132-208` | CONSUMED_AS_IS | + Comisión Admin |
| `datos_operativos.tasa_ica` | `panel.py:37` (`=None`) | `tasa_ica` | `user_input_loader.py:309` | `costos_financieros/calculator.py:321` | CONSUMED_WITH_DEFAULT | `None`→`get_ica(ciudad)` |
| `datos_operativos.tasa_gmf` | `panel.py:38` (`=None`) | `tasa_gmf` | `user_input_loader.py:310` | `costos_financieros/calculator.py:337` | CONSUMED_WITH_DEFAULT | `None`→`get_gmf()` |
| `datos_operativos.cons_costo_de_financiacion` | `panel.py:33` (`activa_financiacion=True`) | `activa_financiacion` | `user_input_loader.py:311` | `costos_financieros/calculator.py:303` | CONSUMED_AS_IS | gate financiación |
| `escenarios_comerciales[]` (`modelo_cobro`, props fijo/var) | `escenarios.py:19-24` (`extra=allow`) | `EscenarioComercialInput` | `user_input_builders_panel.py:167-180` | `vision_tarifas/reglas.py:108-200` | CONSUMED_AS_IS | tarifa por canal |
| `condiciones_cadena_b.*` (opex/capex/equipo/costo_var/hitl) | `cadena_b.py:52-61` | `CondicionesCadenaBInput` | `user_input_builders_cadena_b.py:122` | `cadena_b/reglas.py:44-210` | CONSUMED_AS_IS | ver §6 |
| `condiciones_cadena_c.*` (tarifa_prov/costo_var/hitl) | `cadena_c.py:30-35` | `CondicionesCadenaCInput` | `user_input_builders_cadena_c.py` | `cadena_c/reglas.py:47-220` | CONSUMED_AS_IS | ver §6 |
| `…perfiles[].roles_operativos[]` (estructura completa) | ✗ | — | `input_normalizer_cadena_a.py:30` (preservado) | — | PRESENT_NOT_CONSUMED | el motor usa `staff_config`; `roles_operativos` se preserva sin parsear |

### Campos del contrato V1 no presentes en el deal (informativo)

`panel.py` expone `op_cont` (28), `com_cont` (29), `tasa_mensual_financ` (39), `imprevistos` (49) — el deal
los entrega vía `reglas_negocio` / `volumetria`, no vía el contrato directo. `cadena_b.py` /`cadena_c.py` V1
exponen una forma "aplanada" (`canales[]` con `opex_fijo`/`tarifa_unitaria` escalares) distinta del entry_data
del deal (`opex.items[]`, `costo_variable.tarifas_por_canal`), reconciliada por los builders.

---

## 2. Mapa Excel input → request → backend (Fase 2)

Valores Excel extraídos con `openpyxl` (`data_only=True`) de las hojas de input real.

### 2a. Panel de Control General — Datos Operativos / Impuestos / Indexación

| Sección | Celda | Concepto | Tipo fuente | Valor Excel | Request path | Valor request | Backend consumed | Status |
|---|---|---|---|---|---|---|---|---|
| Datos Op | C5 | Servicio | REAL_INPUT | SAC | `datos_operativos.servicio` | SAC | sí | MATCH |
| Datos Op | C6 | Cliente | REAL_INPUT | METROCUADRADO COM SAS | `datos_operativos.cliente` | idem | sí | MATCH |
| Datos Op | C7 | Antigüedad | REAL_INPUT | Cliente Antiguo | `datos_operativos.antiguedad` | idem | contexto | MATCH |
| Datos Op | C8 | Tipo cliente | REAL_INPUT | Grupo Aval | `datos_operativos.tipo_cliente` | idem | sí | MATCH |
| Datos Op | C9 | Periodo de pago | REAL_INPUT | 30 | `datos_operativos.periodo_pago` | 30 | financiación | MATCH |
| Datos Op | C10 | Fecha inicio | REAL_INPUT | 2026-07-01 | `datos_operativos.fecha_inicio` | 2026-07-01 | sí | MATCH |
| Datos Op | C11 | Duración meses | REAL_INPUT | 24 | `datos_operativos.duracion_meses` | 24 | sí | MATCH |
| Datos Op | C12 | Ciudad | REAL_INPUT | Bogota | `datos_operativos.ciudad` | Bogota | ICA/HR | MATCH |
| Datos Op | C16 | Tarifa diaria capacitación | REAL_INPUT | 20000 | `datos_operativos.tarifa_diaria_capacitacion` | 20000 | `nomina.py` cap | MATCH |
| Datos Op | C17 | Crucero (tarifa) | REAL_INPUT | 8408 | `datos_operativos.crucero` | 8408 | `nomina.py:304` | MATCH |
| Datos Op | C18 | Horas formación mes | REAL_INPUT | 8 | `datos_operativos.horas_formacion_mes` | 8 | sí | MATCH |
| Datos Op | C19 | % Ausentismo | REAL_INPUT | 0.065 | `datos_operativos.pct_ausentismo` | 0.065 | **no** | **MISSING_IN_BACKEND_CONSUMPTION** (PRESENT_NOT_CONSUMED) |
| Datos Op | C20 | % Rotación | REAL_INPUT | 0.0815 | `datos_operativos.pct_rotacion` | 0.0815 | `nomina.py:251` | MATCH |
| Datos Op | C21 | ¿Costo de financiación? | REAL_INPUT | No (False) | `datos_operativos.cons_costo_de_financiacion` | false | `costos_financieros:303` | MATCH |
| Impuestos | C34 | ICA | REAL_INPUT | 0.01 | `datos_operativos.tasa_ica` | 0.01 | sí | MATCH |
| Impuestos | C35 | GMF | REAL_INPUT | 0.004 | `datos_operativos.tasa_gmf` | 0.004 | sí | MATCH |
| Indexación | L6 | ¿Aplica indexación a la tarifa? | REAL_INPUT | **No** | (no hay campo de gate) | — | n/a | **MAPPING_AMBIGUOUS** — el deal sí puebla indexación; Excel marca "No" en el gate de tarifa. Ver §5. |
| Indexación | L7 | Componente humano | REAL_INPUT | IPC | `volumetria.indexacion.componente_humano` | IPC | sí | MATCH |
| Indexación | L8 | Componente tecnológico | REAL_INPUT | 20% SMMLV 80% IPC | `volumetria.indexacion.componente_tecnologico` | idem | sí | MATCH |
| Indexación | L9 | Frecuencia | REAL_INPUT | Anual | `volumetria.indexacion.frecuencia` | Anual | sí | MATCH |
| Indexación | L10 | Mes de ajuste | REAL_INPUT | 6 | `volumetria.indexacion.mes_aplicacion` | 6 | sí | MATCH |
| Indexación | L11 | Tasa interés mensual | REAL_INPUT | 0.0153 | `volumetria.indexacion.tasa_interes_mensual` | 0.0153 | sí | MATCH |

### 2b. Panel — Volumetría Mensual (Inbound)

| Celda | Concepto | Tipo fuente | Valor Excel | Request | Valor request | Status |
|---|---|---|---|---|---|---|
| L19 | Voz 1 (total volumetría) | REAL_INPUT | 280,500 | `volumetria.inbound.canales[Voz1]` (multi-cadena) | A=130 FTE / C=170000 vol | DERIVED_VALUE — Excel L19 es volumen agregado del canal; el deal lo reparte A/B/C |
| L20 | Voz 2 | REAL_INPUT | 168,000 | canales[Voz2] | A=80 FTE / B=100000 | DERIVED_VALUE |
| L23 | WhatsApp | REAL_INPUT | 42,500 | canales[WhatsApp].cadena_a | 50 FTE | DERIVED_VALUE |
| W31 | Denominador Cadena A (tx/mes) | DERIVED_INPUT | 221,000 | `vol_cadena_a_mensual` Σ (110500+42500+68000) | 221,000 | **MATCH** ✓ |

> **Nota:** `vol_cadena_a_mensual` por perfil (110500/42500/68000) es la partición de Cadena A; su suma =
> Panel!W31 = 221,000. Es el denominador CTS-001 (verificado).

### 2c. Panel — Reglas de Negocio (rows 60-75)

| Celda | Concepto | Valor Excel | Request | Valor request | Status |
|---|---|---|---|---|---|
| C63 | Margen objetivo Cadena A | 0.21 | `reglas_negocio.margen_objetivo` | 0.21 | MATCH |
| D63 | Margen objetivo Cadena B | 0.30 | `reglas_negocio.margen_objetivo_cadena_b` | 0.30 | MATCH |
| E63 | Margen objetivo Cadena C | 0.20 | (no en request → default backend 0.20) | — | MATCH (default) |
| C67 | Contingencia operativa | 0 | `reglas_negocio.contingencia_operativa.valor` | 0 | MATCH |
| C68 | Contingencia comercial | 0 | `reglas_negocio.contingencia_comercial.valor` | 0 | MATCH |
| C69 | Markup | 0 | `reglas_negocio.markup.valor` | 0.0 | MATCH |
| C70 | Descuento volumen | 0 | `reglas_negocio.descuento_volumen` | 0 | MATCH |
| C73 | Imprevistos | 0 | `reglas_negocio.imprevistos` | 0 | MATCH |
| C75 | Porcentaje acumulado | **0** | `reglas_negocio.porcentaje_acumulado.actual` | **0.02** | **VALUE_MISMATCH** (request 0.02 vs Excel 0) |

### 2d. Panel — Pólizas (rows 37-46) y Escenarios (rows 80-90)

| Celda | Concepto | Valor Excel | Request | Status |
|---|---|---|---|---|
| C38-C46 | Flags activación pólizas | Seriedad=F, Cumpl=T, Salarios=T, Calidad=T, rc=F, IRF=F, Resp=F, ComAdm=T, Otros=F | `polizas[].activa` | MATCH (10 pólizas idénticas) |
| D39-D45 | % prima | 0.0063/0.0128/0.0128/…/0.0118 | `polizas[].pct_poliza` | MATCH |
| E39-E45 | % atribuible/exigido | 0.2/0.2/0.2/1.0 | `polizas[].pct_atribuible` | MATCH |
| Escenario 1 (B81-D85) | Voz1 / Variable / Transacción / 1.0 | idem | `escenarios_comerciales[0]` | MATCH |
| Escenario 2 (B88-C90) | WhatsApp / Fijo | idem | `escenarios_comerciales[1]` | MATCH |

### 2e. Condiciones Cadena A — perfiles (cols E/F/G = SAC/WhatsApp/Crecimiento)

| Celda | Concepto | Tipo fuente | Valor Excel | Request path | Valor request | Status |
|---|---|---|---|---|---|---|
| E9/F9/G9 | FTE agentes | REAL_INPUT | 130/50/80 | `perfiles[].fte` | 130/50/80 | MATCH |
| E10 | % estaciones | REAL_INPUT | 0.6 | `perfiles[].pct_presencia` | 0.6 | MATCH |
| E11/F11/G11 | Estaciones presenciales | DERIVED_INPUT | 78/30/48 | `perfiles[].estaciones_presenciales` | 78/30/48 | MATCH |
| E12 | Salario base | REAL_INPUT | 1,750,905 | `perfiles[].salario_base` | 1,750,905 | MATCH |
| E13 | Comisiones perfil ($) | REAL_INPUT | 600,000 | `perfiles[].comision_pct` (=600000/1750905) | 0.3427 | MATCH (derivado) |
| **E26/G26** | **Cargos adicionales (ratio FTE)** | **REAL_INPUT** | **12 / 0 / 7.3846** | — | **ausente** | **MISSING_IN_REQUEST** (gap Support FTE, ver §4) |
| E95/F95/G95 | Supervisor FTE | INTERMEDIATE_FORMULA | **9.5** /2.5/4.369 | (derivado de ratio+cargos) | backend 13.0 | VALUE_MISMATCH — E95=9.5 **override literal**, no fórmula |
| E44/F44 | Director cuentas salario/comisión | REAL_INPUT | 22,761,150 / **3,868,125** | `roles_operativos[].comision_rol` | **0.0** | **MISSING_IN_REQUEST** (staff variable) |
| E51/F51 | Jefe Operación salario/comisión | REAL_INPUT | 4,329,699.6 / **1,500,000** | `comision_rol` | **0.0** | **MISSING_IN_REQUEST** |
| E62/F62 | Supervisor salario/comisión | REAL_INPUT | 2,334,300 / **700,000** | `comision_rol` | **0.0** | **MISSING_IN_REQUEST** |
| C79/C80/C87 | Activación JCR / AFAC / GTR | REAL_INPUT | **False/False/False** | `roles_operativos[].incluye_en_deal` | **true/true/true** | **MAPPING_AMBIGUOUS** (request activa lo que Excel desactiva) |
| E104-E127 | Ratios staff | LOOKUP_OR_PARAMETRIZATION | 750/1200/…/20/100 | `roles_operativos[].ratio` "N Agentes" | idem (string) | MATCH (valores coinciden con HR-Ratios provider) |
| E133 | Tarifa diaria capacitación | REAL_INPUT | 20,000 | (= Panel C16) | 20,000 | MATCH |
| E134 | Crucero tarifa | REAL_INPUT | 8,408 | `datos_operativos.crucero` | 8,408 | MATCH |
| E135 | % exámenes anuales | REAL_INPUT | 0.28 | (provider patch) `pct_examen_anual` | 0.28 | MATCH (vía provider) |
| E139/F139/G139 | Días capacitación por perfil | REAL_INPUT | **11** | `capacitacion.dias_capacitacion_perfil` | **11** | ✅ **MATCH** (VALUE_MISMATCH resuelto 2026-06-12) |
| E141-E146 | Flags capacitación/exámenes | REAL_INPUT | True | `capacitacion.incluye_*` | true | MATCH |
| E148-E151 | Flags estudios seguridad | REAL_INPUT | False | `capacitacion.incluye_estudio_seguridad_*` | false | MATCH |
| E152/F152/G152 | Crucero (costo mensual total) | INTERMEDIATE_FORMULA | 1,193,936 / 420,400 / 734,730 | (= tarifa × FTE × idx) | — | DERIVED_VALUE — Excel da el total/mes; backend lo reconstruye per-FTE |

### 2f. Condiciones Cadena A — OPEX Fijo / Inversiones (No payroll)

| Concepto | Tipo fuente | Excel (No payroll!C107/C108/C111) | Request | Status |
|---|---|---|---|---|
| OPEX TI mensual SAC | DERIVED_INPUT | 39,973,918.08 | `perfiles[0].no_payroll_mensual` | MATCH (override aplicado) |
| OPEX TI mensual WhatsApp | DERIVED_INPUT | 3,525,293.25 | `perfiles[1].no_payroll_mensual` | MATCH |
| OPEX TI mensual Crecimiento | DERIVED_INPUT | 24,599,334.20 | `perfiles[2].no_payroll_mensual` | MATCH |
| `opex_fijo.items[]` (Internet/VPN/Antivirus/CCaaS/Backup) | REAL_INPUT | ≠ items Excel (Worki/Speech/Genesys) | request items | MAPPING_AMBIGUOUS (ignorado por override) |
| `inversiones[]` (CAPEX por perfil) | REAL_INPUT | amortizado per-item | request inversiones | CONSUMED (residual +16.72) |

### 2g. Condiciones Cadena B / C

| Celda | Concepto | Valor Excel | Request | Status |
|---|---|---|---|---|
| B!H8 / qty | OPEX Plataformas (Voz2) | 250 × 10,000 | `condiciones_cadena_b.opex.items[0]` (250 / 10000) | MATCH |
| B!F47/G47/H47 | CAPEX Infra cloud | 2,500,000 × 60 / 24m | `inversiones_capex[0]` (2.5M/60/24) | MATCH |
| B!F48-F50 | CAPEX transversal/outbound | 3,612 × 143 + outbound | (ausente en request) | MISSING_IN_REQUEST (menor; outbound inactivo) |
| B!C79 | FTE equipo soporte | 3 | `equipo_soporte_mantenimiento.fte` | MATCH |
| C!G9/H9 | Tarifa proveedor Nexa AI | 5,130.66 × 170,000 | `tarifa_proveedor_canal.items[0]` | MATCH |
| C!G29/H29 | OPEX consumo variable (metering) | 117 × 190,000 | `costo_variable.tarifas_por_canal` 117 | MATCH |
| C!hitl vol | Volumen HITL Cadena C | 190,000 | `hitl.total_volumen_cadena_c` | MATCH |

---

## 3. Conceptos críticos — cobertura obligatoria (Fase 3)

| Concepto | Excel source | Request source | Contrato/API | Backend consumed | Match real | Hallazgo |
|---|---|---|---|---|---|---|
| crucero / tarifa / incluye_crucero | C17, A!E134, A!E152 | `crucero=8408` + `incluye_crucero=true` | `cadena_a.py:36` | `nomina.py:304` | **sí** (residual -0.74) | residual = `cargos_adicionales` en FTE |
| opex_fijo / no_payroll_mensual | No payroll!C107/8/11 | `no_payroll_mensual` perfiles | interno | `costs.py:98` | **sí (EXACT)** | override OPEX = paridad 0.0 |
| comision_rol / costo_empresa_override | A!F44/F51/F62 | `comision_rol=0.0` | ✗ | provider HR (W-override en test) | **no (request)** | staff variable ausente del deal; provider lo simula |
| fte / cargos_adicionales | A!E9 + A!E26/G26 | `fte` ✓ / cargos ✗ | `fte` sí; cargos no | soporte mixin:122 | **parcial** | `cargos_adicionales` = `MISSING_BACKEND_INPUT_SOURCE` |
| rotación / ausentismo | C20 / C19 | `pct_rotacion` ✓ / `pct_ausentismo` ✓ | `panel.py:40-41` | rotación sí; ausentismo no | rotación **sí**, ausentismo **no** | `pct_ausentismo` PRESENT_NOT_CONSUMED |
| componente_tecnológico | L8 | `componente_tecnologico` | `panel.py:36` | `cadena_c/reglas.py:144` | **sí** | factor C + P&G B/C |
| capex (inversiones) | A!inversiones, B/C CAPEX | `inversiones[]`, `inversiones_capex` | interno / `cadena_b.py:59` | `costs.py:222` | **sí** (residual +16.72) | reconciliación de plazos |
| volumen / vol_cadena_a_mensual | W31 / L19-23 | `vol_cadena_a_mensual` | `cadena_a.py:43` | `cost_to_serve:214` | **sí** (denom 221k) | MATCH |
| margen | C63/D63/E63 | `margen_objetivo`, `_cadena_b` | `panel.py:27,45,46` | `pyg_calculator.py:160` | **sí** | MATCH |
| indexación | K5-L11 | `volumetria.indexacion.*` | `panel.py:35-48` | `nomina.py:149` | **sí** | gate "L6=No" no modelado (ver §5) |
| SENA / Inclusión / Aprendiz | A!E64/E65 (1,750,905) | `salario_base` perfil | provider | SENA/Inclusion calc | **sí** (vía provider patch) | base 1,750,905 parchada en provider |
| exámenes médicos | A!E135 (0.28), Nomina Loaded!C329 (60,800) | flags + provider | `cadena_a.py:34` | `nomina.py:259` | **sí** (residual -0.73) | residual = `fte_examenes` (soporte) |
| payroll variable / cumplimiento / carga prestacional | Inputs Nomina!F62 | `comision_pct` + provider | `cadena_a.py:32` | `nomina_cargada.py:117`, `nomina.py:200` | **sí** | carga completa (Bug 2 fixed) |
| canales / SAC / WhatsApp / Crecimiento | A!E7:G8 | `perfiles[].canal/modalidad` | `cadena_a.py` | escenarios + perfiles | **sí** | MATCH |

---

## 4. Rutas de consumo backend (Fase 4)

| Concepto | Request path | Contract field | Loader/context/provider | Consumer backend | Transformación | Riesgo |
|---|---|---|---|---|---|---|
| crucero | `datos_operativos.crucero` + perfil flag | `cadena_a.py:36` | `user_input_loader.py:323` → `context_builder_panel_bc_mixin.py:90` | `nomina.py:297-308` | `tarifa×fte×idx` (gate `incluye_crucero`) | LOW_DIRECT_CONSUMPTION |
| no_payroll OPEX | `…no_payroll_mensual` | interno | `user_input_builders_cadena_a.py:165` | `costs.py:98-103` | suma override > 0 bypasea items | LOW_DIRECT_CONSUMPTION |
| support FTE (numerador) | `…fte` | `cadena_a.py:30` | `context_builder_perfiles_soporte_mixin.py:122` | mixin `_construir_perfiles_soporte` | `fte/ratio` (sin cargos_adic) | **BLOCKED_MISSING_SOURCE** (cargos_adicionales) |
| comision staff | `comision_rol=0.0` | ✗ | provider `get_comision_pct_rol` | `context_builder_perfiles_soporte_mixin.py:156` | provider, no request | **HIGH_DEFAULT_OR_PROVIDER_OVERRIDE** |
| staff_config activación | `roles_operativos[].incluye_en_deal` | ✗ → `staff_config[].activo` | `user_input_builders_cadena_a.py:131` | soporte mixin:64-75 | request `roles_operativos` no parseado | **HIGH_PRESENT_NOT_CONSUMED** (roles_operativos) / MEDIUM (staff_config) |
| pct_ausentismo | `datos_operativos.pct_ausentismo` | `panel.py:41` | `context_builder_panel_mixin.py:55` | (no calculator) | — | **HIGH_PRESENT_NOT_CONSUMED** |
| indexación | `volumetria.indexacion.*` | `panel.py:35-48` | `user_input_loader.py:285+` | `nomina.py:149`, `pyg_calculator.py:213` | factor anual por año calendario | MEDIUM_TRANSFORMED |
| margen | `reglas_negocio.margen_objetivo` | `panel.py:27` | `user_input_loader.py:304` | `pyg_calculator.py:160` | factor billing | MEDIUM_TRANSFORMED |
| polizas / ComAdm | `polizas[]` | ✗ (dict) | `user_input_loader.py:239` | `costos_financieros/calculator.py:132` | gross-up por cadena | MEDIUM_TRANSFORMED |
| escenarios tarifa | `escenarios_comerciales[]` | `escenarios.py:19` | `user_input_builders_panel.py:167` | `vision_tarifas/reglas.py:108` | modelo_cobro→fórmula tarifa | MEDIUM_TRANSFORMED |
| CAPEX inversiones | `inversiones[]` | interno | `context_builder_perfiles_soporte_mixin.py:342` | `costs.py:222-233` | `precio/meses × factor_capex` | MEDIUM_TRANSFORMED |

---

## 5. Opacidad y límites (Fase 5)

| Fuente Excel | Razón | Tratamiento |
|---|---|---|
| `Nomina Loaded`!232/253 (agregados soporte FTE) | layout multi-bloque (COP mezclados con HC); extracción cruda dio HC imposibles (SENA=308) | `EXCEL_SOURCE_OPAQUE` — no usar para inferir dotación; usar bloque limpio `Condiciones Cadena A`!E77:G100 |
| `HME`!C296/C304/C312 (base ingreso) | agregados internos del workbook, cacheados con otro deal | `OUTPUT_ONLY` / ACCEPTED_ARCHITECTURAL_DELTA (ver `v28_formula_parity_matrix.md`) |
| Panel!L6 "¿Aplica indexación a la tarifa?" = No | gate booleano de indexación de tarifa; el deal sí puebla `volumetria.indexacion` y el backend aplica indexación a payroll/P&G | `AMBIGUOUS_SOURCE` — el "No" aplica a indexación **de tarifa de venta**, no a la indexación de costo (payroll/tecnológico) que sí corre. No hay campo de gate equivalente; no inventar uno. |
| `Condiciones Cadena A`!E95 (Supervisor=9.5) | literal hardcodeado en celda, no fórmula | `EXCEL_SOURCE_OPAQUE` — override manual sin mecanismo backend; no replicable sin hardcode (prohibido) |

---

## 6. Gaps detectados (Fase 6)

| Gap | Tipo | Impacto probable | Req. request | Req. contrato | Req. modules | Prioridad | Siguiente acción |
|---|---|---|---|---|---|---|---|
| `cargos_adicionales` (A!E26/G26 = 12/0/7.3846) ausente | `CONTRACT_FIELD_MISSING` | ~-68 COP/tx CTS (Supervisor) | no | **sí** | sí (numerador soporte) | P0_BLOCKS_FULL_MATCH | decisión de contrato `PerfilCadenaAInput` (DEFERRED) |
| Supervisor E95=9.5 override manual | `EXCEL_SOURCE_OPAQUE` | incluido en el -68 anterior | no | sí (override per-rol) | sí | P0_BLOCKS_FULL_MATCH | requiere mecanismo override; no hardcode |
| comision_rol staff = 0.0 (Excel F44/F51/F62 ≠ 0) | `INPUT_FIELD_MISSING` / `PROVIDER_MISMATCH` | ~-289 COP/tx nomina_loaded soporte | sí (request lleva 0) | posible | no (si provider) | P1_HIGH_DELTA | decisión: ¿comisión staff vía request o provider HR? |
| `roles_operativos[]` no consumido (motor usa `staff_config`) | `BACKEND_NOT_CONSUMING_FIELD` | activación JCR/AFAC/GTR divergente | sí (alinear a `staff_config`) | no | no | P2_MEDIUM_DELTA | reconciliar deal: emitir `staff_config` o parsear `roles_operativos` |
| `pct_ausentismo` PRESENT_NOT_CONSUMED | `BACKEND_NOT_CONSUMING_FIELD` | desconocido (no en fórmula de costo) | no | no | posible | P3_LOW_DELTA | confirmar si Excel lo usa en algún costo; si no, doc-only |
| `dias_capacitacion_perfil` Excel 11 vs request 10 | `INPUT_VALUE_MISMATCH` | menor (cap inicial/rotación) | **sí** | no | no | P2_MEDIUM_DELTA | alinear request a 11 (verificar Excel E139) |
| `porcentaje_acumulado.actual` request 0.02 vs Excel 0 | `INPUT_VALUE_MISMATCH` | factor billing / P&G | **sí** | no | no | P2_MEDIUM_DELTA | confirmar fuente canónica Panel!C75=0 |
| CAPEX inversiones residual +16.72 | `KNOWN_DELTA` | +16.72 no-payroll | sí (plazos/precios) | no | no | P3_LOW_DELTA | reconciliar plazos vs Excel |
| crucero modelado per-FTE vs total Excel (E152) | `FORMULA_SCOPE` | residual -0.74 (cargos_adic) | no | no | no | P3_LOW_DELTA | cerrado al resolver cargos_adicionales |
| P&G ingreso base (HME) | `OUTPUT_USED_AS_INPUT_RISK` | ~18-24% P&G | no | sí (decisión negocio) | sí | P1_HIGH_DELTA | ACCEPTED_ARCHITECTURAL_DELTA (HME single-base) |
| OPEX item-level mapping (Worki/Speech ≠ Internet/Antivirus) | `MAPPING_AMBIGUOUS` | 0 (override neutraliza) | no | no | no | P4_DOC_ONLY | doc — items request no 1:1 con Excel |

---

## 7. Resumen cuantitativo

- **Total inputs Excel revisados:** ~70 celdas/conceptos de input real (Panel + Cadena A/B/C).
- **MATCH:** ~48
- **VALUE_MISMATCH:** 3 (`porcentaje_acumulado`, `dias_capacitacion`, Supervisor E95)
- **MISSING_IN_REQUEST:** 3 (`cargos_adicionales`, comision_rol staff, CAPEX transversal B menor)
- **MISSING_IN_BACKEND_CONSUMPTION:** 2 (`pct_ausentismo`, `roles_operativos[]`)
- **MAPPING_AMBIGUOUS:** 3 (activación staff, OPEX item-level, gate indexación L6)
- **EXCEL_SOURCE_OPAQUE:** 3 (Nomina Loaded agregados, Supervisor E95, HME base)
- **DERIVED_VALUE:** crucero E152, volumetría L19-23.

**Estado CTS-001 actual (post OPEX exact parity):** backend ≈ 6,093.24 vs Excel 6,224.58 →
-131.33 COP/tx (2.110%). Déficit dominante = payroll soporte (comision_rol staff + cargos_adicionales),
ahora desenmascarado por OPEX en paridad exacta.

---

## 8. Decisión de siguiente fase

| Frente | Acción recomendada | Motivo |
|---|---|---|
| **CTS** | Resolver el binomio payroll soporte: (1) decidir si `comision_rol` de staff entra por request (deal real) o por provider HR; (2) decisión de contrato `cargos_adicionales` por escenario. Ambos son P0/P1 y dominan el residual ahora que OPEX = paridad exacta. | El -131 COP/tx es 100% payroll soporte; no quedan frentes request-scope baratos que lo muevan. `cargos_adicionales` y comision_rol staff requieren decisión (contrato/provider), no más hipótesis delta. |
| **PyG** | Mantener `OUTPUT_USED_AS_INPUT_RISK` (HME base) como `ACCEPTED_ARCHITECTURAL_DELTA`. No abrir hasta tener golden V2-8 numéricos del deal real. Validar primero `dias_capacitacion` (11) y `porcentaje_acumulado` (0) que afectan factor billing. | El gap P&G (~18%) es estructural (HME single-base vs cálculo dinámico), no un input. Pero 2 VALUE_MISMATCH de input (dias_cap, pct_acumulado) sí son corregibles y tocan ingreso/factor billing. |
| **Vision Tarifas** | Sin gap de input nuevo: escenarios/modelo_cobro = MATCH. VTM-001 (revenue cumulativo vs base) es field-mapping en el output, no input. Diferir a sesión de output. | Inputs de tarifas (escenarios_comerciales) están en paridad; el delta VTM-001 vive en el render, no en el deal. |

---

## 9. Veredicto

**`V28_INPUT_FULL_MAPPING_COMPLETED`** — mapa extremo-a-extremo construido para Panel + Cadena A/B/C.

- Sin cambios en `modules/`, `request/request.json`, `storage/`, tests ni baselines.
- Hardcoded nuevos en motor: **0**.
- Próxima fase recomendada: **V28_FIX_ROADMAP consolidado** centrado en el binomio payroll soporte
  (`comision_rol` staff + `cargos_adicionales`), con los 2 VALUE_MISMATCH de input (dias_cap, pct_acumulado)
  como quick-wins request-scope previos.
