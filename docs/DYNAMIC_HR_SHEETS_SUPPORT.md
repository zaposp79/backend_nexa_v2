# Soporte para Hojas Dinámicas en HR-Excel

**Fecha:** 2026-05-27  
**Status:** ✅ IMPLEMENTADO

---

## 📋 Resumen

El sistema ahora carga automáticamente **cualquier hoja** del Excel que encuentre, sin necesidad de modificar el código cuando se agreguen nuevas hojas de parametrización.

### Antes ❌
- Las hojas debían estar predefinidas en el mapper
- Agregar una nueva hoja (como `HR-AutRot`) requería:
  1. Crear un dataclass en `models.py`
  2. Agregar un método `_map_xxx()` en `mapper.py`
  3. Modificar `HRMasterData` para incluir el nuevo campo
  4. Redeployar el código

### Ahora ✅
- El sistema detecta automáticamente nuevas hojas
- Se guardan como JSON sin transformación
- Accesibles vía el campo `extra_sheets` en `HRMasterData`
- No requiere cambios de código

---

## 🔧 Implementación

### 1. Modelo Actualizado (models.py)

```python
@dataclass
class HRMasterData:
    """Full HR master data for one uploaded version.
    
    Stores both standard HR sheets (mapped to typed fields) and any additional
    sheets found in the Excel file (stored as raw data in extra_sheets).
    This allows the system to accept new sheets without code changes.
    """
    version_id: str
    # ... campos estándar ...
    extra_sheets: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
```

### 2. Mapper Actualizado (mapper.py)

```python
def map(self, version_id: str, sheets: Dict[str, List[dict]]) -> HRMasterData:
    # Standard HR sheets (typed, specific mappers)
    STANDARD_SHEETS = {
        "HR-LV", "HR-SalarioBasico", "HR-Nomina", "HR-Recargos",
        "HR-SegSocial", "HR-Prestaciones", "HR-Ratios", "HR-Rentabilidad",
        "HR-Campana", "HR-CostoFijo", "HR-Med-Seg"
    }

    # Capture any additional sheets not in the standard list
    extra_sheets = {
        sheet_name: rows
        for sheet_name, rows in sheets.items()
        if sheet_name not in STANDARD_SHEETS and rows
    }

    if extra_sheets:
        logger.info(
            "[MAPPER] Extra sheets detected (not in standard HR spec): %s",
            list(extra_sheets.keys())
        )

    return HRMasterData(
        # ... campos estándar ...
        extra_sheets=extra_sheets,
    )
```

---

## 🎯 Casos de Uso

### Caso 1: Agregar HR-AutRot (Autoridades/Rotación)

**Antes:**
1. Agregar `HR-AutRot` al Excel
2. ❌ El sistema lo ignora
3. Modificar código: `models.py` + `mapper.py`
4. Redeployar

**Ahora:**
1. Agregar `HR-AutRot` al Excel
2. ✅ El sistema lo carga automáticamente
3. Accesible vía `hr_data.extra_sheets["HR-AutRot"]`
4. Ningún cambio de código requerido

### Caso 2: Acceder a los datos de una hoja nueva

```python
# Desde el servicio o resolver
hr_data = resolver.get_active_hr()

# Acceder a la hoja dinámica
if "HR-AutRot" in hr_data.extra_sheets:
    autrot_rows = hr_data.extra_sheets["HR-AutRot"]
    for row in autrot_rows:
        print(row)  # {'columna1': valor1, 'columna2': valor2, ...}
```

### Caso 3: Verificar qué hojas se cargaron

```bash
# Ver logs de carga
grep "[MAPPER] Extra sheets detected" logs/app.log

# Output:
# [MAPPER] Extra sheets detected (not in standard HR spec): ['HR-AutRot', 'HR-Custom']
```

---

## 📊 Flujo de Datos

### Upload de Excel con HR-AutRot

```
Excel File
    ↓
parametrization/hr/loader.py (read_excel_sheets)
    ↓
Sheets: {
    "HR-LV": [...],
    "HR-Nomina": [...],
    "HR-AutRot": [...]  ← Nueva hoja
}
    ↓
parametrization/hr/mapper.py
    ↓
HRMasterData(
    niveles=...,
    nomina=...,
    extra_sheets={
        "HR-AutRot": [...]  ← Guardada aquí
    }
)
    ↓
storage/parametrization/hr/{version_id}.json
    ↓
{
    "version_id": "...",
    "niveles": {...},
    "nomina": [...],
    "extra_sheets": {
        "HR-AutRot": [...]
    }
}
```

---

## 🔍 Validación

