# Debug: Identificar Nombres Exactos de Columnas en HR-Ratios

**Problema:** Los campos `categoria_servicio` y `servicio` siguen vacíos aunque el Excel tiene datos.

**Causa probable:** Los nombres de las columnas en el Excel son diferentes a los que estamos buscando.

---

## 🔍 Cómo Diagnosticar

### Paso 1: Subir el Excel y Capturar Logs

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx" 2>&1 | tee upload_response.json
```

### Paso 2: Revisar Logs de Mapeo

```bash
# En una terminal, ver logs en tiempo real:
tail -f logs/app.log | grep "\[MAPPING\] HR-Ratios"
```

**Buscar líneas como:**
```
[MAPPING] HR-Ratios sheet columns: ['Cargo', '???', '???', 'Agentes']
[MAPPING] HR-Ratios row 1: cargo='Director de cuentas', categoria_servicio='', tipo='Administrativo', agentes=750.0 | raw_keys=['Cargo', '???', '???', 'Agentes']
```

### Paso 3: Identificar Nombres Exactos

Reportar exactamente qué dice en `raw_keys`. Por ejemplo:
```
raw_keys=['Cargo', 'CategoriaServicio', 'Tipo', 'Agentes']
raw_keys=['Cargo', 'Categoría Servicio', 'Tipo', 'Agentes']
raw_keys=['Cargo', 'Categoria Servicio', 'Tipo_Perfil', 'Agentes']
```

---

## 📋 Nombres Potenciales de Columnas

Si tu Excel tiene columnas en **español**, pueden ser:

| Variación | Probabilidad |
|-----------|-------------|
| `CategoriaServicio` | Alta |
| `Categoría Servicio` (con tilde) | Alta |
| `Categoria Servicio` | Media |
| `categoria_servicio` | Media |
| `Tipo` | Alta |
| `Tipo de Perfil` | Media |
| `TipoPerfil` | Baja |
| `Agentes` | Alta |
| `Cantidad Agentes` | Baja |

---

## 🛠️ Solución Temporal

Si identificas el problema, puedes actualizar el mapper manualmente:

**Archivo:** `parametrization/hr/mapper.py`

```python
# En la función _map_ratios(), buscar:
categoria_servicio = (
    _str(row.get("CategoriaServicio")) or  # ← Tu columna real va aquí
    ...
)
```

**Ejemplo: Si tu Excel tiene `"Categoría Servicio"` (con tilde):**

```python
categoria_servicio = (
    _str(row.get("Categoría Servicio")) or  # ← Agregar esta línea
    _str(row.get("CategoriaServicio")) or
    ...
)
```

---

## 📝 Pasos para Reportar

1. Sube el Excel
2. Revisa los logs: `grep "\[MAPPING\] HR-Ratios sheet columns" logs/app.log`
3. Copia exactamente los nombres que aparecen en `raw_keys`
4. Reporta: "El Excel tiene columnas: ['Cargo', 'Xxx', 'Yyy', 'Agentes']"

Yo actualizaré el mapper para capturar esos nombres exactos.

---

## 🔧 Mapper Actual (Detecta Automáticamente)

El mapper ahora intenta múltiples variaciones:

```python
categoria_servicio = (
    _str(row.get("CategoriaServicio")) or
    _str(row.get("categoriaservicio")) or
    _str(row.get("categoria_servicio")) or
    _str(row.get("Categoria Servicio")) or  # ← Espacios
    _str(row.get("categoria servicio")) or
    _str(row.get("servicio")) or
    _str(row.get("Servicio"))
)
```

Si ninguna coincide, queda vacío y necesitamos los nombres exactos del Excel.

---

## 📥 Cómo Compartir Logs

**Opción 1: Copiar y pegar desde terminal**
```bash
tail -50 logs/app.log | grep "HR-Ratios"
# Copiar output aquí
```

**Opción 2: Guardar en archivo**
```bash
grep "HR-Ratios" logs/app.log > ratios_logs.txt
# Compartir ratios_logs.txt
```

---

## ✅ Una Vez Identificado

Una vez que identifiques el nombre exacto de las columnas, reporta:

> "El Excel tiene columnas: ['Cargo', 'Categoría Servicio', 'Tipo', 'Agentes']"

Y actualizaré el mapper para:
1. Agregar esas columnas específicas
2. Hacer el mapping correcto
3. Guardar los datos correctamente en JSON

---

**Próximo paso:** Sube el Excel y revisa los logs con el comando:
```bash
grep "\[MAPPING\] HR-Ratios" logs/app.log
```

Copia aquí las líneas que ves. 👇
