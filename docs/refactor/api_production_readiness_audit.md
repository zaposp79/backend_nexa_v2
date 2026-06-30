# API Production Readiness Audit

**Date:** 2026-06-12  
**Branch:** `refactor/modular-pure`  
**Scope:** API layer only — routers, handlers, exception handling, logging, HTTP contracts, test coverage  
**Baseline:** V2-8 CLOSED / engine audit CLOSED / golden suite 99/99 / make verify PASS

> **This audit does not reopen V2-8, CTS-001, CTS-002, or the engine runtime contract audit.**  
> The calculation engine remains closed and stable. All findings in this document  
> concern exclusively the HTTP/API layer (routers, handlers, exception mapping, logging,  
> response contracts, and test coverage).

---

## Executive Summary

The global exception handlers (`exception_handlers.py`) are correctly implemented and do not expose internal details for uncaught exceptions. However, the **calculate endpoint has its own local catch-all** that overrides the global handler and **exposes raw `str(exc)` in the HTTP response** for unhandled exceptions — bypassing the sanitized global 500 response. The certified-mode handler has the same issue with `HTTPException(status_code=500, detail=str(exc))`.

Additional findings:
- `ParametrizationError` and `ValueError` error responses include `panel_context` and `datos_operativos` dicts in `details` — returning user-supplied business data (client names, city, service) in error payloads.
- `VisionIncompleteError` returns internal pipeline step names (`str(exc)`) in 500 responses.
- The certified handler uses `HTTPException` for errors, breaking the `ApiResponse` envelope contract.
- Two missing tests: no HTTP-level test for the calculate endpoint's own catch-all 500; no test for certified handler error response format.

**Highest-risk items require fixes before production deployment:**
1. Catch-all `str(exc)` in `calculate_normal_handler.py` response payload (HIGH)
2. `detail=str(exc)` in `calculate_certified_handler.py` HTTPException (HIGH)
3. `panel_context` / `datos_operativos` in `ParametrizationError` and `ValueError` response `details` (MEDIUM)

---

## Baseline

| Check | Result |
|-------|--------|
| golden suite | 99/99 PASS |
| make verify | ✅ Baseline match. Sin drift. |
| Active blockers | 0 |

---

## API Surface Map

| Component | File | Responsibility | Initial Risk |
|-----------|------|----------------|--------------|
| App factory | `app.py` | FastAPI creation, CORS, lifespan, middleware, exception handlers | LOW |
| API v1 router | `modules/api_v1/router.py` | Composition root — all subrouters | NONE |
| Calculate router | `modules/calculator/api/calculate_router.py` | `POST /simulation/calculate` | HIGH |
| Calculate normal handler | `modules/calculator/api/calculate_normal_handler.py` | Engine execution, persistence, error mapping | HIGH |
| Calculate certified handler | `modules/calculator/api/calculate_certified_handler.py` | Certified mode (baseline hash enforcement) | HIGH |
| Calculate DTO | `modules/calculator/api/calculate_dto.py` | Request parsing (`user_input` + auto-wrap) | LOW |
| Calculate deps | `modules/calculator/api/calculate_dependencies.py` | Singleton repos | LOW |
| Validate helper | `modules/calculator/api/calculate_validate.py` | Diagnostic (NOT exposed as HTTP endpoint) | LOW |
| Results router | `modules/calculator/api/results_router.py` | `GET /simulation/{id}/results`, `/traceability` | LOW |
| Global exception handlers | `modules/shared/infrastructure/exception_handlers.py` | `DomainError`, `NotFoundError`, `ValidationError`, `Exception` | LOW |
| Middleware | `modules/shared/middleware/middlewares.py` | Request logging, correlation_id | LOW |
| Request utils | `modules/shared/infrastructure/request_utils.py` | Header/query sanitization, correlation_id | LOW |
| App settings | `modules/shared/config/app_settings.py` | CORS, docs_enabled, production guards | LOW |
| Parametrization router | `modules/parametrizacion/api/router.py` | HR/GN/OP upload + versioning | UNKNOWN |
| Vision routers | `modules/vision_*/api/router.py` | Read-only vision endpoints | LOW |
| Audit router | `modules/audit/api/audit_router.py` | Audit trail queries | LOW |

