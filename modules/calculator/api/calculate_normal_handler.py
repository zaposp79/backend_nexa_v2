"""Normal-mode handler for POST /api/v1/simulation/calculate.

Runs the NEXA pricing engine end-to-end and persists results, traceability
and the simulation snapshot. Extracted verbatim from calculate_router.py
(FASE Y Batch 4b) — behaviour unchanged.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.serializers import (
    VisionIncompleteError,
    pricing_result_to_dict,
    validate_visions_complete,
)
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.shared.exceptions import (
    AuditIntegrityError,
    DomainError,
    ParametrizationError,
)
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator

from nexa_engine.modules.calculator.api.calculate_dto import CalculationRequest
from nexa_engine.modules.calculator.api.calculate_dependencies import (
    _results_repo,
    _trace_writer,
    _snapshot_repo,
    _lineage_repo,
    _version_registry,
)

logger = logging.getLogger("nexa.calculate")


def _calculate_normal(body: CalculationRequest):
    """
    Ejecuta el motor de precios NEXA y persiste el resultado.

    Flujo: UserInputLoader → SimulationContextBuilder → NexaPricingEngine →
    validación de visiones → persistencia (resultado + traceabilidad +
    SimulationSnapshot) → devuelve ``simulation_id``.

    ``user_input`` admite formato legacy (panel_de_control + condiciones_*)
    o entry_data (datos_operativos + reglas_negocio + volumetria); ver el
    contrato api_v1 para el detalle de campos y ejemplos.

    Errores: 422 (input/parametrización inválidos), 400 (DomainError),
    500 (VISION_INCOMPLETE / AuditIntegrityError / error inesperado).
    """
    try:
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 1: Log de entrada — trazabilidad completa del payload
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("=" * 80)
        logger.info("[calculate] ▶ INICIO DE CÁLCULO")
        logger.info("[calculate] Timestamp: %s", datetime.now(timezone.utc).isoformat())
        logger.info("[calculate] Payload keys: %s", list(body.user_input.keys()))

        # Log seguro del payload (resumido, sin datos sensibles completos)
        try:
            payload_keys = list(body.user_input.keys()) if isinstance(body.user_input, dict) else []
            payload_size = len(json.dumps(body.user_input)) if body.user_input else 0
            logger.debug(
                "[calculate] Payload estructura: keys=%s, tamaño=%d bytes, top_level_count=%d",
                payload_keys,
                payload_size,
                len(payload_keys),
            )
        except Exception as json_serialization_error:
            logger.warning("[calculate] No se pudo analizar estructura del payload: %s", json_serialization_error)

        # Log contextual del panel (si existe)
        if "panel_de_control" in body.user_input:
            panel = body.user_input["panel_de_control"]
            logger.info(
                "[calculate] Panel: cliente=%r ciudad=%r linea=%r meses=%r margen=%r",
                panel.get("cliente"),
                panel.get("ciudad"),
                panel.get("linea_negocio"),
                panel.get("meses_contrato"),
                panel.get("margen")
            )
        elif "datos_operativos" in body.user_input:
            operational_data_dict = body.user_input["datos_operativos"]
            logger.info(
                "[calculate] Datos operativos: cliente=%r ciudad=%r servicio=%r duracion=%r",
                operational_data_dict.get("cliente"),
                operational_data_dict.get("ciudad"),
                operational_data_dict.get("servicio"),
                operational_data_dict.get("duracion_meses")
            )

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 2: Validación de contrato (si aplica)
        # ═══════════════════════════════════════════════════════════════════════
        if "datos_operativos" in body.user_input:
            logger.info("[calculate] → Validando contrato entry_data")
            ContractValidator().raise_if_invalid(body.user_input)
            logger.info("[calculate] ✓ Contrato entry_data válido")

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: Carga de user_input
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Cargando user_input")
        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(body.user_input)
        logger.info("[calculate] ✓ UserInput cargado correctamente")

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 4: Construcción de PricingRequest (parametrización activa)
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Construyendo PricingRequest desde parametrización")
        builder   = SimulationContextBuilder()
        solicitud = builder.construir(user_input)
        logger.info("[calculate] ✓ PricingRequest construido correctamente")

        # Trazabilidad de parametrización cargada
        if hasattr(builder, 'last_parametrization_snapshot') and builder.last_parametrization_snapshot:
            snapshot = builder.last_parametrization_snapshot
            logger.info("[calculate] Parametrización cargada:")
            for module, data in snapshot.items():
                if isinstance(data, dict) and 'version_id' in data:
                    logger.info("  - %s: version=%s", module, data.get('version_id'))

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 5: Ejecución del motor (10 capas de cálculo)
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Ejecutando motor de precios")
        engine    = NexaPricingEngine(lineage_repository=_lineage_repo, version_registry=_version_registry)
        resultado = engine.calcular(solicitud)
        logger.info("[calculate] ✓ Motor ejecutado correctamente")

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 6: Validación de completitud de visiones
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Validando completitud de visiones")
        validate_visions_complete(resultado)
        logger.info("[calculate] ✓ Todas las visiones completas")

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 7: Persistencia de resultados
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Persistiendo resultados")
        # WAVE 14 — honour any explicit simulation_id the engine attached
        # to the result (e.g. when with_lineage=True or the request
        # carried metadata.simulation_id). Falls back to a fresh UUID.
        simulation_id = getattr(resultado, "simulation_id", None) or _results_repo.new_id()
        full_dict     = pricing_result_to_dict(resultado, simulation_id)

        # client_id = partition key del container 'simulation' en Cosmos.
        client_id = (
            body.user_input.get("datos_operativos", {}).get("cliente")
            or body.user_input.get("panel_de_control", {}).get("cliente")
            or ""
        )
        full_dict["client_id"] = client_id

        # Campos de auditoría/lineage que no consumen las visiones y que
        # hacen el documento demasiado grande para el límite de 2 MB de Cosmos.
        # El SimulationSnapshot (JSON local, PHASE 9) ya preserva estos datos.
        _COSMOS_EXCLUDED = {"audit_trace", "datasets_vision", "panel"}
        cosmos_dict = {k: v for k, v in full_dict.items() if k not in _COSMOS_EXCLUDED}
        cosmos_dict["type"] = "results"

        _results_repo.save(cosmos_dict)
        logger.info("[calculate] ✓ Resultados guardados: %s (client_id=%r)", simulation_id, client_id)

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 8: Persistencia de traceabilidad (FASE G)
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Persistiendo traceabilidad (FASE G)")
        raw_escenarios = body.user_input.get("escenarios_comerciales", [])
        _trace_writer.write(
            simulation_id       = simulation_id,
            raw_request         = body.user_input,
            solicitud           = solicitud,
            resultado           = resultado,
            escenarios_aplicados= raw_escenarios if raw_escenarios else None,
            polizas_usuario     = solicitud.polizas_usuario,
        )
        logger.info("[calculate] ✓ Traceabilidad guardada")

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 9: Persistencia de SimulationSnapshot (FASE 4)
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] → Persistiendo SimulationSnapshot (FASE 4)")
        try:
            from nexa_engine.modules.calculator_motor.serializers import build_simulation_snapshot
            panel = solicitud.panel
            total_fte = sum(p.fte for p in solicitud.perfiles_cadena_a if not p.es_soporte)
            _snapshot = build_simulation_snapshot(
                simulation_id             = simulation_id,
                raw_input                 = loader.last_raw_input or body.user_input,
                normalized_input          = loader.last_normalized_input or {},
                normalization_log         = loader.last_normalization_log or {},
                parametrization_snapshot  = builder.last_parametrization_snapshot or {},
                data_provenance           = builder.last_provenance.as_dict() if builder.last_provenance else {},
                pricing_result_dict       = full_dict,
                panel_summary_data        = {
                    "cliente":        panel.cliente,
                    "tipo_cliente":   panel.tipo_cliente,
                    "linea_negocio":  panel.linea_negocio,
                    "ciudad":         panel.ciudad,
                    "fecha_inicio":   panel.fecha_inicio,
                    "meses_contrato": panel.meses_contrato,
                    "margen":         panel.margen,
                    "total_fte":      total_fte,
                },
            )
            _snapshot_repo.save(_snapshot)
            logger.info("[calculate] ✓ SimulationSnapshot guardado: %s", simulation_id)
        except Exception as _snap_exc:
            logger.exception("[calculate] ✗ Error al persistir SimulationSnapshot")
            raise AuditIntegrityError(
                f"SimulationSnapshot obligatorio no pudo persistirse: {_snap_exc}"
            ) from _snap_exc

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 10: Respuesta exitosa
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[calculate] ✓ CÁLCULO COMPLETADO EXITOSAMENTE")
        logger.info("[calculate] simulation_id: %s", simulation_id)
        logger.info("=" * 80)

        return ApiResponse.ok({
            "simulation_id": simulation_id,
            "message":       "Cálculos guardados correctamente",
            "timestamp":     datetime.now(timezone.utc).isoformat(),
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # EXCEPTION HANDLERS — Captura robusto con trazabilidad completa
    # ═══════════════════════════════════════════════════════════════════════════

    except HTTPException as exc:
        """Captura HTTPException de FastAPI (incluye 400, 422, etc.)"""
        logger.exception("[calculate] ✗ HTTPException capturada")
        logger.error("[calculate] status_code: %d", exc.status_code)
        logger.error("[calculate] detail: %s", exc.detail)
        logger.error("[calculate] exception_type: %s", type(exc).__name__)
        logger.error("[calculate] exception_module: %s", type(exc).__module__)
        logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))

        # Re-raise para que FastAPI lo maneje naturalmente
        raise

    except PydanticValidationError as exc:
        """Captura errores de validación de Pydantic"""
        logger.exception("[calculate] ✗ Pydantic ValidationError capturada")
        logger.error("[calculate] exception_type: %s", type(exc).__name__)
        logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))

        # Serializar errores de Pydantic para obtener detalle de campo
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
                    type="VALIDATION_ERROR",
                    message=f"Error de validación en el payload: {len(validation_errors)} error(es)",
                    details={
                        "errors": validation_errors,
                        "payload_keys": list(body.user_input.keys()),
                    }
                ),
            ).model_dump(),
        )

    except VisionIncompleteError as exc:
        """Captura errores de visión incompleta (rotura en cadena de cálculo)"""
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
                    type="INTERNAL_SERVER_ERROR",
                    message="Error interno: resultado de cálculo incompleto.",
                ),
            ).model_dump(),
        )

    except ValueError as exc:
        """Captura errores de validación de entrada (ValueError genérico)"""
        logger.exception("[calculate] ✗ ValueError capturado (input inválido)")
        logger.error("[calculate] status_code: 422")
        logger.error("[calculate] detail: %s", str(exc))
        logger.error("[calculate] exception_type: %s", type(exc).__name__)
        logger.error("[calculate] exception_module: %s", type(exc).__module__)
        logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))

        # Log contextual del panel (si existe)
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
                    type="VALIDATION_ERROR",
                    message="Error en datos de entrada.",
                    details={
                        "payload_keys": list(body.user_input.keys()),
                    }
                ),
            ).model_dump(),
        )

    except ParametrizationError as exc:
        """Captura errores de parametrización activa incompleta o inválida"""
        logger.exception("[calculate] ✗ ParametrizationError capturado")
        logger.error("[calculate] status_code: 422")
        logger.error("[calculate] detail: %s", exc.message)
        logger.error("[calculate] exception_type: %s", type(exc).__name__)
        logger.error("[calculate] exception_module: %s", type(exc).__module__)

        # Contexto de parametrización
        if hasattr(exc, 'module') and exc.module:
            logger.error("[calculate] parametrization_module: %s", exc.module)
        if hasattr(exc, 'version_id') and exc.version_id:
            logger.error("[calculate] parametrization_version: %s", exc.version_id)

        # Contexto del payload
        panel = body.user_input.get("panel_de_control", {})
        if panel:
            logger.error(
                "[calculate] Panel context: cliente=%r ciudad=%r linea=%r",
                panel.get("cliente"),
                panel.get("ciudad"),
                panel.get("linea_negocio")
            )

        datos = body.user_input.get("datos_operativos", {})
        if datos:
            logger.error(
                "[calculate] Datos operativos: ciudad=%r servicio=%r",
                datos.get("ciudad"),
                datos.get("servicio")
            )

        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="PARAMETRIZATION_ERROR",
                    type="PARAMETRIZATION_ERROR",
                    message=exc.message,
                    details={
                        "module": getattr(exc, 'module', None),
                        "version_id": getattr(exc, 'version_id', None),
                    }
                ),
            ).model_dump(),
        )

    except AuditIntegrityError as exc:
        """Captura errores de integridad de auditoría (snapshot/traceabilidad)"""
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
                    type="INTERNAL_SERVER_ERROR",
                    message="Error de integridad de auditoría.",
                ),
            ).model_dump(),
        )

    except DomainError as exc:
        """Captura errores de dominio (lógica de negocio)"""
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
                    type="DOMAIN_ERROR",
                    message=exc.message,
                    details=extra_details if extra_details else None,
                ),
            ).model_dump(),
        )

    except Exception as exc:
        """Captura catch-all para cualquier excepción no manejada"""
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

        logger.error("[calculate] Payload keys: %s", list(body.user_input.keys()))
        logger.error("[calculate] Payload size (bytes): %d", len(json.dumps(body.user_input, default=str)))

        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    type="INTERNAL_SERVER_ERROR",
                    message="Error inesperado en el servidor.",
                    details={
                        "payload_keys": list(body.user_input.keys()),
                    }
                ),
            ).model_dump(),
        )


__all__ = ["_calculate_normal"]
