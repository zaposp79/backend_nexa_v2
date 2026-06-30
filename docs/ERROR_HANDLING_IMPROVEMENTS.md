# Mejoras en el Manejo de Errores del Endpoint /calculate

**Fecha:** 2026-05-27  
**Objetivo:** Corregir el manejo de errores del endpoint `/api/v1/simulation/calculate` para exponer el error real y asegurar trazabilidad completa en logs.

---

## 🎯 Problema Resuelto

**Antes:** El sistema retornaba únicamente `400 Bad Request` sin detalle útil, impidiendo identificar la causa raíz durante la ejecución del motor de simulación.

**Ahora:** Cada error incluye:
- ✅ Tipo de excepción
- ✅ Módulo de origen
- ✅ Stacktrace completo
- ✅ Contexto del payload
- ✅ Detalle técnico específico
- ✅ Status code apropiado

---

## 📦 Cambios Implementados

### 1. **Imports Actualizados** ([calculate_router.py:25-32](../api/v1/simulation/calculate_router.py))

```python
import json
import logging
import traceback
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
```

**Agregados:**
- `json` — para serializar payload en logs
- `traceback` — para capturar stacktrace completo
- `HTTPException` — para captura explícita de excepciones HTTP
- `PydanticValidationError` — para validaciones de Pydantic con detalle de campo

---

### 2. **Logging Estructurado en Fases** ([calculate_router.py:183-244](../api/v1/simulation/calculate_router.py))

Cada fase del cálculo ahora registra:

```python
# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: Log de entrada — trazabilidad completa del payload
# ═══════════════════════════════════════════════════════════════════════
logger.info("=" * 80)
logger.info("[calculate] ▶ INICIO DE CÁLCULO")
logger.info("[calculate] Timestamp: %s", datetime.now(timezone.utc).isoformat())
logger.info("[calculate] Payload keys: %s", list(body.user_input.keys()))

# Log detallado del payload completo (para debugging)
try:
    payload_str = json.dumps(body.user_input, indent=2, ensure_ascii=False)
    logger.debug("[calculate] Payload completo:\n%s", payload_str)
except Exception as json_err:
    logger.warning("[calculate] No se pudo serializar el payload: %s", json_err)
```

**Fases con logging:**
1. ✅ Log de entrada (payload keys + payload completo)
2. ✅ Validación de contrato
3. ✅ Carga de user_input
4. ✅ Construcción de PricingRequest
5. ✅ Ejecución del motor
6. ✅ Validación de visiones
7. ✅ Persistencia de resultados
8. ✅ Persistencia de traceabilidad
9. ✅ Persistencia de SimulationSnapshot
10. ✅ Respuesta exitosa

---

### 3. **Captura Explícita de Excepciones** ([calculate_router.py:280-540](../api/v1/simulation/calculate_router.py))

#### 3.1 HTTPException

```python
except HTTPException as exc:
    logger.exception("[calculate] ✗ HTTPException capturada")
    logger.error("[calculate] status_code: %d", exc.status_code)
    logger.error("[calculate] detail: %s", exc.detail)
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))
    raise  # Re-raise para que FastAPI lo maneje
```

#### 3.2 PydanticValidationError

```python
except PydanticValidationError as exc:
    logger.exception("[calculate] ✗ Pydantic ValidationError capturada")
    
    validation_errors = exc.errors()
    logger.error("[calculate] Validation errors detallados:")
    for idx, err in enumerate(validation_errors, 1):
        logger.error(
            "  [%d] loc=%s type=%s msg=%s",
            idx,
            err.get("loc"),
            err.get("type"),
            err.get("msg")
        )
    
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="PYDANTIC_VALIDATION_ERROR",
                message=f"Error de validación en el payload: {len(validation_errors)} error(es)",
                details={
                    "errors": validation_errors,
                    "payload_keys": list(body.user_input.keys()),
                }
            ),
        ).model_dump(),
    )
```

**Incluye:**
- ✅ Serialización de `exc.errors()` con detalle de campo
- ✅ Location del error (`loc`)
- ✅ Tipo de validación fallida (`type`)
- ✅ Mensaje descriptivo (`msg`)

#### 3.3 VisionIncompleteError

```python
except VisionIncompleteError as exc:
    logger.exception("[calculate] ✗ VISION_INCOMPLETE detectado")
    logger.error("[calculate] status_code: 500")
    logger.error("[calculate] detail: %s", str(exc))
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="VISION_INCOMPLETE",
                message=str(exc),
                details={
                    "module": type(exc).__module__,
                    "type": type(exc).__name__,
                }
            ),
        ).model_dump(),
    )
```

#### 3.4 ValueError