---

## Error Handling and Status Code Risks

| Error | Current Behavior | Status Code | Risk | Recommendation |
|-------|-----------------|-------------|------|----------------|
| `ValidationError` (domain) | Global handler → generic `"Validación de entrada inválida."` | 422 | OK | None |
| `DomainError` | Global handler → generic `"Error en la lógica de negocio."` | 400 | OK | None |
| `NotFoundError` | Global handler → generic `"Recurso no encontrado."` | 404 | OK | None |
| `Exception` (global) | Global handler → generic `"Error inesperado en el servidor."` + correlation_id | 500 | OK | None |
| `ParametrizationError` (normal handler) | Local handler → `message=exc.message`, `details.panel_context=<panel dict>`, `details.datos_operativos=<ops dict>` | 422 | LEAKS_INTERNALS | Remove `panel_context` and `datos_operativos` from response `details`; keep in server log only |
| `ValueError` (normal handler) | Local handler → `message=str(exc)`, `details.panel_context=<panel dict>`, `details.type`, `details.module` | 422 | LEAKS_INTERNALS | Remove `panel_context`, `type`, `module` from response `details`; sanitize to generic input error message |
| `VisionIncompleteError` (normal handler) | Local handler → `message=str(exc)` which includes internal pipeline step names like `"pyg_por_mes vacío — PyGCalculator no ejecutó"`, `details.type`, `details.module` | 500 | LEAKS_INTERNALS | Replace with generic `"Error interno: resultado de cálculo incompleto"` in response; log detail server-side only |
| `AuditIntegrityError` (normal handler) | Local handler → `message=exc.message` | 500 | OK | `exc.message` is domain-controlled; acceptable if message content is reviewed |
| `DomainError` (normal handler) | Local handler → `message=exc.message`, `details.type`, `details.module` | 400 | LEAKS_INTERNALS | Remove `type` and `module` from response `details` |
| `Exception` catch-all (normal handler) | Local handler → `message=f"Error inesperado en el servidor: {str(exc)}"`, `details.exception_type`, `details.exception_module` | 500 | LEAKS_INTERNALS | **HIGH RISK.** Replace with `"Error inesperado en el servidor."` (generic). Remove `exception_type` and `exception_module` from response. Log `str(exc)` server-side only. This bypasses the sanitized global handler. |
| `PydanticValidationError` (normal handler) | Local handler → `details.errors=validation_errors` (field paths and Pydantic error codes), `details.payload_keys` | 422 | UNSTABLE_CONTRACT | Pydantic error format is internal implementation detail. Consider flattening to stable field+message format. `payload_keys` is low risk. |
| `(DomainError, ParametrizationError)` (certified handler) | `raise HTTPException(status_code=422, detail=str(exc))` | 422 | LEAKS_INTERNALS | **HIGH RISK.** `detail=str(exc)` exposes raw exception string. FastAPI returns `{"detail": <str>}` bypassing `ApiResponse` envelope. Fix: return `JSONResponse` with `ApiResponse` contract. |
| `Exception` (certified handler) | `raise HTTPException(status_code=500, detail=str(exc))` | 500 | LEAKS_INTERNALS | **HIGH RISK.** Same as above — `str(exc)` exposed in response, outside `ApiResponse` envelope. |
| `HTTPException` re-raise (normal handler) | Re-raised after logging (line 230-240) | varies | AMBIGUOUS | HTTPException caught and re-raised is correct pattern for FastAPI. But logs `body.user_input.keys()` at error level for every re-raise including valid auth redirects. |

### Status Code Consistency

| Scenario | Normal handler | Certified handler | Global handler |
|----------|---------------|-------------------|----------------|
| `ParametrizationError` | 422 | 422 (str exposed) | 400 (if not caught locally) |
| `DomainError` | 400 | 422 (str exposed) | 400 |
| Unexpected error | 500 (str exposed) | 500 (str exposed) | 500 (sanitized) |

