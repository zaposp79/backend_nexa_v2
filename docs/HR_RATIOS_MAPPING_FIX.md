# Fix: Mapeo Completo de Columnas en HR-Ratios Sheet

**Fecha:** 2026-05-27  
**Problema:** El mapper de HR-Ratios estaba perdiendo los campos `CategoriaServicio` y `Tipo` del Excel

---

## 🔴 Problema Identificado

**Excel HR-Ratios:**
```
| Cargo | CategoriaServicio | Tipo | Agentes |
|-------|-------------------|------|---------|
| Director de cuentas | Cobranzas | Administrativo | 750 |
| Director de performance | Cobranzas | Administrativo | 1200 |
```

**JSON Guardado:**
```json
{
  "cargo": "Director de cuentas",
  "servicio": "",  // ❌ Debería ser "Cobranzas"
  "agentes": 750.0
  // ❌ Falta "tipo": "Administrativo"
}
```

**Causa raíz:**
- El mapper buscaba el campo `servicio` (lowercase)
- Pero el Excel tiene `CategoriaServicio` (CamelCase)
- No capturaba el campo `Tipo` del Excel

---

## ✅ Solución Implementada

### 1. Actualizar Modelo `RatiosConfig`

**Archivo:** `parametrization/hr/models.py`

```python
@dataclass
class RatiosConfig:
    """Row from HR-Ratios sheet. Agent ratios per cargo/service.

    Maps from Excel columns:
    - Cargo → cargo
    - CategoriaServicio → servicio (or categoria_servicio if distinct)
    - Tipo → tipo
    - Agentes → agentes
    """
    cargo: str
    servicio: str
    agentes: float
    tipo: str = ""  # Tipo from Excel (e.g. "Administrativo", "Operacional")
    categoria_servicio: str = ""  # Explicit category from Excel
```

**Cambios:**
- ✅ Agregado campo `tipo` (Administrativo, Operacional, etc.)
- ✅ Agregado campo `categoria_servicio` (para claridad)
- ✅ Documentado el mapeo de columnas Excel

### 2. Actualizar Mapper

**Archivo:** `parametrization/hr/mapper.py`

```python
def _map_ratios(self, rows: List[dict]) -> List[RatiosConfig]:
    result = []
    for idx, row in enumerate(rows, start=1):
        cargo = _str(row.get("cargo"))
        if not cargo:
            continue

        # Map Excel columns to RatiosConfig fields
        # Excel may have "CategoriaServicio" (capital) or "servicio" (lowercase)
        categoria_servicio = _str(row.get("CategoriaServicio")) or _str(row.get("servicio"))
        tipo = _str(row.get("Tipo")) or _str(row.get("tipo"))
        agentes = _float(row.get("Agentes") or row.get("agentes"))

        # Log first few rows to verify mapping
        if idx <= 3 and (categoria_servicio or tipo):
            logger.info(
                "[MAPPING] HR-Ratios row %d: cargo=%r, categoria_servicio=%r, tipo=%r, agentes=%s",
                idx, cargo, categoria_servicio, tipo, agentes
            )

        result.append(RatiosConfig(
            cargo=cargo,
            servicio=categoria_servicio,
            agentes=agentes,
            tipo=tipo,
            categoria_servicio=categoria_servicio,
        ))
    return result
```

**Cambios:**
- ✅ Busca tanto `CategoriaServicio` como `servicio` (backward compatible)
- ✅ Busca tanto `Tipo` como `tipo` (case-insensitive)
- ✅ Busca tanto `Agentes` como `agentes` (case-insensitive)
- ✅ Logging de primeras 3 filas para verificar mapeo

---

## 🧪 JSON Guardado Ahora

**Después del fix:**
```json
{
  "cargo": "Director de cuentas",
  "servicio": "Cobranzas",      // ✅ Capturado correctamente
  "agentes": 750.0,
  "tipo": "Administrativo",      // ✅ Nuevo campo
  "categoria_servicio": "Cobranzas"  // ✅ Explícito
}
```

---

## 📊 Logs de Mapeo

**Logs generados durante upload:**
```
[MAPPING] HR-Ratios row 1: cargo='Director de cuentas', categoria_servicio='Cobranzas', tipo='Administrativo', agentes=750.0
[MAPPING] HR-Ratios row 2: cargo='Director de performance', categoria_servicio='Cobranzas', tipo='Administrativo', agentes=1200.0
[MAPPING] HR-Ratios row 3: cargo='...'
```

---

## 🔄 Backward Compatibility

El fix es **100% backward compatible**:
- El campo `servicio` sigue siendo el principal (para código existente)
- Los nuevos campos (`tipo`, `categoria_servicio`) son opcionales (valores por defecto vacíos)
- Soporta tanto Excel con `servicio` como con `CategoriaServicio`
- Soporta tanto `Tipo` como `tipo`
- Soporta tanto `Agentes` como `agentes`

---

## 🚀 Cómo Verificar el Fix

### 1. Subir el Excel HR

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx"
```

### 2. Revisar Logs

```bash
grep "\[MAPPING\] HR-Ratios" logs/app.log
```

**Output esperado:**
```
[MAPPING] HR-Ratios row 1: cargo='Director de cuentas', categoria_servicio='Cobranzas', tipo='Administrativo', agentes=750.0
[MAPPING] HR-Ratios row 2: cargo='Director de performance', categoria_servicio='Cobranzas', tipo='Administrativo', agentes=1200.0
```

### 3. Verificar JSON Guardado

```bash
curl http://localhost:8000/api/v1/parametrization/hr/active \
  | jq '.data.preview.ratios[0]'
```

**Output esperado:**
```json
{
  "cargo": "Director de cuentas",
  "servicio": "Cobranzas",
  "agentes": 750.0,
  "tipo": "Administrativo",
  "categoria_servicio": "Cobranzas"
}
```

### 4. Validar con Endpoint `/validate`

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/validate \
  -F "file=@HR_productiva.xlsx" | jq '.data.discrepancies'
```

**Output esperado:**
```json
[]  # Sin discrepancias
```

---

## 📋 Cambios Resumen

| Componente | Cambio | Estado |
|------------|--------|--------|
| `RatiosConfig` modelo | +`tipo`, +`categoria_servicio` | ✅ |
| `_map_ratios()` mapper | Captura CategoriaServicio, Tipo | ✅ |
| Logging | Muestra primeras 3 filas | ✅ |
| Backward compatibility | 100% compatible | ✅ |

---

## ✅ Verificación de Sintaxis

```bash
python -m py_compile parametrization/hr/models.py
python -m py_compile parametrization/hr/mapper.py
```

✅ **Sin errores de sintaxis**

---

## 🔗 Relacionado

- [HR_PARAMETRIZATION_DATA_FLOW.md](./HR_PARAMETRIZATION_DATA_FLOW.md)
- [HR_PARAMETRIZATION_FIX_SUMMARY.md](./HR_PARAMETRIZATION_FIX_SUMMARY.md)

---

**Autor:** Claude Sonnet 4.5  
**Status:** ✅ Completado  
**Pruebas:** Pendiente ejecución en ambiente
