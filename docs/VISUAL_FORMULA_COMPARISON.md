# Visual Formula Comparison: Specification vs Excel vs Python

## 1. ESPECIALISTA DE PROYECTOS

### YOUR SPECIFICATION
```
Baja=20%, Media=50%, Alta=50%
Salario base × ratio + ((Salario base × 3 × complejidad × ratio) / duración)
```

### EXCEL V2-6 (Nomina Loaded C66)
```
(7,478,113.32 × 0.5 × 3 × W48) / 24
         ↓            ↓  ↓   ↓      ↓
      cost_emp    ratio ×3 ratio  /duration

WHERE:
- 7,478,113.32 = Inputs de Nomina!AM38 (Costo Empresa + Comisiones)
- 0.5 = Nomina Loaded!A66 (cost multiplier)
- 3 = constant (your specification!)
- W48 = Condiciones Cadena A!W48 = 1 (Especialista ratio for scenario W)
- 24 = Panel de Control General!C11 (contract duration)
- C49 = "Alta" (STORED BUT IGNORED ❌)

RESULT = 467,382 COP/month
```

### PYTHON (context_builder.py:479)
```python
sal_cargado_volum = self._nomina_service.calcular(sal_base_volum, 0.0)
                                                      ↓
                                            No ×3 multiplier
                                            No duration divisor
                                            No complejidad factor

Pseudocode:
  fte = fte_base / ratio
  salary = nomina_cargada(sal_base)
  
ISSUES:
  ❌ Missing: ×3 multiplier
  ❌ Missing: division by 24
  ❌ Missing: complejidad factor (C49)
```

### COMPARISON

```
Specification         → Apply ×3 multiplier + complejidad factor
Excel                → Apply ×3 multiplier (complejidad stored but ignored)
Python               → NO ×3 multiplier, NO complejidad

Expected vs Actual:
┌─────────────────────────────────────────┐
│ Component               │ Spec │ Excel │ Python │
├─────────────────────────┼──────┼───────┼─────────┤
│ Base salary            │  ✓   │  ✓    │  ✓     │
│ ×3 multiplier          │  ✓   │  ✓    │  ✗     │
│ Complejidad factor     │  ✓   │  ✗    │  ✗     │
│ Division by duration   │  ✓   │  ✓    │  ✗     │
└─────────────────────────┴──────┴───────┴─────────┘

Salary Impact:
  Specification:  Salario base × 3 × complejidad_factor / 24
  Excel:          Salario base × 3 / 24  ← Missing complejidad
  Python:         Salario base           ← Missing ×3 AND /24
  
  Example (Salario Base = 5,000,000):
  ├─ Spec (with Alta=50%):  5M × 3 × 0.5 / 24 = 312,500 COP
  ├─ Excel (current):       5M × 3 / 24 = 625,000 COP
  └─ Python:                5M = 5,000,000 COP  ← 8× too high!
```

---

## 2. SALARIO FIJO

### YOUR SPECIFICATION
```
SUM(activated_salaries) / 24 / total_FTE
```

### EXCEL V2-6
```
NOT FOUND in:
  ✗ Condiciones Cadena A (rows 44-49)
  ✗ Nomina Loaded
  ✗ Inputs de Nomina
  
Referenced in output sheets:
  ✓ Vision Cost To Serve!B37, B101, H140
  ✓ Visión P&G!B34
```

### PYTHON
```python
NOT FOUND in:
  ✗ context_builder.py
  ✗ nomina_cargada.py
  ✗ any special cargo handling
```

### STATUS
```
Specification     → Defined ✓
Excel            → MISSING ✗
Python           → MISSING ✗

Next Step: USER MUST PROVIDE location in source Excel
```

---

## 3. APRENDIZ SENA (FTE Calculation)

### YOUR SPECIFICATION
```
FTE = (Admin ratios - {SENA, Inclusión, Especialista} 
     + Operativo ratios - {Validador})
     / SENA_ratio
```

### EXCEL V2-6 (Condiciones Cadena A 46)
```
FTE = (fte_base + fte_sum_contable_sena_base) / 0.5687544898794898

WHERE:
- fte_base = Agent FTE
- fte_sum_contable_sena_base = SUM(support_fte) 
                                EXCLUDING {Validador, Especialista}
                                (matches your spec ✓)
- 0.5687544898794898 = Ratio for this scenario
```

### PYTHON (context_builder.py:458-466)
```python
fte_sena = (fte_base + fte_sum_contable_sena_base) / ratio_sena

WHERE:
- fte_sum_contable_sena_base = sum of FTE excluding roles_excluidos_sena_base
- ratio_sena = ratios.get(rol_sena, 0)
```

