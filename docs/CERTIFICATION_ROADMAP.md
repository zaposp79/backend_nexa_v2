# FASE ACTUAL: Certificación Financiera — Roadmap Detallado

**Initiated**: 2026-05-26  
**Target**: Excel parity certification + hardening (no new structural features)  
**Current Status**: Diagnostic complete, H-04 divergence identified, framework in place

---

## 1. Diagnostic Results

### Formula Implementation Audit

| Formula | Implementation | Spec | Status | Notes |
|---------|-----------------|------|--------|-------|
| **Especialista** | (sal × ratio × 3 × comp) / meses | Excel V2-6 C66 | ✅ OK | Correct, Decimal/ROUND_HALF_UP |
| **Salario Fijo** | Σ(sal × fte) / meses / total_fte | "agents inbound+outbound only" | 🔴 **DIVERGENCE** | Currently includes ALL (agents+support) |
| **SENA** | (agents + filter_support) / ratio | Exclude: Val, Esp, SENA, Inc | ✅ OK | CargoClassifier correct |
| **Inclusión** | (agents + support + SENA) / ratio | Include SENA ✓ | ✅ OK | Formula correct |

### Test Status
- **Passing**: 499/503 (99%)
- **Failing**: 12 (pre-existing: parametrization, provenance)
- **Errors**: 4 (setup issues: missing OP-Config)

### Rounding Precision Status
- ✅ Shared layer: `shared/precision.py` fully implemented
- ✅ P1 fixes applied: `cop_round()` in Cadena B/C components
- ✅ Excel parity: Using ROUND_HALF_UP, not Python banker's rounding
- ⏳ Coverage: Applied to cadena_b, cadena_c; need to audit other components

---

## 2. H-04: Salario Fijo Divergence (CRITICAL FIX NEEDED)

### Problem
Current implementation:
```python
# SalarioFijoCalculator.calcular(perfiles_activos) where
# perfiles_activos = [(sal_cargado, fte) for ALL profiles]
# 
# Includes: agents + validadores + especialista + sena + inclusión
# Result: inflates Salario Fijo by including non-agent costs
```

User spec:
```
Salario_Fijo = Σ(salarios activos) / duración contrato / total FTE inbound + outbound
```

"total FTE inbound + outbound" = **agents only**, not support staff.

### Impact
- Salario Fijo metric inflated
- Affects Cost To Serve vision dataset
- Affects pricing benchmarking vs Excel

### Fix Required
Filter `perfiles_activos` to include ONLY agent profiles:
```python
def _filter_agents_only(perfiles_activos):
    # Filter to Cadena A profiles with modalidad in ["Inbound", "Outbound"]
    # Exclude: support (es_soporte=True)
    return [p for p in perfiles_activos if not p.es_soporte and p.modalidad in ("Inbound", "Outbound")]

def calcular(self, perfiles_activos, meses_contrato):
    agentes_solo = self._filter_agents_only(perfiles_activos)
    if not agentes_solo:
        return 0.0
    # ... rest of formula
```

### Test Case
```python
# BEFORE (current): 
#   perfiles = [(1.5M, 10 agentes), (2M, 2 validadores)]
#   salario_fijo = (1.5M×10 + 2M×2) / 12 / 12 = inflated

# AFTER (fixed):
#   perfiles_agents_only = [(1.5M, 10 agentes)]
#   salario_fijo = (1.5M×10) / 12 / 10 = correct
```

---

## 3. Golden Master Validation Framework

### Setup
- **File**: `tests/unit/test_certification_golden_master.py`
- **Helper**: `assert_financial_equal(engine, expected, tolerance=0.01)`
- **Coverage Target**: 20-30 real commercial scenarios

### Scenario Types (To Implement)

#### Type A: Simple Single-Cadena (2 scenarios)
1. **Scenario 01**: 10 Inbound Agents + 2 Validadores, 12 meses, no extras
2. **Scenario 02**: 5 Inbound + 5 Outbound + Support, 12 meses

