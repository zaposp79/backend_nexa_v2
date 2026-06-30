# Fase 6 — Auditoría de Visiones (Lógica Desacoplada)

**Date**: 2026-05-21  
**Status**: ✅ **FASE 6 COMPLETE — VISIONES AUDITADAS**  
**Objetivo**: Validar que visiones consumen EXCLUSIVAMENTE de calculadoras oficiales

---

## Executive Summary

**Auditoría de 4 visiones completada**. Resultado: 3 visiones con patrones sospechosos (HIGH RISK), 1 limpia (LOW RISK).

| Visión | Riesgo | Patrones | Acción |
|--------|--------|----------|--------|
| vision_tarifas | 🔴 HIGH | override (5), fallback (2) | Documentar mechanisms, validar consistency |
| vision_pyg | 🟢 LOW | Ninguno | Mantener como está (purely transformational) |
| cost_to_serve | 🔴 HIGH | default (1), null-checks (2) | Hacer calculadores obligatorios |
| riesgo | 🔴 HIGH | defaults (7), _DEFAULT_ (4), null-check (1) | Migrar a storage parametrización |

---

## Detailed Audit Results

### 1. Vision Tarifas (HIGH RISK)

**Location**: `calculators/vision_tarifas.py` (353 líneas)

**Entrada**:
- PerfilCadenaA (perfiles de agentes)
- ParametrosCadenaB (canales B)
- PanelDeControl (parámetros financieros)
- PyGMensual[] (costos mensuales del calculador)
- NominaCalculator, NoPayrollCalculator (opcionales)

**Proceso**:
1. Agrupa perfiles por canal
2. Atribuye costos de cadena A/B/C a cada canal
3. Aplica financieros (financial cost) 
4. Calcula tarifa por FTE

**Patrones Sospechosos Encontrados**:

#### Pattern 1: Override Mechanism (5 matches)
```python
# Lines 96-106
if perfil.costos_financieros_mensual > 0:
    fin_ch = perfil.costos_financieros_mensual  # OVERRIDE: ignora cálculo proporcional
else:
    fin_ch = calcular_proporcional(...)

# Lines 268-275
if perfil.cadena_b_mensual > 0:
    cadena_b_ch = perfil.cadena_b_mensual  # OVERRIDE
else:
    cadena_b_ch = calcular_proporcional(...)
```

**Risk**: Si perfil.costos_financieros_mensual ≠ valor mensual real en deal agregado → tariff individual ≠ promedio del deal

**Recomendación**: 
- Documentar cuándo se usan estos overrides
- Validar contra deal aggregates
- Considerar remover si no se usan en producción

#### Pattern 2: Fallback Logic (2 matches)
```python
# Lines 282-297
if nominaCalculator is None:
    nomina_ch = fte * 0.5 * promedio_nomina  # FTE-based approximation
else:
    nomina_ch = nominaCalculator.resultado.payroll_a / fte
```

**Risk**: Sin calculador, usa rough approximation 50/50 split → potencial divergencia vs Excel

**Recomendación**: 
- Hacer NominaCalculator obligatorio
- Fallar ruidosamente si no disponible

**Risk Level**: 🔴 **HIGH** — Overrides pueden causar inconsistencia; fallbacks pueden diverger de Excel

---

### 2. Vision PyG (LOW RISK)

**Location**: `calculators/vision_pyg.py` (137 líneas)

**Entrada**:
- PyGMensual[] (monthly P&G from calculator)
- KPIsDeal (aggregated metrics)

**Proceso**:
- Puramente transformacional
- Mapea cada campo PyGMensual via extractores lambda
- Estructura para tabla frontend (filas ordenadas)

**Patrones Sospechosos Encontrados**: ✅ **NINGUNO**

**Notable Design Decisions**:
- Percentage fields use `average` (not sum) for acumulado
- No new calculations — direct extraction from PyGMensual

**Risk Level**: 🟢 **LOW** — Puramente transformacional, sin lógica desacoplada

