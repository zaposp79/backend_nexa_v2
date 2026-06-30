# API Contract Audit — Field Classification
> Phase 1 of API Contract Refactoring (Request 3)
> Generated: 2026-05-21

## 1. Overview

This document classifies every field in the NEXA pricing engine's API surface
into one of four categories:

| Code | Category | Description |
|------|----------|-------------|
| **A** | `INPUT_REAL_FRONTEND` | Genuine user input from the frontend UI / REST API |
| **B** | `DERIVADO_BACKEND` | Computed by backend from parametrization + user inputs |
| **C** | `METADATA_TESTING` | Test scaffolding: scenario names, expected values, comments |
| **D** | `DOCUMENTACION_EXCEL` | Excel reference values embedded in fixtures for parity checks |

**Decision rule:** If a field appears in a frontend DTO (`PcgInput`, `CdcAInput`,
`CdcBInput`, `CdcCInput`) AND the `UnifiedInputAdapter` maps it to a domain
`UserInput` field, it is **A**. If it only exists in test fixtures with `_` prefix,
it is **C** or **D**. If the `SimulationContextBuilder` or `ParametrizationProvider`
computes it, it is **B**.

---

## 2. Data Flow Summary

```
Frontend (nexaGetState)          REST DTOs (PcgInput, CdcAInput, CdcBInput, CdcCInput)
         |                                       |
         +----------> UnifiedInputAdapter <-------+
                            |
                      UserInput (domain)
                            |
                  SimulationContextBuilder + ParametrizationProvider
                            |
                      PricingRequest (domain)
                            |
                    NexaPricingEngine.calcular()
                            |
                      PricingResult
```

**Two entry paths, one domain:** Both frontend JSON and REST DTOs converge to
the same `UserInput` via `UnifiedInputAdapter`. The `calculate_router.py` endpoint
uses a third path: `CalculationRequest.user_input: Dict[str, Any]` deserialized
via `UserInputLoader.cargar_desde_dict()`.

---

## 3. Request Endpoint Contract

**POST `/api/v1/simulation/calculate`**

```python
class CalculationRequest(BaseModel):
    user_input: Dict[str, Any]   # untyped — accepts test_cases/*.json format
```

The `user_input` dict must contain:

| Key | Required | Maps To |
|-----|----------|---------|
| `panel_de_control` | **Yes** | `PanelDeControlInput` |
| `condiciones_cadena_a` | Yes (at least empty `{"perfiles": []}`) | `CondicionesCadenaAInput` |
| `condiciones_cadena_b` | Yes (at least empty `{"canales": []}`) | `CondicionesCadenaBInput` |
| `condiciones_cadena_c` | Yes (at least empty `{"canales": []}`) | `CondicionesCadenaCInput` |

Keys starting with `_` are silently ignored by `UserInputLoader`.

---

## 4. Field Classification by Layer

### 4.1 Panel de Control (`panel_de_control`)

