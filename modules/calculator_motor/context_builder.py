"""Simulation context builder owned by calculator_motor.

Builder de contexto de simulación.

Current role:
  - recibe ``UserInput`` y parametrización resuelta
  - construye un ``PricingRequest`` listo para el motor
  - mantiene la composición actual basada en mixins internos

This docstring describes the current canonical path only. It does not claim that
any old compatibility stub still exists.

Responsabilidad
---------------
Combinar los datos ingresados por el usuario (UserInput) con los datos
de parametrización activa y la configuración estática del sistema para
producir un PricingRequest coherente, completo y listo para el motor.

Flujo
-----
    UserInput  +  ParametrizationProvider
         │
         ▼
    SimulationContextBuilder.construir()
         │
         ▼
    PricingRequest  →  NexaPricingEngine

Fuentes de datos
----------------
- ParametrizationProvider: única fuente de datos de negocio (HR, GN, OP)
    salarios, ICA, GMF, costos infraestructura, márgenes, índices,
    rotacion/ausentismo, reglas_staff, ratios_staff, constantes operativas

Principios de diseño
--------------------
- Los defaults (rotación, ausentismo, ICA) se resuelven en el orden:
  1. Override explícito del usuario (si lo proporcionó)
  2. Valor de parametrización activa (versionado)
- La lógica de nómina cargada vive en NominaCargadaService (dominio puro).
- Los roles de soporte y sus reglas de FTE se leen de storage/parametrization/hr/.

Produce
-------
PricingRequest con:
  - PanelDeControl completo (incluye tasas, indexación, período de pago)
  - Lista de PerfilCadenaA (agentes base + staff de soporte calculado)
  - ParametrosNomina y ParametrosCalculo
  - ParametrosCadenaB / ParametrosCadenaC
"""

from __future__ import annotations

import logging

from nexa_engine.modules.calculator_motor.constants.global_constants import MES_INICIO_AJUSTE_ANUAL

_logger = logging.getLogger("nexa_engine.context_builder")
from nexa_engine.modules.shared.models import (
    CanalCadenaB,
    CanalCadenaC,
    CadenasActivas,
    DispositivoSM,
    EscenarioComercial,
    Indexacion,
    ItemOpexConsumoB,
    MiembroEquipo,
    PanelDeControl,
    ParametrosCadenaB,
    ParametrosCadenaC,
    ParametrosCalculo,
    ParametrosNomina,
    ParametrosNoPayroll,
    PerfilCadenaA,
    PolizaContractual,
    PricingRequest,
    mes_inicio_contrato,
)
from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService
from nexa_engine.modules.cadena_a.services.special_roles_calculator import (
    CargoClassifier,
    EspecialistaCalculator,
    SENACalculator,
    InclusionCalculator,
    SalarioFijoCalculator,
)
from nexa_engine.modules.calculator_motor.dto.user_inputs import UserInput
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.parametrizacion.services.provider import get_provider



from nexa_engine.modules.calculator_motor.mixins.context_builder_methods import ContextBuilderMethodsMixin