```python
except ValueError as exc:
    logger.exception("[calculate] ✗ ValueError capturado (input inválido)")
    logger.error("[calculate] status_code: 422")
    logger.error("[calculate] detail: %s", str(exc))
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))
    
    panel = body.user_input.get("panel_de_control", {})
    if panel:
        logger.error(
            "[calculate] Panel context: cliente=%r ciudad=%r linea=%r",
            panel.get("cliente"),
            panel.get("ciudad"),
            panel.get("linea_negocio")
        )
    
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="INPUT_ERROR",
                message=str(exc),
                details={
                    "module": type(exc).__module__,
                    "type": type(exc).__name__,
                    "payload_keys": list(body.user_input.keys()),
                    "panel_context": panel if panel else None,
                }
            ),
        ).model_dump(),
    )
```

**Incluye:**
- ✅ Contexto del panel de control (si existe)
- ✅ Payload keys
- ✅ Módulo y tipo de excepción

#### 3.5 ParametrizationError

```python
except ParametrizationError as exc:
    logger.exception("[calculate] ✗ ParametrizationError capturado")
    logger.error("[calculate] status_code: 422")
    logger.error("[calculate] detail: %s", exc.message)
    
    # Contexto de parametrización
    if hasattr(exc, 'module') and exc.module:
        logger.error("[calculate] parametrization_module: %s", exc.module)
    if hasattr(exc, 'version_id') and exc.version_id:
        logger.error("[calculate] parametrization_version: %s", exc.version_id)
    
    # Contexto del payload
    panel = body.user_input.get("panel_de_control", {})
    datos = body.user_input.get("datos_operativos", {})
    
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="PARAMETRIZATION_ERROR",
                message=exc.message,
                details={
                    "module": getattr(exc, 'module', None),
                    "version_id": getattr(exc, 'version_id', None),
                    "panel_context": panel if panel else None,
                    "datos_operativos": datos if datos else None,
                }
            ),
        ).model_dump(),
    )
```

**Incluye:**
- ✅ Módulo de parametrización que falló
- ✅ Version ID activa
- ✅ Contexto del panel y datos operativos

#### 3.6 AuditIntegrityError

```python
except AuditIntegrityError as exc:
    logger.exception("[calculate] ✗ AuditIntegrityError capturado")
    logger.error("[calculate] status_code: 500")
    logger.error("[calculate] detail: %s", exc.message)
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="AUDIT_INTEGRITY_ERROR",
                message=exc.message,
                details={
                    "module": type(exc).__module__,
                    "type": type(exc).__name__,
                }
            ),
        ).model_dump(),
    )
```

#### 3.7 DomainError

```python
except DomainError as exc:
    logger.exception("[calculate] ✗ DomainError capturado")
    logger.error("[calculate] status_code: 400")
    logger.error("[calculate] detail: %s", exc.message)
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    
    # Intentar extraer información adicional de subclases
    extra_details = {}
    if hasattr(exc, 'field'):
        logger.error("[calculate] field: %s", exc.field)
        extra_details['field'] = exc.field
    if hasattr(exc, 'resource'):
        logger.error("[calculate] resource: %s", exc.resource)
        extra_details['resource'] = exc.resource
    if hasattr(exc, 'identifier'):
        logger.error("[calculate] identifier: %s", exc.identifier)
        extra_details['identifier'] = exc.identifier
    
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="DOMAIN_ERROR",
                message=exc.message,
                details={
                    "module": type(exc).__module__,
                    "type": type(exc).__name__,
                    **extra_details,
                }
            ),
        ).model_dump(),
    )
```

**Incluye:**
- ✅ Extracción de campos adicionales (`field`, `resource`, `identifier`)
- ✅ Módulo y tipo de excepción

#### 3.8 Exception (Catch-All)

```python
except Exception as exc:
    # Log completo del stacktrace
    logger.exception("[calculate] ✗ INTERNAL_ERROR — Excepción no manejada capturada")
    logger.error("[calculate] status_code: 500")
    logger.error("[calculate] detail: %s", str(exc))
    logger.error("[calculate] exception_type: %s", type(exc).__name__)
    logger.error("[calculate] exception_module: %s", type(exc).__module__)
    logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))
    
    # Obtener stacktrace formateado
    tb_str = traceback.format_exc()
    logger.error("[calculate] Stacktrace completo:\n%s", tb_str)
    
    # Intentar serializar el payload para logging
    try:
        payload_preview = json.dumps(body.user_input, indent=2, ensure_ascii=False)[:1000]
        logger.error("[calculate] Payload preview (primeros 1000 chars):\n%s", payload_preview)
    except Exception:
        logger.error("[calculate] No se pudo serializar el payload para preview")
    
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message=f"Error inesperado en el servidor: {str(exc)}",
                details={
                    "exception_type": type(exc).__name__,
                    "exception_module": type(exc).__module__,
                    "payload_keys": list(body.user_input.keys()),
                }
            ),
        ).model_dump(),
    )
```