#### Type B: Multi-Cadena (3 scenarios)
3. **Scenario 03**: Cadena A + B (digital platform), 24 meses, margen 30%
4. **Scenario 04**: Cadena A + B + C (IA integration), 12 meses, margen 25%
5. **Scenario 05**: Complex: A+B+C with multiple channels per cadena

#### Type C: Special Cases (4 scenarios)
6. **Scenario 06**: With Especialista de Proyectos (all complejidades: BAJA/MEDIA/ALTA)
7. **Scenario 07**: With Aprendiz SENA (verify exclusions)
8. **Scenario 08**: With Inclusión (verify includes SENA)
9. **Scenario 09**: Multi-scenario engine (3 scenarios per deal: optimista/conservador/agresivo)

#### Type D: Edge Cases (5 scenarios)
10. **Scenario 10**: Zero volumes (cadenas inactivos)
11. **Scenario 11**: Rounding accumulation (12 months with precision drift)
12. **Scenario 12**: Indexación (annual + monthly compounding)
13. **Scenario 13**: Negative margins (loss scenario)
14. **Scenario 14**: Very short contract (3 meses)

### Data Source
- **Frozen values**: Extract from Excel V2-6 for each scenario
- **Reference file**: `docs/golden_master_values.csv` (to create)
- **Format**: scenario_id | metric | expected_value | tolerance | notes

### Validation
```python
# Example:
def test_escenario_01():
    engine = calculate_scenario_01()
    golden = load_golden_master("scenario_01")
    
    for metric, expected in golden.items():
        assert_financial_equal(
            engine[metric],
            expected,
            tolerance=0.01,
            field_name=f"Scenario01.{metric}"
        )
```

---

## 4. Precision Layer Audit

### Current State (Post P1 Fixes)
✅ `shared/precision.py`: excel_round, cop_round, pct_round all implemented  
✅ `cadena_b.py`: cop_round applied to _costo_variable, _costo_escalamiento  
✅ `cadena_c.py`: cop_round applied to tarifa_proveedor, opex, escalamiento  

### Gap Analysis (To Do)
- [ ] Audit all salary calculations for cop_round/excel_round usage
- [ ] Check indexación calculations for pct_round(6 decimales)
- [ ] Verify ramp-up factor precision (must not accumulate)
- [ ] Check acumulados_mensuales calculations
- [ ] Verify polizas and financial components use excel_round

### Action Items
1. Grep for `*` and `/` operations that should use Decimal
2. Apply cop_round() before summing in any Σ() operation
3. Apply pct_round(6) to any indexación factors
4. Apply excel_round() to final monthly acumulados

---

## 5. Escenarios Comerciales (TASK 5)

### Architecture
Each scenario = independent `PricingRequest` in the same simulation run.

### Implementation Pattern
```python
class PricingRequest:
    scenario: str  # "optimista" | "conservador" | "agresivo"
    margen: float  # Overrides panel.margen for this scenario
    volumen_adjustments: Dict[str, float]  # Per-channel volume multiplier
    ...

engine.calcular_multiples([
    PricingRequest(..., scenario="optimista", margen=0.35),
    PricingRequest(..., scenario="conservador", margen=0.25),
    PricingRequest(..., scenario="agresivo", margen=0.40),
])
```

### Return Format
```python
{
    "optimista": PricingResult(...),
    "conservador": PricingResult(...),
    "agresivo": PricingResult(...),
}
```

### Validation
- No logic duplication (reuse calculadores)
- All 3 scenarios use same audit_trace, datasets_vision
- Serialization includes all 3 scenarios in single response
- Snapshot captures all 3 scenarios

---

## 6. Audit Trail Completeness Checklist

### Per Calculation
- [ ] Input values logged (with source: JSON, parametrization, formula)
- [ ] Intermediate results logged (before rounding)
- [ ] Final result logged (after rounding)
- [ ] Rounding decision visible (tolerance applied? ±0.01?)

### Per Component
- [ ] Salario Fijo: input profiles, filter logic, final fte
- [ ] Especialista: sal_cargado, ratio, complejidad, meses, result
- [ ] SENA: fte_agentes, fte_soporte_filtered, ratio, result
- [ ] Inclusión: agents, support, sena, ratio, result

