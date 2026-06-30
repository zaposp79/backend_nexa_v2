# Error Handling Quick Reference — NEXA Simulator

**Guía rápida para desarrolladores** 📖

---

## 🔍 Identificar Errores en Logs

### Buscar errores del endpoint `/calculate`

```bash
# Buscar todos los errores
grep "[calculate] ✗" logs/app.log

# Buscar por tipo de error
grep "ParametrizationError" logs/app.log
grep "INTERNAL_ERROR" logs/app.log
grep "ValidationError" logs/app.log
```

### Formato de logs

```
ERROR: [calculate] ✗ <TipoError> capturado
ERROR: [calculate] status_code: <código>
ERROR: [calculate] detail: <mensaje>
ERROR: [calculate] exception_type: <clase>
ERROR: [calculate] exception_module: <módulo.origen>
Traceback (most recent call last):
  ...
```

---

## 📊 Códigos de Error

| Status | Error Code | Significado | Causa Común |
|--------|-----------|-------------|-------------|
| 422 | `PYDANTIC_VALIDATION_ERROR` | Validación de Pydantic falló | Campo requerido faltante, tipo incorrecto |
| 422 | `INPUT_ERROR` | Entrada inválida | `ValueError` en parsing de user_input |
| 422 | `PARAMETRIZATION_ERROR` | Parametrización incompleta | Falta parametrización para ciudad/servicio |
| 400 | `DOMAIN_ERROR` | Error de lógica de negocio | Regla de negocio violada |
| 500 | `VISION_INCOMPLETE` | Visión no construida | Rotura en cadena de cálculo |
| 500 | `AUDIT_INTEGRITY_ERROR` | Snapshot/traceabilidad falló | Error al persistir auditoría |
| 500 | `INTERNAL_ERROR` | Excepción no manejada | Error inesperado del servidor |
| 500 | `INTERNAL_SERVER_ERROR` | Global exception handler | Excepción fuera de `/calculate` |

---

## 🛠️ Debugging por Tipo de Error

### 1. PYDANTIC_VALIDATION_ERROR (422)

**Síntoma:**
```json
{
  "error": {
    "code": "PYDANTIC_VALIDATION_ERROR",
    "message": "Error de validación en el payload: 2 error(es)",
    "details": {
      "errors": [
        {"loc": ["panel_de_control", "margen"], "type": "type_error.float", "msg": "..."}
      ]
    }
  }
}
```

**Cómo resolverlo:**
1. Revisar `details.errors[].loc` — indica campo exacto
2. Revisar `details.errors[].type` — indica tipo de validación fallida
3. Corregir payload según el mensaje `msg`

**Ejemplo:**
```python
# ❌ Incorrecto
{"margen": "18%"}  # String en vez de float

# ✅ Correcto
{"margen": 0.18}
```

---

### 2. PARAMETRIZATION_ERROR (422)

**Síntoma:**
```json
{
  "error": {
    "code": "PARAMETRIZATION_ERROR",
    "message": "No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas",
    "details": {
      "module": "HR",
      "version_id": null,
      "panel_context": {"ciudad": "Cali", "linea_negocio": "Cobranzas"}
    }
  }
}
```

**Cómo resolverlo:**
1. Verificar que existe parametrización para la ciudad solicitada:
   ```bash
   curl http://localhost:8000/api/v1/parametrization/hr/active
   ```
2. Si no existe, cargar parametrización para esa ciudad
3. O usar una ciudad válida (ej. "Bogota")

**Logs a revisar:**
```bash
grep "parametrization_module" logs/app.log
grep "Panel context" logs/app.log
```

---

### 3. INPUT_ERROR (422)

**Síntoma:**
```json
{
  "error": {
    "code": "INPUT_ERROR",
    "message": "Campo requerido 'meses_contrato' faltante en panel_de_control",
    "details": {
      "payload_keys": ["panel_de_control", "condiciones_cadena_a"],
      "panel_context": {"cliente": "Bancamía", "ciudad": "Bogota"}
    }
  }
}
```

**Cómo resolverlo:**
1. Revisar `payload_keys` — secciones presentes en el payload
2. Revisar `panel_context` — valores del panel de control
3. Agregar campo faltante

**Validar payload antes de enviar:**
```bash
curl -X POST http://localhost:8000/api/v1/simulation/calculate/validate \
  -H "Content-Type: application/json" \
  -d @payload.json
```

---

### 4. VISION_INCOMPLETE (500)

**Síntoma:**
```json
{
  "error": {
    "code": "VISION_INCOMPLETE",
    "message": "Vision 'vision-pyg' no fue construida durante el cálculo",
    "details": {
      "module": "nexa_engine.adapters.pricing_serializer",
      "type": "VisionIncompleteError"
    }
  }
}
```

**Cómo resolverlo:**
1. **NO** es un error de payload — es un bug del motor
2. Revisar logs del motor:
   ```bash
   grep "calcular\|Vision" logs/app.log
   ```
3. Identificar qué paso del motor falló
4. Reportar como bug con:
   - Payload completo
   - Stacktrace de logs
   - `simulation_id` (si existe)

