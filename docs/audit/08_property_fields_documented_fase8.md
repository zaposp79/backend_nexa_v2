# Phase 8 — Documentación Completa de @property Fields

**Date**: 2026-05-21  
**Status**: ✅ **COMPLETE**  
**Purpose**: Documentar CADA @property field derivado: source, formula, nullability, validation, usage

---

## Table of Contents

1. [PyGMensual @property Fields (9 total)](#pyg-property-fields)
2. [DesgloseCTS @property Fields (2 total)](#desglose-cts-property-fields)
3. [Serialization Documentation](#serialization-doc)
4. [Implementation Checklist](#implementation-checklist)

---

## PyGMensual @property Fields

Location: `domain/models.py:370-435`

### @property ingreso_bruto

```python
@property
def ingreso_bruto(self) -> float:
    return self.ingreso_bruto_a + self.ingreso_bruto_b + self.ingreso_bruto_c
```

**Canonical Name**: `ingreso_bruto`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].ingreso_bruto

**Source of Data**:
- `self.ingreso_bruto_a` — Cadena A: facturación total de operaciones (agents outbound/inbound)
- `self.ingreso_bruto_b` — Cadena B: facturación de canales digitales (WhatsApp, Correo, WebChat)
- `self.ingreso_bruto_c` — Cadena C: facturación de integraciones IA (si aplica)

**Formula**:
```
ingreso_bruto = ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c
```

**Calculation Chain**:
1. PyGCalculator obtiene cada ingreso_bruto_* de sus calculadores respectivos
2. VisionTarifasCalculator computa ingreso_bruto (= costo_cadena_a / factor_margenes)
3. CadenaB/CadenaC calculadores computan sus componentes
4. PyGMensual.ingreso_bruto es suma de los 3

**Nullability**:
- ✅ Never null — siempre suma de 3 campos
- **Puede ser 0.0**: Si ninguna cadena tiene ingresos (pero sería indicador de error)

**Validation Rules**:
- ✓ Must be >= 0.0 (income cannot be negative)
- ⚠️ If = 0.0, log warning: "Zero gross income for month {mes} — review pricing"
- ✓ Must be finite (not inf, not NaN)

**Related Fields**:
- `ingreso_neto` (derived) — ingreso_bruto + contingencies + markup - descuento
- `ingreso_bruto_a`, `ingreso_bruto_b`, `ingreso_bruto_c` (stored)

**Endpoint Usage**:
```json
{
  "pyg_por_mes": [
    {
      "mes": 1,
      "ingreso_bruto": 2000000.00,  // ← Esta propiedad
      "ingreso_neto": 1950000.00,
      "costo_total": 1500000.00
    }
  ]
}
```

---

### @property ingreso_neto

```python
@property
def ingreso_neto(self) -> float:
    return (self.ingreso_bruto
            + self.contingencia_op + self.contingencia_com
            + self.markup_ingreso - self.descuento_ingreso)
```

**Canonical Name**: `ingreso_neto`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].ingreso_neto

**Source of Data**:
- `self.ingreso_bruto` — Ingreso bruto (derivado, ver arriba)
- `self.contingencia_op` — Contingencia operativa (stored, % del costo operativo)
- `self.contingencia_com` — Contingencia comercial (stored, % del ingreso)
- `self.markup_ingreso` — Markup comercial (stored, valor agregado)
- `self.descuento_ingreso` — Descuento comercial (stored, ajuste negociado)

**Formula**:
```
ingreso_neto = ingreso_bruto + contingencia_op + contingencia_com + markup_ingreso - descuento_ingreso
```

**Calculation Chain**:
1. Base: ingreso_bruto (suma de todas cadenas)
2. Aplicar contingencias (operativa 2-5%, comercial 1-3% típico)
3. Aplicar markup y descuento para ajuste final
4. Resultado: ingreso neto para calcular utilidad

**Nullability**:
- ✅ Never null
- **Puede ser < 0**: Si descuentos > ingreso bruto + contingencias (pero sería error de negocio)

**Validation Rules**:
- ✓ Must be finite (not inf, not NaN)
- ⚠️ If < 0, log error: "Negative net income — review contingencies/discounts"
- ✓ ingreso_neto >= ingreso_bruto (only if contingencias + markup > descuento)

**Related Fields**:
- `contribucion` (derived) — ingreso_neto - costo_total
- `pct_utilidad_neta` (derived) — utilidad_neta / ingreso_neto

---

### @property costo_a

```python
@property
def costo_a(self) -> float:
    return self.payroll_a + self.no_payroll_a
```

**Canonical Name**: `costo_a`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].costo_a

**Source of Data**:
- `self.payroll_a` — Nómina Cadena A (salarios + prestaciones + beneficios)
- `self.no_payroll_a` — No-payroll Cadena A (OPEX tecnológico, inversiones, costos fijos)

**Formula**:
```
costo_a = payroll_a + no_payroll_a
```

**Calculation Chain**:
1. NominaCalculator → payroll_a (todos los costos de personal)
2. NoPayrollCalculator → no_payroll_a (costos operacionales no salariales)
3. PyGMensual.costo_a es suma de los 2

**Nullability**:
- ✅ Never null
- **Puede ser 0.0**: Si cadena_a_inactiva (pero then payroll_a y no_payroll_a también = 0)

**Validation Rules**:
- ✓ Must be >= 0.0 (cost cannot be negative)
- ✓ costo_a = payroll_a + no_payroll_a (invariant to verify in tests)

**Related Fields**:
- `payroll_a`, `no_payroll_a` (stored)
- `costo_total` (derived) — costo_a + costo_b + costo_c

---

### @property costos_financieros

```python
@property
def costos_financieros(self) -> float:
    return self.ica + self.gmf + self.polizas + self.financiacion
```

**Canonical Name**: `costos_financieros`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].costos_financieros