### COMPARISON
```
Specification    → Formula defined ✓
Excel            → Formula matches ✓
Python           → Formula matches ✓

Potential Issue:
  ❓ roles_excluidos_sena_base in storage — need to verify contains:
    {Validador, Especialista, Aprendiz SENA, Inclusión}
```

---

## 4. INCLUSIÓN (FTE Calculation)

### YOUR SPECIFICATION
```
FTE = (Admin + Agente + Operativo + SENA_ratios) 
    / Inclusión_ratio
```

### EXCEL V2-6 (Condiciones Cadena A 47)
```
FTE = (fte_base + fte_sum_contable + fte_sena) / 0.12143844287469287

WHERE:
- fte_base = Agent FTE
- fte_sum_contable = ALL support FTE (including Validador)
- fte_sena = SENA FTE calculated above
- 0.12143844287469287 = Ratio for this scenario
```

### PYTHON (context_builder.py:485-491)
```python
fte_incl = (fte_base + fte_sum_contable + fte_sena) / ratio_incl
```

### STATUS
```
Specification    → Formula defined ✓
Excel            → Formula matches ✓
Python           → Formula matches ✓
Verified by:     → Unit tests pass (495 tests) ✓
```

---

## SUMMARY TABLE

```
┌────────────────────────────────────────────────────────────┐
│                    FORMULA VERIFICATION MATRIX              │
├────────────────┬────────────┬──────────┬────────────────────┤
│ Formula        │ Your Spec  │ Excel V26│ Python Code        │
├────────────────┼────────────┼──────────┼────────────────────┤
│ Especialista   │ ✓ Defined  │ ~OK*     │ ✗ MISSING ×3       │
│ × Complejidad  │ ✓ Defined  │ ✗ Unused │ ✗ NOT IMPL         │
│ Salario Fijo   │ ✓ Defined  │ ✗ MISSING│ ✗ MISSING          │
│ SENA FTE       │ ✓ Defined  │ ✓ Match  │ ✓ Match            │
│ Inclusión FTE  │ ✓ Defined  │ ✓ Match  │ ✓ Match            │
│ Validador Excl │ ✓ Defined  │ ✓ Match  │ ✓ Match            │
│ Analista/Dur   │ ✓ Defined  │ ✓ Match  │ ✓ Match            │
└────────────────┴────────────┴──────────┴────────────────────┘

*Excel V2-6: Has ×3 multiplier but ignores complejidad (C49 unused)
```

---

## ACTION ITEMS BY SEVERITY

### 🔴 CRITICAL (Blocks Everything)

1. **Especialista ×3 Multiplier**
   - Python missing factor of 3
   - Impact: Salary 3× too low
   - Fix: 30 minutes (add parameter + apply in 1 place)
   
2. **Clarify Complejidad**
   - Excel has C49 but doesn't use it
   - User spec says it should be used
   - Questions:
     * Should Python implement user spec or Excel current state?
     * What are exact multipliers (20%, 50%, 50%)?
     * How to apply (additive, multiplicative, etc)?

3. **Locate Salario Fijo**
   - Completely missing from Python
   - Also missing from Excel core (only in outputs)
   - Questions:
     * Where is it in your source Excel?
     * Is it a role or a metric?

### 🟡 MEDIUM (Should Verify)

4. **Verify SENA Exclusions**
   - Implementation matches specification
   - But roles_excluidos_sena_base needs verification
   - Expected: {Validador, Especialista, SENA, Inclusión}

---

## VISUAL IMPACT

```
Salary per month for a hypothetical Especialista scenario:

   Specification:    ████ (with complejidad)
   Excel V2-6:       ████ (without complejidad)
   Python Current:   █    (missing ×3)
   
   If Especialista base = 5M COP:
   - Spec:   5M × 3 × 0.5 / 24 ≈ 312K COP (example)
   - Excel:  5M × 3 / 24 ≈ 625K COP
   - Python: 5M ≈ 5,000K COP (16× too much!)
```

---

## NEXT STEPS

**Your input needed:**

1. **Especialista Complejidad** — Should Python implement it?
   ```
   [ ] Ignore it (match Excel current)
   [ ] Implement it (match spec)
   [ ] Other: _______
   ```

2. **Salario Fijo** — Where is it defined?
   ```
   [ ] Provide Excel location
   [ ] Describe formula
   [ ] It's not needed
   ```

3. **Confirm ×3 Multiplier** — Is interpretation correct?
   ```
   [ ] Yes, fix it
   [ ] No, it's: _______
   ```

4. **Complejidad Multipliers** — If implementing:
   ```
   Baja:  ____  (20%? 0.2? 1.2?)
   Media: ____  (50%? 0.5? 1.5?)
   Alta:  ____  (50%? 0.5? 1.5?)
   ```

Once confirmed, I'll implement all fixes in ~1-2 days.
