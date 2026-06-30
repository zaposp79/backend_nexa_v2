"""
nexa_engine/engine.py
======================
Motor de precios NEXA — Facade principal del pipeline de cálculo.

Responsabilidad
---------------
Orquestar el pipeline de 10 capas para transformar un PricingRequest
en un PricingResult con P&G mensual completo y KPIs del deal.

El motor es el punto de entrada único al sistema de cálculo. No conoce
el origen de los datos (JSON, API, frontend) ni el destino del resultado
(consola, base de datos, REST). Recibe y produce objetos de dominio puros.

Pipeline interno
----------------
  PricingRequest
      │
      ├─ NominaCalculator        (Capa 2) — nómina cargada
      ├─ NoPayrollCalculator     (Capa 3) — infraestructura y TI
      ├─ CadenaBCalculator       (Capas 4-5) — plataforma digital
      ├─ CadenaCCalculator       (Capa 6) — integración IA
      ├─ CostosTotalesCalculator (Capa 7) — costos agregados
      ├─ CostosFinancierosCalculator (Capa 8) — ICA, GMF, pólizas, financiación
      ├─ PyGCalculator           (Capa 9) — Estado de Resultados mensual
      └─ KPIsCalculator          (Capa 10) — KPIs del deal
          │
          ▼
      PricingResult

Patrón de uso recomendado
--------------------------
    from nexa_engine.modules.parametrizacion.services.provider import get_provider

    provider = get_provider()                         # singleton, carga versión activa
    builder  = SimulationContextBuilder(provider)
    request  = builder.construir(user_input)
    engine   = NexaPricingEngine(parametrizacion=provider)
    result   = engine.calcular(request)

Todos los calculadores reciben sus dependencias por inyección desde
el motor (Composition Root). Ningún calculador accede directamente a
archivos JSON ni al repositorio global de datos.

Arquitectura de datos
---------------------
Los calculadores dependen de `IParametrizationProvider` (Protocol), NO de
una implementación concreta. El motor inyecta `ParametrizationProvider`
por defecto, que lee de `storage/parametrization/{hr,gn,op}/` (versión activa).
Para tests se puede inyectar un `MockParametrizationProvider` sin tocar nada más.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry as VersionRegistryT  # noqa: F401

import logging as _logging

from nexa_engine.modules.audit.integration import audit_context, export_audit_trace

_engine_logger = _logging.getLogger("nexa_engine.modules.calculator_motor.engine")
from nexa_engine.modules.cadena_b.reglas import CadenaBCalculator
from nexa_engine.modules.cadena_c.reglas import CadenaCCalculator
from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.vision_pyg.services.costos_totales_calculator import CostosTotalesCalculator
from nexa_engine.modules.vision_pyg.services.kpis_calculator import KPIsCalculator
from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
from nexa_engine.modules.calculator_motor.formulas.no_payroll import NoPayrollCalculator
from nexa_engine.modules.calculator_motor.formulas.pyg import build_pyg_detail_read_model
from nexa_engine.modules.vision_pyg.services.pyg_calculator import PyGCalculator
from nexa_engine.modules.vision_pyg.builders.vision_pyg_builder import VisionPyGBuilder
from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
from nexa_engine.modules.calculator_motor.formulas.graphics.graficos_result_builder import build_graficos_result
from nexa_engine.modules.vision_imprimible.builders.vision_datasets_builder import VisionDatasetsBuilder
from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder
from nexa_engine.modules.vision_imprimible.models.vision_datasets import DatasetsVision
from nexa_engine.modules.calculator_motor.formulas.tarifas import build_vision_tarifas_result
from nexa_engine.modules.calculator_motor.formulas.cts import build_cost_to_serve_result
from nexa_engine.modules.shared.models import (
    KPIsDeal,
    PanelDeControl,
    PricingRequest,
    PricingResult,
    PyGMensual,
    ReglaNegocios,
    WaterfallPromedio,
)
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.shared.exceptions import AuditIntegrityError
from nexa_engine.modules.calculator_motor.helpers.engine_helpers import (  # noqa: F401
    _calcular_waterfall,
    _calcular_reglas_negocio,
)
from nexa_engine.modules.vision_tarifas.models.vt_facts import VisionTarifasFacts
from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import (
    CanalCTSFacts,
    CostToServeFacts,
)


def _denominador_cadena_a_para_facts(perfiles: "List") -> float:
    """Réplica de CostToServeCalculator._denominador_cadena_a — sin instanciar la clase."""
    total = 0.0
    for perfil in perfiles:
        if perfil.es_soporte:
            continue
        modalidad = (perfil.modalidad or "").strip().lower()
        total += perfil.fte if modalidad == "outbound" else perfil.vol_cadena_a_mensual
    return total


def _build_cts_facts(
    perfiles: "List",
    numero_meses: int,
    calc_nomina: "NominaCalculator",
    calc_no_payroll: "NoPayrollCalculator",
    calc_cadena_b: "CadenaBCalculator",
) -> CostToServeFacts:
    """Pre-computa los resultados finos de Nomina/NoPayroll/CadenaB para CostToServeCalculator.

    El engine llama a los calculadores core una sola vez y empaqueta los
    resultados en CostToServeFacts. CostToServeCalculator los consume sin
    re-calcular.

    nomina_por_mes/no_payroll_por_mes solo se computan si denominador_cadena_a > 0,
    preservando el comportamiento del antiguo _calcular_desglose_a (que retornaba temprano
    cuando denominador = 0 sin llamar calcular_para_mes). Esto evita audit trace drift.
    """
    from collections import defaultdict

    if _denominador_cadena_a_para_facts(perfiles) > 0:
        nomina_por_mes = [
            calc_nomina.calcular_para_mes(perfiles, mes)
            for mes in range(1, numero_meses + 1)
        ]
        no_payroll_por_mes = [
            calc_no_payroll.calcular_para_mes(perfiles, mes)
            for mes in range(1, numero_meses + 1)
        ]
    else:
        nomina_por_mes = []
        no_payroll_por_mes = []

    # cadena_b ANTES de per-canal: preserva el orden del antiguo código donde
    # _calcular_desglose_b se llamaba antes que _calcular_canales_detalle.
    # El audit trace es sensible al orden de llamadas.
    cadena_b_por_mes = [
        calc_cadena_b.calcular_para_mes(mes)
        for mes in range(1, numero_meses + 1)
    ]

    # Per-canal facts: misma semántica que el workbook.
    # nomina: todos los perfiles del canal (agente + soporte).
    # no_payroll: solo perfiles agente del canal.
    canal_modalidad_fte: "dict" = {}
    canal_all_profiles: "dict" = defaultdict(list)
    for perfil in perfiles:
        canal_all_profiles[perfil.canal or ""].append(perfil)
        if not perfil.es_soporte:
            clave = (perfil.canal or "", (perfil.modalidad or "").strip())
            canal_modalidad_fte[clave] = canal_modalidad_fte.get(clave, 0.0) + perfil.fte

    canales: "List[CanalCTSFacts]" = []
    for (canal, modalidad), fte_del_canal in sorted(canal_modalidad_fte.items()):
        if fte_del_canal <= 0:
            continue  # igual que el workbook: "No Activado" cuando FTE=0
        perfiles_del_canal = canal_all_profiles.get(canal, [])
        perfiles_agente = [p for p in perfiles_del_canal if not p.es_soporte]
        # Interleave nomina + no_payroll per month to match old _calcular_canales_detalle
        # call order (cada mes: calcular_nomina luego calcular_no_payroll). El audit trace
        # es sensible al orden exacto de llamadas.
        canal_nomina = []
        canal_no_payroll = []
        for mes in range(1, numero_meses + 1):
            canal_nomina.append(calc_nomina.calcular_para_mes(perfiles_del_canal, mes))
            canal_no_payroll.append(calc_no_payroll.calcular_para_mes(perfiles_agente, mes))
        canales.append(CanalCTSFacts(
            canal=canal,
            modalidad=modalidad,
            fte_del_canal=fte_del_canal,
            nomina_por_mes=canal_nomina,
            no_payroll_por_mes=canal_no_payroll,
        ))

    return CostToServeFacts(
        nomina_por_mes=nomina_por_mes,
        no_payroll_por_mes=no_payroll_por_mes,
        cadena_b_por_mes=cadena_b_por_mes,
        canales=canales,
    )


def _build_vt_facts(
    escenarios: "List",
    perfiles: "List",
    polizas_usuario: "Optional[List]",
    numero_meses: int,
    calc_nomina: "NominaCalculator",
    calc_no_payroll: "NoPayrollCalculator",
) -> VisionTarifasFacts:
    """Pre-computes Nomina/NoPayroll facts for VisionTarifasCalculator.

    Replicates the exact call order of the old VisionTarifasCalculator code so the
    audit trace is preserved:
      1. Per active escenario (has agent_perfiles): nomina_canal, nomina_agente, no_payroll_canal
      2. Extension pólizas (if has_deal_wide_polizas): interleaved per canal
    """
    from nexa_engine.modules.vision_tarifas.models.vt_facts import (
        CanalExtensionFacts,
        EscenarioCanalFacts,
    )

    # ── Backward compat: no escenarios — build canales_direct per unique canal ─
    # Mirrors the old backward compat path in VisionTarifasCalculator.calcular()
    # where one TarifaCanal is built per non-soporte profile, using perfiles_canal
    # = all profiles with the same canal. Facts are keyed by canal (case-preserving).
    if not escenarios:
        canales_direct: "dict[str, EscenarioCanalFacts]" = {}
        for perfil in perfiles:
            if perfil.es_soporte:
                continue
            canal_key = perfil.canal or ""
            if canal_key in canales_direct:
                continue  # already built for this canal
            perfiles_canal = [p for p in perfiles if p.canal == canal_key]
            agent_perfiles_bc = [p for p in perfiles_canal if not p.es_soporte]
            if not agent_perfiles_bc:
                continue
            perfil_agente_bc = agent_perfiles_bc[0]
            # Build nomina_por_mes (for perfiles_canal)
            nom_bc = [
                calc_nomina.calcular_para_mes(perfiles_canal, mes)
                for mes in range(1, numero_meses + 1)
            ]
            # Build nomina_agente_por_mes (for agent_perfiles only)
            nom_ag_bc = [
                calc_nomina.calcular_para_mes(agent_perfiles_bc, mes)
                for mes in range(1, numero_meses + 1)
            ]
            # Build no_payroll_por_mes (skip if override)
            if perfil_agente_bc.no_payroll_mensual > 0:
                nop_bc: "List" = []
            else:
                nop_bc = [
                    calc_no_payroll.calcular_para_mes(perfiles_canal, mes)
                    for mes in range(1, numero_meses + 1)
                ]
            canales_direct[canal_key] = EscenarioCanalFacts(
                canal=canal_key,
                modalidad=perfil.modalidad or "",
                nomina_por_mes=nom_bc,
                nomina_agente_por_mes=nom_ag_bc,
                no_payroll_por_mes=nop_bc,
            )
        return VisionTarifasFacts(canales_direct=canales_direct)

    # ── Phase 1: Per-escenario facts ─────────────────────────────────────────
    # Replicates _costo_op_canal_decomposed call pattern for each active escenario.
    escenarios_facts: "List[EscenarioCanalFacts]" = []
    for escenario in escenarios:
        perfiles_canal = [
            p for p in perfiles
            if p.canal.lower() == escenario.canal.lower()
            and (p.modalidad.lower() == escenario.modalidad.lower() or p.es_soporte)
        ]
        agent_perfiles = [p for p in perfiles_canal if not p.es_soporte]
        if not agent_perfiles:
            continue  # same skip as VisionTarifasCalculator.calcular()

        perfil_agente = agent_perfiles[0]

        # Step 1a: nomina for perfiles_canal (old for-mes loop in _costo_op_canal_decomposed)
        nomina_canal = [
            calc_nomina.calcular_para_mes(perfiles_canal, mes)
            for mes in range(1, numero_meses + 1)
        ]
        # Step 1b: nomina for agent_perfiles (old "if agent_perfiles:" branch)
        nomina_agente = [
            calc_nomina.calcular_para_mes(agent_perfiles, mes)
            for mes in range(1, numero_meses + 1)
        ]
        # Step 1c: no_payroll for perfiles_canal (old "elif self._calc_no_payroll" branch)
        # Only if no override (no_payroll_mensual == 0)
        if perfil_agente.no_payroll_mensual > 0:
            no_payroll_canal: "List" = []  # override path — original code skipped calcular_para_mes
        else:
            no_payroll_canal = [
                calc_no_payroll.calcular_para_mes(perfiles_canal, mes)
                for mes in range(1, numero_meses + 1)
            ]

        escenarios_facts.append(EscenarioCanalFacts(
            canal=escenario.canal,
            modalidad=escenario.modalidad,
            nomina_por_mes=nomina_canal,
            nomina_agente_por_mes=nomina_agente,
            no_payroll_por_mes=no_payroll_canal,
        ))

    # ── Phase 2: Extension pólizas facts ─────────────────────────────────────
    # Only if has_deal_wide_polizas=True (same condition as reglas.py).
    def _es_poliza_extension_deal_wide(p: "object") -> bool:
        return (
            not p.per_canal
            and p.activa
            and p.aplica_a
            and not getattr(p, "is_comision_administracion", False)
            and p.aplica_extension
            and bool(p.meses_extension)
        )

    has_deal_wide_polizas = bool(
        polizas_usuario
        and any(_es_poliza_extension_deal_wide(p) for p in polizas_usuario)
    )

    canales_extension: "dict[str, CanalExtensionFacts]" = {}

    if has_deal_wide_polizas:
        # Determine esc_canal (same logic as reglas.py)
        esc_canal = None
        for esc in escenarios:
            esc_c = esc.canal.lower()
            if any((p.canal or "").lower() == esc_c for p in perfiles if not p.es_soporte):
                esc_canal = esc_c
                break

        def _build_canal_ext_facts(perfiles_ch: "List", canal_key: str) -> "CanalExtensionFacts":
            """Interleaved nomina+no_payroll per month, then last month again (audit trace)."""
            nom_list: "List" = []
            nop_list: "List" = []
            for mes in range(1, numero_meses + 1):
                nom_list.append(calc_nomina.calcular_para_mes(perfiles_ch, mes))
                nop_list.append(calc_no_payroll.calcular_para_mes(perfiles_ch, mes))
            nom_last = calc_nomina.calcular_para_mes(perfiles_ch, numero_meses)
            nop_last = calc_no_payroll.calcular_para_mes(perfiles_ch, numero_meses)
            return CanalExtensionFacts(
                canal=canal_key,
                nomina_por_mes=nom_list,
                no_payroll_por_mes=nop_list,
                nomina_ultimo_mes=nom_last,
                no_payroll_ultimo_mes=nop_last,
            )

        if esc_canal:
            perfiles_esc = [p for p in perfiles if (p.canal or "").lower() == esc_canal]
            if perfiles_esc:
                canales_extension[esc_canal] = _build_canal_ext_facts(perfiles_esc, esc_canal)

            # Other canales (same seen_canales loop as reglas.py)
            seen_canales: "set" = {esc_canal}
            for esc in escenarios:
                ch = esc.canal.lower()
                if ch not in seen_canales:
                    perfiles_ch = [p for p in perfiles if (p.canal or "").lower() == ch]
                    if perfiles_ch:
                        canales_extension[ch] = _build_canal_ext_facts(perfiles_ch, ch)
                    seen_canales.add(ch)

    return VisionTarifasFacts(
        escenarios=escenarios_facts,
        canales_extension=canales_extension,
        canales_direct={},
    )


class NexaPricingEngine:  # noqa: E302
    """
    Motor de precios NEXA.

    Recibe un `IParametrizationProvider` para resolver las tablas de referencia
    que necesitan los calculadores (ramp-up, pólizas, período de pago,
    márgenes mínimos, tasa de financiación).

    Por defecto construye un `ParametrizationProvider` que lee de la versión
    activa en `storage/parametrization/`. Para tests, inyectar un mock.

    El proveedor se carga una sola vez y se reutiliza en todos los deals
    procesados con la misma instancia del motor.
    """

    def __init__(
        self,
        parametrizacion: IParametrizationProvider | None = None,
        parametrization_version: str | None = None,
        version_registry: "Optional[VersionRegistryT]" = None,
        lineage_repository=None,
    ) -> None:
        """
        Args:
            parametrizacion: Provider de parametrización. Si se omite, se carga el activo.
            parametrization_version: Si se especifica (ej. "v2-6"), carga la parametrización
                frozen para reproducibilidad exacta. Ignorado si `parametrizacion` se pasa
                explícitamente.
            version_registry: WAVE 14 — opcional. Si se omite se instancia
                un `VersionRegistry` por defecto que lee de
                ``storage/parametrization``.
            lineage_repository: STEP3C — opcional. Si se omite, se crea uno con fallback filesystem
                (legacy compatible). Para runtime con DocumentStore, inyectar desde composition root.
        """
        if parametrizacion is not None:
            self._parametrizacion = parametrizacion
        elif parametrization_version is not None:
            # H-04: cargar versión frozen desde storage
            from nexa_engine.modules.parametrizacion.shared.repositories.frozen_parametrization_adapter import (
                FrozenParametrizationAdapter,
            )
            self._parametrizacion = FrozenParametrizationAdapter.from_version(
                parametrization_version
            )
        else:
            self._parametrizacion = ParametrizationProvider.build()

        # WAVE 14 — versioning registry (lazy-friendly).
        from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry as _VR

        self._version_registry = version_registry or _VR()

        # STEP3C — lineage repository (agnóstico JSON/Cosmos si inyectado).
        self._lineage_repository = lineage_repository

    # ----------------------------------------------------------------------
    # WAVE 14 — simulation_id helper
    # ----------------------------------------------------------------------
    @staticmethod
    def _generate_simulation_id(solicitud) -> str:
        """Pick or generate a simulation_id for this request.

        Order of precedence:
            1. ``solicitud.metadata.simulation_id`` (explicit caller id).
            2. ``solicitud.panel.simulation_id`` (compat alias).
            3. uuid4 hex.
        """
        import uuid as _uuid

        metadata = getattr(solicitud, "metadata", None)
        if metadata is not None:
            sid = getattr(metadata, "simulation_id", None) or (
                metadata.get("simulation_id") if isinstance(metadata, dict) else None
            )
            if sid:
                return str(sid)
        panel = getattr(solicitud, "panel", None)
        sid = getattr(panel, "simulation_id", None) if panel else None
        if sid:
            return str(sid)
        return _uuid.uuid4().hex

    def calcular(self, solicitud: PricingRequest, with_lineage: bool = False):
        """
        Ejecuta el pipeline de 10 capas y produce el resultado completo del deal.

        Args:
            solicitud: PricingRequest construido por SimulationContextBuilder.
            with_lineage: si True, también construye y persiste el
                `LineageGraph` (WAVE 10). Retorna una tupla
                `(PricingResult, LineageGraph)`. Si False (default),
                retorna solo `PricingResult` — comportamiento idéntico
                pre-WAVE 10.

        Returns:
            PricingResult con P&G mensual (lista) y KPIs del deal.
            o (PricingResult, LineageGraph) cuando with_lineage=True.
        """
        # ── FASE 7: Activar AuditTracer para toda la simulación ──────────────
        _trace_id = getattr(solicitud.panel, "cliente", "unknown")
        if not with_lineage:
            with audit_context(enabled=True, simulation_id=_trace_id) as _tracer:
                return self._calcular_pipeline(solicitud, _tracer)

        # ── WAVE 10/14: Lineage emission path ───────────────────────────────
        from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter
        from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository
        from nexa_engine.modules.lineage.application.builder import (
            seed_lineage_from_request,
            seed_lineage_from_result,
        )

        # WAVE 14 — resolve simulation_id deterministically and stamp the
        # lineage graph with the live VersionMetadata.
        sim_id = self._generate_simulation_id(solicitud)
        version_metadata = self._version_registry.get_current()
        _engine_logger.info(
            "[LINEAGE] sim_id=%s engine=%s param=%s formula_set=%s",
            sim_id,
            version_metadata.engine_version,
            version_metadata.parametrization_version,
            version_metadata.formula_set,
        )

        lineage_emitter = JsonLineageEmitter(
            simulation_id=sim_id,
            version_metadata=version_metadata,
        )
        seed_lineage_from_request(lineage_emitter, solicitud)
        with audit_context(enabled=True, simulation_id=_trace_id) as _tracer:
            result = self._calcular_pipeline(solicitud, _tracer)
        seed_lineage_from_result(lineage_emitter, solicitud, result)
        graph = lineage_emitter.get_graph()

        # Propagate the simulation_id back into the result envelope so
        # callers (and the /calculate router) can return it to clients.
        try:
            setattr(result, "simulation_id", sim_id)
        except Exception:  # pragma: no cover — defensive
            pass

        try:
            # STEP3C — use injected lineage_repo (agnóstico), fallback to new instance (legacy)
            repo = self._lineage_repository or LineageSnapshotRepository()
            repo.save(graph)
        except Exception as _persist_exc:  # pragma: no cover - persistence best-effort
            _engine_logger.warning(
                "[LINEAGE] persistence failed sim_id=%s err=%s",
                sim_id,
                _persist_exc,
            )
        return result, graph

    def _calcular_pipeline(self, solicitud: PricingRequest, _tracer=None) -> PricingResult:
        """
        Pipeline de cálculo interno. Separado de `calcular()` para aislar
        el context manager del AuditTracer.

        TASK 3: Respeta cadenas_activas — soporta AI-only, SaaS, B-only, C-only, etc.
        """
        calculadores  = self._construir_calculadores(solicitud)

        # TASK 3: Validar que AL MENOS una cadena esté activa
        cadenas = solicitud.cadenas_activas
        if not (cadenas.cadena_a or cadenas.cadena_b or cadenas.cadena_c):
            raise ValueError("TASK_3: Al menos una cadena debe estar activa (A, B, o C)")

        # GAP-CADENA-A-FASE4 / hallazgo "wiring del margen": el ingreso de Cadena A usa
        # `panel.margen` (input del request) vía calcular_factor_margenes. El storage tiene
        # el margen por servicio (get_margen_minimo) que el Excel deriva de Rot/Ausent!B29:B34.
        # Validación NO destructiva: si difieren > tolerancia, se loguea warning. NO se cambia
        # el valor usado (sigue siendo el input) — la fuente del margen es decisión de negocio.
        # TODO(GAP-CADENA-A-FASE4): decidir si el ingreso debe usar get_margen_minimo(servicio)
        # en lugar de panel.margen (impacto medido: +9,63% en ingreso_cadena_a para Captura de Datos).
        if cadenas.cadena_a:
            try:
                _margen_storage = self._parametrizacion.get_margen_minimo(solicitud.panel.linea_negocio)
                if _margen_storage is not None and abs(_margen_storage - solicitud.panel.margen) > 0.001:
                    _engine_logger.warning(
                        "[MARGEN_WIRING] margen input (panel.margen=%.4f) difiere del margen de storage "
                        "por servicio '%s' (get_margen_minimo=%.4f, Δ=%.4f). Se usa el INPUT (sin cambio). "
                        "Ver GAP-CADENA-A-FASE4.",
                        solicitud.panel.margen, solicitud.panel.linea_negocio,
                        _margen_storage, _margen_storage - solicitud.panel.margen,
                    )
            except Exception as _mexc:
                # Servicio sin margen en storage u otro fallo de lookup → no bloquea el cálculo.
                _engine_logger.debug("[MARGEN_WIRING] lookup margen storage no disponible: %s", _mexc)

        # TASK 3: Calcular P&G solo si Cadena A está activa
        # Si no, usar lista vacía de perfiles y P&G mínimo
        if cadenas.cadena_a:
            pyg_contrato = calculadores["pyg"].calcular_contrato(solicitud.perfiles_cadena_a)
        else:
            # Cadena A NO activa: P&G desde cero (solo B y C si existen)
            pyg_contrato = calculadores["pyg"].calcular_contrato([])

        kpis_deal = calculadores["kpis"].calcular(pyg_contrato)

        # Pre-compute CTS facts (fine-grained Nomina/NoPayroll/CadenaB per month)
        # so CostToServeCalculator does not call core calculators directly.
        numero_meses_pyg = len(pyg_contrato)
        perfiles_cts = solicitud.perfiles_cadena_a if cadenas.cadena_a else []
        cts_facts = _build_cts_facts(
            perfiles_cts,
            numero_meses_pyg,
            calculadores["nomina"],
            calculadores["no_payroll"],
            calculadores["cadena_b"],
        )

        # TASK 3: CostToServe a través de calculator_motor CTS builder
        cost_to_serve = build_cost_to_serve_result(
            perfiles_cadena_a=solicitud.perfiles_cadena_a if cadenas.cadena_a else [],
            parametros_cadena_b=solicitud.cadena_b,
            parametros_cadena_c=solicitud.cadena_c,
            linea_negocio=solicitud.panel.linea_negocio,
            cts_facts=cts_facts,
            pyg_por_mes=pyg_contrato,
        )

        # Pre-compute VisionTarifas facts so VisionTarifasCalculator does not call core calculators.
        vt_facts = _build_vt_facts(
            escenarios=solicitud.escenarios or [],
            perfiles=solicitud.perfiles_cadena_a if cadenas.cadena_a else [],
            polizas_usuario=solicitud.polizas_usuario,
            numero_meses=numero_meses_pyg,
            calc_nomina=calculadores["nomina"],
            calc_no_payroll=calculadores["no_payroll"],
        )

        # TASK 3: VisionTarifasCalculator solo si Cadena A activa
        # Si no está activa, no generar vision_tarifas
        if cadenas.cadena_a:
            _engine_logger.info(
                "[ENGINE_TRACE] VisionTarifas input: perfiles=%d escenarios=%d",
                len(solicitud.perfiles_cadena_a),
                len(solicitud.escenarios) if solicitud.escenarios else 0,
            )
            _engine_logger.info(
                "[ENGINE_TRACE] payroll_a_avg=%s (from pyg mes 1 if available)",
                pyg_contrato[0].payroll_a if pyg_contrato else "N/A",
            )
            vision_tarifas = build_vision_tarifas_result(
                perfiles_cadena_a=solicitud.perfiles_cadena_a,
                parametros_cadena_b=solicitud.cadena_b,
                panel=solicitud.panel,
                pyg_por_mes=pyg_contrato,
                vt_facts=vt_facts,
                escenarios=solicitud.escenarios if solicitud.escenarios else None,
                polizas_usuario=solicitud.polizas_usuario,
            )
        else:
            vision_tarifas = None

        # PROBLEMA 2 (Opción A): se ELIMINA el overwrite post-cálculo de kpis/cts.
        # Cada calculator produce su valor final sin mutación posterior:
        #   - kpis_deal.* conserva la base nativa deal-wide (KPIsCalculator).
        #   - cost_to_serve.costo_total_acumulado conserva sum(m.costo_total) nativo.
        # Las cifras de escenario (Excel B19=Tarifas C72, H19=C40+C60) se leen
        # directamente desde `vision_tarifas` donde se consumen (Visión Imprimible
        # builder y serializer _configuracion_comercial), SIN pisar kpis/cts.

        # ── Vision P&G (structured frontend model) ─────────────────────
        # GAP-PYG-HIER-1/2/3/4: pass per-cadena calculators + perfiles so the builder
        # can emit sub-component detail rows (Excel rows 34-64) and "Contribución por
        # Puesto" (row 75). Perfiles empty when Cadena A inactive (matches pyg_contrato).
        _perfiles_vp = solicitud.perfiles_cadena_a if cadenas.cadena_a else []
        pyg_detail_rows = build_pyg_detail_read_model(
            pyg_por_mes        = pyg_contrato,
            perfiles_cadena_a  = _perfiles_vp,
            calc_nomina        = calculadores["nomina"],
            calc_no_payroll    = calculadores["no_payroll"],
            calc_cadena_b      = calculadores["cadena_b"],
            calc_cadena_c      = calculadores["cadena_c"],
        )
        vision_pyg = VisionPyGBuilder().construir(
            pyg_contrato,
            kpis_deal,
            perfiles_cadena_a = _perfiles_vp,
            fecha_inicio      = solicitud.panel.fecha_inicio,
            panel             = solicitud.panel,
            filas_detalle     = pyg_detail_rows,
        )

        # ── Secciones adicionales para Visión Imprimible ──────────────
        waterfall = _calcular_waterfall(pyg_contrato)
        reglas = _calcular_reglas_negocio(solicitud.panel, pyg_contrato, self._parametrizacion)
        riesgo_config = self._parametrizacion.get_riesgo_config()
        # BUSINESS_RULES_FIX_2: inyectar SMMLV desde HR vía IParametrizationProvider.get_smmlv()
        # (fuente canónica). El valor de business_rules.constantes_regulatorias.smmlv es
        # LEGACY_NON_CANONICAL y NO se usa en producción para este cálculo.
        evaluacion_riesgo = RiesgoCalculator(
            riesgo_config,
            smmlv=self._parametrizacion.get_smmlv(),
        ).calcular(
            panel             = solicitud.panel,
            kpis              = kpis_deal,
            pyg_por_mes       = pyg_contrato,
            perfiles_cadena_a = solicitud.perfiles_cadena_a,
            cadena_b          = solicitud.cadena_b,
            cadena_c          = solicitud.cadena_c,
        )

        # ── GAP-VIS-1: Visión Imprimible (composición) ──────────────────
        # TASK 3: VisionImprimibleBuilder puede recibir vision_tarifas=None si no hay Cadena A
        vision_imprimible = VisionImprimibleBuilder().construir(
            panel              = solicitud.panel,
            kpis               = kpis_deal,
            pyg_por_mes        = pyg_contrato,
            vision_tarifas     = vision_tarifas,  # Puede ser None si Cadena A no activa
            waterfall          = waterfall,
            reglas_negocio     = reglas,
            evaluacion_riesgo  = evaluacion_riesgo,
            escenarios         = solicitud.escenarios,
            cost_to_serve      = cost_to_serve,
            perfiles_cadena_a  = solicitud.perfiles_cadena_a,
        )

        resultado = PricingResult(
            kpis               = kpis_deal,
            pyg_por_mes        = pyg_contrato,
            panel              = solicitud.panel,
            cost_to_serve      = cost_to_serve,
            vision_tarifas     = vision_tarifas,
            waterfall          = waterfall,
            reglas_negocio     = reglas,
            evaluacion_riesgo  = evaluacion_riesgo,
            vision_pyg         = vision_pyg,
            # GAP-VIS-1
            vision_imprimible  = vision_imprimible,
        )

        resultado.datasets_vision = DatasetsVision(
            graficos=build_graficos_result(
                resultado=resultado,
                solicitud=solicitud,
                parametrizacion=self._parametrizacion,
            )
        )

        # ── FASE 5: Datasets de visión completos (obligatorio) ───────────────
        try:
            resultado.datasets_vision = VisionDatasetsBuilder(parametrizacion=self._parametrizacion).construir(solicitud, resultado)
        except Exception as _ds_exc:
            raise AuditIntegrityError(f"datasets_vision no construidos: {_ds_exc}") from _ds_exc
        if resultado.datasets_vision is None:
            raise AuditIntegrityError("datasets_vision no construidos")

        # ── FASE 7: Exportar AuditTrace al resultado (obligatorio) ───────────
        try:
            if _tracer is not None:
                resultado.audit_trace = export_audit_trace(_tracer)
        except Exception as _at_exc:
            raise AuditIntegrityError(f"audit_trace no exportado: {_at_exc}") from _at_exc
        if _tracer is not None and resultado.audit_trace is None:
            raise AuditIntegrityError("audit_trace no exportado")

        return resultado

    # ──────────────────────────────────────────────────────────────
    # Composition Root — wiring de dependencias del pipeline
    # ──────────────────────────────────────────────────────────────

    def _construir_calculadores(self, solicitud: PricingRequest) -> dict:
        """
        Instancia y conecta todos los calculadores del pipeline.

        Este método es el Composition Root del motor: decide qué calculador
        recibe qué dependencia. No debe contener lógica de negocio.

        Todos los calculadores que necesitan datos de parametrización reciben
        `self._parametrizacion` (IParametrizationProvider), no un archivo JSON.
        """
        p     = self._parametrizacion
        panel = solicitud.panel

        calc_nomina         = NominaCalculator(solicitud.parametros_nomina,
                                               solicitud.parametros_calculo)
        calc_no_payroll     = NoPayrollCalculator(solicitud.parametros_no_payroll)
        calc_cadena_b       = CadenaBCalculator(solicitud.cadena_b)
        calc_cadena_c       = CadenaCCalculator(solicitud.cadena_c, p)
        calc_costos_totales = CostosTotalesCalculator(
            calc_nomina, calc_no_payroll, calc_cadena_b, calc_cadena_c,
        )
        # FASE D / Gap C3: inyectar pólizas del usuario cuando las provea el deal
        calc_financiero = CostosFinancierosCalculator(
            panel, p, polizas_usuario=solicitud.polizas_usuario
        )
        calc_pyg        = PyGCalculator(panel, calc_costos_totales, calc_financiero, p)
        calc_kpis       = KPIsCalculator(panel, calc_financiero, p)

        return {
            "pyg":        calc_pyg,
            "kpis":       calc_kpis,
            "nomina":     calc_nomina,
            "no_payroll": calc_no_payroll,
            "cadena_b":   calc_cadena_b,
            "cadena_c":   calc_cadena_c,
        }
