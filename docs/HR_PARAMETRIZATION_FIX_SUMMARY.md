# Fix: Parametrización HR Auto-Activación y Validación

**Fecha:** 2026-05-27  
**Problema:** Upload de Excel HR no reflejaba cambios en la versión activa

---

## ✅ Problema Resuelto

### Antes:
- 🔴 Upload generaba nueva versión pero NO la activaba (`is_active=False`)
- 🔴 Usuario debía activar manualmente vía `/activate` endpoint
- 🔴 Sin logging detallado del proceso
- 🔴 Sin forma de validar Excel vs JSON guardado

### Ahora:
- ✅ Upload **activa automáticamente** la nueva versión
- ✅ Logging completo con trazabilidad (previous/current version_id)
- ✅ Endpoint `/active` con row_counts y preview de datos
- ✅ Endpoint `/validate` para verificar Excel vs JSON 1:1

---

## 📦 Archivos Modificados

### 1. **parametrization/hr/service.py**

**Cambios:**
```python
# ANTES
summary = VersionSummary(
    version_id=version_id,
    filename=filename,
    uploaded_at=uploaded_at,
    is_active=False,  # ❌ No activaba automáticamente
    ...
)

# AHORA
summary = VersionSummary(
    version_id=version_id,
    filename=filename,
    uploaded_at=uploaded_at,
    is_active=True,  # ✅ Auto-activa
    ...
)
```

**Logging agregado:**
```python
logger.info("[PARAMETRIZATION] HR upload started: file=%s", filename)
logger.info("[PARAMETRIZATION] Previous active version: %s", previous_version_id)
logger.info("[PARAMETRIZATION] HR version created: version_id=%s", version_id)
logger.info("[PARAMETRIZATION] HR active version updated: previous=%s, current=%s",
            previous_version_id, version_id)
logger.info("[PARAMETRIZATION] ✓ HR upload completed in %.1f ms", elapsed_ms)
```

**Nuevos métodos:**
- `get_active()` — mejorado con row_counts y preview
- `validate_excel_vs_stored()` — compara Excel contra JSON guardado

### 2. **api/v1/parametrization/hr_router.py**

**Nuevo endpoint:**
```python
@router.post("/validate")
async def validate_hr_excel(file: UploadFile = File(...)):
    """Valida que Excel coincida con JSON guardado 1:1"""
    ...
```

---

## 🧪 Cómo Usar

### 1. **Subir Excel HR (auto-activa)**

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva_2026-05-27.xlsx"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "version_id": "abc-123",
    "filename": "HR_productiva_2026-05-27.xlsx",
    "uploaded_at": "2026-05-27T10:30:00Z",
    "sheets_found": ["HR-CostoFijo", "HR-Med-Seg", ...],
    "row_counts": {
      "HR-CostoFijo": 50,
      "HR-Med-Seg": 10,
      ...
    }
  }
}
```

**Logs generados:**
```
================================================================================
[PARAMETRIZATION] HR upload started: file=HR_productiva_2026-05-27.xlsx
[PARAMETRIZATION] Previous active version: def-456 (uploaded: 2026-05-26T...)
[PARAMETRIZATION] → Parsing Excel sheets
[PARAMETRIZATION] Excel parsed: sheets_found=11
[PARAMETRIZATION] Sheets: HR-LV, HR-SalarioBasico, HR-Nomina, ...
[PARAMETRIZATION] → Mapping sheets to domain models
[PARAMETRIZATION] HR parsed: rows_total=523
[PARAMETRIZATION] Row counts by section:
  - HR-CostoFijo: 50 rows
  - HR-Med-Seg: 10 rows
  - HR-Nomina: 45 rows
  ...