The discrepancy means `ParametrizationError` returns **422 from the calculate endpoint** but **400 from all other endpoints** (global handler). This is intentional but undocumented.

---

## Logging and Sensitive Data Risks

| File | Log Behavior | Risk | Recommended Action |
|------|--------------|------|--------------------|
| `calculate_normal_handler.py:68` | `logger.info("[calculate] Payload keys: %s", list(body.user_input.keys()))` | OK | Key names only, not values. Acceptable. |
| `calculate_normal_handler.py:74-79` | `logger.debug(...)` payload structure at DEBUG level | OK | DEBUG level — not emitted in INFO production mode. |
| `calculate_normal_handler.py:86-102` | `logger.info(...)` client name, city, line, months, margin | OK | These are business context fields, appropriate for server-side tracing. Not secrets. |
| `calculate_normal_handler.py:237` | `logger.error("Payload keys: %s", ...)` on HTTPException | EXCESSIVE_LOG | ERROR level for every re-raised HTTPException is too aggressive. Should be WARNING. |
| `calculate_normal_handler.py:305` | `logger.error("Payload keys: %s", ...)` on ValueError | OK | Key names only. |
| `calculate_normal_handler.py:351-364` | `logger.error("Panel context: cliente=%r ciudad=%r ...")` on ParametrizationError | MISSING_CONTEXT | Logging client data is OK in ERROR logs; confirm PII policy allows client names in logs. |
| `calculate_normal_handler.py:453-461` | `logger.error("Stacktrace: %s", tb_str)` — full stack trace in logs | SAFE_WITH_EXC_INFO | Stack traces in server logs are correct. Not sent to client via global handler. But local catch-all also sends `str(exc)` to client (separate issue above). |
| `calculate_normal_handler.py:458-459` | `logger.error("Payload preview: %s", payload[:1000])` | SENSITIVE_PAYLOAD_LOG | **MEDIUM RISK.** First 1000 chars of `json.dumps(body.user_input)` written to error log. May contain client business data (prices, volumes, margins). Confirm log retention/access policies. Consider logging only `payload_keys` and `payload_size` at ERROR level. |
| `calculate_certified_handler.py:149-153` | `logger.exception(...)` + re-raise HTTPException | SAFE_WITH_EXC_INFO | Server log is fine. But `detail=str(exc)` is then in the HTTP response (separate issue). |
| `middlewares.py` | Logs method, path (sanitized), status_code, elapsed_ms, headers (sanitized) | OK | `_safe_headers` and `_safe_path` are correctly implemented. |
| `exception_handlers.py:26` | `str(exc)` logged at ERROR level | OK | Server log only. Response contains generic message. |
| `exception_handlers.py:64` | `str(exc)` in DomainError logs | OK | Server log only. |

---

## Request/Response Contract Risks

| Endpoint | Request Contract | Response Contract | Existing Tests | Risk |
|----------|-----------------|-------------------|----------------|------|
| `POST /api/v1/simulation/calculate` (normal) | `CalculationRequest { user_input: Dict }` with auto-wrap validator. Accepts both legacy (`panel_de_control`) and entry_data (`datos_operativos`) formats. | Success: `ApiResponse { success: true, data: { simulation_id, message, timestamp } }`. Errors: `ApiResponse { success: false, error: ErrorDetail }` but catch-all leaks `str(exc)` | `test_parametrization_error_422.py` covers ParametrizationError. No test for catch-all 500 at endpoint level. | UNSTABLE_ERROR_PAYLOAD |
| `POST /api/v1/simulation/calculate` (certified) | Same request. | Success: `ApiResponse { success: true, data: { simulation_id, certified: true, certificate, ... } }`. Errors: **raw FastAPI `{"detail": <str>}` envelope** — NOT `ApiResponse` | No HTTP error path tests for certified mode | UNSTABLE_ERROR_PAYLOAD |
| `GET /api/v1/simulation/{id}/results` | `simulation_id` path param | `ApiResponse` wrapping `VisionImprimibleApiResponseV1` | Typed contract test in `test_vision_imprimible_typed_contract.py` | OK |
| `GET /api/v1/simulation/{id}/traceability` | `simulation_id` path param | `ApiResponse.ok(FieldTraceabilityRegistry().build(data))` — structure depends on registry impl | Tested indirectly via audit endpoint tests | MISSING_TEST |
| `POST /api/v1/simulation/calculate` with invalid JSON | Pydantic 422 validation | `ApiResponse` with `PYDANTIC_VALIDATION_ERROR` + field-level details | None | MISSING_TEST |

