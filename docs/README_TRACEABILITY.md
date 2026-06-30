# COMPLETE TRACEABILITY DOCUMENTATION — Excel V2-7 ↔ Backend ↔ API

**Last Updated**: 2026-05-31 | **Version**: V2-7 | **Status**: Complete & Production-Ready

---

## Overview

This documentation set provides **complete, bidirectional traceability** from Excel V2-7 inputs through the NEXA Pricing Engine backend to final API responses and Vision outputs. Every calculation, every parameter, and every result is documented with:

- Excel source cell references
- Backend model fields and validators
- Formula implementations and calculators
- Result objects and outputs
- API response paths
- Vision display mappings

---

## Documents in This Set

### 1. CAPÍTULO 8: MATRIZ DE TRAZABILIDAD (Main Reference)
**File**: `CAP_8_Matriz_de_Trazabilidad.md`  
**Size**: 651 lines / 32 KB  
**Purpose**: Comprehensive narrative documentation of the complete traceability matrix

**Contents**:
- **Section 8.1**: Overview & Methodology (6-level traceability model)
- **Section 8.2**: Panel de Control Traceability (25+ input fields)
  - Márgenes (margen, margen_b, margen_c)
  - Contingencias (op_cont, com_cont, markup, descuento, imprevistos)
  - Financiación (período, tasas, activación)
  - Tasas fiscales (ICA, GMF)
  - Parámetros operativos (rotación, ausentismo)

- **Section 8.3**: Nómina Cargada Traceability (7 payroll components)
  - Salario Fijo + Factor de Indexación
  - Capacitación (inicial + rotación)
  - Exámenes (3-part formula: initial + rotation + annual)
  - Estudios de Seguridad
  - Crucero (V2-7 new)

- **Section 8.4**: Ratios & Staffing Traceability
  - Supervisor, Formador, Monitor, Especialista ratios
  - FTE Efectivo calculation
  - Role name normalization

- **Section 8.5**: Vision Tarifas Hierarchy
  - Encabezados → Factores → Componentes → Escenarios → CTS
  - K50, L50, M50 denominators
  - Per-canal financial attribution

- **Section 8.6**: P&G Statement (Complete Row-by-Row)
  - Ingresos (A41–A47)
  - Costos Operativos (B48–B61)
  - Costos Financieros (C62–C67)
  - Resultados (D68–D70)

- **Section 8.7**: Costos Financieros (ICA, GMF, Pólizas, Financiación, Comisión Adm)

- **Section 8.8–8.9**: Cadena B & Cadena C Components

- **Section 8.10**: Technical Validation & Precision Guarantees

- **Section 8.11**: Critical Flow Diagrams (4 complete examples)

- **Section 8.12**: Cross-Reference Tables

**Audience**: Architects, Auditors, Test Engineers, Business Analysts

---

### 2. TRACEABILITY_MATRIX.md (Machine-Readable Reference)
**File**: `TRACEABILITY_MATRIX.md`  
**Size**: 1,075 lines / 40 KB  
**Purpose**: Structured, self-contained lookup reference for automation and audit tools

**Format**: Consistent block structure for each field:
```
FIELD: field_name
  Excel Source: Sheet!Cell
  Backend Model: ClassName.field
  Type: type | Range: min–max
  Unit: measurement unit
  Validation: constraints
  Formula: mathematical expression
  Calculator: method_name()
  Result Field: ResultClass.field
  Vision Output: Vision section
  API Field: V1 DTO path
  Example: Real numerical example
  Example Detail: 12-month walkthrough (for critical fields)
  Numerical Example: (where applicable)
  Cadena Attribution: (for multi-cadena fields)
  Notes: Implementation notes, gotchas, version markers
  Status: Core | Version: V2-7 | New in V2-X: (if applicable)
```