**Recomendación**: Mantener como está. No cambios necesarios.

---

### 3. Cost To Serve (HIGH RISK)

**Location**: `calculators/cost_to_serve.py` (304 líneas)

**Entrada**:
- PerfilCadenaA (FTE, vol_cadena_a_mensual)
- ParametrosCadenaB (volumen_mensual)
- PyGMensual[] (monthly costs)
- Calculadores opcionales

**Proceso**:
1. K50 = Σ(outbound FTE) + Σ(inbound vol_cadena_a_mensual)
2. L50 = Σ(Cadena B volumen_mensual)
3. CTS = promedio(costo) / K50(L50)

**Patrones Sospechosos Encontrados**:

#### Pattern 1: Default Value (K50 Calculation)
```python
# Lines 155-174
for perfil in perfiles:
    if perfil.modalidad == "Outbound":
        k50 += perfil.fte
    elif perfil.modalidad == "Inbound":
        k50 += perfil.vol_cadena_a_mensual  # DEFAULT: 0.0 if not populated
```

**Risk**: Si vol_cadena_a_mensual = 0.0 (default) → inbound profiles no contribuyen a K50 → CTS sobreestimado

**Recomendación**: 
- Validar que vol_cadena_a_mensual poblado para ALL inbound profiles
- Agregar validación en context_builder

#### Pattern 2: Null Checks (Optional Calculators)
```python
# Line 207
if nominaCalculator is None:
    nomina_ch = 0.0  # Empty desglose
else:
    nomina_ch = nominaCalculator.resultado.payroll_a / k50
```

**Risk**: Frontend obtiene desglose incompleto sin warning

**Recomendación**: 
- Hacer calculadores obligatorios
- Fallar si no disponibles

**Risk Level**: 🔴 **HIGH** — Denominador K50 puede ser subestimado; fallback silencioso

---

### 4. Riesgo (HIGH RISK)

**Location**: `calculators/riesgo.py` (412 líneas)

**Entrada**:
- PanelDeControl (cliente, linea_negocio, valor_total_deal via KPIsDeal)
- KPIsDeal (valor_total_deal para approval threshold)
- PyGMensual[] (contingencia_op para regla validación)
- Perfiles A/B/C
- riesgo_config (from IParametrizationProvider)

**Proceso**:
1. Evalúa 10 criterios × 2 categorías (40% Cliente, 60% Operativo)
2. Score cada criterio 1-3 (Bajo/Medio/Alto)
3. Calcula score ponderado
4. Classifica: <1.5 Bajo, 1.5-2.5 Medio, ≥2.5 Alto
5. Verifica approval threshold (valor_total_deal > 1000 SMMLV)

**Patrones Sospechosos Encontrados**:

#### Pattern 1: _DEFAULT_ Hardcodes (4 matches)
```python
# Lines 86-89
_DEFAULT_SMMLV = 1_423_500  # Hardcoded value, no annual indexing
_DEFAULT_APPROVAL_THRESHOLD = 1000 * _DEFAULT_SMMLV  # ~1.4B COP
```

**Risk**: Threshold no se actualiza automáticamente con inflación anual

**Recomendación**: 
- Migrar a storage parametrización (Fase 9)
- Implementar actualización anual o dinámica

#### Pattern 2: Defaults in Config (7 matches)
```python
# Lines 51-105
if riesgo_config is None:
    config = _DEFAULT_RIESGO_CONFIG  # Fallback a hardcoded defaults
```

**Risk**: Si provider falla, scoring usa valores potencialmente obsoletos

**Recomendación**: 
- Hacer provider obligatorio
- Centralizar config en storage

#### Pattern 3: Null Checks (1 match)
```python
# Various places
if panel.tipo_cliente is None:
    tipo = "Genérico"  # Default type
```

**Risk**: Soft failure sin auditoría trail

**Recomendación**: 
- Validar fields requeridos en context_builder
- Fallar en load time, no en eval time

**Risk Level**: 🔴 **HIGH** — Hardcodes de SMMLV sin indexación; config defaults; null checks silenciosos

