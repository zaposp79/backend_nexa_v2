"""
Resolución contractual de volumetría.

El servicio centraliza la lectura de `volumetria` para evitar que cada adapter
interprete modalidad/canal/cadena de forma distinta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ResolvedChainState:
    cadena_a: bool = False
    cadena_b: bool = False
    cadena_c: bool = False


class VolumeResolutionService:
    """Resuelve activación y volumen oficial por modalidad, canal y cadena."""

    _MODALIDADES = ("inbound", "outbound")
    _CADENAS = ("cadena_a", "cadena_b", "cadena_c")

    def __init__(self, volumetria: Dict[str, Any] | None) -> None:
        self._volumetria = volumetria or {}
        self._index: dict[tuple[str, str, str], float] = {}
        self._active = {"cadena_a": False, "cadena_b": False, "cadena_c": False}
        self._build()

    @property
    def cadenas_activas(self) -> ResolvedChainState:
        return ResolvedChainState(
            cadena_a=self._active["cadena_a"],
            cadena_b=self._active["cadena_b"],
            cadena_c=self._active["cadena_c"],
        )

    def volumen(self, modalidad: str, canal: str, cadena: str) -> float:
        key = (self._norm(modalidad), self._norm(canal), cadena)
        if not self._active.get(cadena, False):
            return 0.0
        return self._index.get(key, 0.0)

    def volumen_canal_total(self, modalidad: str, canal: str) -> float:
        return sum(
            self.volumen(modalidad, canal, cadena)
            for cadena in self._CADENAS
        )

    def _build(self) -> None:
        for modalidad in self._MODALIDADES:
            bloque = self._volumetria.get(modalidad, {}) or {}
            activas = bloque.get("cadenas_activas", {}) or {}
            for cadena in self._CADENAS:
                if bool(activas.get(cadena, False)):
                    self._active[cadena] = True

            for canal_item in bloque.get("canales", []) or []:
                canal = str(canal_item.get("canal", ""))
                for cadena in self._CADENAS:
                    celda = canal_item.get(cadena, {}) or {}
                    valor = float(celda.get("valor", 0.0) or 0.0)
                    key = (modalidad, self._norm(canal), cadena)

                    # H-09 FIX: Validate no duplicate channels
                    if key in self._index and valor > 0:
                        raise ValueError(
                            f"VolumeResolution: duplicate channel detected: "
                            f"modalidad={modalidad}, canal={canal}, cadena={cadena}. "
                            f"Existing value: {self._index[key]}, new value: {valor}"
                        )

                    self._index[key] = valor

    @staticmethod
    def _norm(value: str) -> str:
        return str(value or "").strip().lower()
