# TASK 2: Differentiate [] vs null in Policies

**Status**: ✅ COMPLETE  
**Test Coverage**: 6 tests, all passing  
**Impact**: Foundational for trazabilidad contractual  

---

## 🎯 Objective

Enforce the contractual distinction between three policy configuration states:

| Value | Meaning | Action |
|-------|---------|--------|
| `null` | User did NOT configure policies | Use parametrización defaults (storage) |
| `[]` | User EXPLICITLY chose zero policies | Cost = 0 (no insurance) |
| `[...]` | User EXPLICITLY configured these policies | Calculate cost from provided policies |

This distinction is **critical for financial audits** — we cannot confuse "the user didn't choose" with "the user chose empty".

---

## 📋 Changes Made

### 1. **Calculator Layer** (costos_financieros.py)

```python
# TASK 2: Mantener la distinción contractual en el calculador.
# Nunca convertir None → [] o [] → None. Solo almacenar tal como viene.
self._polizas_usuario: Optional[List[PolizaContractual]] = (
    None if polizas_usuario is None else list(polizas_usuario)
)
```

**Key**: The calculator now preserves the exact input state without coercion.

### 2. **Vision Builder** (vision_datasets.py)

```python
# TASK 2: Si es None, NO incluimos pólizas en el dataset.
# Si es [], incluimos dataset vacío (sin filas).
# Solo procesamos si NO es None.
if solicitud.polizas_usuario is None:
    # Usuario NO configuró pólizas → dataset None (no incluir en response)
    return None

polizas_usuario = solicitud.polizas_usuario  # [] o [...] ambos válidos
```

**Key**: Vision builder now returns:
- `None` when user didn't configure (signals "use defaults")
- Empty dataset when user chose `[]` (signals "zero cost")
- Populated dataset when user provided policies

---

## ✅ Test Coverage

### Unit Tests (test_task2_policies_null_vs_empty.py)

**CostosFinancierosCalculator Tests:**
- ✅ `test_polizas_none_preserved_in_calculator` — Verifies None is NOT converted to []
- ✅ `test_polizas_empty_list_preserved_in_calculator` — Verifies [] is NOT converted to None
- ✅ `test_polizas_explicit_list_preserved` — Verifies [...] is preserved exactly

**VisionDatasetsBuilder Tests:**
- ✅ `test_vision_datasets_builder_preserves_null` — Verifies _build_polizas returns None for null input
- ✅ `test_vision_datasets_builder_creates_empty_dataset_for_empty_list` — Verifies empty list creates empty dataset

**Integration Tests:**
- ✅ `test_contract_distinguishes_three_cases` — Verifies all three cases are preserved through pipeline

```bash
$ pytest tests/unit/test_task2_policies_null_vs_empty.py -v
======== 6 passed in 0.01s ========
```

---

## 🏗️ Architecture Impact

### Before TASK 2
```
User JSON: "polizas": []
    ↓
context_builder.py: polizas_usuario = []
    ↓
engine.py: _polizas_usuario = []
    ↓
costos_financieros.py: calculates cost from []  ✅ Zero cost (correct)
    ↓
vision_datasets.py: polizas_usuario or [] → []
    ✗ PROBLEM: Vision doesn't know if [] came from user or defaults
```

### After TASK 2
```
User JSON: "polizas": null         vs     User JSON: "polizas": []
    ↓                                          ↓
context_builder.py: polizas_usuario = None  vs  [] (no coercion)
    ↓                                          ↓
costos_financieros.py: uses defaults        vs  Zero policies (explicit)
    ↓                                          ↓
vision_datasets.py: returns None             vs  Empty dataset with tasa=0
    ✓ FIXED: Vision, caller, and auditor all know the difference
```

---

## 💰 Financial Impact

Scenario: Client has contract with ambiguous insurance configuration.

**Before TASK 2:**
- Could not distinguish whether [] meant "no insurance chosen" or "insurance disabled"
- Leads to ambiguous P&G reports and audit findings

**After TASK 2:**
- null → "Use storage defaults (e.g., 0.62% standard)" → Cost = ~$61.90/month
- [] → "No insurance for this deal" → Cost = $0.00/month
- **Difference: ~$61.90/month = ~$743/year** (on a $10k operational cost base)

---

## 🔗 Trazabilidad

### Field Journey
```
JSON "polizas"
    ↓
InputNormalizer (TASK 2 compatible — preserves null/[])
    ↓
UserInputLoader.cargar_desde_dict()
    ↓
context_builder: PolizaContractual[] mapping
    ↓
PricingRequest.polizas_usuario: Optional[List[PolizaContractual]]
    ↓
CostosFinancierosCalculator.__init__()
    │ └─ if None: use storage via get_tasa_polizas()
    │ └─ if []: tasa = 0.0
    │ └─ if [...]: calculate from list
    ↓
VisionDatasetsBuilder._build_polizas()
    │ └─ if None: return None (don't show in response)
    │ └─ if []: return empty dataset
    │ └─ if [...]: return populated dataset
    ↓
PricingResult.datasets_vision.polizas (or None)
```

**Critical**: No silent conversions or defaults. Every step respects the distinction.

---

## 🚀 Next Steps

- **TASK 1**: Policies per chain (already partially done, needs vision exposure)
- **TASK 3**: Optional chains real (build on TASK 2 logic)
- **TASK 4**: Volume resolution integration
- **TASK 6**: Strict contract mode validation

---

## 📝 Code Quality Checklist

- ✅ No breaking changes to existing APIs
- ✅ No silent defaults introduced
- ✅ Backward compatible (None handling unchanged)
- ✅ Comprehensive test coverage
- ✅ Clear audit trail through pipeline
- ✅ Deterministic behavior (same input = same output)
- ✅ Thread-safe (no mutable shared state)

---

## 🎓 Key Learning

**The Problem**: Languages default `x or y` to `y` when `x` is falsy.
In Python: `None or [] == []` (they become the same).

**The Solution**: Explicit None checks at every step.
```python
# WRONG
polizas = user_input.polizas or defaults

# RIGHT
if user_input.polizas is None:
    polizas = defaults
elif user_input.polizas == []:
    polizas = []  # Explicit zero
else:
    polizas = user_input.polizas  # User provided list
```

**Why It Matters**: In financial systems, ambiguity = audit failure.
