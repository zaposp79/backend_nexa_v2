"""
nexa_engine/calculators/vision_datasets.py
==========================================
FASE 5 — Builder de datasets de visión completos.

Responsabilidad
---------------
Construir `DatasetsVision` a partir de `PricingRequest` + `PricingResult`.
NO recalcula nada del motor — consume los datos ya calculados.

Los datasets se persistirán en `PricingResult.datasets_vision` para que los
endpoints GET los sirvan directamente sin recalcular.

NOTA: Los tipos de canales (Cadena B, Cadena C) se determinan completamente
desde el JSON de entrada (`condiciones_cadena_b`, `condiciones_cadena_c`).
No se hacen asunciones sobre la naturaleza de los canales — cada uno aporta
sus campos (`nombre`, `modalidad`, `volumen_mensual`, etc.) tal como están
configurados en el usuario.

Principios:
  - Pure function style: sin estado, sin side effects
  - Fail-safe: cada sub-builder atrapa sus excepciones → dataset = None si falla
  - Backward compatible: PricingResult existente sin datasets_vision sigue siendo válido

NO importar desde engine.py (evitar importación circular).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from nexa_engine.modules.calculator_motor.formulas.graphics.models import GraficosResult
from nexa_engine.modules.shared.models import (
    PerfilCadenaA,
    PricingRequest,
    PricingResult,
)

if TYPE_CHECKING:
    from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.vision_imprimible.models.vision_datasets import (
    CanalVolumetriaRow,
    DatasetIndexacion,
    DatasetPolizasMensual,
    DatasetStaffing,
    DatasetVolumetriaPorCanal,
    DatasetsVision,
    MesIndexacionRow,
    PerfilStaffingRow,
    PolizaActivaRow,
)

logger = logging.getLogger("nexa.vision_datasets")


class VisionDatasetsBuilder:
    """
    Construye el contenedor `DatasetsVision` desde los artefactos del pipeline.

    Uso:
        builder = VisionDatasetsBuilder(parametrizacion=provider)
        datasets = builder.construir(solicitud, resultado)
    """

    def __init__(
        self,
        parametrizacion: "Optional[IParametrizationProvider]" = None,
    ) -> None:
        self._parametrizacion = parametrizacion

    def construir(
        self,
        solicitud: PricingRequest,
        resultado: PricingResult,
    ) -> DatasetsVision:
        """
        Construye todos los datasets de visión.

        Cada dataset se construye de forma independiente (fail-safe):
        si uno falla, los demás siguen construyéndose.
        """
        staffing   = self._build_staffing(solicitud)
        polizas    = self._build_polizas(solicitud, resultado)
        indexacion = self._build_indexacion(solicitud)
        volumetria = self._build_volumetria(solicitud)
        graficos   = self._build_graficos(solicitud, resultado)

        return DatasetsVision(
            staffing   = staffing,
            polizas    = polizas,
            indexacion = indexacion,
            volumetria = volumetria,
            graficos   = graficos,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Sub-builders
    # ──────────────────────────────────────────────────────────────────────

    def _build_staffing(self, solicitud: PricingRequest) -> Optional[DatasetStaffing]:
        """
        Construye tabla de staffing desde los perfiles de Cadena A.

        Cada perfil aporta una fila con FTE, salarios y costo mensual.
        """
        try:
            filas: List[PerfilStaffingRow] = []
            for perfil in solicitud.perfiles_cadena_a:
                salario_base    = perfil.salario_base
                salario_cargado = perfil.salario_cargado if perfil.salario_cargado > 0 else salario_base
                costo_mensual   = salario_cargado * perfil.fte

                filas.append(PerfilStaffingRow(
                    nombre             = perfil.nombre,
                    modalidad          = perfil.modalidad,
                    canal              = perfil.canal,
                    es_soporte         = perfil.es_soporte,
                    fte                = perfil.fte,
                    salario_base       = salario_base,
                    salario_cargado    = salario_cargado,
                    costo_total_mensual= costo_mensual,
                    tipo_carga         = getattr(perfil, "tipo_carga", "EMPLEADO_ESTANDAR"),
                    modelo_cobro       = getattr(perfil, "modelo_cobro", "Fijo FTE"),
                ))

            return DatasetStaffing(filas=filas)

        except Exception as exc:
            logger.warning("[vision_datasets] staffing build failed (non-fatal): %s", exc)
            return None

    def _build_polizas(
        self,
        solicitud: PricingRequest,
        resultado: PricingResult,
    ) -> Optional[DatasetPolizasMensual]:
        """
        Construye el dataset de pólizas activas.

        Regla contractual (TASK 2):
          - None  → usuario NOT configuró pólizas; motor usó parametrización defaults
          - []    → usuario EXPLÍCITAMENTE pidió CERO pólizas; no hay costos de pólizas
          - [...]  → usuario EXPLÍCITAMENTE pidió estas pólizas; úsalas

        Esto es crítico para trazabilidad financiera: no podemos confundir
        "el usuario no eligió" (None) con "el usuario eligió vacío" ([]).
        """
        try:
            # TASK 2: Si es None, NO incluimos pólizas en el dataset.
            # Si es [], incluimos dataset vacío (sin filas).
            # Solo procesamos si NO es None.
            if solicitud.polizas_usuario is None:
                # Usuario NO configuró pólizas → dataset None (no incluir en response)
                return None

            polizas_usuario = solicitud.polizas_usuario  # [] o [...] ambos válidos

            filas: List[PolizaActivaRow] = []
            tasa_total = 0.0

            for pol in polizas_usuario:
                if not pol.activa:
                    continue
                tasa = pol.tasa_efectiva
                tasa_total += tasa
                filas.append(PolizaActivaRow(
                    nombre          = pol.nombre,
                    pct_poliza      = pol.pct_poliza,
                    pct_atribuible  = pol.pct_atribuible,
                    tasa_efectiva   = tasa,
                    aplica_cadena_a = getattr(pol, "aplica_a", True),
                    aplica_cadena_b = getattr(pol, "aplica_b", False),
                    aplica_cadena_c = getattr(pol, "aplica_c", False),
                    aplica_extension= getattr(pol, "aplica_extension", False),
                    meses_extension = getattr(pol, "meses_extension", None),
                ))

            # TASK 1: Costo mensual promedio de pólizas desde el P&G
            # Calcula total y por-cadena
            costo_mensual_promedio = 0.0
            costo_mensual_promedio_a = 0.0
            costo_mensual_promedio_b = 0.0
            costo_mensual_promedio_c = 0.0

            if resultado.pyg_por_mes:
                costos_polizas = [
                    getattr(m, "polizas", 0.0)
                    for m in resultado.pyg_por_mes
                ]
                costos_polizas_a = [
                    getattr(m, "polizas_a", 0.0)
                    for m in resultado.pyg_por_mes
                ]
                costos_polizas_b = [
                    getattr(m, "polizas_b", 0.0)
                    for m in resultado.pyg_por_mes
                ]
                costos_polizas_c = [
                    getattr(m, "polizas_c", 0.0)
                    for m in resultado.pyg_por_mes
                ]

                if costos_polizas:
                    costo_mensual_promedio = sum(costos_polizas) / len(costos_polizas)
                    costo_mensual_promedio_a = sum(costos_polizas_a) / len(costos_polizas_a)
                    costo_mensual_promedio_b = sum(costos_polizas_b) / len(costos_polizas_b)
                    costo_mensual_promedio_c = sum(costos_polizas_c) / len(costos_polizas_c)

            return DatasetPolizasMensual(
                polizas_activas        = filas,
                tasa_total_efectiva    = tasa_total,
                costo_mensual_promedio = costo_mensual_promedio,
                costo_mensual_promedio_a = costo_mensual_promedio_a,
                costo_mensual_promedio_b = costo_mensual_promedio_b,
                costo_mensual_promedio_c = costo_mensual_promedio_c,
            )

        except Exception as exc:
            logger.warning("[vision_datasets] polizas build failed (non-fatal): %s", exc)
            return None

    def _build_indexacion(self, solicitud: PricingRequest) -> Optional[DatasetIndexacion]:
        """
        Construye la timeline de indexación para todos los meses del contrato.

        Fuente de datos (H-02 fix):
          - factor_humano_anual: 1 + pct_aumento_salarial de ParametrosNomina
          - mes_aplicacion: ParametrosNomina.mes_aplicacion_aumento
          - componente_humano/tecnologico: Indexacion.componente_humano/tecnologico del panel
          - factor_base_año1: ParametrosNomina.factor_indexacion_base
            (salarios ya expresados en COP del año de inicio del contrato)
        """
        try:
            from nexa_engine.modules.shared.precision import pct_round  # H-05: Excel rounding
            panel = solicitud.panel
            meses = panel.meses_contrato
            if meses <= 0:
                return None

            # ── Fuente correcta: ParametrosNomina (H-02) ─────────────────────────
            nom = solicitud.parametros_nomina
            pct_aumento_salarial   = getattr(nom, "pct_aumento_salarial", 0.0) or 0.0
            factor_humano_anual    = 1.0 + pct_aumento_salarial
            # Para tecnológico usamos ParametrosNoPayroll si tiene pct_aumento, o el mismo de nómina
            pct_aumento_no_payroll = getattr(solicitud.parametros_no_payroll, "pct_aumento_tecnologico", pct_aumento_salarial) or pct_aumento_salarial
            factor_tecnologico_anual = 1.0 + pct_aumento_no_payroll

            mes_aplicacion = getattr(nom, "mes_aplicacion_aumento", 1) or 1
            frecuencia     = getattr(panel, "indexacion_frecuencia", "Anual")

            # Componentes de indexación (metadata para el dataset)
            indexacion_obj     = getattr(panel, "indexacion", None)
            componente_humano  = getattr(indexacion_obj, "componente_humano", "") if indexacion_obj else ""
            componente_tecnol  = getattr(indexacion_obj, "componente_tecnologico", "") if indexacion_obj else ""

            # Factor base año 1 (salarios ya vienen indexados al año de inicio)
            factor_base = getattr(nom, "factor_indexacion_base", 1.0) or 1.0

            filas: List[MesIndexacionRow] = []
            # Mes 1 arranca con el factor base del año de inicio del contrato
            f_h = factor_base
            f_t = factor_base

            for mes in range(1, meses + 1):
                anio_contrato = (mes - 1) // 12 + 1
                # El ajuste se aplica en el primer mes del año 2+ que coincide con mes_aplicacion
                aplica = (
                    anio_contrato >= 2
                    and ((mes - 1) % 12 + 1) == mes_aplicacion
                    and frecuencia == "Anual"
                )
                if aplica:
                    # H-02 FIX: Round once immediately after multiplication
                    f_h = pct_round(f_h * factor_humano_anual, 6)
                    f_t = pct_round(f_t * factor_tecnologico_anual, 6)

                # H-02 FIX: Don't round again — already rounded above
                filas.append(MesIndexacionRow(
                    mes              = mes,
                    anio_contrato    = anio_contrato,
                    factor_humano    = f_h,  # Already rounded, no double pct_round()
                    factor_tecnologico = f_t,  # Already rounded
                    aplica_ajuste    = aplica,
                ))

            return DatasetIndexacion(
                componente_humano      = componente_humano,
                componente_tecnologico = componente_tecnol,
                frecuencia             = frecuencia,
                mes_aplicacion         = mes_aplicacion,
                filas                  = filas,
            )

        except Exception as exc:
            logger.warning("[vision_datasets] indexacion build failed (non-fatal): %s", exc)
            return None

    def _build_volumetria(self, solicitud: PricingRequest) -> Optional[DatasetVolumetriaPorCanal]:
        """
        Construye el dataset de volumetría por canal y cadena.

        Cadena A: FTE × vol_cadena_a_mensual (o 0 si no aplica outbound).
        Cadena B: volumen_mensual del canal.
        Cadena C: volumen_mensual del canal.
        """
        try:
            filas: List[CanalVolumetriaRow] = []

            # Cadena A — perfiles humanos
            for perfil in solicitud.perfiles_cadena_a:
                filas.append(CanalVolumetriaRow(
                    nombre               = perfil.nombre,
                    modalidad            = perfil.modalidad,
                    canal                = perfil.canal,
                    cadena               = "A",
                    fte                  = perfil.fte,
                    volumen_mensual      = getattr(perfil, "vol_cadena_a_mensual", 0.0) or 0.0,
                    pct_automatizacion   = 0.0,
                    tarifa_unitaria      = 0.0,
                ))

            # Cadena B — canales de tecnología/plataforma (modalidad del JSON)
            cadena_b = solicitud.cadena_b
            if cadena_b and hasattr(cadena_b, "canales"):
                for canal in (cadena_b.canales or []):
                    filas.append(CanalVolumetriaRow(
                        nombre             = canal.nombre,
                        modalidad          = getattr(canal, "modalidad", ""),
                        canal              = canal.nombre,
                        cadena             = "B",
                        fte                = 0.0,
                        volumen_mensual    = getattr(canal, "volumen_mensual", 0.0) or 0.0,
                        pct_automatizacion = 1.0,
                        tarifa_unitaria    = getattr(canal, "tarifa_unitaria", 0.0) or 0.0,
                    ))

            # Cadena C — canales de integración (modalidad configurable en JSON)
            cadena_c = solicitud.cadena_c
            if cadena_c and hasattr(cadena_c, "canales"):
                for canal in (cadena_c.canales or []):
                    filas.append(CanalVolumetriaRow(
                        nombre             = canal.nombre,
                        modalidad          = getattr(canal, "modalidad", ""),
                        canal              = canal.nombre,
                        cadena             = "C",
                        fte                = 0.0,
                        volumen_mensual    = getattr(canal, "volumen_mensual", 0.0) or 0.0,
                        pct_automatizacion = 1.0,
                        tarifa_unitaria    = 0.0,
                    ))

            return DatasetVolumetriaPorCanal(filas=filas)

        except Exception as exc:
            logger.warning("[vision_datasets] volumetria build failed (non-fatal): %s", exc)
            return None

    def _build_graficos(
        self,
        solicitud: PricingRequest,
        resultado: PricingResult,
    ) -> Optional[GraficosResult]:
        datasets = getattr(resultado, "datasets_vision", None)
        if datasets is None:
            return None
        return getattr(datasets, "graficos", None)