### Key Contract Risk: Certified vs Normal Response Envelope

Normal handler errors use `JSONResponse(status_code=X, content=ApiResponse(...).model_dump())` — correct.  
Certified handler errors use `raise HTTPException(status_code=X, detail=str(exc))` — FastAPI formats as `{"detail": <str>}` — **breaks the `ApiResponse` contract**.

Clients that parse error responses from `/calculate` will encounter different structures depending on the `mode` parameter.

---

## API Test Coverage Gaps

| Case | Existing Test | Gap | Recommended Test |
|------|---------------|-----|------------------|
| Valid normal request → 201 + simulation_id | `test_parametrization_error_422.py::test_valid_request_still_works` | PARTIALLY_COVERED | Full response schema assertion (success, simulation_id format, timestamp) |
| ParametrizationError → 422 + ApiResponse envelope | `test_parametrization_error_422.py` | COVERED | — |
| DomainError in engine → 400 + ApiResponse envelope | None at HTTP level | MISSING | Monkeypatch engine to raise DomainError, assert HTTP 400 + ApiResponse contract |
| Catch-all unhandled error at endpoint → 500 response format | `test_sec_p0_1_production_hardening.py` tests GLOBAL handler only | MISSING | **HIGH.** Test that calculate endpoint's own catch-all does NOT expose `str(exc)` in response. Monkeypatch a dependency to raise an unexpected error (e.g. RuntimeError). Assert response message is generic. |
| ValueError (malformed input field) → 422 response format | None at HTTP level | MISSING | Monkeypatch loader to raise ValueError, assert 422 + response does not contain class path/module |
| VisionIncompleteError → 500 response format | None | MISSING | Monkeypatch `validate_visions_complete` to raise VisionIncompleteError, assert 500 + generic message (no pipeline step names) |
| Certified mode: DomainError → 422 response format | None | MISSING | Assert certified error returns `ApiResponse` envelope, not raw `{"detail": ...}` |
| Certified mode: unexpected error → 500 response format | None | MISSING | Assert certified error 500 does not expose `str(exc)` to client |
| Missing simulation_id → 404 response format | `test_audit_endpoint.py` covers audit 404 | PARTIALLY_COVERED | Add 404 test for `/results` endpoint |
| Production: calculate returns 5xx without stack trace | `test_sec_p0_1_production_hardening.py::test_500_response_does_not_expose_internal_details` covers /boom (global handler) | MISSING | Same test targeting `/api/v1/simulation/calculate` with injected failure |
| CORS preflight on calculate endpoint | None | MISSING | Low priority; covered implicitly by CORS tests on /health |
| Auto-wrap flat body (`user_input` key absent) | None | MISSING | Test that flat body is auto-wrapped without 422 |

---

## Top Recommended Fixes

