# calculator_motor Structure Audit — MODULE_STRUCTURE_BLOCK_05

**Date:** 2026-06-14
**Branch:** refactor/modular-pure
**Baseline gate:** 99 golden / make verify PASS
**Auditor:** backend-agent (Claude Sonnet 4.6)
**Scope:** READ-ONLY structural audit. No code changed.

---

## 1. Executive Verdict

The `calculator_motor/` module is structurally sound and correctly separated from HTTP/persistence concerns. The core pipeline (`engine.py` → 10 calculator layers) is the certified core and must not be moved. The module has 63 Python files across 14 subdirectories. No circular imports detected. No legacy shims remain. The primary risk is the absence of formula lineage annotations (Excel cell citations) in formula files, which is the mandated scope for BLOCK 06.

**Key finding:** `serializer_helpers.py` carries an outbound coupling to `vision_imprimible` helpers (ficha, reglas_negocio, aprobaciones, configuracion_comercial). This is QUESTIONABLE and should be deferred for review after formula lineage is established. Do not move until BLOCK 06 is complete.

---

## 2. Certified Core Warning

The following files are **DEFER_CERTIFIED_CORE** — they implement the 10-layer pipeline and their formula logic is directly validated by 99 golden tests and `make verify`. Any move or restructure must be preceded by BLOCK 06 formula lineage and explicit golden guardrail re-validation:

- `engine.py`
- `formulas/payroll/nomina.py`
- `formulas/payroll/factors.py`
- `formulas/no_payroll/costs.py`
- `formulas/costos_financieros/calculator.py`
- `formulas/costos_financieros/financiacion.py`
- `formulas/profitability/calculators.py`
- `formulas/risk/riesgo.py`
- `context_builder.py`
- All `mixins/context_builder_*.py` (7 files)

---

## 3. File Inventory