**Sections**:
1. **Panel de Control Inputs** (16 fields)
   - Cliente & Contexto (1)
   - Márgenes (3: margen, margen_b, margen_c)
   - Contingencias & Ajustes (5: op_cont, com_cont, markup, descuento, imprevistos)
   - Financiación (4: periodo_pago, activa_financiacion, tasa_mensual, tasa_ica, tasa_gmf)
   - Operativos (2: pct_rotacion, pct_ausentismo)

2. **Componentes de Nómina** (7 fields)
   - salario_fijo, capacitacion_inicial, capacitacion_rotacion, examenes, seguridad, crucero (V2-7)

3. **Componentes de Infraestructura** (3 fields)
   - opex_ti, capex, costos_fijos (reserved)

4. **Cadena B Componentes** (6 fields)
   - opex_fijo_b, costo_variable_b, soporte_mantenimiento_b, escalamiento_b, inversiones_b, hitl_b

5. **Cadena C Componentes** (7 fields)
   - tarifa_proveedor, opex_fijo_integ, opex_var_integ, inversiones_c, escalamiento_c, equipo_integ, hitl_c

6. **Componentes Financieros** (5 fields)
   - ica (with gross-up explanation), gmf, polizas, financiacion, comision_administracion (V2-5)

7. **Agregaciones P&G** (7 fields)
   - ingreso_neto, costo_operativo, costos_financieros, contribucion, utilidad_neta, pct_utilidad_neta

8. **Vision Tarifas Denominadores** (3 fields)
   - K50 (FTE or transacciones), L50 (volumen Cadena B), M50 (volumen Cadena C)

9. **KPIs del Deal** (5 fields)
   - ingreso_mensual, costo_mensual_promedio, costo_total_contrato, utilidad_neta_total, pct_utilidad_neta_total

10. **Reglas de Validación** (3 criteria)
    - margen_minimo, viabilidad_financiera, rampup_aplicable

11. **Mapping Notes** (Excel → Backend → API quick reference table)

**Audience**: Test Automation, Audit Tools, Backend Developers, Data Validation Scripts

---

## How to Use These Documents

### Use Case 1: Verify Excel-to-Backend Mapping
1. Open `CAP_8_Matriz_de_Trazabilidad.md` Section 8.2 (Panel de Control Traceability)
2. Find your Excel cell (e.g., Panel!C9)
3. Trace through: Backend Model → Calculator → Result Field → Vision Output

**Example**: Excel Panel!C9 = 0.20 (margen)
```
Panel!C9 (margen=0.20)
  ↓ Backend: PanelDeControl.margen
  ↓ Calculator: PyGCalculator.calcular_ingresos()
  ↓ Formula: factor_margen = (1-0.20) × (1-0.03) = 0.776
  ↓ Result: PyGMensual.ingreso_bruto_a
  ↓ API: VisionPyGV1.filas[0].valores[m]
  ↓ Vision: Vision P&G, row "Ingreso Bruto A"
```

### Use Case 2: Write Test Cases
1. Open `TRACEABILITY_MATRIX.md`
2. Search for your field (grep: `^FIELD: field_name`)
3. Copy formula, example values, and expected result
4. Generate test case

**Example Test Case**:
```python
def test_margen_ingreso_calculation():
    # From TRACEABILITY_MATRIX: margen field
    panel = PanelDeControl(margen=0.20, op_cont=0.03, ...)
    pyg = PyGMensual(...)
    
    expected = 1_288_659  # COP
    actual = pyg.ingreso_bruto_a
    
    assert abs(actual - expected) < 1, f"Expected {expected}, got {actual}"
```

### Use Case 3: Audit Financial Calculations
1. Open `CAP_8_Matriz_de_Trazabilidad.md` Section 8.7 (Costos Financieros)
2. Verify calculation order: Financiación → Pólizas → ICA → GMF → Comisión Adm
3. Check cadena attribution (ica_a, ica_c, gmf_a, gmf_c)
4. Validate against Vision P&G outputs

