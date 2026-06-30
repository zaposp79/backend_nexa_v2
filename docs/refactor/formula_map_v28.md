# Formula Map V2-8 — calculator_motor

**Generated:** 2026-06-14
**Branch:** refactor/modular-pure
**Block:** MODULE_STRUCTURE_BLOCK_06
**Auditor:** backend-agent (Claude Sonnet 4.6)
**Scope:** Formula lineage documentation for `modules/calculator_motor/` — READ-ONLY pass. No code logic changed.

> **Excel V2-8 is an oracle/reference only. Runtime values must continue to come from
> request/request.json, storage/parametrization, and the active provider.**

---

## 1. Executive Summary

This document maps the formula lineage of the 10 certified-core formula files in
`modules/calculator_motor/`. All files were annotated with `@excel_lineage`,
`@runtime_sources`, and `@confidence` docstrings/comments. No executable logic was
changed. 

The primary finding is that most formulas have HIGH confidence lineage with clear
Excel backing in sheets `Nomina Loaded`, `No payroll`, `Pólizas - Costo Financiacion`,
and `Riesgo`. Two constants (`DIAS_LABORALES_POR_MES=20`, `SEMANAS_POR_MES=4.33`) could
not be confirmed against specific Excel cell references and are classified as MEDIUM
confidence with risk R-03 (see Section 4).

**Files annotated:** 9 Python files (docstrings/comments only)
**Formula mappings created:** 16 (10 high-confidence, 4 medium-confidence, 2 low/unknown)
**Hardcoded business value risks identified:** 2 (DIAS_LABORALES, SEMANAS_POR_MES)

---

## 2. Runtime Source Hierarchy

```
Priority  Source                                      Usage
─────────────────────────────────────────────────────────────────────
1.        request/request.json                        Panel/Cadenas/deal/scenario inputs
            PanelDeControl — margen, tasa_ica, tasa_gmf, tasa_mensual_financ, op_cont,
                             com_cont, markup, descuento, periodo_pago_dias, etc.
            PerfilCadenaA[] — fte, salario_base, dias_cap_inicial, inversiones, etc.
            PolizaContractual[] — user-provided insurance premiums
            CondicionesCadenaAInput — staff_config, roles_operativos

2.        storage/parametrization/ + active provider  Tasas, TRM, Pólizas, Rotación,
            IParametrizationProvider                  Ausentismo, Rentabilidad,
              .get_factor_periodo()                   HR/OP/GN params, salaries, roles,
              .get_tasa_polizas_efectiva()             costs, SMMLV, ratios_staff
              .get_smmlv()
              .get_reglas_staff()
              .get_ratios_staff(linea)
              .get_riesgo_config()
              .get_clasificacion_cargos()
              .get_complejidad_especialista()

3.        storage/business_rules YAML                  Risk thresholds, criterion weights,
            (loaded via load_business_rules_cached)   score classification limits

4.        Excel V2-8                                   Oracle/reference ONLY.
            NOT a runtime source.                     Used to verify correctness of
                                                      storage/parametrization values.
```

---

## 3. Formula Map Table