### Per Scenario
- [ ] Scenario ID logged
- [ ] Parameter overrides logged (margen, volumen_adj)
- [ ] Differentiation from baseline logged

---

## 7. Implementation Timeline

### Phase 1: H-04 Fix (2 hours)
- [ ] Fix SalarioFijoCalculator to filter agents only
- [ ] Update test_certification_golden_master.py with scenario values
- [ ] Verify Cadena A profiles have correct es_soporte, modalidad flags
- [ ] Run 499 test suite — verify no regression

### Phase 2: Golden Master (1-2 days)
- [ ] Extract 20-30 scenarios from Excel V2-6
- [ ] Create golden_master_values.csv with frozen outputs
- [ ] Implement scenario test functions
- [ ] Achieve 100% pass rate with ±0.01 COP tolerance

### Phase 3: Precision Audit (1 day)
- [ ] Grep for float arithmetic operations
- [ ] Apply cop_round/pct_round/excel_round systematically
- [ ] Re-run Golden Master tests
- [ ] Verify tolerance compliance

### Phase 4: Escenarios Comerciales (2-3 days)
- [ ] Extend PricingRequest for scenario parameters
- [ ] Implement multi-scenario engine
- [ ] Test all 3 scenarios per deal
- [ ] Verify serialization completeness

### Phase 5: Final Audit (1 day)
- [ ] Review all audit_trace completeness
- [ ] Verify no data contaminación between cadenas
- [ ] Verify no defaults silenciosos
- [ ] Snapshot persistence round-trip validation

---

## 8. Success Criteria

✅ **MUST HAVE**:
- [ ] 499 tests passing (no regression from P0/P1 fixes)
- [ ] H-04 fixed (Salario Fijo agents-only)
- [ ] 20-30 Golden Master scenarios certified (±0.01 COP tolerance)
- [ ] All special formulas validated against Excel

✅ **SHOULD HAVE**:
- [ ] Precision layer 100% coverage
- [ ] Escenarios comerciales (TASK 5) implemented
- [ ] Audit trail complete and verifiable

✅ **NICE TO HAVE**:
- [ ] Performance optimizations (if any identified)
- [ ] Enhanced error messages for debugging
- [ ] Documentation of all formula derivations

---

## 9. Monitoring & Validation

### Daily Checkpoints
1. Golden Master pass rate (target: 100%)
2. Unit test suite: 499+ passing
3. Max deviation from Excel: 0.01 COP per metric
4. No silent defaults in calculations

### Integration Checkpoints
- Audit trail serializes correctly
- Datasets vision JSON complete
- Snapshot persistence round-trip valid
- No cadena contamination in multi-scenario runs

---

## 10. Documentation

### To Create
- [ ] `golden_master_values.csv` — Frozen Excel reference values
- [ ] `FORMULAS_VERIFICATION.md` — Each formula with derivation + test case
- [ ] `PRECISION_LAYER_APPLIED.md` — Which calculations use which rounding function
- [ ] `ESCENARIOS_COMERCIALES_SPEC.md` — Schema for scenario parameters

### To Update
- [ ] `AUDIT_FIXES_COMPLETED.md` — Add H-04 fix status
- [ ] API documentation — Explain multi-scenario response format
- [ ] Test README — Document Golden Master test approach

---

## Next Immediate Action

**Start with H-04 Fix**:

1. Review `SalarioFijoCalculator` and identify where `perfiles_activos` is built
2. Add filter to exclude non-agents (support staff)
3. Update call sites to pass agents-only list
4. Create test with expected vs actual for simple scenario
5. Run full 499 test suite to verify no regression

**Timeline**: 2 hours  
**Risk**: Low (isolated change, good test coverage)  
**Rollback**: Easy (revert one commit)

---

## Files Ready

✅ Test framework: `tests/unit/test_certification_golden_master.py`  
✅ Memory: `fase_actual_certification.md`  
✅ Documentation: This file  

**Ready to implement H-04 fix and Golden Master scenarios.**