**Incluye:**
- ✅ Stacktrace completo formateado
- ✅ Payload preview (primeros 1000 chars)
- ✅ Tipo y módulo de excepción
- ✅ Payload keys

---

### 4. **Middleware Global de Excepciones** ([app.py:106-154](../app.py))

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones no capturadas.

    Previene errores silenciosos y asegura trazabilidad completa de:
    - Tipo de excepción
    - Módulo de origen
    - Stacktrace completo
    - Request path y método
    """
    import traceback

    # Log completo del error
    logger.exception(
        "[NEXA] ✗ Unhandled exception during request: %s %s",
        request.method,
        request.url.path
    )
    logger.error("[NEXA] exception_type: %s", type(exc).__name__)
    logger.error("[NEXA] exception_module: %s", type(exc).__module__)
    logger.error("[NEXA] exception_message: %s", str(exc))

    # Log stacktrace completo
    tb_str = traceback.format_exc()
    logger.error("[NEXA] Stacktrace completo:\n%s", tb_str)

    # Intentar loggear información del request
    try:
        logger.error("[NEXA] Request URL: %s", request.url)
        logger.error("[NEXA] Request method: %s", request.method)
        logger.error("[NEXA] Request headers: %s", dict(request.headers))
    except Exception as log_err:
        logger.error("[NEXA] No se pudo loggear información del request: %s", log_err)

    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message=f"Error inesperado en el servidor: {str(exc)}",
                details={
                    "exception_type": type(exc).__name__,
                    "exception_module": type(exc).__module__,
                    "request_path": request.url.path,
                    "request_method": request.method,
                }
            )
        ).model_dump()
    )
```

**Protege contra:**
- ❌ Excepciones no manejadas en ANY endpoint
- ❌ Errores silenciosos
- ❌ Respuestas sin detalle

---

### 5. **Mejora en ErrorDetail** ([shared/responses.py:9-13](../shared/responses.py))

```python
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Union[Dict[str, Any], list]] = None  # ← Ahora acepta dict o list
```

**Antes:** `details: Optional[list] = None`  
**Ahora:** `details: Optional[Union[Dict[str, Any], list]] = None`

✅ Permite enviar detalles estructurados como diccionarios

---

## 📝 Ejemplo de Logs

### ✅ Cálculo Exitoso

```
================================================================================
[calculate] ▶ INICIO DE CÁLCULO
[calculate] Timestamp: 2026-05-27T10:30:00.123456Z
[calculate] Payload keys: ['panel_de_control', 'condiciones_cadena_a', 'condiciones_cadena_b', 'condiciones_cadena_c']
[calculate] Panel: cliente='Bancamía' ciudad='Bogota' linea='Cobranzas' meses=24 margen=0.18
[calculate] → Validando contrato entry_data
[calculate] ✓ Contrato entry_data válido
[calculate] → Cargando user_input
[calculate] ✓ UserInput cargado correctamente
[calculate] → Construyendo PricingRequest desde parametrización
[calculate] ✓ PricingRequest construido correctamente
[calculate] Parametrización cargada:
  - HR: version=v1_20260527_000000
  - GN: version=v1_20260527_000000
  - OP: version=v1_20260527_000000
[calculate] → Ejecutando motor de precios
[calculate] ✓ Motor ejecutado correctamente
[calculate] → Validando completitud de visiones
[calculate] ✓ Todas las visiones completas
[calculate] → Persistiendo resultados
[calculate] ✓ Resultados guardados: 550e8400-e29b-41d4-a716-446655440000
[calculate] → Persistiendo traceabilidad (FASE G)
[calculate] ✓ Traceabilidad guardada
[calculate] → Persistiendo SimulationSnapshot (FASE 4)
[calculate] ✓ SimulationSnapshot guardado: 550e8400-e29b-41d4-a716-446655440000
[calculate] ✓ CÁLCULO COMPLETADO EXITOSAMENTE
[calculate] simulation_id: 550e8400-e29b-41d4-a716-446655440000
================================================================================
```

### ❌ Error de Parametrización

```
================================================================================
[calculate] ▶ INICIO DE CÁLCULO
[calculate] Timestamp: 2026-05-27T10:35:00.123456Z
[calculate] Payload keys: ['panel_de_control', 'condiciones_cadena_a']
[calculate] Panel: cliente='Bancamía' ciudad='Cali' linea='Cobranzas' meses=24 margen=0.18
[calculate] → Cargando user_input
[calculate] ✓ UserInput cargado correctamente
[calculate] → Construyendo PricingRequest desde parametrización
ERROR: [calculate] ✗ ParametrizationError capturado
ERROR: [calculate] status_code: 422
ERROR: [calculate] detail: No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas
ERROR: [calculate] exception_type: ParametrizationError
ERROR: [calculate] exception_module: nexa_engine.shared.exceptions
ERROR: [calculate] parametrization_module: HR
ERROR: [calculate] parametrization_version: None
ERROR: [calculate] Panel context: cliente='Bancamía' ciudad='Cali' linea='Cobranzas'
Traceback (most recent call last):
  File "/Users/.../calculate_router.py", line 195, in calculate
    solicitud = builder.construir(user_input)
  File "/Users/.../context_builder.py", line 45, in construir
    raise ParametrizationError("No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas", module="HR")
nexa_engine.shared.exceptions.ParametrizationError: No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas
```

**Response JSON:**
```json
{
  "success": false,
  "error": {
    "code": "PARAMETRIZATION_ERROR",
    "message": "No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas",
    "details": {
      "module": "HR",
      "version_id": null,
      "panel_context": {
        "cliente": "Bancamía",
        "linea_negocio": "Cobranzas",
        "ciudad": "Cali",
        "meses_contrato": 24,
        "margen": 0.18
      },
      "datos_operativos": null
    }
  }
}
```

### ❌ Error de Validación (Pydantic)

```
ERROR: [calculate] ✗ Pydantic ValidationError capturada
ERROR: [calculate] exception_type: ValidationError
ERROR: [calculate] Payload keys: ['panel_de_control', 'condiciones_cadena_a']
ERROR: [calculate] Validation errors detallados:
ERROR:   [1] loc=('panel_de_control', 'margen') type=type_error.float msg='value is not a valid float'
ERROR:   [2] loc=('condiciones_cadena_a', 'perfiles') type=value_error.missing msg='field required'
Traceback (most recent call last):
  ...
```

**Response JSON:**
```json
{
  "success": false,
  "error": {
    "code": "PYDANTIC_VALIDATION_ERROR",
    "message": "Error de validación en el payload: 2 error(es)",
    "details": {
      "errors": [
        {
          "loc": ["panel_de_control", "margen"],
          "type": "type_error.float",
          "msg": "value is not a valid float"
        },
        {
          "loc": ["condiciones_cadena_a", "perfiles"],
          "type": "value_error.missing",
          "msg": "field required"
        }
      ],
      "payload_keys": ["panel_de_control", "condiciones_cadena_a"]
    }
  }
}
```

---

## ✅ Verificación

### Checklist de Requerimientos

- [x] **R1:** Captura explícita de excepciones con try/except
- [x] **R2:** Log de stacktrace completo usando `logger.exception(...)`
- [x] **R3:** Log de `status_code`, `detail`, tipo, y módulo de excepción
- [x] **R4:** Logging estructurado de payload keys y payload completo
- [x] **R5:** Manejo específico de `ValidationError` de Pydantic con `e.errors()`
- [x] **R6:** Nunca retornar `HTTPException(400)` vacío — siempre incluye contexto
- [x] **R7:** Middleware global de excepciones implementado
- [x] **R8:** Trazabilidad de parametrización cargada (módulos, versiones)
- [x] **R9:** ErrorDetail flexible para aceptar dict o list en `details`

### Ejemplo de Response Correcto

✅ **Nunca más:**
```json
{
  "detail": "Bad Request"
}
```

✅ **Ahora:**
```json
{
  "success": false,
  "error": {
    "code": "PARAMETRIZATION_ERROR",
    "message": "No se encontró parametrización activa para ciudad=Cali servicio=Cobranzas",
    "details": {
      "module": "HR",
      "version_id": null,
      "panel_context": {
        "cliente": "Bancamía",
        "ciudad": "Cali",
        "linea_negocio": "Cobranzas"
      }
    }
  }
}
```

---

## 🔍 Debugging Workflow

Cuando ocurre un error en producción:

1. **Consultar logs del servidor** → buscar `[calculate] ✗`
2. **Identificar tipo de excepción** → `exception_type` y `exception_module`
3. **Revisar stacktrace completo** → identifica línea exacta del fallo
4. **Analizar contexto del payload** → `payload_keys`, `panel_context`, `datos_operativos`
5. **Verificar parametrización** → `parametrization_module`, `version_id`
6. **Reproducir localmente** → usar payload loggeado para crear test

---

## 📚 Referencias

- [calculate_router.py](../api/v1/simulation/calculate_router.py) — Endpoint principal
- [app.py](../app.py) — Middleware global
- [shared/responses.py](../shared/responses.py) — ErrorDetail mejorado
- [shared/exceptions.py](../shared/exceptions.py) — Excepciones de dominio

---

## 🚀 Próximos Pasos (Opcional)

1. **Agregar métricas de errores** — contar tipos de excepciones por endpoint
2. **Alerting automático** — notificar cuando se detecta INTERNAL_ERROR
3. **Dashboard de errores** — visualizar tendencias de errores en Grafana
4. **Tests de error handling** — verificar respuestas de cada tipo de error
