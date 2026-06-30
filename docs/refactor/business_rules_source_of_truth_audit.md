# Business Rules — Source-of-Truth Audit

**Estado:** BUSINESS_RULES_FIX_4A — Snapshot isolation completo, 16 invariantes protegidos  
**Última actualización:** 2026-06-05  
**Tests:** 25 passed en `test_business_rules_guardrails.py` (G-01 a G-16)

---

## Resumen ejecutivo

Esta auditoría documenta la cadena completa de decisiones que establecieron
`storage/parametrization/business_rules/v2-7.json` como única fuente canónica
de las reglas de negocio del motor de pricing NEXA.

| Fase | Problema resuelto | Tests |
|---|---|---|
| FIX_1 | `descuento_volumen` → `descuento`; eliminación de `aprobaciones_umbrales` | Previos |
| FIX_2 | SMMLV: identificar fuente canónica HR vs business_rules | Previos |
| FIX_2B | Eliminar `smmlv` del JSON; `RiesgoCalculator.smmlv` kwarg obligatorio | 34 tests |
| FIX_3 | Eliminar `porcentaje_acumulado` DEAD_FIELD; guard `_PANEL_FIELDS` | 23 tests |
| GUARDRAILS | 14 invariantes permanentes G-01..G-14 | 23 tests |
| **FIX_4A** | **Snapshot WAVE1 isolation; G-15..G-16** | **25 tests** |

---

## Sección 1 — Arquitectura de almacenamiento

### Estructura canonical

```
storage/parametrization/
├── business_rules/            ← FUENTE CANÓNICA RUNTIME
│   ├── versions.json          ← active_version: "v2-7" (sin path override)
│   ├── v2-7.json              ← leída por JsonDocumentStore en runtime
│   └── 2026-01.json           ← versión legacy inactiva
├── hr/                        ← IParametrizationProvider.get_smmlv()
├── gn/
├── op/
├── frozen/                    ← Snapshots certificados (FROZEN-1)
│   └── v2-6.json
└── v2-7/                      ← SNAPSHOT HISTÓRICO WAVE1 (NO runtime)
    ├── manifest.json          ← FROZEN-1 (2026-06-04)
    ├── business_rules.json    ← FROZEN-1 — STALE — smmlv/descuento_volumen/porcentaje_acumulado
    ├── hr.json                ← FROZEN-1
    ├── gn.json                ← FROZEN-1
    └── op.json                ← FROZEN-1
```

### Flujo de lectura runtime

```
API call
  → NexaPricingEngine._calcular_pipeline()
  → ParametrizationProvider.build()
  → BusinessRulesQueryService.get_active_data()
  → BusinessRulesRepository.get_active_data()
  → JsonDocumentStore.get_record("business_rules", "v2-7")
  → storage/parametrization/business_rules/v2-7.json   ← CANÓNICA
```

El snapshot `v2-7/business_rules.json` **NUNCA** es leído en runtime:
- `business_rules/versions.json` no tiene campo `"path"` en el entry activo (G-16)
- Ningún módulo en `modules/` referencia la ruta del snapshot (G-15)

---

## Sección 11 — FIX_1: Renombrado y limpieza

### Problema
El campo `descuento_volumen` en `politicas_comerciales` fue renombrado a `descuento`
en el JSON, pero `panel_service.py` y `panel_dto.py` seguían usando el nombre stale,
produciendo `Rango(minimo=0.0, maximo=0.0)` silenciosamente.

### Solución
- `descuento_volumen` → `descuento` en JSON, DTO y service
- `aprobaciones_umbrales` eliminado del JSON (umbrales son constantes de módulo en `serializer_helpers.py`)

---

## Sección 12 — FIX_2 / FIX_2B: SMMLV canónico exclusivo

### Problema
`RiesgoCalculator` tenía `smmlv: float | None = None` con fallback a
`business_rules.constantes_regulatorias.smmlv = 1_423_500.0` (SMMLV 2024 desactualizado).
HR-Salarios tiene el SMMLV 2026 correcto (1_750_905.0).

### Solución (FIX_2B)

**JSON (`v2-7.json`):**
```json
"constantes_regulatorias": {
  "_nota_umbral": "umbral_aprobacion_smmlv es el multiplicador (1000 SMMLV). La fuente monetaria del SMMLV es exclusivamente HR-Salarios via IParametrizationProvider.get_smmlv(). BUSINESS_RULES_FIX_2B: smmlv fue eliminado de este archivo — no existe fallback a business_rules.",
  "umbral_aprobacion_smmlv": 1000.0
}
```

**`RiesgoCalculator.__init__`:**
```python
def __init__(self, riesgo_config=None, *, smmlv: float) -> None:
    if smmlv <= 0:
        raise ValueError("RiesgoCalculator requiere smmlv > 0 ...")
    self.SMMLV = float(smmlv)
```