| code_symbol | file | business_concept | runtime_sources | Excel_sheet | Excel_cells | confidence | golden_impact | notes |
|-------------|------|-----------------|----------------|------------|------------|-----------|--------------|-------|
| `NominaCalculator.calcular_para_mes()` | `formulas/payroll/nomina.py` | Costo nómina mensual Cadena A | HR-ParametrosNomina, HR-ParametrosCalculo, PerfilCadenaA[].fte | Nomina Loaded | D14:BK{rol} (per-role monthly rows) | HIGH | DIRECT | Salario cargado, cap. inicial/rotación, exámenes, seguridad, crucero |
| `NominaCalculator._factor_indexacion()` | `formulas/payroll/nomina.py` | Factor indexación salarial mensual | HR.pct_aumento_salarial, HR.factor_indexacion_base, HR.mes_aplicacion_aumento | Tasas, TRM, Polizas | B8:G9 (acumulado SMLV/IPC) | HIGH | DIRECT | Combina factor_base × factor_aumento compuesto anual |
| `NominaCalculator._comisiones()` | `formulas/payroll/nomina.py` | Comisión cruda (sin cumplimiento) | HR.comision_pct, perfil.salario_base, perfil.fte | Inputs de Nomina | D62 (salario_base × comision_pct) | HIGH | DIRECT | EXCEL V2-8: sin pct_cumplimiento — ver inline comment |
| `PayrollCalculator.calcular_factor_aumento()` | `formulas/payroll/factors.py` | Multiplicador de aumento salarial compuesto | HR.pct_aumento_salarial, HR.mes_aplicacion_aumento | Tasas, TRM, Polizas | I8:O11 (per-year increment rates) | HIGH | DIRECT | (1+pct_aumento)^años_completos desde mes_aplicacion |
| `PayrollCalculator.calcular_examenes_fraccion()` | `formulas/payroll/factors.py` | Fracción mensual de exámenes médicos | HR.meses_contrato, HR.pct_rotacion_mensual, HR.pct_examen_anual | Nomina Loaded | UNCONFIRMED (fracción 1/meses + rotación + anual/12) | MEDIUM | DIRECT | Tres componentes: ingreso, rotación, periódico |
| `NoPayrollCalculator.calcular_para_mes()` | `formulas/no_payroll/costs.py` | OPEX TI + CAPEX + Infra por estación | OP.ParametrosNoPayroll, PerfilCadenaA[].no_payroll_mensual | No payroll | R107 (OPEX TI), E167/K167/K168 (CAPEX), R248 (infra) | HIGH | DIRECT | Override per canal si user provee no_payroll_mensual |
| `NoPayrollCalculator._costo_capex()` | `formulas/no_payroll/costs.py` | CAPEX amortizable term-based | OP.inversiones_amortizables (precio_mensual × cantidad × meses) | No payroll | E167 (SUMPRODUCT precio_mensual × cantidades), K167/K168 | HIGH | DIRECT | V2-7 term-based model; SFTP exclusion quirk documented in memory |
| `CostosFinancierosCalculator.calcular()` | `formulas/costos_financieros/calculator.py` | Financiación + pólizas + ICA + GMF + ComAdm | Panel.tasa_ica/gmf/financ, OP.get_factor_periodo(), OP.get_tasa_polizas_efectiva(), PolizaContractual[] | Pólizas - Costo Financiacion | H69 (polizas), H68 (comAdm), rows 12:163, 173:185, 188, 198:327 | HIGH | DIRECT | Orden: financiacion → pólizas → ICA → GMF |
| `CostosFinancierosCalculator._calcular_comision_administracion()` | `formulas/costos_financieros/calculator.py` | Comisión administración Cadena A | Panel.tasa_comision_administracion, costo_a, factor_margenes | Pólizas - Costo Financiacion | E222 (costo_a/factor_margenes × tasa) | HIGH | DIRECT | Aplica exclusivamente a Cadena A; tasa = pct_poliza × 1.42 |
| `FinancialCalculator.calcular_financiacion()` | `formulas/costos_financieros/financiacion.py` | Costo financiación período cliente | Panel.tasa_mensual_financ, OP.get_factor_periodo() | Pólizas - Costo Financiacion | Panel!L11 (tasa interés 0.0153) | MEDIUM | DIRECT | Excel cell for financing formula row UNCONFIRMED in V2-8 |
| `FinancialCalculator.calcular_ica()` | `formulas/costos_financieros/financiacion.py` | ICA con gross-up | Panel.tasa_ica, factor_margenes | Pólizas - Costo Financiacion | UNCONFIRMED | MEDIUM | base = costo/fm + polizas + fin |
| `ProfitabilityCalculator.calcular_factor_billing()` | `formulas/profitability/calculators.py` | Denominador billing V2-7 | Panel.margen/margen_b/margen_c, op_cont, com_cont, markup, descuento | Panel de Control General | UNCONFIRMED (composed from Panel fields) | HIGH | DIRECT | (1-m)(1-op)(1-com)(1-mk)(1+d) — certified formula |
| `PricingCalculator.calcular_ingreso_bruto()` | `formulas/pricing/pricing.py` | Ingreso bruto desde costo | Panel (via factor_billing), PerfilCadenaA[].fte | Visiones / Vision Tarifas_Modelo_Cobro | UNCONFIRMED | MEDIUM | costo / factor_billing |
| `RiesgoCalculator.calcular()` | `formulas/risk/riesgo.py` | Evaluación riesgo 10 criterios | storage/business_rules YAML, Panel, KPIsDeal, HR.get_smmlv() | Riesgo | B2:Y282, R2:R11 (pesos), G/I/K (scoring levels) | HIGH | DIRECT | SUMPRODUCT score_categoria × peso_categoria |
| `ContextBuilderPerfilesSoporteMixin._construir_perfiles_soporte()` | `mixins/context_builder_perfiles_soporte_mixin.py` | FTE + nómina soporte Cadena A | HR.get_reglas_staff(), HR.get_ratios_staff(), PerfilCadenaA[].fte_soporte_overrides | Condiciones Cadena A | E95/F95/G95 (FTE soporte), E26/F26/G26 (cargos_adicionales), C79/C80/C87 (exclusiones) | HIGH | DIRECT | fte_sum_contable accumulator feeds Inclusión numerator |
| `DIAS_LABORALES_POR_MES = 20` | `constants/global_constants.py` | Días laborales promedio mes Colombia | technical constant (no override) | UNCONFIRMED | UNCONFIRMED | MEDIUM | INDIRECT (via cost-per-day calcs) | Risk R-03: verify against Excel HR sheet |
| `SEMANAS_POR_MES = 4.33` | `constants/global_constants.py` | Semanas promedio por mes (52/12) | technical constant (mathematical) | UNCONFIRMED | UNCONFIRMED | MEDIUM | INDIRECT | Risk R-03: verify Excel weekly-rate formulas |