| Priority | Area | Risk | Recommended Fix | Suggested Test | Notes |
|----------|------|------|-----------------|----------------|-------|
| **P1-HIGH** | `calculate_normal_handler.py:469` | LEAKS_INTERNALS | Replace `message=f"Error inesperado en el servidor: {str(exc)}"` with `"Error inesperado en el servidor."`. Remove `exception_type` and `exception_module` from `details` in the response payload. Keep full `str(exc)` and stack trace in server logs only. | `test_calculate_endpoint_catch_all_500_is_sanitized` | This bypasses the safe global handler. The global handler already does this correctly — the local catch-all should match it. |
| **P2-HIGH** | `calculate_certified_handler.py:150,153` | LEAKS_INTERNALS | Replace `raise HTTPException(status_code=422, detail=str(exc))` and `raise HTTPException(status_code=500, detail=str(exc))` with `return JSONResponse(status_code=X, content=ApiResponse(...).model_dump())` using generic messages. | `test_certified_error_response_is_api_response` | Fixes both the content leak and the broken envelope contract. |
| **P3-MEDIUM** | `calculate_normal_handler.py:366-381` | LEAKS_INTERNALS | Remove `panel_context` and `datos_operativos` from the `ParametrizationError` response `details`. These dicts include client name, city, service — business data in error responses. Log them server-side (already done). | `test_parametrization_error_response_has_no_panel_context` | The fields logged at ERROR level are sufficient for debugging. |
| **P4-MEDIUM** | `calculate_normal_handler.py:317-332` | LEAKS_INTERNALS | Remove `panel_context`, `type`, `module` from the `ValueError` response `details`. Replace `message=str(exc)` with a generic `"Error en datos de entrada."` or a safe truncated version. Internal error path and module are implementation details. | `test_value_error_response_no_internal_details` | `ValueError` messages can contain file paths, argument names, internal variable names. |
| **P5-MEDIUM** | `calculate_normal_handler.py:283-295` | LEAKS_INTERNALS | Replace `message=str(exc)` in `VisionIncompleteError` response with `"Error interno: resultado de cálculo incompleto."`. Remove `details.type` and `details.module`. The internal pipeline step names in `VisionIncompleteError` are not actionable for API consumers. | `test_vision_incomplete_response_message_is_generic` | Pipeline step names like `"PyGCalculator no ejecutó"` are operational details for developers, not API clients. |

**Also recommended (LOW / next phase):**

| Priority | Area | Recommended Fix |
|----------|------|----------------|
| P6-LOW | `calculate_normal_handler.py:458` | Reduce payload preview log to `payload_keys + payload_size` at WARNING level. Remove full JSON dump of user input from error logs. |
| P7-LOW | `calculate_normal_handler.py:237` | Change `logger.error` to `logger.warning` for HTTPException re-raise path. |
| P8-LOW | `modules/shared/infrastructure/exception_handlers.py` | Add explicit handler for `ParametrizationError` at global level that returns 422 (not 400 via DomainError fallback). Eliminates the status code discrepancy between calculate endpoint and all other endpoints. |
| P9-LOW | `calculate_dto.py` | Add `response_model=None` or explicit `response_model` to the `@router.post` decorator to make the OpenAPI schema explicit for error responses. |
| P10-LOW | Missing tests | Add test suite `tests/api/test_calculate_endpoint_error_contracts.py` covering P1-P5 scenarios. |

---

## What Not to Touch

The following are **explicitly out of scope** for any fix derived from this audit:

- **Engine calculation logic** — all formulas, calculators, and business rules in `modules/calculator_motor/`
- **V2-8, CTS-001, CTS-002** — all closed and stable
- **`request/request.json`** — canonical test fixture, frozen
- **`storage/parametrization/**`** — parametrization state, frozen
- **`tests/golden/fixtures/**`** — golden values, frozen
- **`storage/baselines/**`** — baseline snapshots, frozen
- **Excel files** — external source of truth, read-only
- **Engine parametrization provider** — data loading is correctly designed
- **Global exception handlers** — `exception_handlers.py` is correctly implemented; findings are in the local handlers only

---

## Appendix: Exception Handler Precedence

FastAPI exception handler lookup order (highest to lowest precedence):

1. **Endpoint-local try/except** — catches before exception propagates to global handlers
2. **`add_exception_handler(SpecificClass, handler)`** — most specific class wins
3. **`add_exception_handler(Exception, handler)`** — catch-all fallback

The `calculate_normal_handler` wraps the entire handler in `try/except`, meaning **all exceptions are handled locally** and never reach the global handlers. The global handlers in `exception_handlers.py` only apply to endpoints that do NOT have local try/except (e.g., the results router, audit router).

This means:
- `test_sec_p0_1_production_hardening.py::test_500_response_does_not_expose_internal_details` tests the global handler via `/boom`, but **does not cover the calculate endpoint's local catch-all**, which has a different (unsafe) behavior.
- The production hardening test has a false sense of coverage for the main calculate endpoint.
