# Skill: nexa-security-review

## When to use

Revisión de seguridad del backend FastAPI: exposición de errores, logging de datos sensibles, CORS, middlewares, handlers de errores, configuración de entorno, y production readiness. Aplica antes de un release o cuando se modifican capas HTTP, autenticación, o configuración de entorno.

**Riesgo esperado: alto** — hallazgos de seguridad que se ignoran pueden tener impacto en producción; correcciones mal aplicadas pueden romper contratos de API.

## When not to use

- Tareas de negocio o fórmulas (usa `nexa-backend-context`).
- Infraestructura Azure/Terraform (usa `infra-agent`).
- Revisión de código funcional sin componente de seguridad.

## Context to read first

1. `CLAUDE.md` — sección "Reglas críticas" y "Variables de entorno relevantes".
2. `modules/shared/responses.py` — formato `ApiResponse` y manejo de errores normalizado.
3. `app.py` o entry point de FastAPI — middlewares, CORS, lifespan.
4. `db/container.py` — inyección de dependencias y configuración de persistencia.
5. Handlers de errores globales (si existen en `modules/shared/` o middleware).

**No leer por defecto:** calculadores, fórmulas, parametrizaciones, tests golden.

## Operating rules

1. **Exposición de excepciones**: verificar que ningún handler devuelve `str(exc)` en producción — puede exponer stack traces, rutas, o datos internos.
2. **Logging de payloads sensibles**: verificar que logs no incluyen datos de clientes, valores de simulación completos, o credenciales.
3. **CORS**: verificar que `CORS_ALLOWED_ORIGINS` no incluye wildcards (`*`) en producción. Solo orígenes explícitos permitidos.
4. **Middlewares**: verificar orden de middlewares (CORS debe ir antes de autenticación).
5. **APP_ENV gate**: `/docs`, `/redoc`, `/openapi.json` solo disponibles en `APP_ENV=development` o `test`. Nunca en `production`.
6. **Cosmos**: `COSMOS_ENDPOINT` y `COSMOS_KEY` no deben loguearse ni exponerse. `ALLOW_COSMOS_NON_PRODUCTION=false` por defecto.
7. **Errores normalizados**: todos los errores deben usar `ApiResponse` con códigos estándar (`NOT_FOUND`, `VALIDATION_ERROR`, `DOMAIN_ERROR`, `INTERNAL_SERVER_ERROR`). No devolver excepciones raw.
8. **Inputs externos**: validar que inputs en endpoints de upload (parametrizaciones HR/GN/OP) están validados con Pydantic o guardrails antes de procesarse.
9. No cambiar comportamiento funcional para resolver hallazgos sin justificar el riesgo de la corrección.

## Forbidden actions

- Proponer cambios que alteren contratos de API por razones de seguridad sin análisis de impacto.
- Habilitar CORS wildcard `*` sin justificación explícita.
- Exponer información de configuración interna (`DB_PROVIDER`, rutas de storage) en respuestas de error.
- Activar `ALLOW_COSMOS_NON_PRODUCTION=true` en ambientes de desarrollo compartidos sin análisis.
- Quitar el `APP_ENV` gate de Swagger.

## Validation

```bash
# Verificar que la app levanta sin errores
# (iniciar en background y esperar startup antes de curl)
APP_ENV=development python -m backend_nexa.app &
sleep 2 && curl http://localhost:8000/health

# Verificar que /docs solo está en development
APP_ENV=production curl http://localhost:8000/docs  # debe devolver 404

# Smoke tests de seguridad (si existen)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -k "security" -v

# Revisar CORS en respuesta
curl -i -H "Origin: http://malicious.com" http://localhost:8000/health
```

## Final response format

```md
## Resultado
## Evidencia
## Riesgo
## Validación
## Siguiente paso
```

Incluir tabla de hallazgos con columnas: `Archivo | Línea | Hallazgo | Severidad | Acción recomendada`.

---

**Ejemplo de invocación:**

```
Usando la skill nexa-security-review:
Revisar production readiness de la capa HTTP antes del release.
Verificar: exposición de str(exc), CORS origins, APP_ENV gate de Swagger,
logging de payloads, errores normalizados en ApiResponse.
No cambiar comportamiento funcional — solo reportar hallazgos con severidad.
Leer: app.py, modules/shared/responses.py, db/container.py.
```
