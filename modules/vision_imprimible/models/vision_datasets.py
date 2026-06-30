"""
nexa_engine/domain/visions.py
==============================
FASE 5 — Dataclasses para datasets de visión completos.

Estos datasets complementan las visiones existentes (VisionImprimible, VisionPyG,
VisionTarifas, CostToServe) con información estructurada sobre:

  - Staffing: FTE, salarios y costos por perfil/rol
  - Pólizas: descomposición de pólizas activas por mes
  - Indexación: timeline de factores de ajuste salarial y tecnológico
  - Volumetría: FTE/volumen por canal y modalidad

El builder `VisionDatasetsBuilder` (en calculators/vision_datasets.py) construye
estos datasets a partir de `PricingRequest` + `PricingResult`. El motor los persiste
en `PricingResult.datasets_vision` para que los endpoints GET los sirvan directamente
sin recalcular.

NO importar desde engine.py (evitar importación circular).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from nexa_engine.modules.calculator_motor.formulas.graphics.models import GraficosResult


# ---------------------------------------------------------------------------
# Dataset Staffing — FTE y costos por perfil
# ---------------------------------------------------------------------------

@dataclass
class PerfilStaffingRow:
    """
    Fila de staffing para un perfil operativo de Cadena A.

    Incluye FTE, salarios base y cargados, y costos totales mensuales.
    Los roles de soporte se identifican con `es_soporte=True`.
    """
    nombre: str                        # Nombre del perfil (ej: "Gestor Bancamía")
    modalidad: str                     # "Inbound - Voz" | "Outbound - WhatsApp" | etc.
    canal: str                         # Canal operativo
    es_soporte: bool                   # True = rol de staff, no agente
    fte: float                         # FTE asignado
    salario_base: float                # Salario base mensual COP
    salario_cargado: float             # Salario cargado (con aportes y prestaciones)
    costo_total_mensual: float         # Costo nómina total del perfil (fte × salario_cargado)
    tipo_carga: str                    # EMPLEADO_ESTANDAR | APRENDIZ_SENA | etc.
    modelo_cobro: str                  # "Fijo FTE" | "Híbrido" | "Variable"


@dataclass
class DatasetStaffing:
    """
    Dataset completo de staffing del deal.

    Permite construir tablas de FTE, costos de nómina y estructura de perfiles
    sin necesidad de recalcular nada en el frontend.
    """
    filas: List[PerfilStaffingRow] = field(default_factory=list)

    @property
    def total_fte_agentes(self) -> float:
        return sum(f.fte for f in self.filas if not f.es_soporte)

    @property
    def total_fte_soporte(self) -> float:
        return sum(f.fte for f in self.filas if f.es_soporte)

    @property
    def total_fte(self) -> float:
        return sum(f.fte for f in self.filas)

    @property
    def costo_nomina_mensual_total(self) -> float:
        return sum(f.costo_total_mensual for f in self.filas)

    def as_dict(self) -> dict:
        return {
            "filas": [
                {
                    "nombre": f.nombre,
                    "modalidad": f.modalidad,
                    "canal": f.canal,
                    "es_soporte": f.es_soporte,
                    "fte": f.fte,
                    "salario_base": f.salario_base,
                    "salario_cargado": f.salario_cargado,
                    "costo_total_mensual": f.costo_total_mensual,
                    "tipo_carga": f.tipo_carga,
                    "modelo_cobro": f.modelo_cobro,
                }
                for f in self.filas
            ],
            "totales": {
                "fte_agentes": self.total_fte_agentes,
                "fte_soporte": self.total_fte_soporte,
                "fte_total": self.total_fte,
                "costo_nomina_mensual": self.costo_nomina_mensual_total,
            },
        }


# ---------------------------------------------------------------------------
# Dataset Pólizas — descomposición por póliza y mes
# ---------------------------------------------------------------------------

@dataclass
class PolizaActivaRow:
    """
    Fila de póliza activa con su contribución efectiva al costo.
    """
    nombre: str                       # Nombre de la póliza
    pct_poliza: float                 # Tasa bruta
    pct_atribuible: float             # Factor de atribución al deal
    tasa_efectiva: float              # pct_poliza × pct_atribuible
    aplica_cadena_a: bool
    aplica_cadena_b: bool
    aplica_cadena_c: bool
    aplica_extension: bool
    meses_extension: Optional[int]


@dataclass
class DatasetPolizasMensual:
    """
    Dataset de pólizas activas y su impacto mensual en el costo financiero.

    TASK 1: Incluye descomposición de costos por cadena.
      - costo_mensual_promedio: Costo total de pólizas (todas las cadenas)
      - costo_mensual_promedio_a: Costo solo de pólizas que aplican a Cadena A
      - costo_mensual_promedio_b: Costo solo de pólizas que aplican a Cadena B
      - costo_mensual_promedio_c: Costo solo de pólizas que aplican a Cadena C

    Esta distinción es crítica para trazabilidad contractual: permite auditar
    que una póliza para B no afecte el costo de A (y viceversa).
    """
    polizas_activas: List[PolizaActivaRow] = field(default_factory=list)
    tasa_total_efectiva: float = 0.0   # Σ tasa_efectiva de pólizas activas
    costo_mensual_promedio: float = 0.0  # Costo mensual promedio total
    costo_mensual_promedio_a: float = 0.0  # Costo promedio solo Cadena A
    costo_mensual_promedio_b: float = 0.0  # Costo promedio solo Cadena B
    costo_mensual_promedio_c: float = 0.0  # Costo promedio solo Cadena C

    def as_dict(self) -> dict:
        return {
            "polizas_activas": [
                {
                    "nombre": p.nombre,
                    "pct_poliza": p.pct_poliza,
                    "pct_atribuible": p.pct_atribuible,
                    "tasa_efectiva": p.tasa_efectiva,
                    "aplica_cadena_a": p.aplica_cadena_a,
                    "aplica_cadena_b": p.aplica_cadena_b,
                    "aplica_cadena_c": p.aplica_cadena_c,
                    "aplica_extension": p.aplica_extension,
                    "meses_extension": p.meses_extension,
                }
                for p in self.polizas_activas
            ],
            "tasa_total_efectiva": self.tasa_total_efectiva,
            "costo_mensual_promedio": self.costo_mensual_promedio,
            "costo_por_cadena": {
                "cadena_a": self.costo_mensual_promedio_a,
                "cadena_b": self.costo_mensual_promedio_b,
                "cadena_c": self.costo_mensual_promedio_c,
            },
        }


# ---------------------------------------------------------------------------
# Dataset Indexación — timeline de factores por componente y mes
# ---------------------------------------------------------------------------

@dataclass
class MesIndexacionRow:
    """Fila mensual de la timeline de indexación."""
    mes: int                          # 1-based
    anio_contrato: int                # Año de negocio (1, 2, 3...)
    factor_humano: float              # Factor acumulado componente humano
    factor_tecnologico: float         # Factor acumulado componente tecnológico
    aplica_ajuste: bool               # True si este mes hay reajuste salarial


@dataclass
class DatasetIndexacion:
    """
    Timeline completa de indexación para todos los meses del contrato.

    Permite al frontend mostrar el gráfico de evolución de factores salariales
    y tecnológicos sin recalcular la lógica de indexación.
    """
    componente_humano: str = ""        # "IPC" | "SMMLV" | "Fijo X%"
    componente_tecnologico: str = ""   # "IPC" | "Fijo X%"
    frecuencia: str = "Anual"
    mes_aplicacion: int = 1
    filas: List[MesIndexacionRow] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "componente_humano": self.componente_humano,
            "componente_tecnologico": self.componente_tecnologico,
            "frecuencia": self.frecuencia,
            "mes_aplicacion": self.mes_aplicacion,
            "filas": [
                {
                    "mes": f.mes,
                    "anio_contrato": f.anio_contrato,
                    "factor_humano": f.factor_humano,
                    "factor_tecnologico": f.factor_tecnologico,
                    "aplica_ajuste": f.aplica_ajuste,
                }
                for f in self.filas
            ],
        }


# ---------------------------------------------------------------------------
# Dataset Volumetría — FTE/volumen por canal y modalidad
# ---------------------------------------------------------------------------

@dataclass
class CanalVolumetriaRow:
    """
    Fila de volumetría por canal.

    Los campos se toman directamente del JSON de entrada — no hay asunciones
    sobre la naturaleza del canal.
    """
    nombre: str                       # Nombre del canal/perfil
    modalidad: str                    # Modalidad tal como esté en el JSON
    canal: str                        # Canal operativo (igual a nombre para B/C)
    cadena: str                       # "A" | "B" | "C"
    fte: float                        # FTE (Cadena A) o equivalente (B/C)
    volumen_mensual: float            # Transacciones/mes
    pct_automatizacion: float = 0.0   # % manejado por tecnología
    tarifa_unitaria: float = 0.0      # Tarifa por transacción (si aplica)


@dataclass
class DatasetVolumetriaPorCanal:
    """
    Dataset de volumetría consolidada por canal y cadena.

    Permite mostrar la distribución de FTE y volumen entre Cadena A (humano),
    Cadena B (tecnología) y Cadena C (integración) sin recalcular en el frontend.
    Todos los campos se toman directamente del JSON sin presunciones.
    """
    filas: List[CanalVolumetriaRow] = field(default_factory=list)

    @property
    def total_fte_cadena_a(self) -> float:
        return sum(f.fte for f in self.filas if f.cadena == "A" and not f.fte == 0)

    @property
    def volumen_total_mensual(self) -> float:
        return sum(f.volumen_mensual for f in self.filas)

    def as_dict(self) -> dict:
        return {
            "filas": [
                {
                    "nombre": f.nombre,
                    "modalidad": f.modalidad,
                    "canal": f.canal,
                    "cadena": f.cadena,
                    "fte": f.fte,
                    "volumen_mensual": f.volumen_mensual,
                    "pct_automatizacion": f.pct_automatizacion,
                    "tarifa_unitaria": f.tarifa_unitaria,
                }
                for f in self.filas
            ],
            "totales": {
                "fte_cadena_a": self.total_fte_cadena_a,
                "volumen_total_mensual": self.volumen_total_mensual,
            },
        }


# ---------------------------------------------------------------------------
# Contenedor principal de datasets de visión
# ---------------------------------------------------------------------------

@dataclass
class DatasetsVision:
    """
    Contenedor de todos los datasets de visión completos.

    Persistido en PricingResult y en SimulationSnapshot para que los endpoints
    GET sirvan cualquier visión sin recalcular.

    Todos los campos son Optional para garantizar backward compatibility:
    si el builder no los produce (ej. falta de datos), son None en lugar de error.
    """
    staffing: Optional[DatasetStaffing] = None
    polizas: Optional[DatasetPolizasMensual] = None
    indexacion: Optional[DatasetIndexacion] = None
    volumetria: Optional[DatasetVolumetriaPorCanal] = None
    graficos: "Optional[GraficosResult]" = None

    def as_dict(self) -> dict:
        return {
            "staffing":   self.staffing.as_dict() if self.staffing else None,
            "polizas":    self.polizas.as_dict() if self.polizas else None,
            "indexacion": self.indexacion.as_dict() if self.indexacion else None,
            "volumetria": self.volumetria.as_dict() if self.volumetria else None,
            "graficos":   self.graficos.as_dict() if self.graficos else None,
        }