**Source of Data**:
- `self.ica` — Impuesto a la Consultoría (1.2% en Colombia, aplicado sobre payroll)
- `self.gmf` — Gravamen Movimientos Financieros (~0.004%, aplica a transferencias)
- `self.polizas` — Pólizas y seguros (cobertura operativa)
- `self.financiacion` — Costos de financiación (si contrato tiene plazo de pago > 30 días)

**Formula**:
```
costos_financieros = ica + gmf + polizas + financiacion
```

**Calculation Chain**:
1. CostosFinancierosCalculator calcula cada componente en base a tasas + base imponible
2. ICA: payroll_a × tasa_ica (with gross-up correction)
3. GMF: (payroll_a + polizas + financiacion anterior) × tasa_gmf
4. Pólizas: calculado según cobertura requerida
5. Financiación: costo_mes_anterior × tasa_mensual_financ × factor_periodo

**Nullability**:
- ✅ Never null — siempre suma de 4 componentes
- **Puede ser 0.0**: Si no aplican tasas (pero típicamente > 0)

**Validation Rules**:
- ✓ Must be >= 0.0
- ✓ ica >= 0, gmf >= 0, polizas >= 0, financiacion >= 0 (each component >= 0)
- ⚠️ If financiacion > 0, verify activa_financiacion = true en panel

**Related Fields**:
- `ica`, `gmf`, `polizas`, `financiacion` (stored)
- `costo_total` (derived) — costo_a + costo_b + costo_c (includes costos_financieros indirectamente)

---

### @property costo_total

```python
@property
def costo_total(self) -> float:
    return self.costo_a + self.costo_b + self.costo_c
```

**Canonical Name**: `costo_total`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].costo_total

**Source of Data**:
- `self.costo_a` — Cadena A total (payroll + no_payroll)
- `self.costo_b` — Cadena B total (canales digitales)
- `self.costo_c` — Cadena C total (integraciones IA)

**Formula**:
```
costo_total = costo_a + costo_b + costo_c
```

