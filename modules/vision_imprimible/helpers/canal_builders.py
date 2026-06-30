"""Canal and equipo builder helpers for VisionImprimible (FASE Z4c split).

Extracted from builder.py (>500 LOC) — behaviour unchanged.
"""
from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.shared.models import (
    CanalDetalle,
    CanalDetalleModalidad,
    EstructuraEquipo,
    GrupoCargoEquipo,
    PerfilCadenaA,
    ResultadoCostToServe,
    ResultadoVisionTarifas,
    RolEquipo,
)


def _construir_detalle_por_canal(
    vision_tarifas: Optional[ResultadoVisionTarifas],
    cost_to_serve: Optional[ResultadoCostToServe],
    perfiles_cadena_a: Optional[List[PerfilCadenaA]] = None,
) -> List[CanalDetalle]:
    """
    Vista Detallada por Canal — desglose completo con split Inbound/Outbound.

    Fuente primaria: cost_to_serve.canales_detalle (canales reales con CTS).
    Fuente secundaria: vision_tarifas.canales (tarifas/facturación).
    SIEMPRE retorna lista — 1 entrada por canal real.
    """
    tarifa_por_canal: dict = {}
    if vision_tarifas and vision_tarifas.canales:
        for c in vision_tarifas.canales:
            key = (c.producto or c.nombre_canal or "").lower()
            tarifa_por_canal[key] = c

    seen: set = set()
    canal_keys_ordered: list = []
    if cost_to_serve and cost_to_serve.canales_detalle:
        for cd in cost_to_serve.canales_detalle:
            key = (cd.canal or "").lower()
            if key and key not in seen:
                seen.add(key)
                canal_keys_ordered.append(key)
    for p in (perfiles_cadena_a or []):
        if p.es_soporte:
            continue
        key = (p.canal or "").lower()
        if key and key not in seen:
            seen.add(key)
            canal_keys_ordered.append(key)
    if vision_tarifas and vision_tarifas.canales:
        for c in vision_tarifas.canales:
            key = (c.producto or c.nombre_canal or "").lower()
            if key and key not in seen:
                seen.add(key)
                canal_keys_ordered.append(key)

    cts_por_canal: dict = {}
    cts_por_canal_mod: dict = {}
    if cost_to_serve and cost_to_serve.canales_detalle:
        for cd in cost_to_serve.canales_detalle:
            cts_por_canal[(cd.canal or "").lower()] = cd
            cts_por_canal_mod[
                ((cd.canal or "").lower(), (cd.modalidad or "").lower())
            ] = cd

    def _make_modalidad_detalle(cd) -> CanalDetalleModalidad:
        return CanalDetalleModalidad(
            fte=cd.fte, payroll=cd.payroll, no_payroll=cd.no_payroll,
            nomina_loaded=cd.nomina_loaded, salario_fijo=cd.salario_fijo,
            salario_variable=cd.salario_variable, capacitacion_inicial=cd.capacitacion_inicial,
            capacitacion_rotacion=cd.capacitacion_rotacion, examenes=cd.examenes,
            estudios_seguridad=cd.estudios_seguridad, crucero=cd.crucero,
            opex_fijo=cd.opex_fijo, inversiones=cd.inversiones,
            costos_fijos=cd.costos_fijos, cts=cd.cts,
            pct_participacion=cd.participacion_cadena_a,
        )

    detalles: List[CanalDetalle] = []
    for canal_key in canal_keys_ordered:
        cd = cts_por_canal.get(canal_key)
        tc = tarifa_por_canal.get(canal_key)
        tiene_cts = cd is not None

        canal_nombre = (cd.canal if cd else None) or \
                       (tc.nombre_canal if tc else None) or canal_key.title()
        modalidad = (cd.modalidad if cd else None) or \
                    (tc.modalidad if tc else None) or ""

        detalle = CanalDetalle(
            canal                  = canal_nombre,
            modalidad              = modalidad,
            datos_disponibles      = tiene_cts,
            fte                    = cd.fte if cd else (tc.fte if tc else 0.0),
            payroll                = tc.payroll_ch if tc else (cd.payroll * cd.fte if cd else 0.0),
            no_payroll             = tc.no_payroll_ch if tc else (cd.no_payroll * cd.fte if cd else 0.0),
            cadena_b_atribuible    = tc.cadena_b_atribuible if tc else 0.0,
            financieros_atribuible = tc.financieros_atribuible if tc else 0.0,
            costo_cadena_a         = tc.costo_cadena_a_ch if tc else (cd.cts * cd.fte if cd else 0.0),
            tarifa_fijo_fte        = tc.tarifa_fijo_fte if tc else 0.0,
            tarifa_variable        = tc.tarifa_variable if tc else 0.0,
            facturacion            = tc.facturacion if tc else 0.0,
            ingreso_bruto          = tc.ingreso_bruto if tc else 0.0,
        )
        if tiene_cts:
            detalle.cts                = cd.cts
            detalle.nomina_loaded      = cd.nomina_loaded
            detalle.salario_fijo       = cd.salario_fijo
            detalle.salario_variable   = cd.salario_variable
            detalle.capacitacion_inicial        = cd.capacitacion_inicial
            detalle.capacitacion_rotacion       = cd.capacitacion_rotacion
            detalle.examenes           = cd.examenes
            detalle.estudios_seguridad = cd.estudios_seguridad
            detalle.crucero            = cd.crucero
            detalle.opex_fijo          = cd.opex_fijo
            detalle.inversiones        = cd.inversiones
            detalle.costos_fijos       = cd.costos_fijos

        cd_inbound = cts_por_canal_mod.get((canal_key, "inbound"))
        cd_outbound = cts_por_canal_mod.get((canal_key, "outbound"))
        if cd_inbound is None and cd_outbound is None and cd is not None:
            modal = (cd.modalidad or "").lower()
            if modal == "outbound":
                cd_outbound = cd
            else:
                cd_inbound = cd
        if cd_inbound is not None:
            detalle.inbound = _make_modalidad_detalle(cd_inbound)
        if cd_outbound is not None:
            detalle.outbound = _make_modalidad_detalle(cd_outbound)
        detalles.append(detalle)
    return detalles


