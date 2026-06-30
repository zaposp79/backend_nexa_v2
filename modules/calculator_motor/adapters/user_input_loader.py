"""User-input adapter owned by calculator_motor.

Carga un ``UserInput`` desde archivo o dict, convierte request shapes soportados
al formato del motor y rechaza campos que pertenezcan a datos maestros.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from nexa_engine.modules.calculator_motor.adapters.entry_data_adapter import NewEntryDataAdapter
from nexa_engine.modules.calculator_motor.validation.input_normalizer import InputNormalizer
from nexa_engine.modules.calculator_motor.adapters.volume_resolution import VolumeResolutionService
from nexa_engine.modules.calculator_motor.dto.normalized_input import NormalizationMode
from nexa_engine.modules.shared.exceptions import DomainError
from nexa_engine.modules.calculator_motor.dto.user_inputs import (
    CanalCadenaBInput,
    CanalCadenaCInput,
    CadenasActivasInput,
    CondicionesCadenaAInput,
    CondicionesCadenaBInput,
    CondicionesCadenaCInput,
    DispositivoSMInput,
    EquipoHITLItemInput,
    EscenarioComercialInput,
    ItemOpexConsumoInput,
    MiembroEquipoSMInput,
    MiembroEquipoTransversalInput,
    PanelDeControlInput,
    PerfilCadenaAInput,
    PolizaInput,
    UserInput,
)

# Campos que NO deben aparecer en el JSON del usuario — son datos maestros puros.
# Nota: tasa_ica, tasa_gmf, tasa_mensual_financ, pct_rotacion, pct_ausentismo
# SÍ pueden aparecer en panel_de_control como overrides opcionales del usuario.
_CAMPOS_MAESTROS_PROHIBIDOS = {
    "horas_formacion_mensual",
    "parametros_nomina", "parametros_no_payroll", "parametros_calculo",
}

# Campos legítimos del contrato entry_data (Phase 5.5: Contract Enforcement)
# Formato legacy (test_cases)
_CAMPOS_ENTRY_DATA_VALIDOS = {
    "panel_de_control",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
    "parametros_nomina",
    "reglas_negocio",
    "contingencia_operativa",
    "escenarios_comerciales",
    # FASE D / Gap C3: polizas preservadas por el normalizer
    "polizas",
}

# Campos válidos del formato entry_data (datos_operativos, polizas, etc.)
_CAMPOS_ENTRY_DATA_NUEVO_VALIDOS = {
    "datos_operativos",
    "polizas",
    "reglas_negocio",
    "volumetria",
    "escenarios_comerciales",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
}


def _aplicar_escenarios_a_perfiles(
    condiciones_a: dict,
    escenarios: list,
) -> dict:
    """
    FASE C — Gap C4: Enriquecer perfiles de cadena_a con modelo_cobro y pct_fijo
    según los escenarios_comerciales.

    Matching por (modalidad, canal) — case-insensitive.
    Si un perfil no tiene escenario correspondiente, conserva sus defaults.

    Mapeo:
      escenario.modelo_cobro              → perfil.modelo_cobro
      escenario.proporcion_componente_fijo → perfil.pct_fijo
    """
    # Indexar escenarios por (modalidad_lower, canal_lower)
    idx: dict = {}
    for esc in escenarios:
        mod  = str(esc.get("modalidad", "")).lower().strip()
        canal = str(esc.get("canal", "")).lower().strip()
        idx[(mod, canal)] = esc

    perfiles_enriquecidos = []
    for perfil in condiciones_a.get("perfiles", []):
        clave = (
            str(perfil.get("modalidad", "")).lower().strip(),
            str(perfil.get("canal", "")).lower().strip(),
        )
        esc = idx.get(clave)
        if esc is not None:
            modelo_cobro = str(esc.get("modelo_cobro", perfil.get("modelo_cobro", "Fijo FTE")))
            pct_fijo     = float(esc.get("proporcion_componente_fijo",
                                         perfil.get("pct_fijo", 1.0)))
            perfil = {**perfil, "modelo_cobro": modelo_cobro, "pct_fijo": pct_fijo}
        perfiles_enriquecidos.append(perfil)

    return {**condiciones_a, "perfiles": perfiles_enriquecidos}


from nexa_engine.modules.calculator_motor.mixins.user_input_builders_panel import UserInputBuildersPanelMixin
from nexa_engine.modules.calculator_motor.mixins.user_input_builders_cadena_a import UserInputBuildersCadenaAMixin
from nexa_engine.modules.calculator_motor.mixins.user_input_builders_cadena_b import UserInputBuildersCadenaBMixin
from nexa_engine.modules.calculator_motor.mixins.user_input_builders_cadena_c import UserInputBuildersCadenaCMixin
from nexa_engine.modules.calculator_motor.mixins.user_input_validators import UserInputValidatorsMixin


class UserInputLoader(
    UserInputBuildersPanelMixin,
    UserInputBuildersCadenaAMixin,
    UserInputBuildersCadenaBMixin,
    UserInputBuildersCadenaCMixin,
    UserInputValidatorsMixin,
):
    """Carga y valida un UserInput desde JSON.

    Builder methods organized in mixins (FASE Z.2):
      UserInputBuildersPanelMixin    — _panel, _escenarios
      UserInputBuildersCadenaAMixin  — _cadena_a, _staff_rol, _perfil_a
      UserInputBuildersCadenaBMixin  — _cadena_b, _canal_b, _opex_consumo, etc.
      UserInputBuildersCadenaCMixin  — _cadena_c, _equipo_hitl_item, _canal_c
      UserInputValidatorsMixin       — _requerir*, _validar_no_contiene_maestros
    """

    def __init__(self) -> None:
        # FASE 4 — exponer para SimulationSnapshot
        self._last_normalization_log: dict | None = None
        self._last_raw_input: dict | None = None
        self._last_normalized_input: dict | None = None

    @property
    def last_normalization_log(self) -> dict | None:
        """NormalizationLog del último cargar_desde_dict() con formato oficial."""
        return self._last_normalization_log

    @property
    def last_raw_input(self) -> dict | None:
        """Input original (raw) del último cargar_desde_dict()."""
        return self._last_raw_input

    @property
    def last_normalized_input(self) -> dict | None:
        """Input normalizado (post-InputNormalizer) del último cargar_desde_dict()."""
        return self._last_normalized_input

    def cargar(self, ruta: str | Path) -> UserInput:
        data = self._leer(ruta)
        self._validar_no_contiene_maestros(data)
        return self._construir(data)

    def cargar_desde_dict(self, data: Dict) -> UserInput:
        """Construye un UserInput directamente desde un dict (sin lectura de archivo).

        Útil para el endpoint REST POST /simulation/calculate que recibe
        el user_input como body JSON.

        Soporta dos formatos:
        - Antiguo (legacy): panel_de_control, condiciones_cadena_a/b/c
        - Nuevo (entry_data): datos_operativos, polizas, reglas_negocio, etc.

        Args:
            data: Dict con estructura test_cases o entry_data.

        Returns:
            UserInput construido y validado.

        Raises:
            ValueError: si el dict contiene campos de datos maestros prohibidos,
                        o si falta la sección 'panel_de_control'.
            KeyError:   si falta un campo requerido dentro de una sección.
        """
        # FASE 4 — capturar input original para SimulationSnapshot
        import copy
        self._last_raw_input = copy.deepcopy(data)

        # Detectar y normalizar formato entry_data si es necesario
        if "datos_operativos" in data and "panel_de_control" not in data:
            # FASE 2 — InputNormalizer: validación y normalización de campos
            # antes de la transformación estructural (_normalizar_entry_data_format).
            # El normalizer valida requeridos, aplana capacitacion{} de perfiles,
            # y registra todos los defaults aplicados para auditoría.
            normalizer = InputNormalizer()
            normalized = normalizer.normalize(data, mode=NormalizationMode.STRICT)
            # FASE 4 — exponer log y normalized data para SimulationSnapshot
            self._last_normalization_log = {
                "mode":             normalized.log.mode.value,
                "defaults_applied": [
                    {"field_path": d.field_path, "value": d.value, "reason": d.reason}
                    for d in normalized.log.defaults_applied
                ],
                "warnings": [
                    {"field_path": w.field_path, "message": w.message}
                    for w in normalized.log.warnings
                ],
                "errors": [
                    {"field_path": e.field_path, "message": e.message}
                    for e in normalized.log.errors
                ],
            }
            self._last_normalized_input = copy.deepcopy(normalized.data)
            data = self._normalizar_entry_data_format(normalized.data)
        else:
            # Formato legacy — no hay NormalizationLog
            self._last_normalization_log = {"mode": "legacy", "defaults_applied": [], "warnings": [], "errors": []}
            self._last_normalized_input = copy.deepcopy(data)

        # FASE B: Adaptar estructura de cadena_b / cadena_c si están en formato entry_data
        # Esto resuelve el mismatch estructural documentado en docs/audit/fase_adapter_formula_mapping.md
        # (gaps C1 y C2 — condiciones_cadena_b y cadena_c con fields distintos al formato interno)
        adapter = NewEntryDataAdapter()
        data = adapter.adaptar(data)

        self._validar_no_contiene_maestros(data)
        self._validar_unicidad_canales_por_seccion(data)
        return self._construir(data)

    def _construir(self, data: Dict) -> UserInput:
        """Construye UserInput desde un dict ya validado."""
        return UserInput(
            panel    = self._panel(data["panel_de_control"]),
            cadena_a = self._cadena_a(data.get("condiciones_cadena_a", {})),
            cadena_b = self._cadena_b(data.get("condiciones_cadena_b", {})),
            cadena_c = self._cadena_c(data.get("condiciones_cadena_c", {})),
            polizas  = self._polizas(data["polizas"]) if "polizas" in data else None,
        )

    def _polizas(self, raw: list | None) -> list | None:
        """Parsea la lista de pólizas del usuario (FASE D / Gap C3)."""
        if raw is None:
            return None
        if raw == []:
            return []
        result = []
        for p in raw:
            cadenas = p.get("cadenas", {}) or {}
            result.append(PolizaInput(
                nombre                      = str(p.get("nombre", "")),
                activa                      = bool(p.get("activa", False)),
                pct_poliza                  = float(p.get("pct_poliza", 0) or 0),
                pct_atribuible              = float(p.get("pct_atribuible", 0) or 0),
                aplica_extension            = bool(p.get("aplica_extension", False)),
                meses_extension             = int(p["meses_extension"]) if p.get("meses_extension") is not None else None,
                aplica_a                    = bool(cadenas.get("cadena_a", True)),
                aplica_b                    = bool(cadenas.get("cadena_b", False)),
                aplica_c                    = bool(cadenas.get("cadena_c", False)),
                per_canal                   = bool(p.get("per_canal", False)),
                is_comision_administracion  = bool(p.get("is_comision_administracion", False)),
            ))
        return result

    @staticmethod
    def _normalizar_entry_data_format(data: Dict) -> Dict:
        """Convierte formato entry_data al formato interno (panel_de_control, cadena_a/b/c).

        Prioridades:
          1. condiciones_cadena_a/b/c explícitas en el JSON → se usan directamente.
          2. Si no existen, se derivan desde volumetria.inbound/outbound como fallback.

        Mapeo principal:
          datos_operativos  → panel_de_control
          reglas_negocio    → margen, op_cont, markup
          volumetria        → tasa_mensual_financ + fallback cadenas
        """
        ops        = data.get("datos_operativos", {})
        reg        = data.get("reglas_negocio", {})
        volumetria = data.get("volumetria", {})
        inbound    = volumetria.get("inbound", {})
        outbound   = volumetria.get("outbound", {})
        volume_service = VolumeResolutionService(volumetria)
        cadenas_activas = volume_service.cadenas_activas

        # ── 1. panel_de_control ─────────────────────────────────────────────
        indexacion    = volumetria.get("indexacion", {})
        comp_humano   = indexacion.get("componente_humano", "IPC")
        comp_tecno    = indexacion.get("componente_tecnologico", "IPC")

        # FASE C — Gap C5: com_cont viene de reglas_negocio.contingencia_comercial.valor
        com_cont_val = float(
            reg.get("contingencia_comercial", {}).get("valor", 0.0) or 0.0
        )

        panel_de_control = {
            "cliente":             ops.get("cliente", ""),
            "tipo_cliente":        ops.get("tipo_cliente", ""),
            "linea_negocio":       ops.get("servicio", ""),
            # FASE 1 — H2/H6/H8/H9: Campos requeridos. No se permiten
            # fallbacks silenciosos para valores que afectan cálculos financieros.
            "ciudad":              UserInputLoader._requerir(ops, "ciudad", "datos_operativos"),
            "sede":                ops.get("sede", ""),
            "fecha_inicio":        UserInputLoader._requerir(ops, "fecha_inicio", "datos_operativos"),
            "meses_contrato":      UserInputLoader._requerir_int(ops, "duracion_meses", "datos_operativos"),
            "margen":              UserInputLoader._requerir_float(reg, "margen_objetivo", "reglas_negocio"),
            "op_cont":             reg.get("contingencia_operativa", {}).get("valor", 0.05),
            "com_cont":            com_cont_val,
            "markup":              reg.get("markup", {}).get("valor", 0.0),
            "descuento":           0.0,
            "tasa_ica":            ops.get("tasa_ica", 0.0),
            "tasa_gmf":            ops.get("tasa_gmf", 0.0),
            "activa_financiacion": ops.get("cons_costo_de_financiacion", True),
            "periodo_pago_dias":   90,
            "tasa_mensual_financ": indexacion.get("tasa_interes_mensual", 0.0),
            "pct_rotacion":        ops.get("pct_rotacion", 0.0),
            "pct_ausentismo":      ops.get("pct_ausentismo", 0.0),
            # FASE C — Gap P1: componente de indexación desde entry_data
            "componente_indexacion_humano":      comp_humano,
            "componente_indexacion_tecnologico": comp_tecno,
            # FASE 3 — horas_formacion_mensual: viene de datos_operativos.horas_formacion_mes
            "horas_formacion_mensual": int(ops.get("horas_formacion_mes", 0) or 0),
            # REFACTOR costos_operativos: tarifa_diaria_capacitacion viene de datos_operativos
            "tarifa_diaria_capacitacion": float(ops.get("tarifa_diaria_capacitacion", 0.0) or 0.0),
            "tarifa_crucero":             float(ops.get("crucero", 0.0) or 0.0),
            "pct_examen_anual":           float(ops["pct_examen_anual"]) if ops.get("pct_examen_anual") is not None else None,
            # FASE 3 — indexacion: frecuencia y mes_aplicacion desde volumetria.
            # `mes_aplicacion` del NUEVO format es MES DEL CALENDARIO (ej: 6=junio);
            # se asigna a `mes_ajuste_indexacion` (no a `indexacion_mes_aplicacion` que
            # es CONTRACT month en formato legacy). _construir_parametros_nomina lo
            # convierte a contrato vía _calendario_a_contrato.
            "indexacion_frecuencia":        indexacion.get("frecuencia", "Anual"),
            "mes_ajuste_indexacion":        int(indexacion["mes_aplicacion"]) if indexacion.get("mes_aplicacion") is not None else None,
            "imprevistos":                  float(reg.get("imprevistos", 0.0) or 0.0),
            "cadenas_activas": {
                "cadena_a": cadenas_activas.cadena_a,
                "cadena_b": cadenas_activas.cadena_b,
                "cadena_c": cadenas_activas.cadena_c,
            },
            "escenarios_comerciales": data.get("escenarios_comerciales", []),
        }

        # ── 2. condiciones_cadena_a ─────────────────────────────────────────
        # Usar explícitas si el usuario las incluyó; si no, derivar de volumetria
        if "condiciones_cadena_a" in data:
            condiciones_a = data["condiciones_cadena_a"]
            # Formato canónico: condiciones_cadena_a = { "perfiles": [...], ... }
            # Formato legacy:   condiciones_cadena_a = { "condiciones_cadena_a": { "perfiles": [...], ... } }
            # Guard: detect accidental double-nesting not caught by InputNormalizer
            # (e.g. legacy/format-legacy path that skips InputNormalizer)
            # request/request.json fue normalizado al formato canónico (2026-06-06).
            # Compatibilidad pendiente: mantener este guard solo mientras existan
            # consumidores reales del formato legado anidado.
            if "condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a:
                inner = condiciones_a["condiciones_cadena_a"]
                if isinstance(inner, dict) and "perfiles" in inner:
                    import logging as _log
                    _log.getLogger("nexa_engine.loader").warning(
                        "[NORMALIZER] condiciones_cadena_a double-nesting detected and unwrapped"
                    )
                    condiciones_a = inner
            condiciones_a = UserInputLoader._aplicar_volumenes_a_perfiles(
                condiciones_a, volume_service
            )
        else:
            perfiles = []
            for canal_vol in inbound.get("canales", []):
                canal_name = canal_vol.get("canal", "")
                fte = canal_vol.get("cadena_a", {}).get("valor", 0)
                if fte > 0:
                    salario_base_inbound = ops.get("salario_base_default")
                    if salario_base_inbound is None:
                        raise DomainError(
                            f"Perfil volumétrico Inbound '{canal_name}' requiere "
                            "'salario_base_default' en datos_operativos — "
                            "no se permite valor hardcodeado"
                        )
                    perfiles.append({
                        "nombre":        f"Inbound {canal_name}",
                        "modalidad":     "Inbound",
                        "canal":         canal_name,
                        "fte":           fte,
                        "pct_presencia": 1.0,
                        "salario_base":  float(salario_base_inbound),
                        "comision_pct":  0.0,
                        "vol_cadena_a_mensual": volume_service.volumen("Inbound", canal_name, "cadena_a"),
                    })
            for canal_vol in outbound.get("canales", []):
                canal_name = canal_vol.get("canal", "")
                fte = canal_vol.get("cadena_a", {}).get("valor", 0)
                if fte > 0:
                    salario_base_outbound = ops.get("salario_base_default")
                    if salario_base_outbound is None:
                        raise DomainError(
                            f"Perfil volumétrico Outbound '{canal_name}' requiere "
                            "'salario_base_default' en datos_operativos — "
                            "no se permite valor hardcodeado"
                        )
                    perfiles.append({
                        "nombre":        f"Outbound {canal_name}",
                        "modalidad":     "Outbound",
                        "canal":         canal_name,
                        "fte":           fte,
                        "pct_presencia": 1.0,
                        "salario_base":  float(salario_base_outbound),
                        "comision_pct":  0.0,
                        "vol_cadena_a_mensual": volume_service.volumen("Outbound", canal_name, "cadena_a"),
                    })
            condiciones_a = {"perfiles": perfiles}

        # ── 3. condiciones_cadena_b ─────────────────────────────────────────
        if "condiciones_cadena_b" in data:
            condiciones_b = data["condiciones_cadena_b"]
            # Formato canónico: condiciones_cadena_b = { "opex": {...}, "hitl": {...}, ... }
            # Formato legacy:   condiciones_cadena_b = { "condiciones_cadena_b": { "opex": {...}, ... } }
            # Guard: detect accidental double-nesting (same pattern as cadena_a above).
            # El adapter _es_formato_entry_data_b ve el dict exterior {condiciones_cadena_b}
            # que no tiene las claves internas esperadas → omite traducción → costo_b=0 (D-1 bug).
            # Unwrap here so the adapter receives the actual payload.
            # request/request.json fue normalizado al formato canónico (2026-06-06).
            # Compatibilidad pendiente: mantener este guard solo mientras existan
            # consumidores reales del formato legado anidado.
            if (
                isinstance(condiciones_b, dict)
                and "condiciones_cadena_b" in condiciones_b
                and "canales" not in condiciones_b
                and "opex" not in condiciones_b
            ):
                inner = condiciones_b["condiciones_cadena_b"]
                if isinstance(inner, dict):
                    import logging as _log
                    _log.getLogger("nexa_engine.loader").warning(
                        "[NORMALIZER] condiciones_cadena_b double-nesting detected and unwrapped"
                    )
                    condiciones_b = inner
            condiciones_b = UserInputLoader._inyectar_volumenes_cadena_b(
                condiciones_b, volume_service
            )
        else:
            canales_b = []
            for canal_vol in inbound.get("canales", []):
                canal_name = canal_vol.get("canal", "")
                volumen    = canal_vol.get("cadena_b", {}).get("valor", 0)
                if volumen > 0:
                    canales_b.append({
                        "nombre":          f"{canal_name} Inbound",
                        "canal":           canal_name,
                        "modalidad":       "Inbound",
                        "precio_unitario": 50.0,
                        "volumen_mensual": volumen,
                    })
            condiciones_b = {"canales": canales_b}

        # ── 4. condiciones_cadena_c ─────────────────────────────────────────
        condiciones_c = data.get("condiciones_cadena_c", {"canales": []})
        condiciones_c = UserInputLoader._inyectar_volumenes_cadena_c(
            condiciones_c, volume_service
        )

        # ── 5. FASE C — Gap C4: escenarios_comerciales → modelo_cobro en perfiles ──
        # Enriquecer los perfiles de cadena_a con modelo_cobro y pct_fijo
        # según el escenario que coincida por (modalidad, canal).
        escenarios = data.get("escenarios_comerciales", [])
        if escenarios and "perfiles" in condiciones_a:
            condiciones_a = _aplicar_escenarios_a_perfiles(
                condiciones_a, escenarios
            )

        return {
            "panel_de_control":     panel_de_control,
            "condiciones_cadena_a": condiciones_a,
            "condiciones_cadena_b": condiciones_b,
            "condiciones_cadena_c": condiciones_c,
            # FASE D / Gap C3: preservar polizas del usuario a través de la normalización
            "polizas":              data["polizas"] if "polizas" in data else None,
        }


    def cargar_validaciones(self, ruta: str | Path) -> Dict[str, float]:
        data = self._leer(ruta)
        raw = data.get("validaciones", {})
        return {k: v for k, v in raw.items() if not k.startswith("_")}

    @staticmethod
    def _aplicar_volumenes_a_perfiles(condiciones_a: Dict, volume_service: VolumeResolutionService) -> Dict:
        perfiles = []
        for perfil in condiciones_a.get("perfiles", []) or []:
            modalidad = str(perfil.get("modalidad", ""))
            canal = str(perfil.get("canal", ""))
            # EXCEL V2-8: Vision CTS!C34 denominador = Panel!W31 (volumen transaccional, no FTE)
            # Preferir vol_cadena_a_mensual explícito del perfil cuando está presente y > 0.
            # Fallback al VolumeResolutionService (volumetria.inbound FTE-based) para backward compat.
            vol_explicito = perfil.get("vol_cadena_a_mensual", 0.0)
            vol_resuelto = (
                float(vol_explicito)
                if vol_explicito and float(vol_explicito) > 0.0
                else volume_service.volumen(modalidad, canal, "cadena_a")
            )
            perfiles.append({
                **perfil,
                "vol_cadena_a_mensual": vol_resuelto,
            })
        return {**condiciones_a, "perfiles": perfiles}

    @staticmethod
    def _inyectar_volumenes_cadena_b(condiciones_b: Dict, volume_service: VolumeResolutionService) -> Dict:
        condiciones_b = dict(condiciones_b)
        condiciones_b["_volume_service"] = volume_service
        return condiciones_b

    @staticmethod
    def _inyectar_volumenes_cadena_c(condiciones_c: Dict, volume_service: VolumeResolutionService) -> Dict:
        condiciones_c = dict(condiciones_c)
        condiciones_c["_volume_service"] = volume_service
        return condiciones_c

    # ------------------------------------------------------------------
    # Panel de Control
    # ------------------------------------------------------------------


    def _validar_unicidad_canales_por_seccion(self, data: Dict) -> None:
        """Valida que no haya canales duplicados dentro de la misma sección (inbound/outbound)."""
        from nexa_engine.modules.shared.exceptions import ValidationError

        volumetria = data.get("volumetria", {})

        for modalidad in ["inbound", "outbound"]:
            canales = volumetria.get(modalidad, {}).get("canales", [])
            nombres_normalizados = set()
            for canal in canales:
                nombre = str(canal.get("canal", "")).strip().casefold()
                if not nombre:
                    continue
                if nombre in nombres_normalizados:
                    raise ValidationError(
                        f"Canal duplicado en {modalidad}: '{canal.get('canal')}'. "
                        f"Cada canal debe ser único dentro de {modalidad} (después de trim y casefold)"
                    )
                nombres_normalizados.add(nombre)

    # -- Mixin delegated builders --
    # _panel, _escenarios  → UserInputBuildersPanelMixin
    # _cadena_a, _staff_rol, _perfil_a → UserInputBuildersCadenaAMixin
    # _cadena_b, _canal_b, etc.        → UserInputBuildersCadenaBMixin
    # _cadena_c, _equipo_hitl_item, _canal_c → UserInputBuildersCadenaCMixin
    # _requerir, _requerir_int, etc.   → UserInputValidatorsMixin

    @staticmethod
    def _leer(ruta: str | Path) -> Dict[str, Any]:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
