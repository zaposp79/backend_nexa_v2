"""
nexa_engine/domain/snapshot.py
================================
FASE 4 — SimulationSnapshot: Agregado auto-contenido de una simulación completa.

El SimulationSnapshot es el artefacto central de persistencia que permite:
  1. Reproducir exactamente cualquier simulación pasada
  2. Reconstruir cualquier visión sin recalcular
  3. Auditar el origen de cada valor (DataProvenance de FASE 3)
  4. Verificar qué parametrización estaba activa cuando se ejecutó
  5. Rastrear qué defaults se aplicaron (NormalizationLog de FASE 2)

Estructura:
  SimulationSnapshot
    ├── identity         — simulation_id, timestamp, versión del motor
    ├── input_chain      — raw_input → normalized_input → normalization_log
    ├── parametrization  — snapshot de la parametrización activa al momento del cálculo
    ├── data_provenance  — origen de cada campo en PricingRequest (FASE 3)
    ├── pricing_result   — resultado serializado completo (todas las visiones)
    └── panel_summary    — resumen rápido del deal para búsqueda/índice

Principios de diseño:
  - Auto-contenido: no requiere re-consultar storage/parametrization/ para reconstruir
  - Inmutable después de persistir: nunca se modifica el snapshot guardado
  - JSON-serializable: todos los campos son tipos Python básicos (dict, list, str, float, int, bool, None)
  - Determinista: dado el mismo SimulationSnapshot, cualquier recálculo produce idéntico resultado
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParametrizationSnapshot:
    """
    Snapshot de los valores de parametrización activos cuando se ejecutó la simulación.

    Captura los valores específicos que afectaron ESTE deal, no toda la parametrización.
    Permite verificar que una simulación histórica puede reproducirse exactamente
    cargando estos valores en lugar de la parametrización activa (que puede haber cambiado).
    """
    # Identidad de la parametrización capturada
    parametrization_id: str = ""        # ID o versión de la parametrización activa
    captured_at: str = ""               # Timestamp de captura (ISO 8601)

    # Valores HR relevantes para este deal
    smmlv: float = 0.0                  # SMMLV vigente en la parametrización activa
    auxilio_transporte: float = 0.0     # Auxilio de transporte vigente
    linea_negocio: str = ""             # Línea de negocio del deal
    pct_rotacion_linea: float = 0.0     # % rotación para la línea de negocio
    pct_ausentismo_linea: float = 0.0   # % ausentismo para la línea de negocio
    pct_examen_anual_linea: float = 0.0 # % examen anual para la línea de negocio

    # Valores OP relevantes para este deal
    ciudad: str = ""                    # Ciudad del deal
    tasa_ica_ciudad: float = 0.0        # Tasa ICA para la ciudad
    tasa_gmf: float = 0.0              # Tasa GMF activa
    tasa_mensual_financiacion: float = 0.0  # Tasa mensual de financiación

    # Factores de indexación relevantes (para los años del contrato)
    componente_humano: str = "IPC"
    componente_tecnologico: str = "IPC"
    factores_indexacion: Dict[str, float] = field(default_factory=dict)
    # {anio_str: factor} — ej. {"2026": 1.0, "2027": 1.111, ...}

    # Constantes operativas usadas
    constantes_operativas: Dict[str, Any] = field(default_factory=dict)
    # tarifa_dia_cap, opex_ti_por_estacion, etc.

    # Salarios por rol usados en este deal
    salarios_por_rol: Dict[str, float] = field(default_factory=dict)
    # {rol: salario_base} — solo los roles efectivamente usados

    def as_dict(self) -> Dict[str, Any]:
        """Serializa para persistencia en JSON."""
        return {
            "parametrization_id":      self.parametrization_id,
            "captured_at":             self.captured_at,
            "smmlv":                   self.smmlv,
            "auxilio_transporte":      self.auxilio_transporte,
            "linea_negocio":           self.linea_negocio,
            "pct_rotacion_linea":      self.pct_rotacion_linea,
            "pct_ausentismo_linea":    self.pct_ausentismo_linea,
            "pct_examen_anual_linea":  self.pct_examen_anual_linea,
            "ciudad":                  self.ciudad,
            "tasa_ica_ciudad":         self.tasa_ica_ciudad,
            "tasa_gmf":                self.tasa_gmf,
            "tasa_mensual_financiacion": self.tasa_mensual_financiacion,
            "componente_humano":       self.componente_humano,
            "componente_tecnologico":  self.componente_tecnologico,
            "factores_indexacion":     self.factores_indexacion,
            "constantes_operativas":   self.constantes_operativas,
            "salarios_por_rol":        self.salarios_por_rol,
        }


@dataclass
class PanelSummary:
    """
    Resumen rápido del deal para búsqueda, índices y dashboards.

    Permite listar/buscar simulaciones sin cargar el snapshot completo.
    """
    simulation_id: str
    cliente: str = ""
    tipo_cliente: str = ""
    linea_negocio: str = ""
    ciudad: str = ""
    fecha_inicio: str = ""
    meses_contrato: int = 0
    margen: float = 0.0
    total_fte: float = 0.0              # FTE total de agentes base
    created_at: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id":  self.simulation_id,
            "cliente":        self.cliente,
            "tipo_cliente":   self.tipo_cliente,
            "linea_negocio":  self.linea_negocio,
            "ciudad":         self.ciudad,
            "fecha_inicio":   self.fecha_inicio,
            "meses_contrato": self.meses_contrato,
            "margen":         self.margen,
            "total_fte":      self.total_fte,
            "created_at":     self.created_at,
        }


@dataclass
class SimulationSnapshot:
    """
    Snapshot auto-contenido de una simulación de pricing NEXA.

    Este es el artefacto de persistencia de primera clase para FASE 4.
    Contiene todo lo necesario para reproducir, auditar y reconstruir
    cualquier visión sin necesidad de recalcular ni consultar storage.

    Campos:
      simulation_id:        UUID único de la simulación
      created_at:           Timestamp ISO 8601 de creación
      nexa_engine_version:  Versión del motor al momento del cálculo

      raw_input:            JSON original del usuario (intacto, sin modificar)
      normalized_input:     JSON después de InputNormalizer (FASE 2)
      normalization_log:    Log de defaults aplicados y validaciones (FASE 2)

      parametrization:      Snapshot de la parametrización activa (FASE 4)
      data_provenance:      Origen de cada campo en PricingRequest (FASE 3)

      pricing_result:       Resultado serializado completo del motor
      panel_summary:        Resumen rápido para búsqueda/índice
    """
    simulation_id: str
    created_at: str

    # ── Input chain (FASE 2 trazabilidad) ──────────────────────────────
    raw_input: Dict[str, Any]               # Original user JSON — nunca modificado
    normalized_input: Dict[str, Any]        # Post-InputNormalizer (FASE 2)
    normalization_log: Dict[str, Any]       # NormalizationLog serializado

    # ── Parametrización congelada (FASE 4) ─────────────────────────────
    parametrization: ParametrizationSnapshot

    # ── Trazabilidad de datos (FASE 3) ──────────────────────────────────
    data_provenance: Dict[str, Any]         # DataProvenance.as_dict()

    # ── Resultado del motor ─────────────────────────────────────────────
    pricing_result: Dict[str, Any]          # pricing_result_to_dict() completo

    # ── Resumen para índice ─────────────────────────────────────────────
    panel_summary: PanelSummary

    # ── Metadata ────────────────────────────────────────────────────────
    nexa_engine_version: str = "1.0.0"

    def as_dict(self) -> Dict[str, Any]:
        """
        Serializa el snapshot completo para persistencia JSON.

        El dict resultante es auto-contenido: contiene toda la información
        necesaria para reproducir o auditar la simulación sin acceso externo.
        """
        return {
            "simulation_id":        self.simulation_id,
            "created_at":           self.created_at,
            "nexa_engine_version":  self.nexa_engine_version,
            "raw_input":            self.raw_input,
            "normalized_input":     self.normalized_input,
            "normalization_log":    self.normalization_log,
            "parametrization":      self.parametrization.as_dict(),
            "data_provenance":      self.data_provenance,
            "pricing_result":       self.pricing_result,
            "panel_summary":        self.panel_summary.as_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimulationSnapshot":
        """Reconstruye un SimulationSnapshot desde un dict JSON persistido.

        H-03 FIX: Validates critical parametrization fields are present.
        Prevents corrupted snapshots from silently deserializing with zeros.
        """
        param_dict = d.get("parametrization", {})
        summary_dict = d.get("panel_summary", {})

        # H-03: Validate critical parametrization fields exist and are non-zero
        critical_fields = ["smmlv", "auxilio_transporte", "linea_negocio"]
        for field in critical_fields:
            if field not in param_dict:
                raise ValueError(f"Snapshot integrity error: parametrization.{field} is required")
            if field in ["smmlv", "auxilio_transporte"] and float(param_dict.get(field, 0)) <= 0:
                raise ValueError(f"Snapshot integrity error: parametrization.{field} must be positive")

        param = ParametrizationSnapshot(
            parametrization_id      = param_dict.get("parametrization_id", ""),
            captured_at             = param_dict.get("captured_at", ""),
            smmlv                   = float(param_dict.get("smmlv", 0.0)),
            auxilio_transporte      = float(param_dict.get("auxilio_transporte", 0.0)),
            linea_negocio           = param_dict.get("linea_negocio", ""),
            pct_rotacion_linea      = float(param_dict.get("pct_rotacion_linea", 0.0)),
            pct_ausentismo_linea    = float(param_dict.get("pct_ausentismo_linea", 0.0)),
            pct_examen_anual_linea  = float(param_dict.get("pct_examen_anual_linea", 0.0)),
            ciudad                  = param_dict.get("ciudad", ""),
            tasa_ica_ciudad         = float(param_dict.get("tasa_ica_ciudad", 0.0)),
            tasa_gmf                = float(param_dict.get("tasa_gmf", 0.0)),
            tasa_mensual_financiacion = float(param_dict.get("tasa_mensual_financiacion", 0.0)),
            componente_humano       = param_dict.get("componente_humano", "IPC"),
            componente_tecnologico  = param_dict.get("componente_tecnologico", "IPC"),
            factores_indexacion     = param_dict.get("factores_indexacion", {}),
            constantes_operativas   = param_dict.get("constantes_operativas", {}),
            salarios_por_rol        = param_dict.get("salarios_por_rol", {}),
        )

        summary = PanelSummary(
            simulation_id  = summary_dict.get("simulation_id", d.get("simulation_id", "")),
            cliente        = summary_dict.get("cliente", ""),
            tipo_cliente   = summary_dict.get("tipo_cliente", ""),
            linea_negocio  = summary_dict.get("linea_negocio", ""),
            ciudad         = summary_dict.get("ciudad", ""),
            fecha_inicio   = summary_dict.get("fecha_inicio", ""),
            meses_contrato = int(summary_dict.get("meses_contrato", 0)),
            margen         = float(summary_dict.get("margen", 0.0)),
            total_fte      = float(summary_dict.get("total_fte", 0.0)),
            created_at     = summary_dict.get("created_at", ""),
        )

        return cls(
            simulation_id        = d["simulation_id"],
            created_at           = d.get("created_at", ""),
            nexa_engine_version  = d.get("nexa_engine_version", "1.0.0"),
            raw_input            = d.get("raw_input", {}),
            normalized_input     = d.get("normalized_input", {}),
            normalization_log    = d.get("normalization_log", {}),
            parametrization      = param,
            data_provenance      = d.get("data_provenance", {}),
            pricing_result       = d.get("pricing_result", {}),
            panel_summary        = summary,
        )
