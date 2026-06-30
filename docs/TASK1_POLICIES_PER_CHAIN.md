# TASK 1: Policies per Chain (Pólizas por Cadena)

**Status**: ✅ COMPLETE  
**Test Coverage**: 8 tests, all passing  
**Impact**: Enables full financial traceability of insurance costs by chain  

---

## 🎯 Objective

Expose the breakdown of policy costs **per chain** (A, B, C) in vision datasets and serializers, so that auditors can verify:

- Póliza solo Cadena A NO afecta polizas_b ni polizas_c
- Póliza solo Cadena B NO afecta polizas_a ni polizas_c
- Póliza solo Cadena C NO afecta polizas_a ni polizas_b
- Múltiples pólizas mixtas distribuyen costos correctamente

**Before TASK 1**: Policy costs were aggregated (single `polizas` field); no visibility into which cadena paid which cost.  
**After TASK 1**: Vision dataset and JSON output expose `costo_por_cadena` with breakdown by A, B, C.

---

## 📋 Changes Made

### 1. **Vision Model** (domain/visions.py)

Added per-chain cost fields to `DatasetPolizasMensual`:

```python
@dataclass
class DatasetPolizasMensual:
    polizas_activas: List[PolizaActivaRow]
    tasa_total_efectiva: float
    costo_mensual_promedio: float              # Total
    costo_mensual_promedio_a: float = 0.0      # TASK 1: Cadena A only
    costo_mensual_promedio_b: float = 0.0      # TASK 1: Cadena B only
    costo_mensual_promedio_c: float = 0.0      # TASK 1: Cadena C only

    def as_dict(self) -> dict:
        return {
            ...
            "costo_por_cadena": {
                "cadena_a": self.costo_mensual_promedio_a,
                "cadena_b": self.costo_mensual_promedio_b,
                "cadena_c": self.costo_mensual_promedio_c,
            },
        }
```

**Key**: Each cadena gets its own cost metric, extracted from P&G breakdown.

### 2. **Vision Builder** (calculators/vision_datasets.py)

Updated `_build_polizas()` to calculate per-chain averages:

```python
# TASK 1: Costo mensual promedio de pólizas desde el P&G
# Calcula total y por-cadena
costo_mensual_promedio = 0.0
costo_mensual_promedio_a = 0.0
costo_mensual_promedio_b = 0.0
costo_mensual_promedio_c = 0.0

if resultado.pyg_por_mes:
    costos_polizas = [getattr(m, "polizas", 0.0) for m in resultado.pyg_por_mes]
    costos_polizas_a = [getattr(m, "polizas_a", 0.0) for m in resultado.pyg_por_mes]
    costos_polizas_b = [getattr(m, "polizas_b", 0.0) for m in resultado.pyg_por_mes]
    costos_polizas_c = [getattr(m, "polizas_c", 0.0) for m in resultado.pyg_por_mes]

    if costos_polizas:
        costo_mensual_promedio = sum(costos_polizas) / len(costos_polizas)
        costo_mensual_promedio_a = sum(costos_polizas_a) / len(costos_polizas_a)
        costo_mensual_promedio_b = sum(costos_polizas_b) / len(costos_polizas_b)
        costo_mensual_promedio_c = sum(costos_polizas_c) / len(costos_polizas_c)

return DatasetPolizasMensual(
    polizas_activas=filas,
    tasa_total_efectiva=tasa_total,
    costo_mensual_promedio=costo_mensual_promedio,
    costo_mensual_promedio_a=costo_mensual_promedio_a,
    costo_mensual_promedio_b=costo_mensual_promedio_b,
    costo_mensual_promedio_c=costo_mensual_promedio_c,
)
```

**Key**: Extract polizas_a, polizas_b, polizas_c from pyg_por_mes and average them.

### 3. **Serializer** (adapters/pricing_serializer.py)

Already includes per-chain breakdown in `_pyg_to_dict()`:

```python
d["polizas_por_cadena"] = {
    "cadena_a": p.polizas_a,
    "cadena_b": p.polizas_b,
    "cadena_c": p.polizas_c,
}
```

**Status**: No changes needed; serializer already exposes this field.

---

## ✅ Test Coverage

### Unit Tests (test_task1_policies_per_chain.py)

**Isolation Tests (5 tests)**:
- ✅ `test_policy_aplica_a_only_affects_polizas_a` — Póliza solo A
- ✅ `test_policy_aplica_b_only_affects_polizas_b` — Póliza solo B
- ✅ `test_policy_aplica_c_only_affects_polizas_c` — Póliza solo C
- ✅ `test_multiple_policies_mixed_chains` — Múltiples pólizas en cadenas diferentes
- ✅ `test_zero_cost_policies_zero_breakdown` — Explícitamente [] con costo cero

**Vision Output Tests (2 tests)**:
- ✅ `test_dataset_as_dict_includes_costo_por_cadena` — Verifica estructura en as_dict()
- ✅ `test_vision_dataset_none_when_polizas_usuario_none` — Verifica None handling

**Serializer Integration (1 test)**:
- ✅ `test_serializer_includes_polizas_por_cadena` — Verifica JSON output

```bash
$ pytest tests/unit/test_task1_policies_per_chain.py -v
======== 8 passed in 0.02s ========
```

---

## 🏗️ Architecture Impact

### Data Flow (TASK 1)