| Field | Cat | Frontend DTO | Domain Input | Notes |
|-------|-----|-------------|--------------|-------|
| `cliente` | **A** | `PcgInput.cliente_select` / `cliente_nuevo` | `PanelDeControlInput.cliente` | Adapter merges two fields |
| `tipo_cliente` | **A** | `PcgInput.tipo_cliente` | `.tipo_cliente` | "Grupo Aval" / "No Grupo Aval" |
| `linea_negocio` | **A** | `PcgInput.servicio` | `.linea_negocio` | Frontend key is `servicio` |
| `ciudad` | **A** | `PcgInput.ciudad` | `.ciudad` | Drives ICA lookup |
| `sede` | **A** | `PcgInput.localidad` | `.sede` | Falls back to `ciudad` |
| `fecha_inicio` | **A** | `PcgInput.fecha_inicio` | `.fecha_inicio` | "YYYY-MM-DD" |
| `meses_contrato` | **A** | `PcgInput.duracion` | `.meses_contrato` | String in DTO, int in domain |
| `margen` | **A** | `PcgInput.margen` | `.margen` | Auto-scaled: >1 => /100 |
| `op_cont` | **A** | `PcgInput.imprevistos` | `.op_cont` | Contingencia operativa |
| `com_cont` | **A** | — | `.com_cont` | Default 0.0; not in frontend DTO |
| `markup` | **A** | — | `.markup` | Default 0.0; not in frontend DTO |
| `descuento` | **A** | — | `.descuento` | Default 0.0; not in frontend DTO |
| `periodo_pago_dias` | **A** | `PcgInput.periodo_pago` | `.periodo_pago_dias` | String→days mapping in adapter |
| `activa_financiacion` | **A** | `PcgInput.financiacion` | `.activa_financiacion` | "Si"/"No" → bool |
| `antiguedad_cliente` | **A** | — | `.antiguedad_cliente` | Default empty string |
| `componente_indexacion_humano` | **A** | `PcgInput.comp_humano` | `.componente_indexacion_humano` | "IPC", "SMLV", etc. |
| `componente_indexacion_tecnologico` | **A** | `PcgInput.comp_tec` | `.componente_indexacion_tecnologico` | |
| `tasa_ica` | **A** | `PcgInput.ica` | `.tasa_ica` | Optional override; None => lookup |
| `tasa_gmf` | **A** | `PcgInput.gmf` | `.tasa_gmf` | Optional override; None => lookup |
| `tasa_mensual_financ` | **A** | `PcgInput.tasa_interes` | `.tasa_mensual_financ` | Auto-scaled |
| `pct_rotacion` | **A** | `PcgInput.rotacion` | `.pct_rotacion` | Auto-scaled; None => lookup |
| `pct_ausentismo` | **A** | `PcgInput.ausentismo` | `.pct_ausentismo` | Auto-scaled; None => lookup |
| `aplica_ley_1819` | **A** | — | `.aplica_ley_1819` | Default True; only in test fixtures |

**Panel fields in frontend DTO NOT in domain (informational only):**

| Field | Cat | Notes |
|-------|-----|-------|
| `PcgInput.tarifa_cap` | **A** | Used by adapter for cadena A `dias_cap` |
| `PcgInput.crucero` | **A** | Used by adapter for `incluye_crucero` logic |
| `PcgInput.horas_form` | **A** | Training hours override |
| `PcgInput.ciudades_recurso[]` | **A** | Multi-city resource distribution |
| `PcgInput.polizas_fixed[]` | **A** | Fixed policy configuration |
| `PcgInput.polizas_extra[]` | **A** | Extra policies |
| `PcgInput.frecuencia` | **A** | Indexation frequency |
| `PcgInput.mes_ajuste` | **A** | Indexation start month |
| `PcgInput.inbound_cadenas[]` | **A** | Chain activation flags [A, B, C] |
| `PcgInput.inbound[][]` | **A** | Volumetry table inbound |
| `PcgInput.outbound_cadenas[]` | **A** | Chain activation flags [A, B, C] |
| `PcgInput.outbound[][]` | **A** | Volumetry table outbound |
| `PcgInput.escenarios[]` | **A** | Pricing scenarios |
| `PcgInput.reglas[]` | **A** | Business rule selections |

---

### 4.2 Condiciones Cadena A (`condiciones_cadena_a`)

**Container level:**

| Field | Cat | Notes |
|-------|-----|-------|
| `perfiles` | **A** | List of `PerfilCadenaAInput` |

**Per-profile fields:**

