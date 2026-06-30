"""Stateless hashing and extraction helpers for certified calculation."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


def _extract_kpis_from_result(result) -> Dict[str, Any]:
    kpis_obj = getattr(result, "kpis_deal", None) or getattr(result, "kpis", None)
    if kpis_obj is None:
        return {}
    if hasattr(kpis_obj, "__dict__"):
        return {k: v for k, v in kpis_obj.__dict__.items() if not k.startswith("_")}
    if isinstance(kpis_obj, dict):
        return dict(kpis_obj)
    return {}


def _hash_request(raw: Mapping[str, Any], request) -> str:
    payload: Dict[str, Any]
    if raw:
        payload = dict(raw)
    else:
        payload = {
            "cliente": getattr(request.panel, "cliente", None),
            "linea_negocio": getattr(request.panel, "linea_negocio", None),
            "meses_contrato": getattr(request.panel, "meses_contrato", None),
        }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_result(result) -> str:
    """Hash KPIs only — simulation_id excluded so same content → same hash."""
    kpis = _extract_kpis_from_result(result)
    canonical = json.dumps({"kpis": kpis}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_lineage(lineage_graph) -> str:
    try:
        payload = lineage_graph.to_dict(include_timestamps=False)
    except TypeError:
        payload = lineage_graph.to_dict()
    except AttributeError:
        payload = {"simulation_id": getattr(lineage_graph, "simulation_id", None)}
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["_extract_kpis_from_result", "_hash_request", "_hash_result", "_hash_lineage"]
