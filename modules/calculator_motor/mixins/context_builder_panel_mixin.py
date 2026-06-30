from __future__ import annotations
"""Private builder methods for SimulationContextBuilder.

Single mixin containing all private _construir_* and _calcular_* methods.
Extracted FASE Z.4.3 — behaviour unchanged; self.* resolves via Python MRO.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexa_engine.modules.calculator_motor.constants.global_constants import MES_INICIO_AJUSTE_ANUAL
from nexa_engine.modules.shared.exceptions import ParametrizationError
from nexa_engine.modules.shared.models import (
    CanalCadenaB, CanalCadenaC, CadenasActivas, DispositivoSM, EscenarioComercial,
    Indexacion, ItemOpexConsumoB, MiembroEquipo, PanelDeControl, ParametrosCadenaB,
    ParametrosCadenaC, ParametrosCalculo, ParametrosNomina, ParametrosNoPayroll,
    PerfilCadenaA, PolizaContractual, PricingRequest, mes_inicio_contrato,
)
from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService
from nexa_engine.modules.cadena_a.services.special_roles_calculator import (
    CargoClassifier, EspecialistaCalculator, SENACalculator, InclusionCalculator,
    SalarioFijoCalculator,
)
from nexa_engine.modules.calculator_motor.dto.user_inputs import UserInput
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.calculator_motor.models.data_provenance import DataProvenance, DataSource, ProvenanceEntry
from nexa_engine.modules.calculator_motor.dto.normalized_input import NormalizationLog

_logger = logging.getLogger("nexa_engine.context_builder")




class ContextBuilderPanelMixin:
    """Mixin: ContextBuilderPanelMixin."""

    def _construir_panel(self, panel, ciudad: str, linea: str) -> PanelDeControl:
        """
        Construye el PanelDeControl resolviendo defaults desde datos maestros.

        Los valores de tasa (ICA, GMF, financiación, ausentismo) se toman del
        input del usuario si fueron proporcionados explícitamente; en caso
        contrario se resuelven desde la tabla maestra correspondiente.
        """
        tasa_ica    = panel.tasa_ica if panel.tasa_ica is not None else self._prov.get_ica(ciudad)
        tasa_gmf    = panel.tasa_gmf if panel.tasa_gmf is not None else self._prov.get_gmf()
        # WAVE 3 (W3-3): Panel!L10 (tasa_interes_mensual) prevalece sobre el
        # legacy `tasa_mensual_financ` cuando se provee. Si ninguno está, se
        # cae al provider (OP-Config tasa_financiacion_mensual).
        if panel.tasa_mensual_financ is not None:
            tasa_financ = panel.tasa_mensual_financ
        elif getattr(panel, "tasa_interes_mensual", None) is not None:
            tasa_financ = panel.tasa_interes_mensual
        else:
            tasa_financ = self._prov.tasa_mensual_financiacion()
        pct_ausent  = (panel.pct_ausentismo
                       if panel.pct_ausentismo is not None
                       else self._prov.get_pct_ausentismo(linea))

        # ── WAVE 2 (Excel V2-7) — defaults desde op.v2_7_defaults ─────────
        # NO hardcode: si el usuario no override, leemos del JSON de parametrización.
        try:
            v27_defaults = self._prov.get_v27_defaults() or {}
        except Exception as exc:
            raise ParametrizationError(
                "OP parametrization provider failed in get_v27_defaults() — "
                "cannot resolve margen_b/margen_c/tasa_interes defaults",
                module="OP",
            ) from exc
        margenes_def    = v27_defaults.get("margenes", {}) if isinstance(v27_defaults, dict) else {}
        indexacion_def  = v27_defaults.get("indexacion", {}) if isinstance(v27_defaults, dict) else {}
        margen_b_val = (
            getattr(panel, "margen_b", None)
            if getattr(panel, "margen_b", None) is not None
            else float(margenes_def.get("margen_b_default", 0.30))
        )
        margen_c_val = (
            getattr(panel, "margen_c", None)
            if getattr(panel, "margen_c", None) is not None
            else float(margenes_def.get("margen_c_default", 0.20))
        )
        mes_ajuste_val = (
            getattr(panel, "mes_ajuste_indexacion", None)
            if getattr(panel, "mes_ajuste_indexacion", None) is not None
            else int(indexacion_def.get("mes_ajuste", 6))
        )
        tasa_interes_val = (
            getattr(panel, "tasa_interes_mensual", None)
            if getattr(panel, "tasa_interes_mensual", None) is not None
            else float(indexacion_def.get("tasa_interes_mensual", 0.0153))
        )

        return PanelDeControl(
            cliente             = panel.cliente,
            tipo_cliente        = panel.tipo_cliente,
            linea_negocio       = linea,
            fecha_inicio        = panel.fecha_inicio,
            meses_contrato      = panel.meses_contrato,
            margen              = panel.margen,
            op_cont             = panel.op_cont,
            com_cont            = panel.com_cont,
            markup              = panel.markup,
            descuento           = panel.descuento,
            tasa_ica            = tasa_ica,
            tasa_gmf            = tasa_gmf,
            activa_financiacion = panel.activa_financiacion,
            periodo_pago_dias   = panel.periodo_pago_dias,
            tasa_mensual_financ = tasa_financ,
            ciudad              = ciudad,
            sede                = panel.sede,
            antiguedad_cliente  = panel.antiguedad_cliente,
            pct_ausentismo      = pct_ausent,
            horas_formacion_mensual = getattr(panel, "horas_formacion_mensual", 0),
            indexacion          = Indexacion(
                componente_humano      = panel.componente_indexacion_humano,
                componente_tecnologico = panel.componente_indexacion_tecnologico,
                frecuencia             = getattr(panel, "indexacion_frecuencia", "Anual"),
                mes_aplicacion         = (
                    panel.indexacion_mes_aplicacion
                    if panel.indexacion_mes_aplicacion is not None
                    else MES_INICIO_AJUSTE_ANUAL
                ),
            ),
            aplica_ley_1819               = panel.aplica_ley_1819,
            # REFACTOR costos_operativos: tarifa_dia_cap desde input usuario
            tarifa_diaria_capacitacion    = getattr(panel, "tarifa_diaria_capacitacion", 0.0),
            # Crucero mensual por agente (Panel!C17 en Excel V2-7)
            tarifa_crucero                = float(getattr(panel, "tarifa_crucero", 0.0) or 0.0),
            # GAP-PYG-1: Imprevistos (Panel!C73). V2-5 nuevo.
            imprevistos                   = getattr(panel, "imprevistos", 0.0),
            # ── WAVE 2 (Excel V2-7) ────────────────────────────────────
            margen_b                      = margen_b_val,
            margen_c                      = margen_c_val,
            mes_ajuste_indexacion         = mes_ajuste_val,
            tasa_interes_mensual          = tasa_interes_val,
            # GAP-PYG-3: Comisión de Administración (Panel!G45). V2-5 nuevo.
            tasa_comision_administracion  = getattr(panel, "tasa_comision_administracion", 0.0),
            # Complejidad del Especialista de Proyectos (reglas V2-6).
            complejidad_especialista      = getattr(panel, "complejidad_especialista", "ALTA") or "ALTA",
            cadenas_activas               = self._construir_cadenas_activas(panel),
        )

    @staticmethod
    def _construir_cadenas_activas(panel) -> CadenasActivas:
        raw = getattr(panel, "cadenas_activas", None)
        return CadenasActivas(
            cadena_a=bool(getattr(raw, "cadena_a", False)),
            cadena_b=bool(getattr(raw, "cadena_b", False)),
            cadena_c=bool(getattr(raw, "cadena_c", False)),
        )

    # ──────────────────────────────────────────────────────────────
    # Cadena A — perfiles de agentes y staff de soporte
    # ──────────────────────────────────────────────────────────────

__all__ = ["ContextBuilderPanelMixin"]