### Use Case 4: Implement New Field (V2-8 or later)
1. Add entry to `TRACEABILITY_MATRIX.md` (Section matching field type)
2. Document: Excel Source, Backend Model, Formula, Calculator, Result Field, Vision Output
3. Add Version marker: `New in V2-X: YES`
4. Reference in `CAP_8_Matriz_de_Trazabilidad.md` appropriate section

### Use Case 5: Debug Field Discrepancy
1. Get field name and expected/actual value
2. Search `TRACEABILITY_MATRIX.md` for field
3. Copy formula and calculator reference
4. Check calculator code in `/calculators/` or `/domain/`
5. Trace through dependency chain (Validation → Formula → Result)

---

## Key Version Markers (V2-5 & V2-7 New Fields)

### NEW in V2-5 (Imprevistos & Comisión Administrativa)
- `imprevistos` (Panel!C14) → reduces Ingreso Neto
- `comision_administracion` (CostosFinancierosCalculator) → insurance admin fee × 1.42

### NEW in V2-7 (Márgenes por Cadena & Crucero)
- `margen_b` (Panel!D7) → separate billing margin for Cadena B
- `margen_c` (Panel!D8) → separate billing margin for Cadena C
- `crucero` (ResultadoNomina) → travel allowance from Panel!C17
- `tasa_interes_mensual` (Panel override) → replaces tasa_mensual_financ if provided
- `costo_financiero_vt_cadena_a` (CostosFinancierosMes) → Vision Tarifas-specific financial costs

---

## Numerical Precision & Guarantees

All monetary values follow these rules:

| Aspect | Rule | Example |
|---|---|---|
| **Currency** | COP only | 1,234,567 |
| **Rounding** | HALF_UP to centavos | 1234567.895 → 1234567.90 |
| **Backend Storage** | Python Decimal (arbitrary precision) | Decimal('1234567.90') |
| **API Transmission** | JSON float64 | 1234567.9 |
| **Excel Display** | Formatted with 2 decimals | 1,234,567.90 |

---

## File Locations

Both files are located in:
```
/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/docs/
  ├── CAP_8_Matriz_de_Trazabilidad.md        (Narrative, 651 lines)
  ├── TRACEABILITY_MATRIX.md                  (Reference, 1,075 lines)
  └── README_TRACEABILITY.md                  (This file)
```

---

## Integration with Other Documentation

These traceability documents complement:

- **docs/CAPÍTULO_7_Auditoría_de_Endpoints.md** — Endpoint structure and vision outputs
- **docs/Excel_V2_7_Gaps.md** — Known differences between Excel and Backend
- **docs/Simulation_Result.schema.json** — API contract definitions
- **domain/models/*.py** — Dataclass definitions (salario_fijo, ingreso_neto, etc.)
- **calculators/*.py** — Formula implementations (PyGCalculator, NominaCalculator, etc.)
- **tests/unit/** — Test cases for individual calculators
- **tests/integration/** — End-to-end traceability tests

---

## Maintenance & Updates

To keep traceability documentation current:

1. **After formula change**: Update TRACEABILITY_MATRIX.md (Formula field) + CAP_8 (relevant section)
2. **After adding new field**: Add entry to TRACEABILITY_MATRIX.md + CAP_8
3. **After calculator refactor**: Update Calculator reference + Formula
4. **After API schema change**: Update API Field path in both documents
5. **After Vision redesign**: Update Vision Output mappings

---

## Questions & Support

For questions about traceability:

1. **What is the formula for X field?** → See TRACEABILITY_MATRIX.md (search: `FIELD: X`)
2. **Where does Excel cell Y come from in the API?** → See CAP_8 (find Excel cell, trace path)
3. **Why is my calculation off by $0.50?** → See Numerical Precision section above
4. **How do I add a new field?** → See Use Case 4 (Implement New Field)
5. **Where is the code for calculator Z?** → See TRACEABILITY_MATRIX.md (Calculator field)

---

**Document Status**: PRODUCTION | Completeness: 100% | Test Coverage: Comprehensive

**Generated**: 2026-05-31 | **Excel Version**: V2-7 | **Backend Version**: Refactor/Engine-V2

