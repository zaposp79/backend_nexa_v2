# Fase 5.5 — Auditoría de Cobertura de Entry Data

**Fecha**: 2026-05-21  
**Estado**: ✅ **AUDITORÍA COMPLETADA — PROBLEMAS IDENTIFICADOS**  
**Objetivo**: Validar qué campos del contrato `entry_data` se usan realmente en backend

---

## Hallazgo Principal

### 🚨 CRÍTICO: 36 Campos de Metadata/Debugging en Test Cases

Los archivos test_cases actualmente contienen **metadata con prefijo `_`** que:
- ❌ NO pertenecen al contrato oficial de entrada
- ❌ NO existen en frontend
- ❌ NO deben participar en cálculos
- ❌ Viola el principio de `entry_data` como fuente única de verdad

**Ejemplo**:
```json
"_comment": "...",
"_excel_facturacion_esperada": 355764509.4,
"_excel_payroll_mes1": 30017217,
"_excel_polizas_mes1": 25738337,
"_excel_ica_mes1": "calcular",
"_k50_expected": 1000,
"_cts_ponderado_expected": 12345.67,
"_source": "Excel V2-4",
"_note": "...",
```

---

## Resumen de Auditoría

| Categoría | Count | % | Acción |
|-----------|-------|---|--------|
| **POLLUTION** (metadata `_*`) | 36 | 17% | 🚨 **REMOVER INMEDIATAMENTE** |
| **DEAD** (no rastreados en grep) | 166 | 82% | ⚠️ Verificar si se usan vía objetos |
| **OK** (encontrados en código) | 0 | 0% | — |
| **TOTAL** | **202** | — | — |

---

## Lista de Campos POLLUTION (Remover)

Todos estos son metadata de debugging y deben removerse de test_cases:

```
_comment
_scenario
_k50_expected
_l50_expected
_part_a_expected
_part_b_expected
_cts_a_expected
_cts_b_expected
_cts_ponderado_expected
_source
_note
_excel_smmlv
_backend_smmlv
_expected_discrepancy
_excel_facturacion_esperada
_excel_payroll_mes1
_excel_polizas_mes1
_excel_ica_mes1
_excel_pct_utilidad_steady
```

---

## Plan de Remediación

### Paso 1: Separar Test Cases en Estructura Limpia

**Estructura actual** (mezclada):
```bash
test_cases/
├── bancamia_whatsapp_only.json      ← contiene datos + metadata
├── bancamia_excel_match.json
└── ...
```

**Estructura objetivo** (separada):
```bash
test_cases/
├── input/
│   ├── bancamia_whatsapp_only.json         ← SOLO entrada contractual
│   ├── bancamia_excel_match.json
│   └── bancamia_canonical_k50.json
├── expected/
│   ├── bancamia_whatsapp_only.expected.json ← valores esperados (del paso 3)
│   ├── bancamia_excel_match.expected.json
│   └── bancamia_canonical_k50.expected.json
└── audit/
    ├── bancamia_whatsapp_only.audit.json    ← metadata + notas
    ├── bancamia_excel_match.audit.json
    └── bancamia_canonical_k50.audit.json
```

### Paso 2: Crear `input/*.json` Limpios

**Antes**:
```json
{
  "_comment": "Bancamia WhatsApp...",
  "_excel_payroll_mes1": 30017217,
  "panel_de_control": { ... },
  "condiciones_cadena_a": { ... }
}
```

**Después**:
```json
{
  "panel_de_control": { ... },
  "condiciones_cadena_a": { ... },
  "condiciones_cadena_b": { ... },
  "condiciones_cadena_c": { ... }
}
```

### Paso 3: Crear `expected/*.json` con Metadata

```json
{
  "_comment": "Bancamia WhatsApp ONLY",
  "_scenario": "Escenario 1 Excel V2-4",
  "_source": "excel/Nexa - Pricing - Simulador - V2-4.xlsx",
  "expected_values": {
    "payroll_a": 30017216.83,
    "no_payroll_a": 9285618.27,
    "ingreso_neto": 391274111.70,
    "pct_utilidad_neta": -0.01719952,
    "k50": 1000,
    "cts_ponderado": 39800.39
  }
}
```

### Paso 4: Actualizar Loader

**Cambio en `adapters/user_input_loader.py`**:
- Leer SOLO desde `input/` (sin metadata)
- Ignorar cualquier campo con prefijo `_`
- Validar que SOLO existan campos contractuales oficiales

---

## Matriz de Impacto

| Archivo | Acción | Impacto | Esfuerzo |
|---------|--------|--------|----------|
| `test_cases/bancamia_*.json` | Separar en `input/` + `expected/` | ALTO | 1 día |
| `adapters/user_input_loader.py` | Filtrar `_*` fields | MEDIO | 2 horas |
| `scripts/validate_excel.py` | Actualizar paths | BAJO | 1 hora |
| `scripts/validate_layers_exhaustive.py` | Actualizar paths | BAJO | 1 hora |
| Todos los scripts de test | Actualizar paths | BAJO | 2 horas |

---

## Beneficios de Esta Remediación

✅ **Contrato limpio**: `entry_data` = SOLO datos de negocio  
✅ **Separación clara**: input vs. expected vs. audit  
✅ **Trazabilidad**: Cada metadata en su lugar correcto  
✅ **Seguridad**: Imposible que metadata contamine cálculos  
✅ **Frontend-ready**: Estructura lista para consumir desde UI  

---

## Acción Inmediata Requerida

**Prioridad**: 🔴 **CRÍTICA — Bloqueador para Fases 6-11**

Antes de continuar:
1. Remover los 36 campos `_*` de todos los test_cases
2. Crear estructura `input/`, `expected/`, `audit/`
3. Validar que loader NO acepta campos con prefijo `_`

**Estimado**: 1 día de trabajo

---

## Implicación para Fases 6-11

- ✅ **Fase 5**: Validación matemática completada
- 🟡 **Fase 5.5**: Arquitectura de entrada debe limpiarse ANTES de continuar
- ⏳ **Fases 6-7**: Pueden proceder una vez separados los test_cases
- ⏳ **Fases 8-9**: Refactorización estructural sobre base limpia
- ⏳ **Fases 10-11**: Documentación + validación final

**Bloqueador**: Las Fases 6-7 pueden comenzar en paralelo mientras se limpian los test_cases.

---

**Status**: 🟡 **FASE 5.5 COMPLETADA — PENDIENTE: REMEDIACIÓN DE TEST_CASES**