[PARAMETRIZATION] → Saving version to storage
[PARAMETRIZATION] HR version created: version_id=abc-123
[PARAMETRIZATION] HR active version updated: previous=def-456, current=abc-123
[PARAMETRIZATION] ✓ HR upload completed in 234.5 ms
================================================================================
```

---

### 2. **Verificar Versión Activa**

```bash
curl http://localhost:8000/api/v1/parametrization/hr/active
```

**Response (mejorada):**
```json
{
  "success": true,
  "data": {
    "summary": {
      "version_id": "abc-123",
      "filename": "HR_productiva_2026-05-27.xlsx",
      "uploaded_at": "2026-05-27T10:30:00Z",
      "is_active": true,
      "sheet_count": 11,
      "total_rows": 523
    },
    "row_counts": {
      "costo_fijo": 50,
      "med_seg": 10,
      "nomina": 45,
      "ratios": 35,
      "salarios": 8
    },
    "preview": {
      "costo_fijo": [
        {"localidad": "Barranquilla - Barranquilla", "servicio": "Arriendo", "valor": 153301.0},
        {"localidad": "Bogota - Toberin", "servicio": "Energia", "valor": 45200.0},
        ...
      ],
      "med_seg": [
        {"localidad": "Barranquilla", "centrocosto": "Examen Medico Nuevos", "valor": 60800.0},
        ...
      ]
    },
    "data": { ... }  // Full data payload
  }
}
```

✅ **Beneficios:**
- Verificar rápidamente qué versión está activa
- Ver conteo de filas por sección
- Preview de primeras 5 entradas para confirmar formato

---

### 3. **Validar Excel vs JSON**

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/validate \
  -F "file=@HR_productiva_2026-05-27.xlsx"
```

**Response (si coincide):**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "discrepancies": [],
    "excel_row_counts": {"HR-CostoFijo": 50, "HR-Med-Seg": 10},
    "json_row_counts": {"costo_fijo": 50, "med_seg": 10},
    "compared_sections": ["costo_fijo", "med_seg"],
    "version_id": "abc-123"
  }
}
```

**Response (si hay discrepancias):**
```json
{
  "success": true,
  "data": {
    "valid": false,
    "discrepancies": [
      {
        "section": "costo_fijo",
        "type": "localidad_mismatch",
        "row": 3,
        "excel_value": "Barranquilla - Barranquilla",
        "json_value": "Barranquilla",
        "message": "Localidad mismatch at row 3"
      },
      {
        "section": "costo_fijo",
        "type": "valor_mismatch",
        "row": 5,
        "excel_value": 153301.0,
        "json_value": 153.301,
        "difference": 153147.699,
        "message": "Valor mismatch at row 5: Excel=153301.0, JSON=153.301"
      }
    ],
    "excel_row_counts": {"HR-CostoFijo": 50},
    "json_row_counts": {"costo_fijo": 50}
  }
}
```

✅ **Beneficios:**
- Detecta transformaciones no deseadas (división por 1000, colapso de localidad)
- Muestra exactamente qué filas difieren
- Valida que Excel y JSON coincidan 1:1

---

## 🔍 Verificación de Transformaciones

### Mapper (`parametrization/hr/mapper.py`)

```python
def _map_costo_fijo(self, rows: List[dict]) -> List[CostoFijoConfig]:
    result = []
    for row in rows:
        result.append(CostoFijoConfig(
            localidad=_str(row.get("localidad")),  # ✅ Mantiene exacto
            servicio=_str(row.get("servicio")),
            valor=_float(row.get("valor")),        # ✅ Solo convierte a float
        ))
    return result
```

**Verificado:**
- ❌ NO divide por 1000
- ❌ NO colapsa localidades (`"Bogota - Toberin"` se mantiene exacto)

### Normalizer (`shared/value_normalizer.py`)

```python
def _parse_numeric(self, text: str) -> Optional[float]:
    raw = text.replace(" ", "")
    raw = raw.replace("%", "")
    # Handle European vs US decimal formats
    ...
    return float(Decimal(raw))