class SimulationContextBuilder(ContextBuilderMethodsMixin):
    """
    Construye un PricingRequest completo a partir de UserInput.

    Private builder methods live in ``ContextBuilderMethodsMixin`` and the
    related internal mixins under ``calculator_motor.mixins``.
    """

    def __init__(
        self,
        provider: IParametrizationProvider | None = None,
    ) -> None:
        self._prov = provider or get_provider()
        # NominaCargadaService is initialized lazily in construir().
        # Nota: aplica_ley_1819 se pasa por compatibilidad pero su valor es
        # ignorado — Salud e ICBF+SENA se cobran siempre (modo Excel V2-4).
        self._nomina_service = None
        self._last_provenance = None
        self._last_parametrization_snapshot: dict | None = None  # FASE 4

    def construir(self, user_input: UserInput) -> PricingRequest:
        """
        Transforma un UserInput en un PricingRequest listo para el motor.

        Args:
            user_input: Datos configurados por el usuario para este deal.

        Returns:
            PricingRequest con todos los parámetros resueltos y validados.
        """
        panel  = user_input.panel
        linea  = panel.linea_negocio
        ciudad = panel.ciudad
        sede   = panel.sede

        # Inicializar (o re-inicializar) NominaCargadaService.
        # aplica_ley_1819 se pasa por compatibilidad de firma; su valor es
        # ignorado internamente — Salud e ICBF+SENA se cobran siempre
        # (Excel V2-4 legacy no implementa exoneración Ley 1819).
        self._nomina_service = NominaCargadaService.desde_parametrizacion(
            self._prov, aplica_ley_1819=panel.aplica_ley_1819
        )

        pct_rotacion = (
            panel.pct_rotacion
            if panel.pct_rotacion is not None
            else self._prov.get_pct_rotacion(linea)
        )

        # FASE D / Gap C3: mapear pólizas del usuario a PolizaContractual
        polizas_usuario = [
            PolizaContractual(
                nombre                      = p.nombre,
                activa                      = p.activa,
                pct_poliza                  = p.pct_poliza,
                pct_atribuible              = p.pct_atribuible,
                aplica_extension            = p.aplica_extension,
                meses_extension             = p.meses_extension,
                aplica_a                    = p.aplica_a,
                aplica_b                    = p.aplica_b,
                aplica_c                    = p.aplica_c,
                per_canal                   = p.per_canal,
                is_comision_administracion  = p.is_comision_administracion,
            )
            for p in user_input.polizas
        ] if user_input.polizas is not None else None

        # GAP-PCG-1: mapear escenarios comerciales del Panel!A81:D113
        escenarios = [
            EscenarioComercial(
                escenario              = e.escenario,
                modalidad              = e.modalidad,
                canal                  = e.canal,
                modelo_cobro           = e.modelo_cobro,
                componente_fijo_tipo   = e.componente_fijo_tipo,
                componente_fijo_pct    = e.componente_fijo_pct,
                componente_variable_tipo = e.componente_variable_tipo,
                componente_variable_pct  = e.componente_variable_pct,
            )
            for e in getattr(panel, "escenarios", [])
        ]

        # FASE 3 — DataProvenance: registrar origen de campos clave del panel
        from nexa_engine.modules.calculator_motor.models.data_provenance import DataProvenance, DataSource
        provenance = DataProvenance()
        provenance.record_user_input("panel.cliente", panel.cliente, "datos_operativos.cliente")
        provenance.record_user_input("panel.ciudad", panel.ciudad, "datos_operativos.ciudad")
        provenance.record_user_input("panel.fecha_inicio", panel.fecha_inicio, "datos_operativos.fecha_inicio")
        provenance.record_user_input("panel.meses_contrato", panel.meses_contrato, "datos_operativos.duracion_meses")
        provenance.record_user_input("panel.margen", panel.margen, "reglas_negocio.margen_objetivo_cadena_a")
        # tasa_ica: puede ser override del usuario o parametrización
        _src_ica = DataSource.USER_OVERRIDE_PARAMETRIZATION if panel.tasa_ica is not None else DataSource.PARAMETRIZATION
        provenance.record("panel.tasa_ica", panel.tasa_ica or self._prov.get_ica(ciudad), _src_ica, f"OP-ICA[ciudad={ciudad}]")
        # tasa_gmf: puede ser override del usuario o parametrización
        _src_gmf = DataSource.USER_OVERRIDE_PARAMETRIZATION if panel.tasa_gmf is not None else DataSource.PARAMETRIZATION
        provenance.record("panel.tasa_gmf", panel.tasa_gmf or self._prov.get_gmf(), _src_gmf, "OP-Config.tasa_gmf")
        # pct_rotacion: puede ser override del usuario o parametrización
        _src_rot = DataSource.USER_OVERRIDE_PARAMETRIZATION if panel.pct_rotacion is not None else DataSource.PARAMETRIZATION
        provenance.record("parametros_calculo.pct_rotacion", pct_rotacion, _src_rot, f"HR-rotacion[linea={linea}]")
        # defaults explícitos documentados
        provenance.record_default("panel.periodo_pago_dias", panel.periodo_pago_dias, "Estándar BPO Colombia 90 días")
        provenance.record_default("panel.com_cont", panel.com_cont, "Sin contingencia comercial si no se especifica")
        provenance.record_default("panel.markup", panel.markup, "Sin markup si no se especifica")
        self._last_provenance = provenance

        # FASE 4 — capturar snapshot de parametrización para SimulationSnapshot
        try:
            anio_inicio = self._anio_inicio(panel.fecha_inicio)
            roles_usados = [p.rol for p in user_input.cadena_a.perfiles]
            self._last_parametrization_snapshot = self._prov.capture_parametrization_snapshot(
                ciudad                = ciudad,
                linea_negocio         = linea,
                componente_humano     = panel.componente_indexacion_humano,
                componente_tecnologico= panel.componente_indexacion_tecnologico,
                anio_inicio           = anio_inicio,
                roles_usados          = roles_usados,
            )
        except Exception:
            self._last_parametrization_snapshot = {}

        # [PIPELINE_TRACE] Log cadena_a input before building perfiles
        cadena_a_input = user_input.cadena_a
        _logger.info(
            "[PIPELINE_TRACE] cadena_a.perfiles count=%d entries=%s",
            len(cadena_a_input.perfiles),
            [(p.canal, p.modalidad, p.fte) for p in cadena_a_input.perfiles],
        )
        _logger.info(
            "[PIPELINE_TRACE] escenarios count=%d entries=%s",
            len(escenarios),
            [(e.canal, e.modalidad) for e in escenarios],
        )
        # WAVE 5 structured log — scenarios.
        _logger.info(
            "[SCENARIO_BUILD] op=build_escenarios inputs={panel_cliente:%s,linea:%s} "
            "outputs={count:%d,canales:%s} source=Panel!A81:D113",
            getattr(panel, "cliente", "?"), linea,
            len(escenarios),
            list({e.canal for e in escenarios}),
        )

        factor_capex_perfil = 1.0 + float(
            panel.tasa_mensual_financ if panel.tasa_mensual_financ is not None
            else getattr(panel, "tasa_interes_mensual", None) or 0.0
        )
        perfiles_cadena_a     = self._construir_perfiles_a(
                                    user_input.cadena_a, linea,
                                    panel.meses_contrato, pct_rotacion,
                                    getattr(panel, 'complejidad_especialista', 'ALTA') or 'ALTA',
                                    factor_capex=factor_capex_perfil)

        # [PIPELINE_TRACE] Log perfiles built
        agent_perfs = [p for p in perfiles_cadena_a if not p.es_soporte]
        _logger.info(
            "[PIPELINE_TRACE] perfiles_cadena_a total=%d agents=%d support=%d",
            len(perfiles_cadena_a),
            len(agent_perfs),
            len(perfiles_cadena_a) - len(agent_perfs),
        )
        for p in agent_perfs:
            _logger.info(
                "[PIPELINE_TRACE] agent_perfil nombre=%r canal=%r modalidad=%r fte=%s",
                p.nombre, p.canal, p.modalidad, p.fte,
            )
        # WAVE 5 structured log — staffing aggregate.
        total_fte = sum(getattr(p, "fte", 0) or 0 for p in perfiles_cadena_a)
        _logger.info(
            "[STAFFING_BUILD] op=construir_perfiles_a inputs={linea:%s,meses:%d,pct_rotacion:%.4f} "
            "outputs={total_perfiles:%d,agentes:%d,soporte:%d,total_fte:%s} source=cadena_a.perfiles+HR-Ratios",
            linea, panel.meses_contrato, float(pct_rotacion or 0.0),
            len(perfiles_cadena_a), len(agent_perfs),
            len(perfiles_cadena_a) - len(agent_perfs),
            total_fte,
        )

        return PricingRequest(
            panel                 = self._construir_panel(panel, ciudad, linea),
            perfiles_cadena_a     = perfiles_cadena_a,
            parametros_nomina     = self._construir_parametros_nomina(panel, ciudad),
            parametros_no_payroll = self._construir_no_payroll(panel, sede, user_input.cadena_a.perfiles),
            cadena_b              = self._construir_cadena_b(user_input.cadena_b, panel),
            cadena_c              = self._construir_cadena_c(user_input.cadena_c, panel),
            parametros_calculo    = self._construir_parametros_calculo(panel, linea),
            polizas_usuario       = polizas_usuario,
            escenarios            = escenarios,
            cadenas_activas       = self._construir_cadenas_activas(panel),
        )

    @property
    def last_provenance(self):
        """Retorna el DataProvenance del último construir() llamado (FASE 3)."""
        return self._last_provenance

    @property
    def last_parametrization_snapshot(self) -> dict | None:
        """Retorna el snapshot de parametrización del último construir() (FASE 4)."""
        return self._last_parametrization_snapshot

    # ──────────────────────────────────────────────────────────────
    # Panel de Control
    # ──────────────────────────────────────────────────────────────