**`engine._calcular_pipeline`:**
```python
smmlv = self._parametrizacion.get_smmlv()  # HR canónico
riesgo_calc = RiesgoCalculator(riesgo_config, smmlv=smmlv)
```

### Restricciones permanentes
- No reintroducir `smmlv` en business_rules JSON
- No crear fallback silencioso
- `smmlv` siempre viene de `IParametrizationProvider.get_smmlv()` (HR)

---

## Sección 13 — FIX_3: Políticas comerciales saneadas

### Problema
- `porcentaje_acumulado` en JSON pero sin campo en `PanelDeControl` → evaluado con `.get(nombre, 0.0)` → silenciosamente 0.0
- `descuento_volumen` stale en `panel_service.py` (no actualizado en FIX_1)
- `getattr(panel, "imprevistos", 0.0)` cuando el campo existe directamente

### Solución

**Campos eliminados del JSON:**
- `porcentaje_acumulado` — DEAD_FIELD_LEGACY (sin fuente en PanelDeControl)

**Guard en `engine_helpers.py`:**
```python
_PANEL_FIELDS = {
    "contingencia_operativa": panel.op_cont,
    "contingencia_comercial": panel.com_cont,
    "markup":                 panel.markup,
    "descuento":              panel.descuento,
    "imprevistos":            panel.imprevistos,
}
if nombre not in _PANEL_FIELDS:
    raise ValueError(
        f"Política comercial '{nombre}' no tiene campo PanelDeControl mapeado ..."
    )
aplicado = _PANEL_FIELDS[nombre]
```

### 5 políticas activas canónicas

| nombre | label | Panel field | min | max |
|---|---|---|---|---|
| `contingencia_operativa` | Contingencia Operativa | `op_cont` | 0.025 | 0.12 |
| `contingencia_comercial` | Contingencia Comercial | `com_cont` | 0.04 | 0.07 |
| `markup` | Markup | `markup` | 0.02 | 0.08 |
| `descuento` | Descuento volumen | `descuento` | 0.0 | 0.15 |
| `imprevistos` | Imprevistos | `imprevistos` | 0.0 | 1.0 |

---

## Sección 14 — GUARDRAILS: Invariantes permanentes G-01..G-14

### Tabla de invariantes

| ID | Invariante | Detecta si falla |
|---|---|---|
| G-01 | `constantes_regulatorias` sin `smmlv` | Reintroducción de 1,423,500 legacy |
| G-02 | `riesgo_config` sin `aprobaciones_umbrales` | Umbrales Excel movidos al JSON |
| G-03 | `politicas_comerciales` sin `porcentaje_acumulado` | Campo muerto resurge |
| G-04 | `politicas_comerciales` sin `descuento_volumen` | Nombre stale de FIX_1 |
| G-05 | Exactamente 5 políticas canónicas | Adición/eliminación no auditada |
| G-06 | Cada política → campo real de `PanelDeControl` | Nueva política sin fuente Panel |
| G-07 | `RiesgoCalculator()` sin `smmlv` → `TypeError` | Se reintroduce `smmlv=None` default |
| G-08 | `RiesgoCalculator(smmlv=0)` → `ValueError` | Se elimina validación de rango |
| G-09 | Engine inyecta `get_smmlv()` a `RiesgoCalculator` | Pérdida de inyección HR |
| G-10 | `_aprobaciones_requeridas` no lee SMMLV/BR | Acoplamiento a business_rules |
| G-11 | Umbrales 100M/200M/1B son constantes de módulo | Externalización al JSON |
| G-12 | Firma de `_aprobaciones_requeridas` sin params prohibidos | `smmlv`/`firmantes` agregados |
| G-13 | DTO sin `descuento_volumen`/`porcentaje_acumulado` | Campos stale en el DTO |
| G-14 | Guard `ValueError` activo en `_calcular_reglas_negocio` | `.get(nombre, 0.0)` reinstaurado |

**Test file:** `tests/unit/test_business_rules_guardrails.py`  
**Resultado:** 23 tests passed (pre-FIX_4A)

---

## Sección 15 — FIX_4A: Snapshot WAVE1 isolation

### Objetivo
Determinar si `storage/parametrization/v2-7/business_rules.json` puede eliminarse
y, si no, garantizar que el runtime nunca lo lea.

### Inventario del snapshot stale