```
PyGMensual.polizas_a/b/c (calculados por CostosFinancierosCalculador)
    ↓
resultado.pyg_por_mes[*].polizas_a/b/c
    ↓
VisionDatasetsBuilder._build_polizas()
    │ └─ Extrae arreglos de polizas_a, polizas_b, polizas_c
    │ └─ Calcula promedio para cada cadena
    ↓
DatasetPolizasMensual.costo_mensual_promedio_a/b/c
    ↓
DatasetsVision.polizas.as_dict()
    │ └─ "costo_por_cadena": { "cadena_a": X, "cadena_b": Y, "cadena_c": Z }
    ↓
JSON Response + PyG Monthly Breakdown
```

### Vision Dataset JSON Output

```json
{
  "polizas": {
    "polizas_activas": [
      {
        "nombre": "Seguros A+B",
        "pct_poliza": 0.5,
        "aplica_cadena_a": true,
        "aplica_cadena_b": true,
        "aplica_cadena_c": false
      }
    ],
    "tasa_total_efectiva": 0.5,
    "costo_mensual_promedio": 100.0,
    "costo_por_cadena": {
      "cadena_a": 50.0,
      "cadena_b": 50.0,
      "cadena_c": 0.0
    }
  }
}
```

---

## 💰 Financial Impact

### Audit Traceability

**Before TASK 1:**
- "Costo de pólizas para cliente X es $100/mes"
- ❓ No se sabe cuánto fue Cadena A, cuánto B, cuánto C
- Auditor no puede verificar: "¿Por qué Cadena B pagó seguros si no tiene agentes?"

**After TASK 1:**
- "Costo de pólizas para cliente X: Total $100/mes"
- ✅ Cadena A: $50/mes (aplica_a=true)
- ✅ Cadena B: $50/mes (aplica_b=true)
- ✅ Cadena C: $0/mes (aplica_c=false)
- Auditor puede verificar: "Póliza solo-B contribuye $50, póliza A+B distribuye correctamente"

---

## 🔗 Trazabilidad

### Critical Path

```
PolizaContractual.aplica_a/b/c flags (del JSON)
    ↓
CostosFinancierosCalculador (recibe flags, calcula polizas_a/b/c)
    ↓
PyGCalculador (asigna polizas_a/b/c a PyGMensual)
    ↓
PricingResult.pyg_por_mes[*].polizas_a/b/c
    ↓
VisionDatasetsBuilder._build_polizas() (extrae y promedia por cadena)
    ↓
DatasetPolizasMensual.costo_mensual_promedio_a/b/c
    ↓
DatasetsVision.polizas.as_dict() + pricing_result_to_dict()
    ↓
JSON Response: costo_por_cadena
```

### Audit Trail

```
InputNormalizer
    → contract_validator (verifica aplica_a/b/c flags)
    → user_input_loader (carga PolizaContractual)
    → context_builder (preserva flags)
    → engine.py (pasa a CostosFinancierosCalculador)
    → calculadores (calcula polizas_a/b/c)
    → vision_datasets.py (expone breakdown)
    → pricing_serializer.py (serializa costo_por_cadena)
    → endpoint response (auditor verifica)
```

---

## 🚀 What's Next

- **TASK 4**: Volume resolution integration
- **TASK 5**: Real commercial scenarios (multi-scenario engine)
- **TASK 6**: Strict contract mode validation
- **TASK 7**: Enhanced contract validator
- **TASK 8-13**: Traceability registry, traceability endpoint, fail-fast audit, etc.

---

## 📝 Code Quality Checklist

- ✅ No breaking changes to existing APIs
- ✅ Backward compatible (policies without chain flags default safely)
- ✅ Comprehensive test coverage (8 tests, 100% pass)
- ✅ Clear audit trail through pipeline
- ✅ Deterministic behavior (same input = same output)
- ✅ Thread-safe (no mutable shared state)
- ✅ Isolation verified (A-only vs B-only vs C-only vs mixed)

---

## 🎓 Key Learning

**The Problem**: Policy cost breakdown existed in P&G monthly (`polizas_a`, `polizas_b`, `polizas_c`) but was never exposed to clients or auditors.

**The Solution**: Extract and average per-chain costs from P&G, expose in vision dataset and JSON.

```python
# BEFORE — aggregate only
costo_mensual_promedio = sum(pyg.polizas for pyg in pyg_por_mes) / len(pyg_por_mes)

# AFTER — per-chain breakdown
costo_mensual_promedio_a = sum(pyg.polizas_a for pyg in pyg_por_mes) / len(pyg_por_mes)
costo_mensual_promedio_b = sum(pyg.polizas_b for pyg in pyg_por_mes) / len(pyg_por_mes)
costo_mensual_promedio_c = sum(pyg.polizas_c for pyg in pyg_por_mes) / len(pyg_por_mes)
```

**Why It Matters**: Auditors must be able to trace: "Which cadena paid for which policy?" The `aplica_a/b/c` flags determine cost allocation; exposing this breakdown makes that allocation verifiable.

---

## 📌 Integration with TASK 2 & 3

- **TASK 2** (null vs []): Distinguishes "user didn't configure" from "user chose zero". TASK 1 builds on this by exposing per-chain costs even when policies are zero.
- **TASK 3** (Optional chains): Policies can apply to only certain chains. TASK 1 exposes exactly which chains received which costs, enabling audits of "B-only" deals.

Together: **TASK 1 + 2 + 3** = Complete contractual traceability for policies across all deal types.