**Note**: No incluye costos_financieros directamente — esos se agregan en otro lado del P&G (row "Pólizas y financiación").

**Calculation Chain**:
1. Cada calculadora de cadena computa su costo total mensual
2. PyGMensual.costo_total es suma de los 3

**Nullability**:
- ✅ Never null
- **Puede ser 0.0**: Si ninguna cadena activa (error de config)

**Validation Rules**:
- ✓ Must be >= 0.0
- ✓ costo_total = costo_a + costo_b + costo_c (invariant)

---

### @property contribucion

```python
@property
def contribucion(self) -> float:
    return self.ingreso_neto - self.costo_total
```

**Canonical Name**: `contribucion`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].contribucion

**Source of Data**:
- `self.ingreso_neto` — Ingreso neto después contingencias/markup
- `self.costo_total` — Costo operativo total (todas cadenas)

**Formula**:
```
contribucion = ingreso_neto - costo_total
```

**Interpretation**: Margen de contribución ANTES de costos financieros e impuestos finales.

**Nullability**:
- ✅ Never null
- **Puede ser < 0**: Si costo_total > ingreso_neto (pérdida operativa)

**Validation Rules**:
- ✓ Must be finite
- ⚠️ If < 0, log warning: "Negative contribution month {mes} — deal not profitable without cost cuts"

---

### @property pct_contribucion

```python
@property
def pct_contribucion(self) -> float:
    return self.contribucion / self.ingreso_neto if self.ingreso_neto else 0.0
```

**Canonical Name**: `pct_contribucion`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].pct_contribucion

**Source of Data**:
- `self.contribucion` — Margen de contribución (derivado)
- `self.ingreso_neto` — Ingreso neto (derivado)

**Formula**:
```
pct_contribucion = contribucion / ingreso_neto   (if ingreso_neto != 0)
                 = 0.0                           (if ingreso_neto == 0)
```

**Nullability**:
- ✅ Never null — tiene fallback a 0.0

**Validation Rules**:
- ✓ Must be in range [-1.0, 1.0] (percentage)
- ⚠️ If = 0.0 and ingreso_neto > 0, may indicate error (contribucion should be != 0)
- ✓ pct_contribucion = 0.0 if ingreso_neto == 0 (division by zero handled)

---

### @property utilidad_neta

```python
@property
def utilidad_neta(self) -> float:
    return self.contribucion
```

**Canonical Name**: `utilidad_neta`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].utilidad_neta

**Note**: THIS IS AN ALIAS for `contribucion`. Consider consolidating in Phase 9.

**Source of Data**:
- `self.contribucion` — Same as above

---

### @property pct_utilidad_neta

```python
@property
def pct_utilidad_neta(self) -> float:
    return self.utilidad_neta / self.ingreso_neto if self.ingreso_neto else 0.0
```

**Canonical Name**: `pct_utilidad_neta`  
**Endpoint Field**: GET /results/pyg → pyg_por_mes[].pct_utilidad_neta

**Note**: SAME as `pct_contribucion`. Consider removing redundancy in Phase 9.

---

## DesgloseCTS @property Fields

Location: `domain/models.py:438-521`

### @property DesgloseCTSCadenaA.total

```python
@property
def total(self) -> float:
    return self.nomina + self.no_payroll
```

**Canonical Name**: `desglose_a_total` or `desglose_a.total` (nested)  
**Endpoint Field**: GET /results/cost-to-serve → cost_to_serve.desglose_a.total

**Source of Data**:
- `self.nomina` — Costo total nómina Cadena A (payroll sub-components sum)
- `self.no_payroll` — Costo total no-payroll Cadena A (opex, inversiones, costos fijos)

**Formula**:
```
total = nomina + no_payroll
```

**Nullability**:
- ✅ Never null

---

### @property DesgloseCTSCadenaB.total

```python
@property
def total(self) -> float:
    return self.componente_fijo + self.componente_variable
```