| Field | Cat | Frontend DTO | Domain Input | Notes |
|-------|-----|-------------|--------------|-------|
| `nombre` | **A** | `PerfilCdcA.nombre` | `.nombre` | Free-text profile name |
| `rol` | **A** | — | `.rol` | Always "Agente Basico" from adapter |
| `canal` | **A** | `PerfilCdcA.canal` | `.canal` | "WhatsApp", "Correo", etc. |
| `modalidad` | **A** | `PerfilCdcA.modalidad` | `.modalidad` | "Inbound" / "Outbound" |
| `fte` | **A** | `PerfilCdcA.fte` | `.fte` | Number of agents |
| `pct_presencia` | **A** | `PerfilCdcA.pct` | `.pct_presencia` | DTO: 0-100; domain: 0-1 |
| `comision_pct` | **A** | `PerfilCdcA.comision` | `.comision_pct` | DTO: 0-100; domain: 0-1 |
| `salario_base` | **A** | `PerfilCdcA.salario` | `.salario_base` | Optional override; None => parametrization |
| `incluye_examenes` | **A** | Matrix `examenes[]` | `.incluye_examenes` | Derived from cross-product matrix |
| `incluye_seguridad` | **A** | Matrix `seguridad[]` | `.incluye_seguridad` | Derived from cross-product matrix |
| `incluye_crucero` | **A** | — | `.incluye_crucero` | Always True from adapter |
| `dias_cap_inicial` | **A** | `CdcAInput.cap_tarifa` | `.dias_cap_inicial` | Shared across profiles |
| `dias_cap_rotacion` | **A** | `CdcAInput.cap_tarifa` | `.dias_cap_rotacion` | Same as `dias_cap_inicial` |
| `tmo_segundos` | **A** | — | `.tmo_segundos` | Default 0.0; informational |
| `modelo_cobro` | **A** | — | `.modelo_cobro` | Default "Fijo FTE" |
| `pct_fijo` | **A** | — | `.pct_fijo` | Default 1.0 |
| `no_payroll_mensual` | **B** | — | `.no_payroll_mensual` | Excel-derived; default 0.0 |
| `cadena_b_mensual` | **B** | — | `.cadena_b_mensual` | Excel-derived; default 0.0 |
| `costos_financieros_mensual` | **B** | — | `.costos_financieros_mensual` | Excel-derived; default 0.0 |
| `vol_cadena_a_mensual` | **A/B** | — | `.vol_cadena_a_mensual` | K50 denominator; set in test fixtures, derivable from volumetry |
| `_comment` | **C** | — | — | Test metadata; ignored by loader |
| `_k50_contrib` | **C** | — | — | Test metadata; ignored by loader |

---

### 4.3 Condiciones Cadena B (`condiciones_cadena_b`)

**Container level:**

| Field | Cat | Frontend DTO | Domain Input | Notes |
|-------|-----|-------------|--------------|-------|
| `canales` | **A** | Built from `PcgInput.inbound/outbound` | `.canales` | Adapter constructs from volumetry |
| `opex_consumo_variable` | **A** | Built from `CdcBInput.cvar_inbound/outbound` | `.opex_consumo_variable` | |
| `equipo_sm` | **A** | `CdcBInput.esm_equipo[]` | `.equipo_sm` | Only activated members |
| `dispositivos_sm` | **A** | `CdcBInput.esm_disp[]` | `.dispositivos_sm` | Only non-zero entries |
| `inversion_plataforma` | **A** | — | `.inversion_plataforma` | Default 0.0 |
| `fte_equipo_sm` | **A** | `CdcBInput.esm_fte` | `.fte_equipo_sm` | Default 1.0 |
| `amortizar_dispositivos_sm` | **A** | — | `.amortizar_dispositivos_sm` | Default True |
| `_comment` | **C** | — | — | Test metadata |
| `_l50_derivation` | **C** | — | — | Test metadata |

**Per-canal fields (`CanalCadenaBInput`):**

| Field | Cat | Notes |
|-------|-----|-------|
| `nombre` | **A** | "Inbound WhatsApp", "Outbound Correo", etc. |
| `modalidad` | **A** | "Inbound" / "Outbound" |
| `producto` | **A** | Channel type: "WhatsApp", "Correo", etc. |
| `volumen_mensual` | **A** | Monthly volume |
| `activo` | **A** | Default True |
| `opex_fijo` | **A** | Channel-specific fixed OPEX |
| `tarifa_unitaria` | **A** | Variable rate per unit |
| `pct_escalamiento` | **A** | Escalation percentage |
| `costo_escalamiento` | **A** | Escalation cost |

**Per-item fields (`ItemOpexConsumoInput`):**

| Field | Cat | Notes |
|-------|-----|-------|
| `nombre` | **A** | "Consumo Inbound WhatsApp" |
| `producto` | **A** | "WhatsApp", "Token IA", "HITL" |
| `modalidad` | **A** | "Inbound" / "Outbound" |
| `canal` | **A** | Channel name |
| `valor_unitario` | **A** | Unit cost |
| `cantidad` | **A** | Quantity |
| `tipo_cobro` | **A** | Default "Unitario" |

**Per-member fields (`MiembroEquipoSMInput`):**