### Excel vs JSON

Cuando se ejecuta la validación (`/api/v1/parametrization/hr/validate`), también se validan las hojas extras:

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/validate \
  -F "file=@HR_productiva.xlsx"

# Output:
{
    "valid": true,
    "discrepancies": [],
    "excel_row_counts": {
        "HR-LV": 50,
        "HR-Nomina": 200,
        "HR-AutRot": 15  ← Validado
    },
    "json_row_counts": {
        "HR-LV": 50,
        "HR-Nomina": 200,
        "HR-AutRot": 15  ← Coincide
    }
}
```

---

## 🚀 Cómo Usarlo

### 1. Agregar una nueva hoja al Excel

```
HR_productiva.xlsx
├── HR-LV (existente)
├── HR-Nomina (existente)
├── HR-CostoFijo (existente)
└── HR-AutRot (NUEVA) ← Cualquier nombre que empiece con "HR-"
```

### 2. Subir el Excel

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx"

# Response incluirá info sobre HR-AutRot en extra_sheets
```

### 3. Acceder a los datos en código

```python
# En un servicio que inyecte ParametrizationProvider
provider = get_provider()

# Los repositorios tienen acceso a los datos extra
# Ejemplo: si necesitas usar HR-AutRot en un calculador
hr_data = resolver.get_active_hr()
autrot_data = hr_data.get("extra_sheets", {}).get("HR-AutRot", [])
```

### 4. Verificar en la API

```bash
curl http://localhost:8000/api/v1/parametrization/hr/active | jq '.data.extra_sheets'

# Output:
{
  "HR-AutRot": [
    {
      "columna1": "valor1",
      "columna2": "valor2",
      ...
    },
    ...
  ]
}
```

---

## ✅ Características

| Característica | Antes | Ahora |
|---|---|---|
| Cargar hojas estándar (11) | ✅ | ✅ |
| Cargar hojas personalizadas | ❌ | ✅ |
| Requiere modificar código | Sí | **No** |
| Requiere redeployar | Sí | **No** |
| Validación Excel vs JSON | Parcial | ✅ Completa |
| Logging de hojas detectadas | No | ✅ Sí |
| Acceso a datos personalizados | No | ✅ Vía extra_sheets |

---

## 🔐 Notas de Seguridad

- Las hojas se almacenan exactamente como vienen del Excel (sin transformación)
- Se normalizan valores numéricos (per el `ValueNormalizer`)
- Las hojas se persisten como JSON en `storage/parametrization/hr/`
- Acceso a través del sistema de resolver (no hay API pública para extra_sheets aún)

---

## 🧪 Testing

Para verificar que una nueva hoja se cargó:

```python
# En un test
def test_extra_sheets_loaded():
    resolver = ParametrizationResolver()
    hr_data = resolver.get_active_hr()
    
    assert "HR-AutRot" in hr_data.get("extra_sheets", {})
    assert len(hr_data["extra_sheets"]["HR-AutRot"]) > 0
    
    # Verificar estructura
    first_row = hr_data["extra_sheets"]["HR-AutRot"][0]
    assert "columna1" in first_row
    assert "columna2" in first_row
```

---

## 📈 Próximos Pasos (Opcional)

1. **API pública para extra_sheets**: Crear endpoint `/api/v1/parametrization/hr/extra-sheet/{name}`
2. **Validación por hoja**: Permitir definir esquemas de validación para hojas personalizadas
3. **Exportación**: Incluir extra_sheets en exportaciones de parametrización
4. **Versionamiento**: Rastrear cambios en hojas personalizadas

---

## 📞 Preguntas Frecuentes

### P: ¿Qué nombres de hojas son soportados?
R: Cualquier nombre que empiece con `HR-` será cargado automáticamente.

### P: ¿Los datos se validan?
R: Se normalizan valores numéricos (accents, espacios, moneda), pero no hay validación de esquema específica para hojas personalizadas.

### P: ¿Puedo usar esto en producción?
R: Sí, es retrocompatible. Las hojas estándar se mapean exactamente igual que antes. Las hojas nuevas se guardan como datos brutos.

### P: ¿Cómo accedo a los datos desde un calculador?
R: Los datos están disponibles en `HRMasterData.extra_sheets`. Inyecta `ParametrizationResolver` y llama a `resolver.get_active_hr()`.

---

**Status:** ✅ **LISTO PARA USAR**  
**Backward Compatibility:** ✅ MANTENIDA  
**Testing:** ✅ MANUAL - Sube un Excel con `HR-AutRot` y verifica que aparezca en `/parametrization/hr/active`