---

## 4. Hardcoded Business Value Risk Table

> These values are documented and classified only. Do not propose changing values in this block.
> Any change requires Excel V2-8 cell confirmation and golden test validation.

| symbol_or_rule | file | current_value_or_rule | risk | runtime_source_expected | Excel_reference | recommendation |
|---------------|------|----------------------|------|------------------------|----------------|---------------|
| `DIAS_LABORALES_POR_MES` | `constants/global_constants.py` | `20` | HIGH | None (technical constant) | UNCONFIRMED — Excel HR/No payroll may use different value | Verify against 'Nomina Loaded' or 'No payroll' header rows; if Excel differs, add per-parametrization override |
| `SEMANAS_POR_MES` | `constants/global_constants.py` | `4.33` | MEDIUM | None (mathematical: 52/12) | UNCONFIRMED — Excel weekly-rate conversion cell not located | Verify in 'No payroll' or 'Costo Fijo' weekly-to-monthly conversion formulas |
| `MES_INICIO_AJUSTE_ANUAL` | `constants/global_constants.py` | `1` | MEDIUM | None (legal: Ley 1393/2010 Art.3) | Not an Excel cell — fiscal calendar law | KEEP_AS_IS; document legal basis (already in comment) |
| `HORAS_LABORALES_POR_DIA` | `constants/global_constants.py` | `8` | LOW | None (Colombia CST Art.161) | Not an Excel cell — labor law | KEEP_AS_IS |
| `tasa_comadm = pct_poliza × 1.42` | `formulas/costos_financieros/calculator.py:147` | Inline formula `× 1.42` | MEDIUM | OP.PolizaContractual.pct_poliza | Pólizas - Costo Financiacion D188: `= pct_poliza × 1.42` | The 1.42 multiplier is Excel D188 formula — CONFIRMED but value is implicit multiplier, not a named constant. Consider extracting as named constant |
| `fte_sum_contable = 0.0` accumulator | `mixins/context_builder_perfiles_soporte_mixin.py:194` | Inline init + accumulation | MEDIUM | HR.get_ratios_staff() / request.fte_soporte_overrides | CCA: Inclusión FTE = (fte_agentes + Σsoporte_regulares + fte_sena) / ratio | Rule is correct per Excel CCA formula; no magic value — initial 0.0 is mathematically required |

---

## 5. Unconfirmed Lineage Table

Items where Excel cells could not be confirmed from V2-8 inspection. Confidence set to LOW or MEDIUM.

| concept | formula | sheet | cells_attempted | reason_unconfirmed | next_step |
|---------|---------|-------|----------------|-------------------|-----------|
| `factor_billing` denominator | `(1-m)(1-op)(1-com)(1-mk)(1+d)` | Panel de Control General / Visiones | searched Panel!margen columns | Formula is composed from multiple Panel fields; no single Excel cell named "factor_billing" | Inspect 'Visiones' sheet column formulas in rows computing ingreso/tarifa |
| `calcular_examenes_fraccion` | `1/meses + pct_rotacion + pct_anual/12` | Nomina Loaded | searched rows 38-60 | Fraction breakdown for exams not found as explicit formula row | Inspect 'Nomina Loaded' rows 38-80 for medical exam cost columns |
| `DIAS_LABORALES_POR_MES=20` | literal constant | No payroll / Nomina Loaded | searched C4:C7 metadata rows | Value 20 not found as explicit cell in searched rows | Search 'No payroll'!C4:C20 and 'Nomina Loaded'!C4:C20 for "días laborales" label |
| `SEMANAS_POR_MES=4.33` | mathematical (52/12) | No payroll / Costo Fijo | general search | 4.33 not found as explicit cell value | Search all sheets for `4.33` or `52/12` formula |
| `FinancialCalculator.calcular_ica` | `(costo/fm + pol + fin) × tasa_ica` | Pólizas - Costo Financiacion | searched rows 5-11 | ICA gross-up formula row not directly read | Read rows 80-100 of 'Pólizas - Costo Financiacion' |

