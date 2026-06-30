# Cargar rotacion_ausentismo desde Hojas Dinámicas

**Problema:** El sistema busca `rotacion_ausentismo` pero está en la nueva hoja dinámica `HR-AutRot`  
**Solución:** Sistema actualizado para buscar en `extra_sheets` con pattern matching  
**Status:** ✅ IMPLEMENTADO

---

## 🎯 Cómo Funciona Ahora

El sistema busca `rotacion_ausentismo` en **5 ubicaciones** (en este orden):

1. **Top-level:** `data["rotacion_ausentismo"]`
2. **Nested payroll:** `data["payroll"]["rotacion_ausentismo"]`
3. **Nested hr:** `data["hr"]["rotacion_ausentismo"]`
4. **Extra sheets (exact names):**
   - `extra_sheets["HR-Rotacion"]`
   - `extra_sheets["HR-AutRot"]`
   - `extra_sheets["HR-rotacion_ausentismo"]`
   - `extra_sheets["HR-Rotacion-Ausentismo"]`
5. **Extra sheets (pattern matching):** Cualquier sheet que contenga "rotacion", "ausentismo", "rotacion_ausentismo", o "autrot" (case-insensitive)

---

## 📋 Estructura Esperada

### Opción A: Hoja HR-AutRot con estructura de lista

```json
{
  "extra_sheets": {
    "HR-AutRot": [
      {
        "linea": "Cobranzas",
        "pct_rotacion_mensual": 0.1199,
        "pct_ausentismo": 0.0250,
        "pct_examen_anual": 0.0833
      },
      {
        "linea": "SAC",
        "pct_rotacion_mensual": 0.0899,
        "pct_ausentismo": 0.0300,
        "pct_examen_anual": 0.0833
      },
      {
        "linea": "default",
        "pct_rotacion_mensual": 0.0500,
        "pct_ausentismo": 0.0200,
        "pct_examen_anual": 0.0833
      }
    ]
  }
}
```

### Opción B: Top-level (después de mapeador)

```json
{
  "rotacion_ausentismo": [
    {
      "linea": "Cobranzas",
      "pct_rotacion_mensual": 0.1199,
      "pct_ausentismo": 0.0250,
      "pct_examen_anual": 0.0833
    }
  ]
}
```

---

## 🔍 Cómo Verificar

### 1. Ver si se detectó correctamente

```bash
# Buscar logs de detección
grep "[PAYROLL_REPO] Found rotacion_ausentismo" logs/app.log

# Output esperado (una de estas):
# [PAYROLL_REPO] Found rotacion_ausentismo in extra_sheets: HR-AutRot
# [PAYROLL_REPO] Found rotacion_ausentismo in extra_sheets by pattern: HR-AutRot
```

### 2. Ver estructura detectada

```bash
# Buscar logs de estructura
grep "[PAYROLL_REPO] rotacion_ausentismo" logs/app.log

# Output esperado:
# [PAYROLL_REPO] rotacion_ausentismo loaded=True
# [PAYROLL_REPO] rotacion_ausentismo structure: type=list
# [PAYROLL_REPO] rotacion_ausentismo[0] keys=['linea', 'pct_rotacion_mensual', 'pct_ausentismo', 'pct_examen_anual']
# [PAYROLL_REPO] rotacion_ausentismo rows=3
```

### 3. Ver lookup exitoso

```bash
# Buscar acceso exitoso
grep "[PARAM_SOURCE] parameter=pct_examen_anual" logs/app.log

# Output esperado:
# [PARAM_SOURCE] parameter=pct_examen_anual linea=Cobranzas source=HR-rotacion_ausentismo value=0.0833
```

---

## 🚀 Pasos para Configurar

### Paso 1: Verificar nombre de la hoja en Excel

Asegúrate que la hoja empiece con `HR-` y contenga "rotacion" o "autrot":
```
HR-AutRot ✅
HR-Rotacion ✅
HR-Rotacion-Ausentismo ✅
AutRot ❌ (no empieza con HR-)
rotacion_ausentismo ❌ (no empieza con HR-)
```

### Paso 2: Verificar estructura de datos

La hoja debe tener columnas:
- `linea` — Nombre de la línea de negocio
- `pct_rotacion_mensual` — Tasa mensual (ej: 0.1199)
- `pct_ausentismo` — Tasa de ausencia (ej: 0.0250)
- `pct_examen_anual` — Tasa de exámenes (ej: 0.0833)

Al menos una fila debe tener `linea="default"` para fallback.

### Paso 3: Subir el Excel

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx"
```

### Paso 4: Verificar carga

```bash
# Ver en API
curl http://localhost:8000/api/v1/parametrization/hr/active | jq '.data.extra_sheets'