| Field | Cat | Notes |
|-------|-----|-------|
| `rol` | **A** | "Service Owner", "Platform Admin", etc. |
| `activo` | **A** | Always True (only activated members passed) |
| `pct_dedicacion` | **A** | 0-1 fraction |

**Per-device fields (`DispositivoSMInput`):**

| Field | Cat | Notes |
|-------|-----|-------|
| `tipo` | **A** | Device type string |
| `costo_unitario` | **A** | Unit cost |
| `cantidad` | **A** | Quantity |
| `meses_amortizacion` | **A** | Default 1 |

---

### 4.4 Condiciones Cadena C (`condiciones_cadena_c`)

**Container level:**

| Field | Cat | Frontend DTO | Domain Input | Notes |
|-------|-----|-------------|--------------|-------|
| `canales` | **A** | — | `.canales` | `CanalCadenaCInput` list |
| `equipo_transversal` | **A** | Built from `CdcCInput.rht_deds[]` | `.equipo_transversal` | 14-slot role array |
| `inversion_anual` | **A** | — | `.inversion_anual` | Default 0.0 |

**Per-member fields (`MiembroEquipoTransversalInput`):**

| Field | Cat | Notes |
|-------|-----|-------|
| `rol` | **A** | From 14 predefined roles |
| `activo` | **A** | Always True |
| `pct_dedicacion` | **A** | 0-1 fraction |

---

## 5. Legacy Fixture Format (bancamia_cobranzas.json)

This fixture uses the **internal domain format** (pre-adapter), NOT the API format.
It should NOT be used as an API request template.

| Field | Cat | Notes |
|-------|-----|-------|
| `panel_de_control` | **A** | Subset of panel fields (no ciudad, sede, etc.) |
| `perfiles_cadena_a` | **A** | Direct `PerfilCadenaAInput` format |
| `parametros_nomina` | **B** | **FORBIDDEN in API requests.** Loaded from parametrization. Contains: `tarifa_dia_cap`, `costo_crucero`, `costo_examen_medico`, `costo_estudio_seg`, `pct_aumento_salarial`, `mes_aplicacion_aumento` |
| `parametros_no_payroll` | **B** | **FORBIDDEN.** No-payroll cost tables from parametrization |
| `parametros_cadena_b` | **B** | **FORBIDDEN.** Contains: `costo_personal_sm`, `opex_herramientas_sm`, `costo_personal_hitl`, `opex_herramientas_hitl`, `inversion_mensual`, `pct_aumento_tecnologico` |
| `parametros_cadena_c` | **B** | **FORBIDDEN.** Cadena C parametrization |
| `parametros_calculo` | **B** | **FORBIDDEN.** Contains: `pct_rotacion`, `pct_examen_anual` |
| `validaciones` | **D** | Excel reference values for parity checks |

**`UserInputLoader._validar_no_contiene_maestros()`** already rejects:
- `horas_formacion_mensual`
- `parametros_nomina`
- `parametros_no_payroll`
- `parametros_calculo`

---

## 6. Test Fixture Metadata Fields (Category C/D)

All `_`-prefixed fields in fixtures are **ignored by the loader** but serve as
documentation for test authors and Excel parity auditors.

### Category C — Testing Metadata

| Field | Fixtures | Purpose |
|-------|----------|---------|
| `_comment` | All | Human-readable scenario description |
| `_scenario` | canonical_k50, excel_match, excel_v24 | Scenario label |
| `_purpose` | excel_v24 | Why this fixture exists |
| `_note` | canonical_k50, excel_v24 | Additional notes |
| `_source` | canonical_k50 | Source reference |
| `_descripcion` | seguros_adl | Spanish description |
| `_nota` | seguros_adl | Spanish notes |
| `_k50_expected` | canonical_k50 | Expected K50 value |
| `_l50_expected` | canonical_k50 | Expected L50 value |
| `_part_a_expected` | canonical_k50 | Expected participation A |
| `_part_b_expected` | canonical_k50 | Expected participation B |
| `_cts_a_expected` | canonical_k50 | Expected CTS-A value |
| `_cts_b_expected` | canonical_k50 | Expected CTS-B value |
| `_cts_ponderado_expected` | canonical_k50 | Expected weighted CTS |
| `_expected_discrepancy` | canonical_k50, excel_match | Known SMMLV discrepancy note |
| `_k50_derivation` | excel_v24 | Step-by-step K50 derivation |
| `_k50_detail` | excel_v24 | Detailed K50 breakdown |
| `_l50_derivation` | excel_v24 | Step-by-step L50 derivation |
| `_parametrization_agente_basico` | excel_v24 | Expected agent basic config |
| `_k50_contrib` | (nested in perfiles) | K50 contribution per profile |
| `_l50_derivation` | (nested in cadena_b) | L50 derivation notes |