| Campo stale | Valor stale | Existe en canónica | Clasificación | Acción |
|---|---|---|---|---|
| `smmlv` | 1,423,500.0 | No (eliminado FIX_2B) | OBSOLETO_ELIMINAR | Sin acción — snapshot inmutable |
| `anio_vigencia` | 2026 | No (no necesario) | OBSOLETO_ELIMINAR | Sin acción |
| `umbral_aprobacion_smmlv` | 1000.0 | ✅ Sí | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `pesos_categorias` | Cliente/Operativo | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `clasificacion_score` | alto/medio | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `criterios[1..10]` | 10 criterios | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `umbrales` | periodo_pago/alertas/etc | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `margen_objetivo` | a/b/c | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `descuento_volumen` | min=0.012 | No (renombrado FIX_1) | OBSOLETO_ELIMINAR | Sin acción — snapshot inmutable |
| `porcentaje_acumulado` | min=0.012 | No (eliminado FIX_3) | OBSOLETO_ELIMINAR | Sin acción — snapshot inmutable |
| `contingencia_operativa` | 0.025/0.12 | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `contingencia_comercial` | 0.04/0.07 | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `markup` | 0.02/0.08 | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |
| `imprevistos` | 0.0/1.0 | ✅ Sí (idéntico) | ACTIVE_BUSINESS_RULES_CANONICAL | Sin acción |

### Consumidores encontrados

| Consumidor | Clasificación | Lee en runtime |
|---|---|---|
| `tests/unit/test_frozen_parametrization_integrity.py:43` | TEST — hash integrity FROZEN-1 | ❌ No |
| `tests/versioning/conftest.py:68` | TEST — fixture sintético (path override) | ❌ No |
| `scripts/baselines/generate_baselines.py:288` | SCRIPT — generación offline de baselines | ❌ No |
| `scripts/migrations/seed_cosmos_parametrization.py` | SCRIPT — migración one-off | ❌ No |
| `docs/v27/*.md` | DOCUMENTACIÓN histórica | ❌ No |
| `docs/refactor/architecture_exceptions.md` | DOCUMENTACIÓN — excepción registrada | ❌ No |

### Decisión: NO ELIMINAR

El archivo es un **snapshot FROZEN-1** certificado:
- `test_frozen_parametrization_integrity.py` falla si el archivo es eliminado o modificado
- Su hash `b6868eaa05c6dc615d1a6d86324de23362798628a12c40df4405836165a5073a` está registrado
- Cualquier cambio requiere: documentar en `architecture_exceptions.md` + verificar Oracle Δ=0 + actualizar FROZEN_HASHES

El runtime lee exclusivamente `storage/parametrization/business_rules/v2-7.json` vía `JsonDocumentStore`:
```
JsonDocumentStore(root=PARAMETRIZATION_DIR)
  .get_record(CollectionConfig("business_rules"), "v2-7")
  → PARAMETRIZATION_DIR / "business_rules" / "v2-7.json"   ← CANÓNICA ✅
```

### Guardrails añadidos: G-15 y G-16

| ID | Invariante | Detecta si falla |
|---|---|---|
| G-15 | Ningún módulo en `modules/` referencia `v2-7/business_rules.json` | Runtime empieza a leer snapshot stale |
| G-16 | `business_rules/versions.json` active entry sin campo `"path"` | `_read_legacy_path()` activaría snapshot |

**Test class:** `TestSnapshotWave1Isolation` en `test_business_rules_guardrails.py`  
**Resultado:** 2 tests nuevos — **25/25 passed** en total

### Invariante transversal

El snapshot en `storage/parametrization/v2-7/` es el **origen histórico WAVE1**.
La canónica en `storage/parametrization/business_rules/` es su **evolución auditada**.
Los campos stale del snapshot (`smmlv`, `descuento_volumen`, `porcentaje_acumulado`)
están eliminados de la canónica y sus guardrails impiden que regresen.

---

## Sección 16 — Resumen final de invariantes

**16 invariantes permanentes** — `test_business_rules_guardrails.py`

```
G-01..G-04   JSON sin campos prohibidos (smmlv, aprobaciones_umbrales, porcentaje_acumulado, descuento_volumen)
G-05..G-06   5 políticas canónicas; cada una con campo Panel real
G-07..G-09   SMMLV obligatorio; engine inyecta HR; no fallback
G-10..G-12   Visión Imprimible: constantes Excel, sin SMMLV
G-13..G-14   DTO limpio; guard ValueError activo
G-15..G-16   Snapshot WAVE1 isolated; no path override
```

**Suite completa:** 1172 passed, 8 failed pre-existentes (polizas/Cosmos), 0 regresiones.

---

## Pendientes documentados

| Item | Prioridad | Requiere |
|---|---|---|
| `alerta.mensaje` dice "GERENCIA GENERAL" en lugar de "Alta Dirección" | Baja | Cambio nomenclatural, no cálculo |
| D3/P5: deprecar `requiere_aprobacion` bool (1000×SMMLV) | Media | Decisión frontend/business |
| `imprevistos.max = 1.0` (100%) muy amplio | Baja | Confirmación business |
| Snapshot WAVE1 `v2-7/business_rules.json` stale | Resuelto G-15/G-16 | NO eliminar (FROZEN-1) |