# Debe mostrar:
{
  "HR-AutRot": [
    {"linea": "Cobranzas", "pct_rotacion_mensual": 0.1199, ...},
    ...
  ]
}
```

### Paso 5: Ejecutar request que use rotacion_ausentismo

```bash
curl -X POST http://localhost:8000/api/v1/simulation/calculate \
  -H "Content-Type: application/json" \
  -d '{...payload con linea="Cobranzas"...}'

# Debe retornar 200 OK (sin error "rotacion_ausentismo section missing")
```

---

## 📊 Flujo de Carga

```
Excel File
├── HR-LV (estándar)
├── HR-Nomina (estándar)
└── HR-AutRot (NUEVA - dinámica)
    │
    ↓
parametrization_loader.read_excel_sheets("HR-")
    │
    ├─ Carga: HR-LV, HR-Nomina (estándar)
    └─ Carga: HR-AutRot (detecta porque empieza con "HR-")
    │
    ↓
HRMasterData
├── niveles (de HR-LV)
├── nomina (de HR-Nomina)
└── extra_sheets
    └── HR-AutRot [...]
    │
    ↓
JSON Storage
{
  "version_id": "...",
  "niveles": {...},
  "nomina": [...],
  "extra_sheets": {
    "HR-AutRot": [...]
  }
}
    │
    ↓
PayrollParametrizationRepository._load_rotacion_ausentismo_cache()
├─ Check top-level ✗
├─ Check payroll.* ✗
├─ Check hr.* ✗
├─ Check extra_sheets[exact names] ✓ ENCONTRADO: "HR-AutRot"
└─ Cache in self._rotacion_ausentismo
    │
    ↓
_get_rotacion_field() → usa self._rotacion_ausentismo
```

---

## ✅ Validación

### Test 1: Hoja detectada
```bash
grep "[PAYROLL_REPO] Found rotacion_ausentismo" logs/app.log | head -1
# Must show: Found rotacion_ausentismo in extra_sheets
```

### Test 2: Estructura correcta
```bash
grep "[PAYROLL_REPO] rotacion_ausentismo rows" logs/app.log
# Must show: rotacion_ausentismo rows=N
```

### Test 3: Funciona
```bash
curl http://localhost:8000/api/v1/simulation/calculate \
  -d '{...linea="Cobranzas"...}'
# Must return 200 OK (no "section missing" error)
```

---

## 🔧 Si Sigue Sin Funcionar

### Debug 1: Ver qué hay en extra_sheets

```bash
# Buscar logs de search
grep "[PAYROLL_REPO] Searching in extra_sheets" logs/app.log
grep "[PAYROLL_REPO] Available sheets" logs/app.log

# Output debe mostrar: ['HR-AutRot', ...]
```

### Debug 2: Ver si la hoja tiene los datos

```bash
# Buscar logs de carga
grep "[MAPPER] Extra sheets detected" logs/app.log

# Output debe mostrar: ['HR-AutRot']
```

### Debug 3: Verificar nombre exacto de la hoja

La hoja DEBE:
- Empezar con `HR-`
- Contener "rotacion" O "ausentismo" O "autrot" (case-insensitive)

Nombres válidos:
```
HR-AutRot ✅
HR-Rotacion ✅
HR-rotacion_ausentismo ✅
HR-Rotacion-Ausentismo ✅
```

Nombres inválidos:
```
AutRot ❌ (sin HR- prefix)
HR-Autoridades ❌ (no contiene patrones de búsqueda)
HR-Rotation ❌ (idioma diferente)
```

---

## 📝 Próximos Pasos

1. **Subir Excel** con `HR-AutRot` que contenga rotacion_ausentismo
2. **Verificar logs** para confirmar detección
3. **Ejecutar request** para confirmar que funciona
4. **Monitorear logs** para validación en producción

---

## 💡 Notas Importantes

- El nombre de la hoja NO tiene que ser exactamente `HR-AutRot`, pero SÍ debe:
  - Empezar con `HR-`
  - Contener "rotacion" O "ausentismo" O "autrot" en el nombre
- La estructura de datos DEBE tener:
  - Una columna `linea` para identificar línea de negocio
  - Columnas para `pct_rotacion_mensual`, `pct_ausentismo`, `pct_examen_anual`
  - Al menos una fila con `linea="default"` para fallback
- El cache se carga una sola vez (lazy-loading), así que no hay overhead de performance

---

**Status:** ✅ LISTO  
**Updated:** 2026-05-27  
**Tested:** Pending (sube el Excel con HR-AutRot para verificar)