### Category D — Excel Documentation

| Field | Fixtures | Purpose |
|-------|----------|---------|
| `_excel_smmlv` | canonical_k50, excel_match, excel_v24 | Excel SMMLV value |
| `_backend_smmlv` | canonical_k50, excel_match | Backend SMMLV value |
| `_excel_facturacion_esperada` | whatsapp_only | Expected billing |
| `_excel_payroll_mes1` | whatsapp_only | Excel payroll month 1 |
| `_excel_polizas_mes1` | whatsapp_only | Excel policies month 1 |
| `_excel_ica_mes1` | whatsapp_only | Excel ICA month 1 |
| `_excel_pct_utilidad_steady` | whatsapp_only | Excel utility % steady state |
| `_excel_payroll_a` | webchat_only, correo_only | Excel payroll A |
| `_excel_no_payroll_a` | webchat_only, correo_only | Excel no-payroll A |
| `_excel_cadena_b_total` | webchat_only, correo_only | Excel cadena B total |
| `_excel_comp_fijo_b` | webchat_only, correo_only | Excel fixed component B |
| `_excel_comp_var_b` | webchat_only, correo_only | Excel variable component B |
| `_excel_facturacion` | webchat_only, correo_only | Excel billing |
| `validaciones` | bancamia_cobranzas, seguros_adl | Excel reference validation values |

---

## 7. Derived Fields (Category B) — MUST NOT appear in API requests

These fields are computed by `SimulationContextBuilder` from
`IParametrizationProvider` and user inputs. Sending them in the request is either
ignored or (for forbidden master data) causes a validation error.

### 7.1 Fields computed from parametrization

| Computed Field | Source | Builder Method |
|---------------|--------|----------------|
| `ParametrosNomina.*` | `storage/parametrization/hr/` | `_construir_parametros_nomina()` |
| Salario base per rol | `hr/salarios_por_rol` | Lookup by `perfil.rol` |
| `tarifa_dia_cap` | `hr/cap_training_rates` | Lookup by city |
| `costo_crucero` | `hr/crucero_rates` | Lookup by city |
| `costo_examen_medico` | `hr/medical_exam_rates` | Fixed from parametrization |
| `costo_estudio_seg` | `hr/security_study` | Fixed from parametrization |
| `pct_aumento_salarial` | `hr/salary_increase` | By year of contract |
| No-payroll costs | `hr/no_payroll_costs` | By city + sede |
| Ramp-up curve | `hr/ramp_up` | By meses_contrato |
| Poliza rates | `op/polizas` | By policy type |
| Periodo de pago margen | `op/periodo_pago` | By periodo_pago_dias |
| Cadena B S&M salaries | `hr/salarios_por_rol` | By S&M role |
| Cadena C RHT salaries | `hr/salarios_por_rol` | By transversal role |

### 7.2 Fields that are output-only (NOT inputs)

These are result fields from `PricingResult` and MUST NEVER appear in requests:

- `kpis` — `KPIsDeal` with TIR, VAN, payback, etc.
- `pyg_por_mes` — Monthly P&G statements
- `cost_to_serve` — CTS breakdowns by chain and channel
- `vision_tarifas` — Rate vision with K50/L50 derivations
- `waterfall` — `WaterfallPromedio` averages
- `reglas_negocio` — Business rule evaluation results
- `evaluacion_riesgo` — Risk assessment results
- `vision_pyg` — Structured P&G for frontend display

---

## 8. Problematic Fields — Action Items

### 8.1 `vol_cadena_a_mensual` (A/B hybrid)

**Current state:** Present in test fixtures as a user input field. In the
`UnifiedInputAdapter`, it is NOT set (default 0.0) because the frontend does
not expose it. It is only set in test fixtures that use the `UserInputLoader`
path (domain-format JSON).

