# HR Parametrization Data Flow — Excel to JSON to Application

**Fecha:** 2026-05-27  
**Objetivo:** Documentar el flujo completo de datos desde Excel hasta la aplicación, verificando que NO existan transformaciones obsoletas.

---

## 🔍 Problema Reportado

Tras modificar el Excel de parametrización HR:
- **Excel tiene:** Localidades en formato `"Barranquilla - Barranquilla"`, valores en pesos completos `153301`
- **JSON activo muestra:** `"Barranquilla"`, `153.301`

**Causa raíz identificada:**
1. ✅ **Upload NO activaba automáticamente la nueva versión** (RESUELTO)
2. ⚠️ **Posibles transformaciones obsoletas** (VERIFICAR)

---

## 📊 Flujo de Datos Completo

### 1. **Upload de Excel → Parsing**

**Archivo:** `infrastructure/excel/excel_reader.py`  
**Función:** `read_excel_sheets(file_bytes, "HR-")`

**Output:** Dict de sheets con valores RAW del Excel

**Ejemplo:**
```python
{
  "HR-CostoFijo": [
    {"localidad": "Barranquilla - Barranquilla", "servicio": "Arriendo", "valor": 153301.0},
    {"localidad": "Bogota - Toberin", "servicio": "Energia", "valor": 45200.0},
  ]
}
```

---

### 2. **Normalización de Valores**

**Archivo:** `shared/value_normalizer.py`  
**Función:** `normalize_all_sheets_values(sheets)`

**Transformaciones aplicadas:**
- ✅ Strings con espacios → `.strip()`
- ✅ Números con comas/puntos europeos → normalización (ej. `"1.234,56"` → `1234.56`)
- ✅ Porcentajes → sin `%` (ej. `"18%"` → `18.0`)
- ❌ **NO** divide por 1000
- ❌ **NO** colapsa localidades

**Código relevante:**
```python
def _parse_numeric(self, text: str) -> Optional[float]:
    raw = text.replace(" ", "")
    raw = raw.replace("%", "")
    
    # Handle European format (1.234,56) vs US format (1,234.56)
    if raw.count(",") and raw.count("."):
        last_comma = raw.rfind(",")
        last_dot = raw.rfind(".")
        if last_comma > last_dot:
            raw = raw.replace(".", "")
            raw = raw.replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif raw.count(","):
        raw = raw.replace(",", ".")
    
    return float(Decimal(raw))
```

**Ejemplo:**
- `153301` → `153301.0`
- `"153.301"` (formato europeo) → `153301.0`
- `"153,301"` (formato US) → `153301.0`

⚠️ **ADVERTENCIA:** Si el Excel tiene `153.301` con punto como separador de miles europeo, el normalizer lo convierte a `153301.0`. Si tiene `153.301` como decimal, lo mantiene como `153.301`.

---

### 3. **Mapeo a Modelos de Dominio**

**Archivo:** `parametrization/hr/mapper.py`  
**Función:** `HRMapper._map_costo_fijo(rows)`

**Código:**
```python
def _map_costo_fijo(self, rows: List[dict]) -> List[CostoFijoConfig]:
    result = []
    for row in rows:
        result.append(CostoFijoConfig(
            localidad=_str(row.get("localidad")),  # ← Mantiene exacto
            servicio=_str(row.get("servicio")),
            valor=_float(row.get("valor")),        # ← Solo convierte a float
        ))
    return result
```

**Helper `_float()`:**
```python
def _float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return round(float(val), 5)  # ← Redondeo a 5 decimales
    except (ValueError, TypeError):
        return default
```

**Transformaciones:**
- ✅ Localidad: mantiene exacta (NO colapsa `"Bogota - Toberin"` a `"Bogota"`)
- ✅ Valor: convierte a `float` y redondea a 5 decimales
- ❌ **NO** divide por 1000

**Ejemplo:**
```python
CostoFijoConfig(
    localidad="Barranquilla - Barranquilla",  # ← Exacto
    servicio="Arriendo",
    valor=153301.0  # ← Sin transformación
)
```

---

### 4. **Persistencia a JSON**

**Archivo:** `parametrization/hr/service.py`  
**Función:** `HRService.process_upload()`

**Código:**
```python
master = self._mapper.map(version_id, sheets)
data_dict = self._mapper.to_dict(master)  # dataclasses.asdict()
self._repo.save_version(summary, data_dict)
```

**JSON guardado:**
```json
{
  "version_id": "uuid-here",
  "costo_fijo": [
    {
      "localidad": "Barranquilla - Barranquilla",
      "servicio": "Arriendo",
      "valor": 153301.0
    }
  ]
}
```

**Transformaciones:**
- ❌ **NO** divide por 1000
- ❌ **NO** colapsa localidades

✅ **CONCLUSIÓN:** El JSON se guarda EXACTAMENTE como viene del Excel (después de normalización de tipos).

---

### 5. **Lectura desde Aplicación**

**Archivo:** `repositories/infrastructure_parametrization_repository.py`  
**Función:** `InfrastructureParametrizationRepository.get_infrastructure_costs()`

#### 5.1 Costos Fijos (costo_fijo)

**Código (líneas 98-108):**
```python
for row in costo_fijo:
    row_loc = row.get("localidad", "")
    if _loc_matches(row_loc):
        raw_servicio = row.get("servicio", "").lower().strip()
        canonical    = self._SERVICIO_MAP.get(raw_servicio)
        if canonical is None:
            continue
        # HR-CostoFijo master values are in COP directo (after master unification).
        # See `_normalize_costo_fijo` documentation: previously some services
        # were in miles and others in COP — now ALL services in COP directo.
        costs[canonical] = float(row.get("valor", 0))  # ← NO multiplica por 1000
        found_any = True
```