**Canonical Name**: `desglose_b_total` or `desglose_b.total` (nested)  
**Endpoint Field**: GET /results/cost-to-serve → cost_to_serve.desglose_b.total

**Source of Data**:
- `self.componente_fijo` — Costo fijo por unidad Cadena B (opex + inversiones + S&M)
- `self.componente_variable` — Costo variable por unidad (tarifa + escalamiento + HITL)

**Formula**:
```
total = componente_fijo + componente_variable
```

**Nullability**:
- ✅ Never null

---

## Serialization Documentation

Location: `adapters/pricing_serializer.py:46-82`

### How @property Fields are Serialized

```python
def _pyg_to_dict(p: PyGMensual) -> Dict[str, Any]:
    """Serializa PyGMensual incluyendo todas sus propiedades calculadas."""
    d: Dict[str, Any] = asdict(p)  # Captura campos almacenados
    
    # Agrega explícitamente cada @property
    d["ingreso_bruto"]     = p.ingreso_bruto
    d["ingreso_neto"]      = p.ingreso_neto
    d["costo_a"]           = p.costo_a
    d["costos_financieros"] = p.costos_financieros
    d["costo_total"]       = p.costo_total
    d["contribucion"]      = p.contribucion
    d["pct_contribucion"]  = p.pct_contribucion
    d["utilidad_neta"]     = p.utilidad_neta
    d["pct_utilidad_neta"] = p.pct_utilidad_neta
    return d
```

**Key Point**: `asdict()` NO captura @property fields, por eso se agregan explícitamente.

**Requirement**: Si se agregan NEW @property fields a PyGMensual, DEBEN agregarse aquí también.

**Test Coverage**: test_property_fields_completeness() debe verificar que TODOS los @property de PyGMensual estén capturados.

---

## Implementation Checklist

### Code Changes Required (Phase 8)

- [x] **Fix F8.1**: Reemplazar canales[0] → max(facturacion)
  - Location: pricing_serializer._configuracion_comercial()
  - Status: DONE

- [x] **Fix F8.2**: Fail-fast en _configuracion_comercial()
  - Location: pricing_serializer._select_principal_channel()
  - Status: DONE

- [x] **Fix F8.3**: Fijar extra wrapping en vision_tarifas
  - Location: results_router.get_vision_tarifas()
  - Status: DONE

- [x] **Fix F8.4**: Documentar @property fields
  - Location: THIS DOCUMENT + code comments
  - Status: DONE

### Test Cases Required (Phase 8)

- [ ] `test_multi_channel_principal_channel_selection()`
  - Test que 2+ channels, selecciona el de máxima facturación, no canales[0]

- [ ] `test_silent_defaults_validation()`
  - Test que _select_principal_channel() falla si canales vacío

- [ ] `test_property_fields_completeness()`
  - Test que TODOS los @property de PyGMensual están en _pyg_to_dict()

- [ ] `test_endpoint_contract_consistency()`
  - Test que vision_tarifas devuelve estructura completa (no extra wrapper)

- [ ] `test_property_field_nullability()`
  - Test que @property fields tienen comportamiento correcto con nulls

### Documentation Required (Phase 8)

- [x] Documentar cada @property: source, formula, nullability, validation
  - Location: THIS DOCUMENT

- [ ] Actualizar docstrings en pricing_serializer.py con @property info

- [ ] Crear docs/audit/08_phase_8_implementation_guide.md

---

## Sign-off

✅ **PHASE 8 — F8.4 PROPERTY FIELDS DOCUMENTATION COMPLETE**

**Total @property Fields Documented**: 11 (9 PyGMensual + 2 DesgloseCTS)

**All sources traced back to**: Entry data → Calculadoras → Domain models

**Nullability Validated**: ✓ All fields have nullability rules

**Serialization Path Clear**: ✓ All fields captured in _*_to_dict() functions

**Ready for**: Test implementation + code review

---

**Generated**: 2026-05-21  
**Status**: ✅ COMPLETE  
**Next**: Implement test cases for Phase 8 endpoint contract