```

**Verificado:**
- ✅ Normaliza formatos numéricos (comas/puntos)
- ❌ NO divide por 1000

### Repository (`repositories/infrastructure_parametrization_repository.py`)

**costo_fijo (línea 108):**
```python
costs[canonical] = float(row.get("valor", 0))  # ✅ NO multiplica
```

**med_seg (línea 161):**
```python
cost_cop = float(valor) * 1000  # ⚠️ MULTIPLICA por 1000
```

⚠️ **ADVERTENCIA:** Si el Excel HR-Med-Seg tiene valores en pesos completos (ej. `60800`), la multiplicación producirá valores incorrectos (`60,800,000`).

**Solución:** Ver [HR_PARAMETRIZATION_DATA_FLOW.md](./HR_PARAMETRIZATION_DATA_FLOW.md) para decidir formato estándar.

---

## 📊 Ejemplo de Logs Completos

```
================================================================================
[PARAMETRIZATION] HR upload started: file=HR_productiva_2026-05-27.xlsx
[PARAMETRIZATION] Previous active version: v1_20260526_153045 (uploaded: 2026-05-26T15:30:45Z)
[PARAMETRIZATION] → Parsing Excel sheets
[PARAMETRIZATION] Excel parsed: sheets_found=11
[PARAMETRIZATION] Sheets: HR-LV, HR-SalarioBasico, HR-Nomina, HR-Recargos, HR-SegSocial, HR-Prestaciones, HR-Ratios, HR-Rentabilidad, HR-Campana, HR-CostoFijo, HR-Med-Seg
[PARAMETRIZATION] → Mapping sheets to domain models
[PARAMETRIZATION] HR parsed: rows_total=523
[PARAMETRIZATION] Row counts by section:
  - HR-Campana: 24 rows
  - HR-CostoFijo: 50 rows
  - HR-LV: 145 rows
  - HR-Med-Seg: 10 rows
  - HR-Nomina: 45 rows
  - HR-Prestaciones: 14 rows
  - HR-Ratios: 35 rows
  - HR-Recargos: 10 rows
  - HR-Rentabilidad: 12 rows
  - HR-SalarioBasico: 8 rows
  - HR-SegSocial: 5 rows
[PARAMETRIZATION] → Saving version to storage
[PARAMETRIZATION] HR version created: version_id=v1_20260527_103000
[PARAMETRIZATION] HR active version updated: previous=v1_20260526_153045, current=v1_20260527_103000
[PARAMETRIZATION] ✓ HR upload completed in 234.5 ms
================================================================================
```

---

## ✅ Checklist Post-Fix

- [x] Upload activa automáticamente la nueva versión
- [x] Logs estructurados con previous/current version_id
- [x] Endpoint `/active` con row_counts y preview
- [x] Endpoint `/validate` para Excel vs JSON
- [x] Mapper NO divide por 1000
- [x] Mapper NO colapsa localidades
- [x] Normalizer NO divide por 1000
- [ ] **Decisión pendiente:** ¿Excel en miles o COP directo?
- [ ] **Si es COP directo:** Actualizar `InfrastructureParametrizationRepository.get_medical_exam_cost()` (quitar `* 1000`)

---

## 🚀 Próximos Pasos

1. **Subir el Excel actual:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
     -F "file=@HR_productiva_2026-05-27.xlsx"
   ```

2. **Verificar versión activa:**
   ```bash
   curl http://localhost:8000/api/v1/parametrization/hr/active | jq '.data.summary'
   ```

3. **Validar Excel vs JSON:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/parametrization/hr/validate \
     -F "file=@HR_productiva_2026-05-27.xlsx" | jq '.data.discrepancies'
   ```

4. **Si hay discrepancias de valor (ej. 153301 vs 153.301):**
   - Revisar formato del Excel (¿miles o COP directo?)
   - Actualizar `InfrastructureParametrizationRepository` según formato
   - Volver a subir el Excel

5. **Ejecutar cálculo de simulación:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/simulation/calculate \
     -H "Content-Type: application/json" \
     -d @test_case_bancamia.json
   ```

---

## 📚 Documentación Relacionada

- [HR_PARAMETRIZATION_DATA_FLOW.md](./HR_PARAMETRIZATION_DATA_FLOW.md) — Flujo completo Excel → JSON → App
- [ERROR_HANDLING_IMPROVEMENTS.md](./ERROR_HANDLING_IMPROVEMENTS.md) — Mejoras en manejo de errores

---

**Autor:** Claude Sonnet 4.5  
**Estado:** ✅ Completado  
**Fecha:** 2026-05-27
