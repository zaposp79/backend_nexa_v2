"""Registro ligero de trazabilidad contractual persistida."""

from __future__ import annotations

from typing import Any, Dict, List


class FieldTraceabilityRegistry:
    """Clasifica campos contractuales desde snapshot/resultado persistido."""

    def build(self, stored_result: Dict[str, Any]) -> Dict[str, List[str]]:
        panel = stored_result.get("panel", {}) or {}
        datasets = stored_result.get("datasets_vision", {}) or {}
        audit = stored_result.get("audit_trace")

        financially_connected = []
        partial = []
        dead = []

        for field in (
            "cliente", "linea_negocio", "ciudad", "fecha_inicio", "meses_contrato",
            "margen", "op_cont", "com_cont", "markup", "tasa_ica", "tasa_gmf",
            "tasa_mensual_financ", "imprevistos",
        ):
            if field in panel:
                financially_connected.append(f"panel.{field}")

        if stored_result.get("polizas"):
            financially_connected.append("polizas[].cadenas")
        if datasets.get("volumetria"):
            financially_connected.append("volumetria")
        else:
            partial.append("volumetria")
        if datasets.get("indexacion"):
            financially_connected.append("volumetria.indexacion")

        if audit is None:
            partial.append("audit_trace")
        if stored_result.get("datasets_vision") is None:
            partial.append("datasets_vision")

        for field in (
            "datos_operativos.cufin",
            "datos_operativos.sede_combinada_costo_formacion",
            "reglas_negocio.porcentaje_acumulado",
        ):
            dead.append(field)

        return {
            "unused_fields": [],
            "partial_fields": sorted(set(partial)),
            "financially_connected_fields": sorted(set(financially_connected)),
            "dead_fields": sorted(set(dead)),
        }