---

### 5. INTERNAL_ERROR (500)

**Síntoma:**
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Error inesperado en el servidor: division by zero",
    "details": {
      "exception_type": "ZeroDivisionError",
      "exception_module": "builtins",
      "payload_keys": ["panel_de_control"]
    }
  }
}
```

**Cómo resolverlo:**
1. Revisar stacktrace completo en logs:
   ```bash
   grep -A 50 "INTERNAL_ERROR" logs/app.log
   ```
2. Identificar línea exacta del fallo en el stacktrace
3. Revisar payload preview en logs (primeros 1000 chars)
4. Reproducir localmente:
   ```bash
   # Copiar payload de logs
   curl -X POST http://localhost:8000/api/v1/simulation/calculate \
     -H "Content-Type: application/json" \
     -d '<payload_from_logs>'
   ```
5. Debuggear con breakpoint en la línea identificada

---

## 🧪 Testing de Errores

### Verificar endpoint `/validate` antes de `/calculate`

```bash
# Primero validar el payload
curl -X POST http://localhost:8000/api/v1/simulation/calculate/validate \
  -H "Content-Type: application/json" \
  -d '{
    "panel_de_control": {
      "cliente": "Bancamía",
      "ciudad": "Bogota",
      "linea_negocio": "Cobranzas",
      "meses_contrato": 24,
      "margen": 0.18,
      "op_cont": 0.025
    }
  }'
```

**Si retorna `{"valid": true}`**, entonces ejecutar `/calculate`

**Si retorna error**, corregir según el código de error retornado

---

## 📋 Checklist de Debugging

### Cuando un cálculo falla:

1. ✅ **Revisar logs** — buscar `[calculate] ✗`
2. ✅ **Identificar tipo de excepción** — `exception_type`
3. ✅ **Revisar stacktrace** — línea exacta del fallo
4. ✅ **Revisar payload** — keys, panel_context, datos_operativos
5. ✅ **Verificar parametrización** — module, version_id
6. ✅ **Reproducir localmente** — usar payload de logs
7. ✅ **Crear test** — agregar caso fallido a suite de tests
8. ✅ **Corregir root cause** — no solo el síntoma

---

## 🔧 Herramientas de Debugging

### Endpoint de validación (sin ejecutar motor)

```bash
POST /api/v1/simulation/calculate/validate
```

**Respuesta si válido:**
```json
{
  "valid": true,
  "secciones": {
    "panel_de_control": "OK — cliente='Bancamía' ciudad='Bogota'",
    "condiciones_cadena_a": "OK — 2 perfil(es)"
  }
}
```

**Respuesta si inválido:**
```json
{
  "valid": false,
  "error_code": "MISSING_PANEL_FIELDS",
  "error_message": "panel_de_control le faltan campos requeridos: ['margen']",
  "campos_faltantes": ["margen"]
}
```

### Logs estructurados

```bash
# Ver flujo completo de un cálculo exitoso
grep -A 500 "▶ INICIO DE CÁLCULO" logs/app.log | grep -B 500 "✓ CÁLCULO COMPLETADO"

# Ver solo errores
grep "✗" logs/app.log

# Ver parametrización cargada
grep "Parametrización cargada:" logs/app.log
```

---

## 🚀 Best Practices

### Al agregar nuevos endpoints

1. **Siempre capturar excepciones específicas:**
   ```python
   try:
       ...
   except ParametrizationError as exc:
       logger.exception("[endpoint] ✗ ParametrizationError")
       logger.error("[endpoint] status_code: 422")
       logger.error("[endpoint] detail: %s", exc.message)
       ...
   ```

2. **Nunca retornar error vacío:**
   ```python
   # ❌ MAL
   raise HTTPException(400, detail="Error")
   
   # ✅ BIEN
   raise HTTPException(400, detail={
       "error": "Missing required parameter",
       "parameter": "ratios_staff",
       "module": "HRSimulationEngine"
   })
   ```

3. **Siempre loggear contexto:**
   ```python
   logger.error("[endpoint] Payload keys: %s", list(body.keys()))
   logger.error("[endpoint] User: %s", user_id)
   logger.error("[endpoint] Exception type: %s", type(exc).__name__)
   ```

4. **Usar `logger.exception(...)` para stacktrace:**
   ```python
   # ✅ Incluye stacktrace automáticamente
   logger.exception("[endpoint] ✗ Error processing request")
   
   # ❌ No incluye stacktrace
   logger.error("[endpoint] ✗ Error: %s", str(exc))
   ```

---

## 📞 Soporte

**Documentación completa:**
- [ERROR_HANDLING_IMPROVEMENTS.md](./ERROR_HANDLING_IMPROVEMENTS.md)
- [ERROR_HANDLING_SUMMARY.md](./ERROR_HANDLING_SUMMARY.md)

**Código fuente:**
- [calculate_router.py](../api/v1/simulation/calculate_router.py)
- [app.py](../app.py)

**Tests:**
- [test_calculate_endpoint_bancamia.py](../tests/integration/test_calculate_endpoint_bancamia.py)

---

**Última actualización:** 2026-05-27
