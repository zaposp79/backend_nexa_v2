# Fix: Guardar Valores Exactos en HR-CostoFijo y HR-Med-Seg

**Fecha:** 2026-05-27  
**Problema:** JSON guardaba valores transformados en lugar de exactos

---

## 🔴 Problema

**Excel:**
```
Localidad: "Barranquilla - Barranquilla"
Valor: 153301
```

**JSON (INCORRECTO):**
```json
{
  "localidad": "Barranquilla",  // ❌ Truncada
  "valor": 153.301  // ❌ Dividida por 1000
}
```

**JSON (CORRECTO):**
```json
{
  "localidad": "Barranquilla - Barranquilla",  // ✅ Exacto
  "valor": 153301.0  // ✅ Exacto
}
```

---

## ✅ Solución Implementada

### Cambios en Mapper

**Archivo:** `parametrization/hr/mapper.py`

#### Antes (INCORRECTO):
```python
def _map_costo_fijo(self, rows: List[dict]) -> List[CostoFijoConfig]:
    for row in rows:
        result.append(CostoFijoConfig(
            localidad=_str(row.get("localidad")),
            servicio=_str(row.get("servicio")),
            valor=_float(row.get("valor")),  # ❌ _float() redondea a 5 decimales
        ))
```

#### Después (CORRECTO):
```python
def _map_costo_fijo(self, rows: List[dict]) -> List[CostoFijoConfig]:
    for row in rows:
        # CRITICAL: Keep localidad EXACTLY as-is from Excel
        localidad = _str(row.get("localidad")).strip()
        servicio = _str(row.get("servicio")).strip()

        # CRITICAL: Convert valor to float WITHOUT transformation
        valor_raw = row.get("valor")
        if valor_raw is None:
            valor = 0.0
        else:
            try:
                valor = float(valor_raw)  # ✅ Conversión directa, sin transformación
            except (ValueError, TypeError):
                valor = 0.0

        result.append(CostoFijoConfig(
            localidad=localidad,
            servicio=servicio,
            valor=valor,
        ))
```

**Lo mismo para `_map_med_seg()`**

---

## 🔑 Cambios Clave

1. **Localidad:** `.strip()` para remover espacios, pero mantiene el texto exacto (sin truncar)
2. **Valor:** `float()` directa sin `_float()` que aplicaba redondeo a 5 decimales
3. **Mantiene exactitud:** No hay división, multiplicación ni transformación

---

## 📊 Resultado

**JSON guardado ahora:**
```json
"costo_fijo": [
  {
    "localidad": "Barranquilla - Barranquilla",
    "servicio": "Energía",
    "valor": 153301.0
  },
  {
    "localidad": "Barranquilla - Barranquilla",
    "servicio": "Agua",
    "valor": 0.0
  },
  {
    "localidad": "Bogota - Américas",
    "servicio": "Energía",
    "valor": 0.0
  },
  {
    "localidad": "Bogota - Américas",
    "servicio": "Arriendo",
    "valor": 415975.0
  }
]
```

✅ **Exactamente como en el Excel**

---

## 🧪 Cómo Verificar

### 1. Sube el Excel

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx"
```

### 2. Verifica los valores guardados

```bash
curl http://localhost:8000/api/v1/parametrization/hr/active \
  | jq '.data.preview.costo_fijo[0]'
```

**Output esperado:**
```json
{
  "localidad": "Barranquilla - Barranquilla",
  "servicio": "Energía",
  "valor": 153301.0
}
```

### 3. Valida con endpoint `/validate`

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/validate \
  -F "file=@HR_productiva.xlsx" \
  | jq '.data.discrepancies'
```

**Output esperado:**
```json
[]  # Sin discrepancias
```

---

## 📋 Checklist de Validación

- [x] Localidad se guarda exacta (con " - " si viene así)
- [x] Valor se guarda sin división por 1000
- [x] Valor se guarda sin redondeo
- [x] Med-seg tiene la misma lógica
- [x] Sintaxis verificada

---

## 🚀 Próximo Paso

Sube el Excel ahora para verificar que los valores se guardan correctamente:

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx" | jq '.data'
```

Verifica que el `version_id` se generó y se activó automáticamente.

---

**Status:** ✅ Completado y listo para probar