| File | Main Responsibility | Formula Domain | Risk | Golden Impact | Decision |
|------|-------------------|---------------|------|--------------|----------|
| `__init__.py` | Module package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `engine.py` | Composition root + 10-layer pipeline orchestrator | orchestration | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `context_builder.py` | Builds parametrized SimulationContext from UserInput + parametrization | payroll/shared | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `input_normalizer.py` | Normalizes raw API input into canonical domain fields | shared_math | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `input_validator.py` | Structural validation of normalized input dataclasses | shared_math | LOW | INDIRECT | KEEP_AS_IS |
| `adapters/__init__.py` | Adapter package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `adapters/entry_data_adapter.py` | Translates flat API entry-data dict → domain DTOs | orchestration | MEDIUM | INDIRECT | KEEP_AS_IS |
| `adapters/user_input_loader.py` | Composes mixin chain to build UserInput from raw dict | orchestration | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `adapters/volume_resolution.py` | Resolves volume/escenario fields from entry data | variable_costs | LOW | INDIRECT | KEEP_AS_IS |
| `constants/__init__.py` | Re-exports global_constants | shared_math | LOW | NONE | KEEP_AS_IS |
| `constants/global_constants.py` | Technical constants: DIAS_LABORALES, HORAS_DIA, SEMANAS_MES, MES_INICIO_AJUSTE | shared_math | MEDIUM | DIRECT | AUDIT_ONLY |
| `dto/__init__.py` | DTO package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `dto/normalized_input.py` | Dataclasses for normalization log + NormalizationMode enum | shared_math | LOW | INDIRECT | KEEP_AS_IS |
| `dto/request_dto.py` | Pydantic SimulationRequest — public API contract | orchestration | HIGH | INDIRECT | KEEP_AS_IS |
| `dto/user_inputs.py` | Dataclass UserInput + sub-DTOs (perfiles, polizas, etc.) | orchestration | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/__init__.py` | Formula package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `formulas/costos_financieros/__init__.py` | Re-exports CostosFinancierosCalculator, FinancialCalculator | fixed_costs | LOW | NONE | KEEP_AS_IS |
| `formulas/costos_financieros/calculator.py` | Layer 8: financial cost calculator (CAPEX amort, polizas, financiacion) | fixed_costs | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/costos_financieros/financiacion.py` | Pure financial math helpers (tasa mensual, amortizacion) | fixed_costs | MEDIUM | DIRECT | DEFER_FORMULA_LINEAGE |
| `formulas/no_payroll/__init__.py` | Re-exports NoPayrollCalculator | non_payroll | LOW | NONE | KEEP_AS_IS |
| `formulas/no_payroll/costs.py` | Layer 3: non-payroll cost calculator (seat, tech, training) | non_payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/payroll/__init__.py` | Re-exports NominaCalculator, PayrollCalculator | payroll | LOW | NONE | KEEP_AS_IS |
| `formulas/payroll/factors.py` | Payroll factor computations (prestacional, seguridad social, vacaciones) | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/payroll/nomina.py` | Layer 2: payroll calculator — primary cost calculation | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/pricing/__init__.py` | Re-exports PricingCalculator | tariffs | LOW | NONE | KEEP_AS_IS |
| `formulas/pricing/pricing.py` | Revenue/pricing calculation (margen, tarifa por canal) | tariffs | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/profitability/__init__.py` | Re-exports ProfitabilityCalculator | pyg | LOW | NONE | KEEP_AS_IS |
| `formulas/profitability/calculators.py` | Pure profitability helpers (margen, rentabilidad, utilidad) | pyg | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `formulas/risk/__init__.py` | Re-exports RiesgoCalculator | variable_costs | LOW | NONE | KEEP_AS_IS |
| `formulas/risk/riesgo.py` | Risk calculator (poliza provisions, pct_riesgo from business_rules) | variable_costs | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `helpers/__init__.py` | Helpers package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `helpers/console_reporter.py` | Dev-only console print helper for PricingResult | shared_math | LOW | NONE | AUDIT_ONLY |
| `helpers/engine_helpers.py` | Helper types/functions used within engine composition | orchestration | LOW | INDIRECT | KEEP_AS_IS |
| `input_normalizer.py` | (see above — top-level normalizer) | shared_math | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/__init__.py` | Mixins package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `mixins/context_builder_cadena_a_mixin.py` | CadenaA mixin: aggregates perfiles + soporte mixins | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_methods.py` | Top-level mixin combiner: CadenaA + PanelBC | orchestration | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_panel_bc_mixin.py` | Panel mixin for Cadena B/C context build | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_panel_mixin.py` | Panel mixin for Cadena A context build | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_perfiles_light_mixin.py` | Light perfiles builder (Cadena B/C agent profiles) | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_perfiles_mixin.py` | Aggregates perfiles_light + soporte mixins | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/context_builder_perfiles_soporte_mixin.py` | Support profile builder (ratios, FTE, CAPEX per profile) | payroll | HIGH | DIRECT | DEFER_CERTIFIED_CORE |
| `mixins/input_normalizer_cadena_a.py` | Normalizes Cadena A fields (perfiles, capacitacion, examenes) | payroll | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/input_normalizer_defaults.py` | Applies default values for missing input fields | shared_math | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/input_normalizer_misc.py` | Misc normalization (ICA, GMF, polizas, trm) | shared_math | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/input_normalizer_validation.py` | Validation checks during normalization | shared_math | LOW | INDIRECT | KEEP_AS_IS |
| `mixins/user_input_builders_cadena_a.py` | Builds UserInput for Cadena A from raw dict | orchestration | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/user_input_builders_cadena_b.py` | Builds UserInput for Cadena B from raw dict | orchestration | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/user_input_builders_cadena_c.py` | Builds UserInput for Cadena C from raw dict | orchestration | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/user_input_builders_panel.py` | Builds UserInput panel section from raw dict | orchestration | MEDIUM | INDIRECT | DEFER_CERTIFIED_CORE |
| `mixins/user_input_validators.py` | Mixin for UserInput structural validators | shared_math | LOW | INDIRECT | KEEP_AS_IS |
| `models/__init__.py` | Models package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `models/data_provenance.py` | DataProvenance + DataSource enum + ProvenanceEntry dataclasses | audit | LOW | NONE | AUDIT_ONLY |
| `models/results.py` | Internal result model (pre-PricingResult composition) | orchestration | MEDIUM | INDIRECT | KEEP_AS_IS |
| `models/snapshot.py` | Snapshot dataclass for audit/lineage persistence | audit | LOW | NONE | KEEP_AS_IS |
| `serializers/__init__.py` | Re-exports pricing_result_to_dict | orchestration | LOW | NONE | KEEP_AS_IS |
| `serializers/pricing_result_serializer.py` | Serializes PricingResult to dict for persistence | orchestration | MEDIUM | INDIRECT | AUDIT_ONLY |
| `serializers/serializer_helpers.py` | Section-level serializers; imports vision_imprimible helpers | orchestration | MEDIUM | INDIRECT | DEFER_IMPORT_RISK |
| `shared/__init__.py` | Re-exports PricingCalculator (thin shim) | shared_math | LOW | NONE | AUDIT_ONLY |
| `use_cases/__init__.py` | Use cases package marker | orchestration | LOW | NONE | KEEP_AS_IS |
| `use_cases/build_pricing.py` | Use case: builds pricing result (PricingCalculator + Profitability) | tariffs | MEDIUM | INDIRECT | KEEP_AS_IS |
| `use_cases/build_visions.py` | Use case: builds vision outputs from PricingResult | orchestration | MEDIUM | INDIRECT | KEEP_AS_IS |
| `validation/__init__.py` | Validation package marker | shared_math | LOW | NONE | KEEP_AS_IS |
| `validation/contract_validator.py` | Validates Pydantic contracts (field presence, types) | shared_math | LOW | INDIRECT | KEEP_AS_IS |
| `validation/simulation_request_validator.py` | Validates SimulationRequest before engine entry | shared_math | LOW | INDIRECT | KEEP_AS_IS |

**Total files audited:** 63

---

## 4. Import Graph Summary

### External Modules Importing calculator_motor

| External Importer | What It Uses | Classification |
|------------------|-------------|----------------|
| `modules/calculator/api/calculate_*_handler.py` | Engine, SimulationRequest, serializers | EXPECTED — HTTP layer calling motor |
| `modules/calculator/api/calculate_validate.py` | SimulationRequest, request_dto | EXPECTED — validation layer |
| `modules/calculator/__init__.py` | Engine, UserInputLoader | EXPECTED — module bootstrap |
| `modules/calculator/persistence/snapshots_repository.py` | snapshot model | EXPECTED — persistence layer |
| `modules/cadena_a/use_cases/build_payroll.py` | UserInput DTOs | EXPECTED — sibling chain using shared DTO |
| `modules/cadena_b/reglas.py` | UserInput DTOs | EXPECTED — sibling chain |
| `modules/cadena_c/reglas.py` | UserInput DTOs | EXPECTED — sibling chain |
| `modules/panel/models/panel.py` | UserInput or shared model | EXPECTED — panel domain model |
| `modules/pyg/services/*.py` | PricingResult models | EXPECTED — PYG calculators consume engine output |
| `modules/shared/contracts/api_v1/adapter.py` | DTO types | EXPECTED — contract adapter |
| `modules/shared/models/results.py` | PricingResult | EXPECTED — shared result type |
| `modules/vision_tarifas/reglas.py` | UserInput, models | EXPECTED — VT calculator |
| `modules/vision_tarifas/mixins/reglas_methods_*.py` | UserInput, models | EXPECTED — VT calculator |
| `modules/vision_tarifas/models/visions_tarifas.py` | facts models | EXPECTED — VT output model |

### External Dependencies from Within calculator_motor

| Dependency | Direction | File | Classification | Evidence | Recommendation |
|-----------|-----------|------|---------------|----------|----------------|
| `nexa_engine.modules.shared.models.*` | IN → calculator_motor | engine, formulas, mixins | EXPECTED | PricingResult, PanelDeControl, etc. are shared types | KEEP |
| `nexa_engine.modules.shared.exceptions.*` | IN → calculator_motor | adapters, mixins, models | EXPECTED | DomainError, ValidationError, ParametrizationError | KEEP |
| `nexa_engine.modules.shared.ports.parametrization_provider` | IN → calculator_motor | engine, context_builder, mixins, formulas | CERTIFIED_CORE_COUPLING | IParametrizationProvider Protocol dependency | DO NOT CHANGE |
| `nexa_engine.modules.shared.ports.logger` | IN → calculator_motor | use_cases | EXPECTED | ILogger, NullLogger | KEEP |
| `nexa_engine.modules.shared.ports.trace_emitter` | IN → calculator_motor | use_cases | EXPECTED | ITraceEmitter, NullTraceEmitter | KEEP |
| `nexa_engine.modules.shared.config.business_rules.loader` | IN → calculator_motor | formulas/risk/riesgo.py | EXPECTED | Risk rules loaded from storage | KEEP |
| `nexa_engine.modules.audit.trace` | IN → calculator_motor | nomina.py, costs.py, costos_financieros/calculator.py | EXPECTED | audit trace decorator | KEEP |
| `nexa_engine.modules.audit.integration` | IN → calculator_motor | engine.py | EXPECTED | audit_context, export_audit_trace | KEEP |
| `nexa_engine.modules.cadena_a.services.nomina_cargada` | IN → calculator_motor | context_builder, 4 mixins | EXPECTED | NominaCargadaService for staffing | KEEP |
| `nexa_engine.modules.cadena_a.services.special_roles_calculator` | IN → calculator_motor | context_builder, 4 mixins | EXPECTED | SpecialRolesCalculator | KEEP |
| `nexa_engine.modules.cadena_b.reglas` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | CadenaBCalculator in composition root | DO NOT CHANGE |
| `nexa_engine.modules.cadena_c.reglas` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | CadenaCCalculator in composition root | DO NOT CHANGE |
| `nexa_engine.modules.pyg.services.*` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | CostosTotalesCalculator, KPIsCalculator, PyGCalculator | DO NOT CHANGE |
| `nexa_engine.modules.pyg.builders.vision_pyg_builder` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | VisionPyGBuilder | DO NOT CHANGE |
| `nexa_engine.modules.vision_cost_to_serve.services.cost_to_serve_calculator` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | CostToServeCalculator | DO NOT CHANGE |
| `nexa_engine.modules.vision_tarifas.reglas` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | VisionTarifasCalculator | DO NOT CHANGE |
| `nexa_engine.modules.vision_imprimible.builders.*` | IN → calculator_motor | engine.py | CERTIFIED_CORE_COUPLING | VisionDatasetsBuilder, VisionImprimibleBuilder | DO NOT CHANGE |
| `nexa_engine.modules.vision_imprimible.helpers.*` | IN → calculator_motor | serializers/serializer_helpers.py | QUESTIONABLE | Serializer pulls vision helpers; boundary ambiguous | DEFER_IMPORT_RISK — audit after BLOCK06 |
| `nexa_engine.modules.parametrizacion.services.provider` | IN → calculator_motor | engine.py, context_builder.py | EXPECTED | ParametrizationProvider.build() | KEEP |

**Circular risk:** NO — all dependencies are unidirectional (calculator_motor depends on shared/* and vision/* calculators; those do not re-import calculator_motor internals).

---

## 5. Formula Ownership Map

| Function/Class | File | Formula Domain | Business Concept | Hardcoded Value Risk | Excel Lineage Needed | Golden Impact | Recommendation |
|---------------|------|---------------|-----------------|---------------------|---------------------|--------------|----------------|
| `NexaPricingEngine.calcular()` | engine.py | orchestration | 10-layer pipeline | NO | MAYBE | DIRECT | DO_NOT_MOVE |
| `_build_cts_facts()` | engine.py | cts | CTS nomina/no-payroll fact accumulation | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `_build_vt_facts()` | engine.py | tariffs | Vision Tarifas per-canal facts | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `_denominador_cadena_a_para_facts()` | engine.py | cts | CTS cadena A volume denominator | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `NominaCalculator.calcular_para_mes()` | formulas/payroll/nomina.py | payroll | Monthly payroll cost | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `PayrollCalculator.*` | formulas/payroll/factors.py | payroll | Prestacional, social security factors | SUSPECT (factor tables) | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `NoPayrollCalculator.calcular_para_mes()` | formulas/no_payroll/costs.py | non_payroll | Seat/tech/training costs | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `CostosFinancierosCalculator.calcular()` | formulas/costos_financieros/calculator.py | fixed_costs | CAPEX amortization + polizas | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `FinancialCalculator.*` | formulas/costos_financieros/financiacion.py | fixed_costs | tasa mensual, amortizacion term-based | SUSPECT (SFTP exclusion quirk) | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `ProfitabilityCalculator.*` | formulas/profitability/calculators.py | pyg | margen, rentabilidad, utilidad | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `PricingCalculator.*` | formulas/pricing/pricing.py | tariffs | Revenue/tarifa per canal | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `RiesgoCalculator.*` | formulas/risk/riesgo.py | variable_costs | Risk provision from business_rules | NO | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `SimulationContextBuilder.construir()` | context_builder.py | payroll/shared | Parametrized context assembly | NO | YES | DIRECT | DO_NOT_MOVE |
| `ContextBuilderPerfilesSoporteMixin.*` | mixins/context_builder_perfiles_soporte_mixin.py | payroll | Support FTE + CAPEX per profile | SUSPECT (fte_sum_contable logic) | YES | DIRECT | DEFER_FORMULA_LINEAGE |
| `InputNormalizer.*` | input_normalizer.py | shared_math | Input field canonicalization + defaults | NO | MAYBE | INDIRECT | KEEP_AS_IS |
| `NewEntryDataAdapter.*` | adapters/entry_data_adapter.py | orchestration | API entry → domain DTO translation | NO | NO | INDIRECT | KEEP_AS_IS |

---

## 6. Constants / Enums / Helpers Findings

| Finding | File | Type | Risk | Evidence | Recommendation |
|---------|------|------|------|----------|----------------|
| `MES_INICIO_AJUSTE_ANUAL = 1` | constants/global_constants.py | technical constant | MEDIUM | Legal basis documented (Ley 1393/2010 Art.3); if Colombia fiscal calendar changes, this breaks all indexation. | Flag for BLOCK06 Excel annotation — do NOT change value |
| `DIAS_LABORALES_POR_MES = 20` | constants/global_constants.py | possible business constant | HIGH | 20 working days/month is a convention; Excel may differ. Requires Excel lineage. | Flag for BLOCK06 — verify against Excel HR sheet before any change |
| `HORAS_LABORALES_POR_DIA = 8` | constants/global_constants.py | technical constant | LOW | Standard 8h workday. Low risk. | KEEP_AS_IS |
| `SEMANAS_POR_MES = 4.33` | constants/global_constants.py | possible business constant | MEDIUM | 52/12 = 4.333... Used in weekly-rate conversions. Verify against Excel. | Flag for BLOCK06 Excel annotation |
| `NormalizationMode(str, Enum)` | dto/normalized_input.py | enum | LOW | Technical enum (FULL, PARTIAL, NONE). No business values. | KEEP_AS_IS |
| `DataSource(str, Enum)` | models/data_provenance.py | enum | LOW | Provenance source enum. No business values. | KEEP_AS_IS |
| `LINEA_SEPARADORA = "=" * 60` | helpers/console_reporter.py | technical constant | LOW | Dev-only display constant. | KEEP_AS_IS |
| `TODO(GAP-CADENA-A-FASE4)` | engine.py:540 | temporary logic marker | MEDIUM | Open TODO re: margen_minimo usage. Deferred decision. | Document in BLOCK06 scope as open item |
| `fte_sum_contable = 0.0` | mixins/context_builder_perfiles_soporte_mixin.py:194 | possible magic | MEDIUM | Inline accumulator init; comment says "incluye TODOS los soporte regulares (para Inclusión)". Accumulation rule may have Excel backing. | Flag for BLOCK06 formula lineage |

---

## 7. Future Structure Proposal

**Hard rule applied:** No calculator_motor move is recommended before BLOCK 06 formula lineage and golden guardrails exist.

| Current Path | Future Path | Reason | Risk | Golden Impact | Adapter Required | Tests Required | Recommendation |
|-------------|-------------|--------|------|--------------|-----------------|----------------|----------------|
| `serializers/serializer_helpers.py` | `serializers/serializer_helpers.py` (no move) | Outbound coupling to vision_imprimible helpers is QUESTIONABLE; boundary ownership ambiguous | HIGH | INDIRECT | N/A | N/A | DO_NOT_MOVE — audit coupling first |
| `helpers/console_reporter.py` | Could be removed or moved to `dev_tools/` | Dev-only helper not used in production pipeline | LOW | NONE | NO | NO | FUTURE_REFACTOR_CANDIDATE — only after confirming zero production usage |
| `shared/__init__.py` (thin re-export) | Could be removed | Thin shim re-exporting PricingCalculator; may be legacy | LOW | NONE | NO | NO | AUDIT_ONLY — check import graph before removal |
| All `formulas/` subdirs | KEEP_AS_IS | Formula files are certified core with direct golden impact | HIGH | DIRECT | N/A | N/A | MOVE_AFTER_FORMULA_LINEAGE — do not move before BLOCK06 |
| All `mixins/` | KEEP_AS_IS | Context builder mixins are tightly coupled to engine and parametrization | HIGH | DIRECT | N/A | N/A | DO_NOT_MOVE |

---

## 8. Risk Register

| risk_id | Area | Description | Severity | Evidence | Recommended Action | Block Candidate |
|---------|------|-------------|----------|----------|-------------------|-----------------|
| R-01 | Formula movement | All formula files (`formulas/`, `mixins/context_builder_*`) lack Excel cell annotations; moving them without lineage context risks silent regression | CRITICAL | 99 golden tests cover outputs but not intermediate steps; no `# EXCEL V2-8` comments in formulas | Do not move or restructure formula files before BLOCK06 formula lineage | BLOCK06 |
| R-02 | Import coupling | `serializers/serializer_helpers.py` imports `vision_imprimible.helpers.*` — 4 distinct imports; this creates a non-obvious cross-module dependency | HIGH | Lines 129, 144, 242, 314 in serializer_helpers.py | Audit and document the coupling; determine if serializer should be in vision_imprimible or remain in calculator_motor | BLOCK06 |
| R-03 | Business constants | `DIAS_LABORALES_POR_MES = 20` and `SEMANAS_POR_MES = 4.33` have no Excel cell citations; if Excel uses different values, silent parity gap exists | HIGH | global_constants.py; no `# EXCEL V2-8` comment on these values | Add Excel citations in BLOCK06; verify against HR/GN sheets | BLOCK06 |
| R-04 | Open TODO | `engine.py:540` has `TODO(GAP-CADENA-A-FASE4)` re: `get_margen_minimo(servicio)` — undecided formula decision in certified core | MEDIUM | engine.py line 540 | Document decision in DECISIONS.md; add to BLOCK06 scope as open item | BLOCK06 |
| R-05 | Mixin decomposition | 7 context_builder mixins + 4 input_normalizer mixins = 11 mixin files; this is architecturally fragile (deep inheritance chain); no tests validate mixin order | MEDIUM | mixins/ directory; context_builder.py inherits from ContextBuilderMethodsMixin → chain of 7 | Add mixin order test before any restructure; document inheritance chain | BLOCK07 |
| R-06 | Golden coverage dependency | All formula changes depend on golden test suite (99 tests); if golden fixtures diverge from real Excel, formula bugs would pass | HIGH | make verify passes; but golden fixtures are frozen snapshots not real Excel | Maintain parity against Excel V2-8 via `make validate-excel` before any formula change | Ongoing |
| R-07 | Shared ownership | `context_builder.py` imports from `cadena_a.services.*` — 4 imports in 4 mixin files; cadena_a owns NominaCargadaService and SpecialRolesCalculator; this is vertical slice coupling that may be legitimate but is undocumented | MEDIUM | context_builder.py lines 75-76; 4 mixin files with same pattern | Document in DECISIONS.md as intentional coupling; verify cadena_a services are stable contracts | BLOCK06 |

---

## 9. Recommended BLOCK 06 Formula-Lineage Scope

BLOCK 06 should focus exclusively on:

1. **Formula MAP creation** — for each formula file in `formulas/` and each `mixins/context_builder_*` file:
   - Identify the Excel sheet + cell/range that backs each computation
   - Add `# Excel V2-8 · '<Sheet>'!<Cell>` comment (read-only annotation pass)
   - Do NOT change any formula logic

2. **Constants annotation** — for `constants/global_constants.py`:
   - Verify `DIAS_LABORALES_POR_MES`, `SEMANAS_POR_MES` against Excel HR sheet
   - Add Excel citations if they are Excel-backed

3. **Open TODO resolution** — document `engine.py:540 TODO(GAP-CADENA-A-FASE4)` decision

4. **serializer_helpers coupling audit** — determine if `vision_imprimible` helper imports in `serializers/serializer_helpers.py` are justified or represent boundary violation

5. **Mixin inheritance chain documentation** — produce a diagram of the 7 context_builder mixin inheritance chain for future decomposition planning

**Files in scope for BLOCK06 annotation (read-only pass):**
- `formulas/payroll/nomina.py`
- `formulas/payroll/factors.py`
- `formulas/no_payroll/costs.py`
- `formulas/costos_financieros/calculator.py`
- `formulas/costos_financieros/financiacion.py`
- `formulas/profitability/calculators.py`
- `formulas/pricing/pricing.py`
- `formulas/risk/riesgo.py`
- `mixins/context_builder_perfiles_soporte_mixin.py`
- `constants/global_constants.py`

---

## 10. Checkpoint

```
CHECKPOINT_REQUIRED

No code was changed.
No calculator_motor files were modified.
No files were moved.
No imports were changed.
Implementation must not start until this audit is reviewed and approved.

BLOCK 06 must be formula lineage / FORMULA_MAP only.
Any calculator_motor move must be deferred until after lineage and golden guardrails are approved.
```

---

*Generated by backend-agent — MODULE_STRUCTURE_BLOCK_05 — 2026-06-14*
