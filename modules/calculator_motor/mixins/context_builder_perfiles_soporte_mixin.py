from __future__ import annotations
"""Private builder methods for SimulationContextBuilder.

Single mixin containing all private _construir_* and _calcular_* methods.
Extracted FASE Z.4.3 — behaviour unchanged; self.* resolves via Python MRO.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexa_engine.modules.calculator_motor.constants.global_constants import MES_INICIO_AJUSTE_ANUAL
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


def _build_amortizable_item(inversion: dict, factor: float, meses_contrato: int) -> dict:
    """Construye un ítem de CAPEX amortizable desde una inversión del request.

    precio_mensual = precio_total / meses_a_diferir.
    El ítem aporta solo durante los primeros min(meses_a_diferir, meses_contrato) meses,
    por eso meses=meses_diferir (no meses_contrato). Esto produce el salto no_payroll
    mes1 vs mes2+ cuando meses_a_diferir=1 (equipos de una sola cuota).
    """
    meses_diferir = int(inversion.get('meses_a_diferir',
                                      inversion.get('meses_amortizacion', 1)) or 1)
    if meses_diferir <= 0:
        meses_diferir = 1

    precio_mensual = inversion.get('precio_mensual')
    if precio_mensual is None:
        precio_mensual = float(inversion.get('precio', 0.0)) / meses_diferir
    else:
        precio_mensual = float(precio_mensual)
    return {
        "precio_mensual": precio_mensual,
        "cantidad": float(inversion.get('cantidad') or 0.0),
        "meses": min(meses_diferir, meses_contrato),
        "factor": factor,
    }



class ContextBuilderPerfilesSoporteMixin:
    """
    Mixin: ContextBuilderPerfilesSoporteMixin.

    @excel_lineage:
      version: V2-8
      sheet: Condiciones Cadena A
      cells: [E95/F95/G95 (FTE soporte per canal formula),
              E26/F26/G26 (cargos_adicionales per canal),
              C79/C80/C87 (roles_operativos[].incluye_en_deal=False exclusions),
              G78 (Director de Performance FTE override literal = 1.0)]
      concept: perfiles_soporte_fte_y_nomina
    @runtime_sources:
      - storage/parametrization/hr → IParametrizationProvider.get_reglas_staff()
        (roles_excluidos, roles_rotacion, roles_inicial, rol_jefe_comercial, etc.)
      - storage/parametrization/hr → IParametrizationProvider.get_ratios_staff(linea)
        (ratio denominadores per rol per linea de servicio)
      - storage/parametrization/hr → IParametrizationProvider.get_smmlv() (for SENA/Inclusión)
      - request/request.json → PerfilCadenaA[].fte_soporte_overrides
        (manual FTE override per rol — e.g., CCA!E95=9.5 override)
      - request/request.json → CondicionesCadenaAInput.staff_config (ratio overrides, activo flags)
      - request/request.json → CondicionesCadenaAInput.roles_operativos[].incluye_en_deal
    @confidence: HIGH
    @forbidden:
      - hardcoded_excel_values (ratios and salary come from HR parametrization; FTE from request)

    LINEAGE NOTE — fte_sum_contable accumulator (line ~194):
      This is a running sum of ALL regular support FTE (excludes SENA/Inclusión/Especialista).
      It feeds the Inclusión FTE numerator:
        fte_incl = (fte_agentes + fte_sum_contable + fte_sena) / ratio_inclusion
      Excel V2-8 · 'Condiciones Cadena A' · formula for Inclusión FTE:
        = (fte_agentes + Σsoporte_regulares + fte_sena) / ratio_inclusion
      @confidence: MEDIUM (accumulation rule confirmed by code; Excel cell for inclusion row UNCONFIRMED)
    """

    def _construir_perfiles_soporte(self, perfiles_base: list, linea: str,
                                     meses_contrato: int, pct_rotacion: float,
                                     complejidad_especialista: str = "ALTA",
                                     staff_config: list = None,
                                     detalles_recursos_humanos: list = None,
                                     roles_excluidos_deal: frozenset = None):
        """
        Genera automáticamente los perfiles de staff de soporte para cada perfil base.

        Las reglas de categorización de roles (excluidos, rotación, inicial,
        jefe comercial, SENA, Inclusión) se leen desde catalogos.json → reglas_staff,
        sin ningún valor hardcodeado en el código.

        Reglas de FTE por categoría de rol:
          - Normal      : FTE = fte_agentes / ratio
          - Rotación    : FTE = fte_agentes / ratio × pct_rotacion_mensual
          - Inicial     : FTE billing  = fte_agentes / ratio / meses_contrato
                          FTE contable = fte_agentes / ratio  (para SENA)
          - Jefe Comercial: Solo primer perfil base, ratio fijo = 1000
          - Aprendiz SENA : FTE = (fte_agentes + fte_soporte_contable) / ratio
                            Nómina cargada especial (sin pensión ni ARL)
          - Inclusión   : FTE = (fte_agentes + fte_soporte_contable + fte_sena) / ratio
        """
        reglas    = self._prov.get_reglas_staff()
        ratios    = self._prov.get_ratios_staff(linea)
        mes_ajuste = MES_INICIO_AJUSTE_ANUAL
        detalles_por_rol = {
            self._normalize_rol(item.cargo): item
            for item in (detalles_recursos_humanos or [])
        }

        def valores_recurso_humano(rol: str) -> tuple[float, float, bool]:
            detalle = detalles_por_rol.get(self._normalize_rol(rol))
            if detalle is None:
                salario = self._get_salario_rol_safe(
                    rol, f"rol_soporte en cadena_a linea={linea}"
                )
                return salario, self._prov.get_comision_pct_rol(rol), False
            salario = float(detalle.salario_base)
            comision_pct = float(detalle.comisiones) / salario if salario > 0 else 0.0
            return salario, comision_pct, True

        # Apply per-deal staff_config: override ratios and exclude inactive roles.
        # staff_config entries (StaffRolInput) come from CondicionesCadenaAInput.
        staff_excluidos_extra: set[str] = set()
        if staff_config:
            for sc in staff_config:
                rol_n = self._normalize_rol(sc.nombre)
                if not sc.activo:
                    staff_excluidos_extra.add(rol_n)
                elif sc.ratio_override is not None and sc.ratio_override > 0:
                    if rol_n in ratios:
                        ratios = dict(ratios)  # copy before mutating
                    else:
                        ratios = dict(ratios)
                    ratios[rol_n] = sc.ratio_override
        # EXCEL V2-8 CCA!C79/C80/C87: wire roles_operativos[].incluye_en_deal=False exclusions.
        # Names come from the request (not hardcoded here); normalized for comparison.
        if roles_excluidos_deal:
            for rol_name in roles_excluidos_deal:
                if rol_name:
                    staff_excluidos_extra.add(self._normalize_rol(rol_name))

        # NB: repository devuelve la clave canónica `roles_excluidos_ratios`
        # (auto-construida desde HR-Ratios cuando no hay sección reglas_staff
        # explícita). Se acepta también `roles_excluidos` por compatibilidad con
        # configuraciones legacy que usen ese alias.
        # "Agente Básico 1" es la self-row del agente en la tabla de ratios del Excel.
        _excl_raw         = list(reglas.get("roles_excluidos_ratios", []))
        _excl_raw         += list(reglas.get("roles_excluidos", []))
        _excl_raw         += ["Agente Básico 1"]   # self-row del agente en ratios
        excluidos         = {self._normalize_rol(x) for x in _excl_raw} | staff_excluidos_extra
        roles_rotacion    = {self._normalize_rol(x) for x in reglas.get("roles_rotacion", [])}
        roles_inicial     = {self._normalize_rol(x) for x in reglas.get("roles_inicial", [])}
        rol_jefe_comerc   = reglas.get("rol_jefe_comercial", "")
        rol_jefe_comerc_n = self._normalize_rol(rol_jefe_comerc) if rol_jefe_comerc else ""
        rol_sena          = reglas.get("rol_aprendiz_sena", "")
        rol_inclusion     = reglas.get("rol_inclusion", "")
        roles_especiales  = {
            self._normalize_rol(rol_sena) if rol_sena else "",
            self._normalize_rol(rol_inclusion) if rol_inclusion else "",
        }
        # Excel V2-6: Especialista de Proyectos tiene fórmula salarial y FTE especiales.
        # Conservar las versiones originales (para lookup de salario por rol con casing
        # explícito) y derivar el set normalizado para las comparaciones del loop.
        roles_fte_volumetrico_orig = list(reglas.get("roles_fte_volumetrico", []))
        roles_fte_volumetrico = {self._normalize_rol(x) for x in roles_fte_volumetrico_orig}
        # Total FTE across all agent profiles — needed for Especialista cost distribution.
        total_fte_agentes = sum(p.fte for p in perfiles_base)

        # Instanciar calculadores de roles especiales desde parametrización.
        # CargoClassifier determina exclusiones de SENA/Inclusión sin hardcoding.
        try:
            clasificacion_cargos = self._prov.get_clasificacion_cargos()
            complejidad_map      = self._prov.get_complejidad_especialista()
        except Exception:
            clasificacion_cargos = {}
            complejidad_map      = {"BAJA": 0.20, "MEDIA": 0.50, "ALTA": 0.50}

        classifier         = CargoClassifier(clasificacion_cargos)
        esp_calculator     = EspecialistaCalculator(complejidad_map)
        sena_calculator    = SENACalculator(classifier)
        incl_calculator    = InclusionCalculator()
        salario_fijo_calc  = SalarioFijoCalculator()

        perfiles: list[PerfilCadenaA] = []

        for idx_perfil, perfil_base in enumerate(perfiles_base):
            fte_base         = perfil_base.fte
            # EXCEL V2-8 · 'Condiciones Cadena A'!E95/F95/G95 · fórmula: =IF(C,((col9+col26+col30+col34)/col122)…)
            # Traducción: numerador del FTE de soporte regular = fte_agentes + cargos_adicionales (CCA!E26/F26/G26).
            # cargos_adicionales NO se suma a `fte_base` (que alimenta el reparto de Especialista y el salario de
            # agentes) para evitar doble conteo: solo entra al numerador de los roles de soporte regulares.
            fte_base_soporte = fte_base + perfil_base.cargos_adicionales
            # EXCEL V2-8 · 'Condiciones Cadena A'!E95 = 9.5 (literal manual, Supervisor SAC) ·
            # la fórmula daría (130+12)/20 = 7.1; el 9.5 está tecleado a mano (override real).
            # EXCEL V2-8 · 'Condiciones Cadena A'!G78 = 1.0 (literal manual, Director de Performance WhatsApp) ·
            # Override opt-in del FTE de soporte por rol, keyed por nombre normalizado.
            # Valor puede ser float (aplica a todos los canales) o dict {canal: float} (solo el canal indicado).
            # Default vacío = legacy. Reemplaza el FTE derivado del rol indicado ANTES de cascada
            # SENA/Inclusión (consistente con Excel, que lee el valor literal de la columna W).
            canal_actual = str(getattr(perfil_base, "canal", "") or "").strip().lower()
            overrides_norm: dict[str, float] = {}
            for k, v in (getattr(perfil_base, "fte_soporte_overrides", {}) or {}).items():
                rol_n = self._normalize_rol(k)
                if isinstance(v, dict):
                    # Per-channel override: check if current perfil canal matches any key.
                    for ch_key, ch_val in v.items():
                        if str(ch_key).strip().lower() == canal_actual:
                            overrides_norm[rol_n] = float(ch_val)
                            break
                else:
                    overrides_norm[rol_n] = float(v)
            fte_sum_contable = 0.0   # incluye TODOS los soporte regulares (para Inclusión)
            # dict {rol: fte_contable} para SENA — CargoClassifier aplica exclusiones dinámicamente
            fte_soporte_para_sena: dict[str, float] = {}

            soporte_bloque: list[PerfilCadenaA] = []

            for rol, ratio in ratios.items():
                if ratio <= 0 or rol in excluidos or rol in roles_especiales:
                    continue
                # Especialista volumétrico: se procesa al final con su propia fórmula
                if rol in roles_fte_volumetrico:
                    continue

                if rol == rol_jefe_comerc_n:
                    fte_contable = fte_base_soporte / ratio
                elif rol in roles_rotacion:
                    fte_contable = fte_base_soporte / ratio * pct_rotacion
                else:  # rol normal o inicial: numerador idéntico, difieren en el billing
                    fte_contable = fte_base_soporte / ratio

                # Override manual per-rol (EXCEL V2-8 CCA!E95=9.5). Reemplaza el FTE derivado del rol
                # indicado. Si el rol no está en el dict, conserva el valor de la fórmula (legacy).
                if rol in overrides_norm:
                    fte_contable = overrides_norm[rol]

                # roles_inicial: el billing se prorratea entre los meses del contrato; el resto factura
                # el FTE contable completo. El override aplica al FTE contable (base del prorrateo).
                if rol in roles_inicial:
                    fte_billing = fte_contable / meses_contrato
                else:
                    fte_billing = fte_contable

                fte_sum_contable += fte_contable
                # Registrar FTE por rol para que SENACalculator aplique exclusiones vía CargoClassifier
                fte_soporte_para_sena[rol] = fte_contable

                sal_base, comision_rol, usa_detalle = valores_recurso_humano(rol)
                # WAVE 3 (W3-4): Excel V2-7 declara `costo_empresa_override` para ciertos
                # roles (Director de cuentas). Si está presente, reemplaza al cargado
                # estándar (no se re-aplica la fórmula de carga social).
                override_cargado = None
                if not usa_detalle:
                    try:
                        override_cargado = self._prov.get_costo_empresa_override(rol)
                    except Exception:
                        override_cargado = None
                if override_cargado is not None:
                    sal_cargado = override_cargado
                else:
                    # nomina_cargada incluye carga social sobre comisiones (consistent con agente):
                    sal_cargado = self._nomina_service.calcular(sal_base, comision_rol)

                soporte_bloque.append(self._perfil_soporte(
                    rol, fte_billing, sal_base, sal_cargado, mes_ajuste,
                    canal=perfil_base.canal, comision_pct=comision_rol
                ))

            perfiles.extend(soporte_bloque)

            # Aprendiz SENA: FTE = (fte_agentes + Σsoporte_sin_excluidos) / ratio_sena
            # Exclusiones (Validador, Especialista, APRENDIZ, INCLUSION) determinadas por CargoClassifier.
            # Excel V2-6 W46 = SUM(W25:W44) / E46
            fte_sena = 0.0
            ratio_sena = ratios.get(self._normalize_rol(rol_sena), 0)
            if ratio_sena > 0:
                fte_sena = sena_calculator.calcular_fte(fte_base, fte_soporte_para_sena, ratio_sena)
                sal_base_sena, _, _ = valores_recurso_humano(rol_sena)
                sal_cargado_sena = self._nomina_service.calcular_aprendiz(sal_base_sena)
                perfiles.append(self._perfil_soporte(
                    rol_sena, fte_sena, sal_base_sena, sal_cargado_sena,
                    mes_ajuste, canal=perfil_base.canal
                ))

            # Especialista de Proyectos: costo total = sal_cargado × 3 × complejidad / meses_contrato,
            # distribuido proporcionalmente por fte_base / total_fte_agentes entre perfiles.
            # Ratio en hr.json/staff_config no afecta el resultado (se cancela), así que se computa
            # usando total_fte_agentes como denominador de la distribución.
            for rol_volum in roles_fte_volumetrico_orig:
                rol_volum_norm = self._normalize_rol(rol_volum)
                # Skip if excluded by staff_config
                if rol_volum_norm in excluidos:
                    continue
                if total_fte_agentes <= 0:
                    continue
                sal_base_volum, _, usa_detalle = valores_recurso_humano(rol_volum)
                override_esp = None
                if not usa_detalle:
                    try:
                        override_esp = self._prov.get_costo_empresa_override(rol_volum)
                    except Exception:
                        pass
                sal_cargado_base = override_esp if override_esp is not None else self._nomina_service.calcular(sal_base_volum, 0.0)
                # total operation cost for Especialista, then split by this profile's share
                complejidad_factor = float(esp_calculator.get_complejidad_multiplicador(complejidad_especialista))
                costo_total_esp = sal_cargado_base * 3.0 * complejidad_factor / meses_contrato
                fte_volum = fte_base / total_fte_agentes
                # sal_cargado stored per-unit = costo_total_esp so cost = fte_volum × costo_total_esp
                perfiles.append(self._perfil_soporte(
                    rol_volum, fte_volum, sal_base_volum, costo_total_esp,
                    mes_ajuste, canal=perfil_base.canal
                ))

            # Inclusión: FTE = (fte_agentes + fte_soporte_total + fte_sena) / ratio_inclusion
            # Incluye TODO el soporte sin exclusiones adicionales (reglas V2-6).
            rol_inclusion_norm = self._normalize_rol(rol_inclusion)
            ratio_incl = ratios.get(rol_inclusion_norm, 0)
            if ratio_incl > 0:
                fte_incl = incl_calculator.calcular_fte(
                    fte_base, fte_sum_contable, fte_sena, ratio_incl
                )
                sal_base_incl, _, _ = valores_recurso_humano(rol_inclusion)
                sal_cargado_incl = self._nomina_service.calcular_aprendiz(sal_base_incl)
                perfiles.append(self._perfil_soporte(
                    rol_inclusion, fte_incl, sal_base_incl, sal_cargado_incl,
                    mes_ajuste, canal=perfil_base.canal
                ))

        # Salario Fijo: costo promedio mensual por FTE en el horizonte del contrato.
        # Fórmula: Σ(sal_cargado_i × fte_i) / meses_contrato / total_fte
        # Se calcula sobre TODOS los perfiles generados (agentes base + soporte).
        # Referencia: Vision Cost To Serve — métrica de salida de nómina.
        rol_salario_fijo = reglas.get("rol_salario_fijo", "")
        if rol_salario_fijo:
            # H-01 FIX: Reconstruir lista SOLO con agentes (excluir soporte)
            # Salario Fijo Excel spec: solo agentes inbound + outbound
            perfiles_para_fijo = [
                (p.salario_cargado, p.fte)
                for p in perfiles
                if p.fte > 0 and p.salario_cargado > 0 and not p.es_soporte  # ✅ Filtrar support
            ]
            # Agregar perfiles base (agentes) — estos NO son soporte por definición
            for pb in perfiles_base:
                if pb.fte > 0 and pb.salario_cargado > 0:
                    perfiles_para_fijo.append((pb.salario_cargado, pb.fte))

            sal_fijo = salario_fijo_calc.calcular(perfiles_para_fijo, meses_contrato)
            if sal_fijo > 0:
                perfiles.append(self._perfil_soporte(
                    rol_salario_fijo, 1.0, sal_fijo, sal_fijo,
                    mes_ajuste, canal=perfiles_base[0].canal if perfiles_base else ""
                ))

        return perfiles

    def _perfil_soporte(self, rol: str, fte: float, sal_base: float,
                         sal_cargado: float, mes_ajuste: int,
                         canal: str = "", comision_pct: float = 0.0) -> PerfilCadenaA:
        """Construye un perfil de soporte etiquetado con el canal del perfil agente padre.

        Args:
            comision_pct: Si > 0, el rol percibe comisión (consistente con Excel V2-4
                          Director cuentas 5%, GTR 10%, etc.). Se propaga al
                          NominaCalculator que sumará la comisión al payroll.

        El tipo_carga se resuelve desde HR-rol_a_tipo_carga (catálogo de storage).
        """
        tipo_carga = self._prov.get_tipo_carga_rol(rol)
        return PerfilCadenaA(
            nombre            = f"Soporte — {rol}",
            modalidad         = "Staff",
            canal             = canal,
            fte               = fte,
            pct_presencia     = 0.0,
            salario_base      = sal_base,
            salario_cargado   = sal_cargado,
            comision_pct      = comision_pct,
            dias_cap_inicial  = 0,
            dias_cap_rotacion = 0,
            incluye_examenes  = False,
            incluye_seguridad = False,
            es_soporte        = True,
            tipo_carga        = tipo_carga,
        )

    # ──────────────────────────────────────────────────────────────
    # REFACTOR costos_operativos: Cálculos Derivados
    # ──────────────────────────────────────────────────────────────

    def _calcular_opex_ti_total(self, perfiles_a: List[PerfilCadenaAInput]) -> float:
        """
        Calcula OPEX fijo total promedio por estación desde opex_fijo.items[].

        REGLA: opex_ti_por_estacion NO es concepto atómico.
        Es Σ(todos los costos opex_fijo) / estaciones presenciales.
        El Excel incluye TODOS los ítems de opex_fijo.items en "OPEX Fijo"
        sin distinguir entre TI y no-TI.
        """
        total_opex_ti = 0.0
        total_estaciones = 0.0

        for perfil in perfiles_a:
            if not hasattr(perfil, 'opex_fijo') or not perfil.opex_fijo:
                continue

            items = perfil.opex_fijo.get('items', []) if isinstance(perfil.opex_fijo, dict) else []
            if not items:
                continue

            estaciones_perfil = perfil.fte * getattr(perfil, 'pct_presencia', 1.0)
            if estaciones_perfil <= 0:
                continue

            total_estaciones += estaciones_perfil

            for item in items:
                costo = float(item.get('costo', 0.0))
                cantidad = float(item.get('cantidad', 1.0))
                costo_totalizado = item.get('costo_totalizado', False)

                if costo_totalizado:
                    opex_unitario = costo / estaciones_perfil
                else:
                    opex_unitario = (costo * cantidad) / estaciones_perfil

                total_opex_ti += opex_unitario * estaciones_perfil

        return total_opex_ti / total_estaciones if total_estaciones > 0 else 0.0

    def _calcular_inversiones_amortizables(
        self,
        perfiles_a: List[PerfilCadenaAInput],
        factor: float,
        meses_contrato: int,
    ) -> List[dict]:
        """
        Construye los ítems de CAPEX amortizable desde inversiones[] (Excel V2-8).

        Cada ítem lleva: precio (total), meses_a_diferir (plazo), cantidad.
        cuota(mes) = precio_mensual × cantidad × factor, solo para mes ≤ meses_diferir.
        Ítems con meses_a_diferir=1 aportan únicamente en el mes 1 (costos únicos de arranque).
        Las cuotas de todos los perfiles se acumulan.
        """
        items: List[dict] = []
        for perfil in perfiles_a:
            inversiones = getattr(perfil, 'inversiones', None)
            if not isinstance(inversiones, list):
                continue
            for inversion in inversiones:
                items.append(_build_amortizable_item(inversion, factor, meses_contrato))
        return items

    @staticmethod
    def _calcular_opex_fijo_mensual_perfil(perfil) -> float:
        """
        Compute per-channel monthly OPEX TI total from this profile's opex_fijo.items.

        Used to populate PerfilCadenaA.opex_fijo_mensual for channel-specific nop
        decomposition in VisionTarifasCalculator.
        """
        opex_fijo = getattr(perfil, 'opex_fijo', None)
        if not opex_fijo:
            return 0.0
        items = opex_fijo.get('items', []) if isinstance(opex_fijo, dict) else []
        total = 0.0
        estaciones = float(perfil.fte) * float(getattr(perfil, 'pct_presencia', 1.0))
        for item in items:
            costo = float(item.get('costo', 0.0))
            cantidad = float(item.get('cantidad', 1.0))
            costo_totalizado = item.get('costo_totalizado', False)
            if costo_totalizado:
                total += costo
            else:
                total += costo * cantidad
        return total

    @staticmethod
    def _calcular_inversiones_amortizables_perfil(perfil, factor: float, meses_contrato: int) -> list:
        """
        Build per-channel CAPEX amortizable items from this profile's inversiones.

        Same format as ParametrosNoPayroll.inversiones_amortizables but scoped to
        a single channel profile. Used by VisionTarifasCalculator for channel-specific
        CAPEX decomposition (Oracle VT C42 = Voz-only nop).
        """
        inversiones = getattr(perfil, 'inversiones', None)
        if not isinstance(inversiones, list):
            return []
        return [_build_amortizable_item(inv, factor, meses_contrato) for inv in inversiones]

    # ──────────────────────────────────────────────────────────────
    # Parámetros de nómina
    # ──────────────────────────────────────────────────────────────


__all__ = ["ContextBuilderCadenaAMixin"]

__all__ = ["ContextBuilderPerfilesMixin"]

__all__ = ["ContextBuilderPerfilesSoporteMixin"]