def _construir_estructura_equipo(
    perfiles_cadena_a: Optional[List[PerfilCadenaA]],
) -> Optional[EstructuraEquipo]:
    """
    Estructura del Equipo — roles, FTE y costos desde perfiles_cadena_a.

    Sección OPCIONAL: si no hay perfiles, retorna None (sin fabricar).
    """
    perfiles = perfiles_cadena_a or []
    if not perfiles:
        return None

    roles: List[RolEquipo] = []
    por_cargo_acc: dict = {}
    fte_total = fte_agentes = fte_soporte = costo_total = 0.0

    for p in perfiles:
        costo = p.salario_cargado * p.fte
        cargo = p.cargo_tipo or "DESCONOCIDO"
        roles.append(
            RolEquipo(
                rol                      = p.nombre,
                cargo_tipo               = cargo,
                canal                    = p.canal,
                modalidad                = p.modalidad,
                fte                      = p.fte,
                es_soporte               = p.es_soporte,
                salario_cargado_unitario = p.salario_cargado,
                costo_mensual            = costo,
            )
        )
        acc = por_cargo_acc.setdefault(cargo, [0.0, 0.0, 0])
        acc[0] += p.fte
        acc[1] += costo
        acc[2] += 1

        fte_total += p.fte
        costo_total += costo
        if p.es_soporte:
            fte_soporte += p.fte
        else:
            fte_agentes += p.fte

    por_cargo = [
        GrupoCargoEquipo(
            cargo_tipo  = cargo,
            fte_total   = vals[0],
            costo_total = vals[1],
            num_roles   = vals[2],
        )
        for cargo, vals in sorted(por_cargo_acc.items())
    ]

    return EstructuraEquipo(
        roles               = roles,
        por_cargo           = por_cargo,
        fte_total           = fte_total,
        fte_agentes         = fte_agentes,
        fte_soporte         = fte_soporte,
        costo_total_mensual = costo_total,
    )


__all__ = ["_construir_detalle_por_canal", "_construir_estructura_equipo"]
