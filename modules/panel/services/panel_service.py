"""Panel de Control General — service layer.

PanelService es inyectable: recibe los repositories por constructor y no accede
al filesystem directamente.
BUSINESS_RULES_CANONICAL_MIGRATION: business rules loaded from canonical YAML.
"""
from __future__ import annotations

from typing import Any, Dict, List

from nexa_engine.modules.panel.dto.panel_dto import (
    DatosOperativos, Indexacion, MargenObjetivo, ParametrosPanel,
    Poliza, Rango, ReglasNegocio, Volumetria,
)
from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules_cached,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)


def _get_sheet_rows(op_data: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    for sheet in op_data.get("sheets", []):
        if sheet.get("key") == key:
            return sheet.get("rows", [])
    return []


class PanelService:
    """Construye ParametrosPanel a partir de repositories inyectados."""

    def __init__(
        self,
        op_repo: OPActiveParametrizationRepository,
        gn_repo: GNActiveParametrizationRepository,
    ) -> None:
        self._op = op_repo
        self._gn = gn_repo

    def build_parametros(self) -> ParametrosPanel:
        op = self._op.get_active_data()
        gn = self._gn.get_active_data()

        datos_rows = _get_sheet_rows(op, "datosoperativos")
        datos_map = {r["nombre"].lower(): r["valor"] for r in datos_rows}

        poliza_rows = _get_sheet_rows(op, "poliza")
        tasa_rows = _get_sheet_rows(op, "tasa")
        tasa_map = {r.get("tasa", "").lower(): r["valor"] for r in tasa_rows}

        gmf_row = next((r for r in poliza_rows if "gmf" in r["poliza"].lower()), None)
        tasa_gmf = gmf_row["valor"] if gmf_row else datos_map.get("gmf", 0.004)

        polizas = [
            Poliza(nombre=r["poliza"], pct_atribuible=r["pct_atribuible"])
            for r in poliza_rows
            if "pct_atribuible" in r
        ]

        br_politicas = load_business_rules_cached("politicas_comerciales")
        margen_obj = br_politicas.get("margen_objetivo", {})
        politicas = {p["nombre"]: p for p in br_politicas.get("politicas_comerciales", [])}

        def _rango(nombre: str) -> Rango:
            p = politicas.get(nombre, {})
            return Rango(minimo=p.get("min", 0.0), maximo=p.get("max", 0.0))

        gn_lv = gn.get("lv", {}).get("catalogs", {})

        return ParametrosPanel(
            datos_operativos=DatosOperativos(
                tarifa_diaria_capacitacion=datos_map.get("tarifa diaria de capacitacion", 0.0),
                crucero=datos_map.get("crucero_base", 8000.0) * (1 + datos_map.get("crucero_tasa", 0.051)),
                horas_formacion_mes=datos_map.get("horas de formacion mensual", 0.0),
                pct_ausentismo=datos_map.get("porcentaje de ausentismo", 0.0),
                pct_rotacion=datos_map.get("porcentaje de rotacion", 0.0),
                tasa_ica=datos_map.get("ica", 0.0),
                tasa_gmf=tasa_gmf,
            ),
            polizas=polizas,
            reglas_negocio=ReglasNegocio(
                margen_objetivo=MargenObjetivo(
                    cadena_a=margen_obj.get("cadena_a", 0.0),
                    cadena_b=margen_obj.get("cadena_b", 0.0),
                    cadena_c=margen_obj.get("cadena_c", 0.0),
                ),
                contingencia_operativa=_rango("contingencia_operativa"),
                contingencia_comercial=_rango("contingencia_comercial"),
                markup=_rango("markup"),
                # BUSINESS_RULES_FIX_3: nombre correcto es "descuento" (alineado con v2-7.json).
                descuento=_rango("descuento"),
                # FIX_3: campo acumulado dead eliminado — sin fuente en PanelDeControl.
            ),
            volumetria=Volumetria(
                indexacion=Indexacion(
                    tasa_interes_mensual=tasa_map.get("tasa interes mensual", 0.0153),
                )
            ),
            ciudades=[c["name"] for c in gn_lv.get("ciudad", [])],
            localidades=[l["name"] for l in gn_lv.get("localidad", [])],
            servicios=[s["name"] for s in gn_lv.get("categoriaservicio", [])],
            clientes=[c["name"] for c in gn_lv.get("cliente", [])],
            tipos_cliente=[t["name"] for t in gn_lv.get("tipocliente", [])],
            periodos_pago=[p["name"] for p in gn_lv.get("periodopago", [])],
        )


__all__ = ["PanelService"]