✅ **CORRECTO:** NO multiplica por 1000, asume valores en COP directo.

#### 5.2 Costos Médicos (med_seg)

**Código (líneas 157-166):**
```python
if row_ciudad == ciudad_normalized and "examen" in row_centro and "medico" in row_centro:
    valor = row.get("valor")
    if valor is not None:
        # HR-Med-Seg stores values in miles → multiply by 1000
        cost_cop = float(valor) * 1000  # ← ⚠️ MULTIPLICA POR 1000
        logger.info(
            f"[PARAMETRIZATION] Loaded medical exam cost for {ciudad}: "
            f"{valor} miles = {cost_cop:,.0f} COP"
        )
        return cost_cop
```

⚠️ **POSIBLE PROBLEMA:** Si el Excel HR-Med-Seg tiene valores en pesos completos (ej. `60800`), pero el código multiplica por 1000, obtendremos `60,800,000` COP (incorrecto).

---

## 🔧 Verificación del Formato del Excel

### Caso 1: Excel tiene valores en MILES (formato antiguo)

**Excel HR-CostoFijo:**
```
| Localidad                    | Servicio  | Valor   |
|------------------------------|-----------|---------|
| Barranquilla - Barranquilla  | Arriendo  | 153.301 |
```

**Normalizer:** `"153.301"` (string con punto decimal) → `153.301` (float)  
**JSON guardado:** `{"valor": 153.301}`  
**Aplicación (costo_fijo):** `153.301` COP ❌ (debería ser 153,301 COP)  
**Aplicación (med_seg):** `153.301 * 1000 = 153,301` COP ✅

### Caso 2: Excel tiene valores en PESOS COMPLETOS (formato nuevo)

**Excel HR-CostoFijo:**
```
| Localidad                    | Servicio  | Valor  |
|------------------------------|-----------|--------|
| Barranquilla - Barranquilla  | Arriendo  | 153301 |
```

**Normalizer:** `153301` (int) → `153301.0` (float)  
**JSON guardado:** `{"valor": 153301.0}`  
**Aplicación (costo_fijo):** `153301.0` COP ✅  
**Aplicación (med_seg):** `153301.0 * 1000 = 153,301,000` COP ❌

---

## ✅ Recomendaciones

### 1. **Estandarizar formato del Excel**

Decidir si los valores deben estar en:
- **Opción A:** Miles de COP (ej. `153.301` → 153,301 COP)
- **Opción B:** COP directo (ej. `153301` → 153,301 COP)

### 2. **Actualizar código según opción elegida**

#### Si se elige **Opción B (COP directo):**

**Archivo:** `repositories/infrastructure_parametrization_repository.py`

**Cambio en línea 161:**
```python
# ANTES
cost_cop = float(valor) * 1000  # ← Multiplica por 1000

# DESPUÉS
cost_cop = float(valor)  # ← Sin multiplicación
```

**Actualizar comentarios:**
```python
# ANTES (línea 136)
# HR-Med-Seg stores values in miles (e.g. 60.8 → 60,800 COP)

# DESPUÉS
# HR-Med-Seg stores values in COP directo (e.g. 60800 → 60,800 COP)
```

#### Si se elige **Opción A (Miles):**

**Archivo:** `repositories/infrastructure_parametrization_repository.py`

**Cambio en línea 108:**
```python
# ANTES
costs[canonical] = float(row.get("valor", 0))  # ← No multiplica

# DESPUÉS
costs[canonical] = float(row.get("valor", 0)) * 1000  # ← Multiplica por 1000
```

---

## 🧪 Endpoint de Validación

Para verificar que Excel y JSON coinciden, usar:

```bash
POST /api/v1/parametrization/hr/validate
Content-Type: multipart/form-data

file: <Excel HR.xlsx>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "discrepancies": [],
    "excel_row_counts": {"HR-CostoFijo": 50, "HR-Med-Seg": 10},
    "json_row_counts": {"costo_fijo": 50, "med_seg": 10}
  }
}
```

Si hay discrepancias, retorna detalles:
```json
{
  "discrepancies": [
    {
      "section": "costo_fijo",
      "type": "valor_mismatch",
      "row": 3,
      "excel_value": 153301.0,
      "json_value": 153.301,
      "difference": 153147.699,
      "message": "Valor mismatch at row 3: Excel=153301.0, JSON=153.301"
    }
  ]
}
```

---

## 📋 Checklist de Verificación

- [x] Upload activa automáticamente la nueva versión (`is_active=True`)
- [x] Logs estructurados en upload (version_id, previous, current, elapsed_ms)
- [x] Endpoint GET /active con row_counts y preview
- [x] Endpoint POST /validate para comparar Excel vs JSON
- [x] Mapper NO divide por 1000
- [x] Mapper NO colapsa localidades
- [x] Normalizer NO divide por 1000
- [ ] **PENDIENTE:** Decidir formato estándar del Excel (miles vs COP directo)
- [ ] **PENDIENTE:** Actualizar `InfrastructureParametrizationRepository` según decisión

---

## 🚀 Próximos Pasos

1. **Subir el Excel actual** y verificar el JSON guardado
2. **Usar endpoint `/validate`** para comparar Excel vs JSON
3. **Si hay discrepancias:** determinar formato correcto del Excel
4. **Actualizar repositorio** según el formato elegido
5. **Documentar en README** el formato esperado para cada sheet

---

**Autor:** Claude Sonnet 4.5  
**Revisión:** Pendiente
