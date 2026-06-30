# CADENA_C_ACTIVE_BASELINE_PREP

**Preparación de línea base real para Cadena C**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **COMPLETED**

---

## Objetivo

Preparar una línea base oficial para Cadena C **activa** (IA/Automation) antes de ejecutar FORMULA_REFACTOR_PHASE4_CADENA_C.

**Por qué:** El `request/request.json` canónico tiene Cadena C desactivada (`activa: False`). Para auditar Cadena C correctamente, necesitamos un baseline con Cadena C produciendo costo > 0.

---

## Contexto

### Status previo
- ✅ FORMULA_REFACTOR_PHASE1_NOPAYROLL — Completado
- ✅ FORMULA_REFACTOR_PHASE2_CADENA_B — Completado
- ✅ FORMULA_REFACTOR_PHASE3_COSTOS_FINANCIEROS — Completado
- ✅ baseline_formula_snapshot_v1.json — Oficial (Cadena A + B solamente)

### Cadena C en request.json
```json
"condiciones_cadena_c": {
  "canales": [],           // Vacío (desactivado)
  "equipo_transversal": [], // Sin personal
  "inversion_anual": 0.0
}
```

---

## 1. Estructura de Cadena C en el código

### DTOs esperados (user_input_builders_cadena_c.py)

```python
CondicionesCadenaCInput:
  - canales: List[CanalCadenaCInput]
    - nombre: str
    - modalidad: str (Inbound/Outbound)
    - volumen_mensual: float
    - activo: bool
    - tarifa_unitaria: float
    - opex_fijo_integ: float
    - opex_var_integ: float
    - pct_escalamiento: float
    - costo_escalamiento: float
  
  - equipo_transversal: List[MiembroEquipoTransversalInput]
    - rol: str
    - activo: bool
    - pct_dedicacion: float
    - salario_cargado: float (opcional)
  
  - equipo_hitl: List[EquipoHITLItemInput]
  - opex_dispositivos_por_persona: float
  - inversion_anual: float
```

---

## 2. Fixture de Cadena C Activa

### Archivo: `tests/refactor/request_cadena_c_active.json`

Basado en `request/request.json` canónico, con Cadena C configurada:

```json
"condiciones_cadena_c": {
  "canales": [
    {
      "nombre": "Chatbot IA",
      "modalidad": "Inbound",
      "volumen_mensual": 15000.0,
      "activo": true,
      "tarifa_unitaria": 200.0,
      "opex_fijo_integ": 5000000.0,
      "opex_var_integ": 0.0,
      "pct_escalamiento": 0.1,
      "costo_escalamiento": 50000.0
    },
    {
      "nombre": "RPA Cobranza",
      "modalidad": "Outbound",
      "volumen_mensual": 8000.0,
      "activo": true,
      "tarifa_unitaria": 150.0,
      "opex_fijo_integ": 3000000.0,
      "opex_var_integ": 0.0,
      "pct_escalamiento": 0.05,
      "costo_escalamiento": 30000.0
    }
  ],
  "equipo_transversal": [
    {
      "rol": "IA Engineer",
      "activo": true,
      "pct_dedicacion": 100.0,
      "salario_cargado": 7000000.0
    },
    {
      "rol": "Data Scientist",
      "activo": true,
      "pct_dedicacion": 50.0,
      "salario_cargado": 6000000.0
    }
  ],
  "equipo_hitl": [],
  "opex_dispositivos_por_persona": 0.0,
  "inversion_anual": 24000000.0
}
```

---

## 3. Baseline Snapshot para Cadena C

### Archivo: `tests/refactor/baseline_formula_snapshot_cadena_c_v1.json`

Snapshot generado del motor ejecutando `request_cadena_c_active.json`.

**Valores key:**
- `simulation_id`: `baseline_cadena_c_v1`
- `pyg_por_mes[0].costo_c`: 101,200,000.0 (mes 1)
- **Total costo_c contrato**: 2,491,534,080.0 (24 meses)

---

## 4. Test Fixture

### Archivo: `tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py`

