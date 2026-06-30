# Debug: Transformaciones en HR-CostoFijo

**Problema identificado:**
- Localidad: `"Barranquilla - Barranquilla"` → `"Barranquilla"` (truncada)
- Valor: `153301` → `153.301` (dividida por 1000)

---

## 🔍 Cómo Diagnosticar

Acabo de agregar logging detallado en 2 puntos:

1. **Value Normalizer** (`shared/value_normalizer.py`) — muestra transformaciones antes/después
2. **Mapper** (`parametrization/hr/mapper.py`) — muestra valores almacenados

### Paso 1: Sube el Excel

```bash
curl -X POST http://localhost:8000/api/v1/parametrization/hr/upload \
  -F "file=@HR_productiva.xlsx" 2>&1 | head -50
```

### Paso 2: Revisa los logs de normalización

```bash
grep "\[NORMALIZER\] HR-CostoFijo" logs/app.log
```

**Ejemplo de output esperado:**
```
[NORMALIZER] HR-CostoFijo row 2 BEFORE: localidad='Barranquilla - Barranquilla' valor='153301'
[NORMALIZER] HR-CostoFijo row 2 AFTER: localidad='Barranquilla - Barranquilla' valor=153301.0

[NORMALIZER] HR-CostoFijo row 3 BEFORE: localidad='Barranquilla - Barranquilla' valor='0'
[NORMALIZER] HR-CostoFijo row 3 AFTER: localidad='Barranquilla - Barranquilla' valor=0.0
```

### Paso 3: Revisa logs del mapper

```bash
grep "\[COSTO_FIJO\]" logs/app.log
```

**Ejemplo esperado:**
```
[COSTO_FIJO] row 1: localidad 'Barranquilla - Barranquilla'→'Barranquilla - Barranquilla' | valor '153301'→153301.0 | servicio='Energía'
[COSTO_FIJO] row 2: localidad 'Barranquilla - Barranquilla'→'Barranquilla - Barranquilla' | valor '0'→0.0 | servicio='Agua'
```

---

## 🎯 Interpretación de Logs

### Si dice en AFTER: `valor=153.301`

Significa que el normalizer está interpretando `153301` como `153.301`.

**Posible causa:**
- El Excel tiene `153.301` con punto como separador de miles (formato europeo)
- El normalizer lo interpreta como decimal

**Solución:**
- Cambiar Excel a formato sin separadores: `153301`
- O cambiar el normalizer para detectar formato correctamente

### Si dice en AFTER: `localidad='Barranquilla'` (sin "- Barranquilla")

Significa que el normalizer está truncando la localidad.

**Posible causa:**
- El normalizer de cadenas está removiendo parte del texto
- O el Excel tiene una columna diferente

**Solución:**
- El mapper debería mantener exacto (lo que hace ahora)

---

## 📋 Qué Reportar

Copia EXACTAMENTE lo que ves en los logs:

```
[NORMALIZER] HR-CostoFijo row 2 BEFORE: localidad='Xxx' valor='Yyy'
[NORMALIZER] HR-CostoFijo row 2 AFTER: localidad='Xxx' valor=Zzz

[COSTO_FIJO] row 1: localidad 'Aaa'→'Bbb' | valor 'Ccc'→Ddd | servicio='Eee'
```

Esto me permitirá identificar exactamente dónde está el problema:
- ¿Normalizer?
- ¿Mapper?
- ¿Excel?

---

## 🚀 Próximos Pasos

1. Sube el Excel
2. Revisa los dos logs (NORMALIZER + COSTO_FIJO)
3. Copia aquí EXACTAMENTE qué dice
4. Yo identificaré y corregiré el problema

**Sube el Excel ahora y reporta los logs.** 👇