---

## Traceability Matrix

### Entry Data → Calculator → Vision → Endpoint

```
entry_data
├─ PerfilCadenaA.fte
│  └─ NominaCalculator → payroll_a
│     └─ vision_tarifas → tarifa_fijo_fte = facturacion / fte ✓
│        └─ GET /results/vision-tarifas → TarifaCanal.tarifa_fijo_fte ✓
│
├─ ParametrosCadenaB.volumen_mensual
│  └─ CadenaBCalculator → costo_b
│     └─ cost_to_serve → k50 / l50 ✓ (pero K50 depends on vol_cadena_a_mensual!)
│        └─ GET /results/cost-to-serve → cts_ponderado ✓
│
├─ PanelDeControl.tipo_cliente
│  └─ RiesgoCalculator → score_cliente
│     └─ GET /results → evaluacion_riesgo.score_cliente ✓ (pero SMMLV hardcoded!)
│
└─ PyGMensual[]
   ├─ vision_pyg → (purely transformation, no new calc) ✓
   │  └─ GET /results → vision_pyg.filas[] ✓
   │
   └─ cost_to_serve → desglose_a/b (depends on calculators being available!)
      └─ GET /results → cost_to_serve.desglose_a/b ⚠️
```

---

## Risk Classification

### 🟢 GREEN (No Action Required)
- **vision_pyg**: Purely transformational, no decoupled logic

### 🟡 YELLOW (Document & Validate)
- **vision_tarifas**: Override mechanisms OK if documented and validated
  - Action: Document override usage patterns
  - Timeline: Before Phase 8

### 🔴 RED (Fix Required)
- **cost_to_serve**: K50 default value risk, missing validator
  - Action: Add vol_cadena_a_mensual validation in context_builder
  - Timeline: Before Phase 7 endpoint audit
  
- **riesgo**: SMMLV hardcodes, config defaults, silent null checks
  - Action: Migrate to storage (Phase 9); add mandatory validation (Phase 8)
  - Timeline: Phase 8-9

---

## Recommendations

### Immediate (Before Phase 7)
1. **vision_tarifas**: Document override mechanism patterns
   - When are profile overrides used?
   - How do they impact deal aggregates?
   - Add tests to ensure consistency

2. **cost_to_serve**: Add K50/L50 validator
   - Require vol_cadena_a_mensual > 0 for inbound profiles
   - Fail in context_builder if not met
   - Add unit test for denominator validation

### Phase 7-8 (Endpoints & Nomenclature)
3. **Standardize field naming**: vol_cadena_a_mensual → consistent naming
4. **Add contract test**: Visión Imprimible structure validation

### Phase 9 (Parametrization)
5. **riesgo**: Migrate SMMLV + thresholds to storage
6. **riesgo**: Make provider mandatory; remove defaults
7. Remove all hardcoded _DEFAULT_ constants

### Optional (Technical Debt)
8. **vision_tarifas**: Consider removing override mechanism if unused
   - Audit: Are profile.costos_financieros_mensual/cadena_b_mensual ever set > 0?
   - If unused: simplify logic, remove override code

---

## Deliverables

| Item | Location | Status |
|------|----------|--------|
| Audit Script | scripts/audit_visiones_fase6.py | ✅ Complete |
| Audit Report | reports/audit/fase6_visiones_audit.json | ✅ Complete |
| Audit Findings | This document | ✅ Complete |
| Traceability Matrix | Section above | ✅ Complete |

---

## Next Steps: Phase 7

Phase 7 will audit endpoints (GET /results/*) to validate that:
1. Each field traces correctly to source (calculator/vision)
2. @property fields don't contain hidden calculations
3. Multi-channel tariff selection logic is correct
4. Nomenclature aligns with entry_data contract

**Blocker**: None. Phase 7 can proceed immediately.

---

**Status**: 🟢 **FASE 6 COMPLETE — VISIONES AUDITADAS CON FINDINGS DOCUMENTADOS**