Sigue patrón idéntico a `test_baseline_formula_snapshot_v1.py`:

**Tests:**
1. `test_engine_runs_request` — Motor ejecuta sin error
2. `test_pricing_result_is_valid` — Todas las visiones presentes (24 meses)
3. `test_snapshot_parity` — Output coincide bit-a-bit con snapshot (ignora timestamps)
4. `test_costo_c_positive` — Validación que Cadena C produce costo > 0
5. `test_cadena_c_anchor_values` — Anclas numéricas: costo_c mes1 = 101,200,000.0

---

## 5. Validación Ejecutada

### Tests corridos

```bash
PYTHONPATH=$(pwd) pytest \
  backend_nexa/tests/refactor/test_input_contract_fix_b1.py \
  backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py \
  backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py \
  backend_nexa/tests/golden/ -q

# Result: 80 tests PASSED ✅
#   - test_input_contract_fix_b1.py:           12 PASSED
#   - test_baseline_formula_snapshot_v1.py:     5 PASSED
#   - test_baseline_formula_snapshot_cadena_c_v1.py: 5 PASSED
#   - tests/golden/:                           58 PASSED
```

### Validaciones

| Aspecto | Estado |
|--------|--------|
| Motor ejecuta sin error con Cadena C activa | ✅ CORRECTO |
| PricingResult válido (todas las visiones) | ✅ CORRECTO |
| Snapshot parity (bit-by-bit, ignora timestamps) | ✅ CORRECTO |
| costo_c mes1 > 0 | ✅ 101,200,000.0 |
| costo_c total contrato > 0 | ✅ 2,491,534,080.0 |
| Rounding/formulas intactas | ✅ CORRECTO |
| Golden tests sin regresiones | ✅ 58/58 PASSED |

---

## 6. Artefactos Creados

### Fixtures y baselines
- ✅ `tests/refactor/request_cadena_c_active.json` — Request canónico con Cadena C activa
- ✅ `tests/refactor/baseline_formula_snapshot_cadena_c_v1.json` — Snapshot oficial Cadena C
- ✅ `tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py` — Test fixture Cadena C

### Documentación
- ✅ `docs/refactor/cadena_c_active_baseline_prep.md` — Esta documentación

---

## 7. Notas para FORMULA_REFACTOR_PHASE4_CADENA_C

### Requisitos cumplidos
✅ Baseline oficial existe con Cadena C activa  
✅ Test fixture preparado  
✅ Costo_c validado > 0  
✅ Todas las visiones funcionales  
✅ Golden tests pasan sin regresiones

### Scope de PHASE4
Cuando ejecutes FORMULA_REFACTOR_PHASE4_CADENA_C:

1. Audita `modules/cadena_c/` (similar a PHASE1/PHASE2/PHASE3)
2. Agrega `FORMULA_ID` internos (cero runtime impact)
3. Valida contra `baseline_formula_snapshot_cadena_c_v1.json`
4. Ejecuta:
   ```bash
   pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
   pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
   pytest backend_nexa/tests/golden/ -q
   ```
5. Confirma costo_c sigue siendo 101,200,000.0 mes1

---

## Cierre

✅ **Estado:** COMPLETED  
✅ **Artefactos:** 3 archivos (request, snapshot, test)  
✅ **Validación:** 80/80 tests PASSED  
✅ **Cadena C activa:** costo_c = 2.49B total (101.2M/mes)  
✅ **Listo para:** FORMULA_REFACTOR_PHASE4_CADENA_C

---

## Comparación con request.json canónico

| Campo | request.json | request_cadena_c_active.json |
|-------|--------------|-------------------------------|
| condiciones_cadena_a | Activa (26 FTE) | Idéntica |
| condiciones_cadena_b | Activa (3 canales) | Idéntica |
| condiciones_cadena_c | Inactiva (vacía) | Activa (2 canales + 2 roles) |
| polizas | Idénticas | Idénticas |
| datos_operativos | Idénticos | Idénticos |

**Cambio único:** `condiciones_cadena_c` de vacío a configurado con IA channels.
