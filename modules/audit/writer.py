"""
Escritor de traceabilidad completa por simulación.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from nexa_engine.modules.shared.exceptions import AuditIntegrityError
from nexa_engine.modules.shared.models import (
    PolizaContractual,
    PricingRequest,
    PricingResult,
)

if TYPE_CHECKING:
    from nexa_engine.modules.calculator.persistence.traceability_repository import TraceabilityRepository

logger = logging.getLogger("nexa.traceability")


class TraceabilityWriter:
    """Escribe la estructura de traceabilidad completa de una simulación."""

    def __init__(self, repository: Optional[TraceabilityRepository] = None) -> None:
        self._repo = repository

    def write(
        self,
        simulation_id: str,
        raw_request: Dict[str, Any],
        solicitud: PricingRequest,
        resultado: PricingResult,
        escenarios_aplicados: Optional[List[Dict]] = None,
        polizas_usuario: Optional[List[PolizaContractual]] = None,
    ) -> None:
        if self._repo is None:
            raise AuditIntegrityError(
                "TraceabilityWriter requiere repository inyectado en __init__"
            )

        try:
            data: Dict[str, Any] = {
                "request": self._sanitize_raw_request(raw_request),
                "visions": self._build_visions(resultado),
                "audit": self._build_audit(solicitud, escenarios_aplicados, polizas_usuario),
            }
            self._repo.save(simulation_id, data)
            logger.info("[TRACEABILITY] Saved %s", simulation_id)
        except AuditIntegrityError:
            raise
        except Exception as exc:
            raise AuditIntegrityError(
                f"No se pudo persistir la trazabilidad obligatoria de la simulación {simulation_id}: {exc}"
            ) from exc

    @staticmethod
    def _sanitize_raw_request(raw_request: Dict[str, Any]) -> Dict[str, Any]:
        """Return a safe trace summary without client business payload.

        Stores structural/versioning metadata only. Full sections that contain
        client-identifying business data are replaced with shape metadata (key
        names and counts) so forensic traceability is preserved without
        persisting sensitive operational data.

        Does not mutate the original dict.
        """
        if not isinstance(raw_request, dict):
            return {"_sanitized": True, "_type": type(raw_request).__name__}

        # Sections that carry client/business-sensitive data — omit values, keep shape.
        _OMIT_SECTIONS = {
            "panel_de_control",
            "condiciones_cadena_a",
            "condiciones_cadena_b",
            "condiciones_cadena_c",
            "datos_operativos",
            "escenarios_comerciales",
            "user_input",
        }
        # Scalar/versioning fields safe to retain verbatim.
        _SAFE_SCALAR_KEYS = {"metadata", "parametrization_version"}

        result: Dict[str, Any] = {
            "_sanitized": True,
            "top_level_keys": sorted(raw_request.keys()),
        }

        for key in _SAFE_SCALAR_KEYS:
            if key in raw_request:
                result[key] = raw_request[key]

        for section in _OMIT_SECTIONS:
            if section in raw_request:
                value = raw_request[section]
                if isinstance(value, dict):
                    result[f"{section}_keys"] = sorted(value.keys())
                elif isinstance(value, list):
                    result[f"{section}_count"] = len(value)

        return result

    def _build_visions(self, resultado: PricingResult) -> Dict[str, Any]:
        return {
            "vision_pyg": self._vision_pyg_to_dict(resultado.vision_pyg) if resultado.vision_pyg else None,
            "vision_tarifas": asdict(resultado.vision_tarifas) if resultado.vision_tarifas else None,
            "cost_to_serve": asdict(resultado.cost_to_serve) if resultado.cost_to_serve else None,
            "vision_imprimible": {
                "kpis": asdict(resultado.kpis),
                "pyg_por_mes": [self._pyg_mes_to_dict(mes) for mes in resultado.pyg_por_mes],
                "waterfall_promedio": asdict(resultado.waterfall) if resultado.waterfall else None,
                "reglas_negocio": [asdict(regla) for regla in resultado.reglas_negocio],
                "evaluacion_riesgo": asdict(resultado.evaluacion_riesgo) if resultado.evaluacion_riesgo else None,
                "cost_to_serve": asdict(resultado.cost_to_serve) if resultado.cost_to_serve else None,
                "vision_tarifas": asdict(resultado.vision_tarifas) if resultado.vision_tarifas else None,
                "vision_pyg": self._vision_pyg_to_dict(resultado.vision_pyg) if resultado.vision_pyg else None,
            },
        }

    def _build_audit(
        self,
        solicitud: PricingRequest,
        escenarios_aplicados: Optional[List[Dict]],
        polizas_usuario: Optional[List[PolizaContractual]],
    ) -> Dict[str, Any]:
        if polizas_usuario is None:
            polizas_data = {
                "fuente": "storage",
                "nota": "No se proveyeron polizas en el payload — se usó storage/parametrization/op/",
            }
        else:
            activas = [poliza for poliza in polizas_usuario if poliza.activa]
            tasa_efectiva = sum(poliza.tasa_efectiva for poliza in activas)
            polizas_data = {
                "fuente": "usuario",
                "tasa_efectiva_total": tasa_efectiva,
                "polizas_activas": [
                    {
                        "nombre": poliza.nombre,
                        "pct_poliza": poliza.pct_poliza,
                        "pct_atribuible": poliza.pct_atribuible,
                        "tasa_efectiva": poliza.tasa_efectiva,
                    }
                    for poliza in activas
                ],
            }
            if len(polizas_usuario) == 0:
                polizas_data["nota"] = "Lista vacía: contrato indicó cero pólizas"

        escenarios_data = (
            {
                "fuente": "escenarios_comerciales",
                "total": len(escenarios_aplicados),
                "escenarios": escenarios_aplicados,
            }
            if escenarios_aplicados
            else {
                "fuente": "defaults",
                "nota": "No se proveyeron escenarios_comerciales — modelo_cobro='Fijo FTE' para todos los perfiles",
            }
        )

        panel = solicitud.panel
        panel_summary = {
            "cliente": panel.cliente,
            "tipo_cliente": panel.tipo_cliente,
            "linea_negocio": panel.linea_negocio,
            "ciudad": panel.ciudad,
            "sede": panel.sede,
            "fecha_inicio": panel.fecha_inicio,
            "meses_contrato": panel.meses_contrato,
            "margen": panel.margen,
            "op_cont": panel.op_cont,
            "com_cont": panel.com_cont,
            "markup": panel.markup,
            "tasa_ica": panel.tasa_ica,
            "tasa_gmf": panel.tasa_gmf,
            "tasa_mensual_financ": panel.tasa_mensual_financ,
            "activa_financiacion": panel.activa_financiacion,
            "total_perfiles_cadena_a": len(solicitud.perfiles_cadena_a),
            "perfiles_base": sum(1 for perfil in solicitud.perfiles_cadena_a if not perfil.es_soporte),
            "perfiles_soporte": sum(1 for perfil in solicitud.perfiles_cadena_a if perfil.es_soporte),
            "total_canales_cadena_b": len(solicitud.cadena_b.canales),
            "total_canales_cadena_c": len(solicitud.cadena_c.canales),
            "polizas_usuario_count": len(polizas_usuario) if polizas_usuario is not None else 0,
        }

        return {
            "polizas_source": polizas_data,
            "escenarios_aplicados": escenarios_data,
            "panel_summary": panel_summary,
        }

    @staticmethod
    def _vision_pyg_to_dict(vision_pyg) -> Dict:
        return asdict(vision_pyg)

    @staticmethod
    def _pyg_mes_to_dict(mes) -> Dict:
        data = asdict(mes)
        data["ingreso_bruto"] = mes.ingreso_bruto
        data["ingreso_neto"] = mes.ingreso_neto
        data["costo_a"] = mes.costo_a
        data["costos_financieros"] = mes.costos_financieros
        data["costo_total"] = mes.costo_total
        data["contribucion"] = mes.contribucion
        data["pct_contribucion"] = mes.pct_contribucion
        data["utilidad_neta"] = mes.utilidad_neta
        data["pct_utilidad_neta"] = mes.pct_utilidad_neta
        return data
