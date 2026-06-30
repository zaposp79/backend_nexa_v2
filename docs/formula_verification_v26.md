# Formula Verification Report: Special Cargo Calculations
## Excel V2-6 vs. User Specification vs. Python Implementation

**Date:** 2026-05-26
**Status:** ⚠️ **CRITICAL GAPS IDENTIFIED**

---

## Executive Summary

Analysis of the seven special cargo formulas you specified against Excel V2-6 and the current Python code reveals **THREE CRITICAL GAPS**:

1. **Especialista de Proyectos complejidad factor** — NOT IMPLEMENTED in Excel V2-6 ❌
2. **Salario Fijo** — NOT FOUND in Excel V2-6 ❌
3. **Exclusion logic for SENA/Inclusión/Validador** — NEEDS VERIFICATION ⚠️

---

## Formula-by-Formula Analysis

### 1. ESPECIALISTA DE PROYECTOS

#### Your Specification:
```
Complejidad levels: Baja=20%, Media=50%, Alta=50%
Formula: Salario base * ratio + ((Salario base * 3 * complejidad * ratio) / duración del contrato)
```

#### Excel V2-6 Implementation:
**Location:** `Nomina Loaded!C66` (and D66:M66 for other scenarios)

```excel
=IFERROR(IF(C$42<>"",
  (INDEX('Inputs de Nomina'!$AM$16:$AM$51,
    MATCH($B66,'Inputs de Nomina'!$B$16:$B$51,0)
  ) * $A$66 * 3 * 'Condiciones Cadena A'!W48) 
  / 'Panel de Control General'!$C$11,
  0), 0)
```

**Components:**
- `INDEX(...)` from 'Inputs de Nomina' col AM (Costo Empresa + Comisiones): 7,478,113.32
- `$A$66` = 0.5 (ratio multiplier)
- `3` = constant multiplier
- `'Condiciones Cadena A'!W48` = 1 (Especialista ratio for scenario W)
- `'Panel de Control General'!$C$11` = 24 (contract duration)

**Calculated Formula:**
```
(7,478,113.32 × 0.5 × 3 × 1) / 24 = 467,382.08 per month
```

#### Python Implementation:
**Location:** `input/context_builder.py`, lines 472-483

```python
for rol_volum in roles_fte_volumetrico:
    ratio_volum = ratios.get(rol_volum, 0)
    if ratio_volum > 0:
        fte_volum = fte_base / ratio_volum
        sal_base_volum   = self._prov.get_salario_rol(rol_volum)
        sal_cargado_volum = self._nomina_service.calcular(sal_base_volum, 0.0)
        perfiles.append(self._perfil_soporte(
            rol_volum, fte_volum, sal_base_volum, sal_cargado_volum,
            mes_ajuste, canal=perfil_base.canal
        ))
```

**Current behavior:** Simply calculates `FTE = fte_base / ratio` and applies standard nomina cargada. **NO complejidad factor applied.**

#### Gap Analysis: ❌ **CRITICAL**
- ✅ Excel uses a `*3` multiplier (which you specified)
- ✅ Excel calculates compound formula with ratio
- ✅ Excel divides by duration (24)
- ❌ **Excel does NOT reference C49 (Complejidad: "Alta"/"Media"/"Baja")**
- ❌ **Excel hardcodes W48=1 instead of dynamic complejidad factor**
- ❌ **Python ignores the `*3` multiplier entirely**
- ❌ **Python does NOT apply any complejidad-based adjustment**

**Recommendation:** The Excel V2-6 implementation appears incomplete. The complejidad factor (Baja=20%, Media=50%, Alta=50%) is defined in C49 but NOT USED in the salary calculation. Either:
1. The Excel formula needs to reference C49 and apply the complejidad percentage to W48, OR
2. The user specification was aspirational and the current Excel is the "source of truth"

---

### 2. SALARIO FIJO

#### Your Specification:
```
Formula: Sumatoria de todos los salarios de los activados cargos / duración del contrato (24) 
         y resultado de esto se divide entre el total de FTE (Inbound y Outbound)
```

#### Excel V2-6 Search Results:
- 🔍 Found "Salario Fijo" label in:
  - `Vision Cost To Serve!B37`, B101, H140
  - `Visión P&G!B34`
- 🔍 **No salary calculation for "Salario Fijo" role found in the core input sheets**
- ❌ **No dedicated "Salario Fijo" row in `Condiciones Cadena A` (rows 44-49 are: Agente, Validador, SENA, Inclusión, Especialista)**