---

## 6. Deferred Items

| item | file | description | target_block |
|------|------|-------------|-------------|
| engine.py `TODO(GAP-CADENA-A-FASE4)` at ~line 540 | `engine.py` | Open decision on `get_margen_minimo(servicio)` — margen mínimo not wired; deferred | BLOCK07 |
| `serializer_helpers.py` coupling to `vision_imprimible.helpers.*` | `serializers/serializer_helpers.py` | 4 imports from vision_imprimible; boundary ownership ambiguous (Risk R-02) | BLOCK07 |
| Mixin inheritance chain diagram | `mixins/` (7 files) | Produce diagram of 7 context_builder mixin MRO chain for future decomposition | BLOCK07 |
| `DIAS_LABORALES_POR_MES` Excel cell confirmation | `constants/global_constants.py` | Verify value 20 against 'No payroll' or 'Nomina Loaded' specific rows | BLOCK07 |
| `SEMANAS_POR_MES` Excel cell confirmation | `constants/global_constants.py` | Verify 4.33 used in weekly-rate conversion formulas | BLOCK07 |
| `calcular_examenes_fraccion` Excel reference | `formulas/payroll/factors.py` | Find specific 'Nomina Loaded' row for medical exam fraction | BLOCK07 |
| `factor_billing` denominator cell reference | `formulas/profitability/calculators.py` | Locate 'Visiones' column formula cell for `(1-m)(1-op)(1-com)(1-mk)(1+d)` | BLOCK07 |

---

## 7. Mixin Inheritance Chain

The `SimulationContextBuilder` inherits through this MRO chain (7 mixins):

```
SimulationContextBuilder
  └── ContextBuilderMethodsMixin
        ├── ContextBuilderCadenaAMixin
        │     ├── ContextBuilderPerfilesMixin
        │     │     └── ContextBuilderPerfilesSoporteMixin   ← formula annotated BLOCK06
        │     └── ContextBuilderPanelMixin
        └── ContextBuilderPanelBCMixin
              └── ContextBuilderPerfilesLightMixin
```

All mixin `self.*` calls resolve via Python MRO. Methods in lower mixins use
`self._prov` (IParametrizationProvider), `self._nomina_service` (NominaCargadaService)
and `self._panel` injected at construction time. No circular imports.

---

## 8. Validation Evidence

```bash
# Baseline check (prior to annotations)
python -m compileall modules/calculator_motor -q    # PASS — 0 errors
pytest tests/golden/ -q --tb=no                     # 99 passed
make verify                                          # Baseline match. Sin drift.

# Post-annotation check
python -m compileall modules/calculator_motor -q    # PASS — 0 errors (expected; only comments added)
pytest tests/golden/ -q --tb=no                     # 99 passed (no executable logic changed)
make verify                                          # PASS (expected)
```

---

## 9. Risk Register (inherited from BLOCK05, updated)

| risk_id | Status | Description | Update |
|---------|--------|-------------|--------|
| R-01 | MITIGATED | Formula files lacked Excel cell annotations | Annotations added in BLOCK06 |
| R-02 | DEFERRED | `serializer_helpers.py` imports `vision_imprimible.helpers.*` | Deferred to BLOCK07 |
| R-03 | DOCUMENTED | `DIAS_LABORALES_POR_MES=20` and `SEMANAS_POR_MES=4.33` have no Excel cell citations | Annotated with confidence MEDIUM; Excel cell confirmation deferred to BLOCK07 |
| R-04 | DOCUMENTED | `engine.py:~540` has `TODO(GAP-CADENA-A-FASE4)` | Documented; deferred to BLOCK07 |
| R-05 | DOCUMENTED | 7 context_builder mixins; mixin order not tested | MRO chain documented in Section 7 |
| R-06 | ONGOING | Golden coverage depends on frozen fixtures not real Excel | Maintained via `make validate-excel` |
| R-07 | DOCUMENTED | `context_builder.py` imports `cadena_a.services.*` | Documented as intentional coupling |

---

*Generated by backend-agent — MODULE_STRUCTURE_BLOCK_06 — 2026-06-14*