**Risk:** The K50/CTS calculation depends on this value for inbound profiles.
If the frontend path never sets it, CTS_A will always be 0 for the frontend flow.

**Recommendation:** This should be computed in `SimulationContextBuilder` from
the volumetry tables (`inbound[][]` column totals minus cadena B automation).
Move to category **B** (derived).

### 8.2 `no_payroll_mensual`, `cadena_b_mensual`, `costos_financieros_mensual`

**Current state:** Present in `PerfilCadenaAInput` as domain fields (default 0.0).
Only populated in test fixtures for Excel parity. The `UnifiedInputAdapter` does
not set them.

**Recommendation:** These are Excel-derived reference values used for CTS
calculations. They should be computed by the builder or the CTS calculator, not
passed as inputs. Move to category **B** (derived) or remove entirely.

### 8.3 Legacy fixture format (bancamia_cobranzas.json)

**Current state:** Uses internal domain format with embedded parametrization
(`parametros_nomina`, `parametros_no_payroll`, etc.).

**Recommendation:** Migrate to the canonical format (`condiciones_cadena_a/b/c`)
or move to a separate `test_cases/legacy/` directory.

### 8.4 `CalculationRequest.user_input: Dict[str, Any]`

**Current state:** Completely untyped. Accepts any JSON structure.

**Recommendation:** Replace with a typed `SimulationRequest` Pydantic model that
validates required sections and field types at the API boundary.

---

## 9. Fixture Inventory Summary

| Fixture File | Format | Chains Used | Category |
|-------------|--------|-------------|----------|
| `bancamia_cobranzas.json` | Legacy (domain) | A, B, C | **Migrate** |
| `bancamia_canonical_k50.json` | Canonical | A, B, C | OK |
| `bancamia_excel_match.json` | Canonical | A, B, C | OK |
| `bancamia_whatsapp_only.json` | Canonical | A, B, C | OK |
| `bancamia_webchat_only.json` | Canonical | A, B, C | OK |
| `bancamia_correo_only.json` | Canonical | A, B, C | OK |
| `seguros_adl_cobranzas.json` | Canonical | A, B, C | OK |
| `excel_v24_canonical_bancamia.json` | Canonical | A, B, C | OK (golden) |
| `fixtures/.../bancamia_12m_input.json` | Mixed (domain) | A, B, C | **Migrate** |

---

## 10. Validator Coverage

| Validator | Location | Fields Validated |
|-----------|----------|-----------------|
| `PanelValidator` | `simulation/panel/validator.py` | servicio, fecha_inicio, ciudad (warn), duracion, ciudades_recurso sum |
| `ChainAValidator` | `simulation/chain_a/validator.py` | nombre (warn), fte > 0, opex.costo >= 0 (warn), inv.meses > 0 |
| `ChainBValidator` | `simulation/chain_b/validator.py` | opex.costo >= 0 (warn), inv.meses > 0, dedicacion >= 0 if activated |
| `ChainCValidator` | `simulation/chain_c/validator.py` | cvar.valor >= 0 (warn), integ.costo >= 0 (warn), capex.meses > 0 |
| `UserInputLoader` | `adapters/user_input_loader.py` | Rejects forbidden master data fields |

**Gap:** No validator exists at the `CalculationRequest` level. Validation only
happens deep in the pipeline (loader rejects master data; individual chain
validators only run on DTO save, not on calculate).

---

## 11. Recommended Phase 2 Actions

1. **Define `SimulationRequest` DTO** — typed Pydantic model replacing
   `Dict[str, Any]` in `CalculationRequest`.

2. **Create `SimulationRequestValidator`** — validates required sections,
   field ranges, and rejects derived/metadata fields at the API boundary.

3. **Create `DerivedOperationalMetricsBuilder`** — computes `vol_cadena_a_mensual`,
   `no_payroll_mensual`, `cadena_b_mensual`, `costos_financieros_mensual` from
   engine outputs, removing them from input surface.

4. **Separate fixtures** — `test_cases/api_requests/` (clean API format) vs.
   `test_cases/excel_certification/` (with `_` metadata and `validaciones`).

5. **Add validation tests** — 10+ tests covering valid/invalid requests,
   rejected derived fields, missing sections, range violations.