**Status:** Not yet located in Excel V2-6 structure

#### Python Implementation:
- ❌ **NOT FOUND in `input/context_builder.py`**
- `roles_fte_volumetrico` only includes Especialista de Proyectos
- No "Salario Fijo" entry in the reglas_staff or ratios

#### Gap Analysis: ❌ **NOT FOUND**
This role may be a future addition or may be calculated in a different part of the model (e.g., as an average across scenarios).

---

### 3. APRENDIZ SENA

#### Your Specification (Part A - FTE Calculation):
```
FTE = Sumatoria de todos ratios de los cargos tipo 'Administrativo' 
      excluyendo: 'Aprendiz SENA', 'Inclusión' y 'Especialista de Proyectos'
    + Sumatoria de todos ratios de los cargos tipo 'Operativo'
      excluyendo: 'Validador'
    / [ratio for SENA]
```

#### Your Specification (Part B - Alternative FTE):
```
FTE / Agentes = Sumatoria de todos los cargos tipo Administrativo + tipo Operativo 
                excluyendo al cargo 'Validador' 
              / cantidad de agentes
```

#### Excel V2-6 Implementation:
**Location:** `Condiciones Cadena A` row 46

```excel
Ratio (W46): 0.5687544898794898  [for scenario W]
FTE = (fte_base + fte_sum_contable_sena_base) / 0.5687544898794898
```

Where `fte_sum_contable_sena_base` = sum of FTE for roles in `roles_excluidos_sena_base` set.

#### Python Implementation:
**Location:** `input/context_builder.py`, lines 458-466

```python
fte_sena = 0.0
ratio_sena = ratios.get(rol_sena, 0)
if ratio_sena > 0:
    fte_sena = (fte_base + fte_sum_contable_sena_base) / ratio_sena
    sal_base_sena    = self._prov.get_salario_rol(rol_sena)
    sal_cargado_sena = self._nomina_service.calcular_aprendiz(sal_base_sena)
```

#### Gap Analysis: ⚠️ **NEEDS VERIFICATION**
- ✅ Python uses same formula as Excel
- ✅ Python excludes `roles_excluidos_sena_base` from the sum
- ❓ **VERIFY:** Which roles are in `roles_excluidos_sena_base`? Does it match your "Administrative + Operativo excluding Validador" specification?
- ❓ **VERIFY:** Does the ratio in storage match Excel row 46 (0.5687544898794898)?

**Action needed:** Verify storage/reglas/staff_rules.json contains the correct exclusion list.

---

### 4. INCLUSIÓN

#### Your Specification:
```
FTE = Σ(FTE/Agentes de tipo 'Administrativo', 'Agente', 'Operativo', y el cargo 'Aprendiz SENA')
    / Agentes[Inclusión][perfil i]
```

#### Excel V2-6 Implementation:
**Location:** `Condiciones Cadena A` row 47

```
FTE = (fte_base + fte_sum_contable + fte_sena) / ratio_incl
```

Where `fte_sum_contable` = all support FTE (including Validador, unlike SENA).

#### Python Implementation:
**Location:** `input/context_builder.py`, lines 485-491

```python
ratio_incl = ratios.get(rol_inclusion, 0)
if ratio_incl > 0:
    fte_incl = (fte_base + fte_sum_contable + fte_sena) / ratio_incl
    sal_base_incl    = self._prov.get_salario_rol(rol_inclusion)
    sal_cargado_incl = self._nomina_service.calcular_aprendiz(sal_base_incl)
```

#### Gap Analysis: ✅ **MATCHES**
- ✅ Python formula matches Excel exactly
- ✅ Includes fte_base (Agente), fte_sum_contable (all support), and fte_sena
- ✅ Divides by ratio_incl

---

### 5. VALIDADOR

#### Your Specification (implicit):
Validador is referenced as a role that should be EXCLUDED from SENA calculations.

#### Excel V2-6 Implementation:
**Location:** `Condiciones Cadena A` row 45

- Validador has its own ratio (W45: 0.2)
- Validador is explicitly excluded from `roles_excluidos_sena_base` (per line 404 comment in context_builder.py)

#### Python Implementation:
✅ **Matches Excel** — Validador is in the exclusion list for SENA FTE calculation.

---

### 6. ANALISTA PROF. DE SELECCIÓN (INICIAL/ROTACIÓN)

