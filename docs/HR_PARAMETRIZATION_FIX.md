# Solución: Corrección de Validación de Parametrización RR.HH.

## Resumen Ejecutivo

Se ha resuelto el error bloqueante `HR parametrization missing required key: 'dotaciones_mensual'` que impedía ejecutar simulaciones. La solución implementa transformaciones automáticas y mapeos flexibles para aceptar diferentes formatos de datos de HR sin requerir modificaciones en los JSONs de entrada.

## Problema Original

El backend exigía claves de parametrización muy específicas:
- **Error**: "HR parametrization missing required key: 'dotaciones_mensual'"
- **Causa raíz**: El JSON enviaba "Dotaciones (annual)" dentro de un array de salarios, pero el backend buscaba exactamente "Dotaciones (mensual)"
- **Impacto**: Las simulaciones se detenían, bloqueando todo el pipeline

## Solución Implementada

### 1. Conversión Automática de Dotaciones Anuales

**Archivo**: `repositories/payroll_parametrization_repository.py`
**Método**: `get_base_salary_data()`

```python
# Busca "Dotaciones (annual)" y convierte automáticamente
if "dotaciones" in servicio_norm and "annual" in servicio_norm:
    dotaciones_annual = float(valor)

# Si no existe "Dotaciones (mensual)", usa annual/12
if "dotaciones_mensual" not in result and dotaciones_annual is not None:
    result["dotaciones_mensual"] = dotaciones_annual / 12.0
```

**Ventaja**: Acepta tanto formatos mensuales como anuales automáticamente.

### 2. Mapeos Flexibles y Normalizados

**Normalizaciones implementadas**:
- Case-insensitive: "Salario Mínimo" = "salario minimo" = "SALARIO MÍNIMO"
- Accent-insensitive: "Mínimo" = "Minimo"
- Remove special characters: "%Cumplimiento" → "Cumplimiento"

**Estrategia de matching**:
1. Intenta coincidencia exacta (backward compatibility)
2. Si falla, intenta matching normalizado
3. Si falla, aplica reglas especiales (ej: annual/12)

### 3. Normalización de Localidades

**Archivo**: `repositories/infrastructure_parametrization_repository.py`
**Método**: `_normalize_city()`

Elimina sufijos compuestos para permitir matching flexible:
```python
"Bogota - Toberin"  → "bogota"
"Bogota - Américas" → "bogota"
"Medellín - Centro" → "medellin"
```

### 4. Manejo de Duplicados

**Método**: `get_ratios_staff()`

Si un cargo aparece múltiples veces, toma el primer valor no nulo:
```python
if cargo and agentes is not None and cargo not in result:
    result[cargo] = float(agentes)
```

## Archivos Modificados

### `repositories/payroll_parametrization_repository.py`
- Mejorada función `_normalize()`: 
  - Ahora también elimina `%` además de `()` y acentos
- Reescrito `get_base_salary_data()`:
  - Soporte para "Dotaciones (annual)"
  - Matching normalizado para nombres de servicios
  - Mejor documentación de la lógica
- Mejorado `get_ratios_staff()`:
  - Documentado manejo de duplicados
  - Toma primer valor no nulo

### `repositories/infrastructure_parametrization_repository.py`
- Mejorada `_normalize_city()`:
  - Elimina sufijos compuestos con regex
  - Mejor manejo de compound names
- Agregadas importaciones: `re`, `unicodedata`

## Tests Agregados

**Archivo**: `tests/unit/test_hr_parametrization_enhancements.py`

10 tests que validan:
- ✓ Normalización de acentos
- ✓ Normalización de caracteres especiales
- ✓ Mapeo exacto (backward compatibility)
- ✓ Mapeo normalizado
- ✓ Conversión annual → monthly
- ✓ Precedencia mensual > annual
- ✓ Manejo de valores None
- ✓ Normalización de localidades
- ✓ Normalización de compound names con sufijos

**Status**: 31/31 tests de parametrización pasan ✓

## Impacto

### ✓ Resuelve
- Bloqueo de simulaciones por dotaciones
- Validación rigidizada de nombres de parámetros
- Inflexibilidad ante diferentes formatos de Excel

### ✓ Mantiene
- Backward compatibility con mapeos existentes
- Precisión de cálculos de nómina
- Estructura de datos interna

### ✓ Permite
- Ejecutar simulaciones sin modificar JSONs
- Aceptar datos de Excel con variaciones de formato
- Mejor robustez ante datos de entrada

## Ejemplo de Uso

**Antes**: Requería exacto "Dotaciones (mensual)"
```json
{
  "salarios": [
    {"servicio": "Salario Mínimo", "valor": 1300000},
    {"servicio": "Dotaciones (mensual)", "valor": 50000}  // ← Exacto requerido
  ]
}
```

**Después**: Acepta tanto monthly como annual
```json
{
  "salarios": [
    {"servicio": "salario minimo", "valor": 1300000},  // ← Case insensitive
    {"servicio": "Dotaciones (annual)", "valor": 600000}  // ← Auto-converted /12
  ]
}
```

## Validación

✓ Todos los tests de parametrización pasan (31/31)
✓ Backward compatibility verificada
✓ Sin impacto en otros módulos
✓ Error bloqueante resuelto

## Próximos Pasos

Para máxima robustez, se podría considerar:
1. Agregar más variaciones de nombres en el mapping (ej. "Auxilio de transporte")
2. Implementar logging detallado de transformaciones aplicadas
3. Crear configuración centralizada de mappings de atributos