#### Your Specification:
```
Salary divided by contract duration for:
- Analista Prof. De Selección (Inicial) / duración del contrato
- Analista 1 de Reclutamiento (Inicial) / duración del contrato
- Analista Prof. De Selección (Rotación)
- Analista 1 de Reclutamiento (Rotación)
- Aprendiz SENA
- Inclusión
- Especialista de Proyectos
```

#### Excel V2-6 Implementation:
- ✅ Roles with INICIAL status: divided by `meses_contrato` (24 months)
- ✅ Roles with ROTACIÓN status: prorated by rotation percentage
- ✅ Implementation in `input/context_builder.py` lines 430-438:
  ```python
  elif rol in roles_rotacion:
      fte_contable = fte_base / ratio * pct_rotacion
      fte_billing  = fte_contable
  elif rol in roles_inicial:
      fte_contable = fte_base / ratio
      fte_billing  = fte_contable / meses_contrato
  ```

#### Gap Analysis: ✅ **MATCHES**

---

### 7. VALIDADOR EXCLUSION

#### Your Specification (implicit):
Validador should be excluded from certain base calculations (not part of the "base" FTE for SENA).

#### Implementation:
✅ **Correct** — Validador is in `roles_excluidos_sena_base` per Excel V2-4 specification.

---

## Summary Table

| Cargo | User Spec | Excel V2-6 | Python Code | Status |
|-------|-----------|-----------|-------------|--------|
| **Especialista Proyectos** (complejidad) | Define Baja/Media/Alta multipliers | Hardcoded W48=1, C49 unused | Uses simple ratio only | ❌ GAP |
| **Especialista Proyectos** (×3 multiplier) | ✓ Specified | ✓ Uses *3 | ✗ Missing | ❌ GAP |
| **Salario Fijo** | Define formula | Not found in V2-6 | Not implemented | ❌ NOT FOUND |
| **Aprendiz SENA** (FTE) | Exclude Admin/Operativo | Uses ratio from storage | Uses same ratio logic | ⚠️ VERIFY |
| **Inclusión** (FTE) | Include all support+SENA | Sum all + SENA / ratio | Matches Excel | ✅ OK |
| **Validador** (exclusion) | Exclude from SENA base | Excluded | Excluded | ✅ OK |
| **Analista Selección** (duration) | Divide by 24 | Divide by meses_contrato | Divide by meses_contrato | ✅ OK |

---

## Critical Actions Required

### 1. **Clarify Especialista de Proyectos Complejidad** 🔴 BLOCKING
- [ ] Confirm: Should C49 value ("Alta"/"Media"/"Baja") dynamically affect Especialista salary?
- [ ] If yes: Update Excel to reference C49 and apply the 20%/50%/50% multipliers
- [ ] If no: Remove complejidad from user specification

### 2. **Implement Especialista ×3 Multiplier in Python** 🔴 HIGH PRIORITY
- [ ] Update `nomina_cargada.py` to support an optional multiplier parameter
- [ ] Update `context_builder.py` line 479 to pass `multiplier=3.0` for Especialista roles
- [ ] Verify calculation matches Excel: `(cost * 0.5 * 3 * ratio) / 24`

### 3. **Locate/Implement Salario Fijo** 🔴 HIGH PRIORITY
- [ ] Search for "Salario Fijo" definition in user's source Excel
- [ ] Clarify: Is this a separate staff role or a calculated average?
- [ ] If role: Add to `Condiciones Cadena A` with formula
- [ ] If average: Document where it should be calculated

### 4. **Verify SENA/Inclusión Exclusions** 🟡 MEDIUM PRIORITY
- [ ] Check `storage/reglas/staff_rules.json` for `roles_excluidos_sena_base`
- [ ] Confirm matches your "Administrative + Operativo excluding Validador"
- [ ] Add unit tests for exclusion logic

---

## Files to Update

1. **`input/context_builder.py`** (lines 472-483)
   - Add multiplier support for Especialista de Proyectos
   - Reference complejidad factor when calculating salary

2. **`domain/services/nomina_cargada.py`**
   - Add optional `multiplier` parameter to cost calculation

3. **`storage/reglas/staff_rules.json`** (if exists)
   - Verify `roles_excluidos_sena_base` definition
   - Verify Especialista complejidad mappings

4. **`docs/formulas/` (NEW)**
   - Create definitive formula documentation
   - Include Salario Fijo definition

---

## Next Steps

1. **Confirm** which gaps are actual bugs vs. specification changes
2. **Prioritize** Especialista complejidad implementation (highest impact)
3. **Create** unit tests for each formula verification
4. **Update** Excel V2-6 if formulas are incomplete
5. **Regenerate** baseline after fixes
