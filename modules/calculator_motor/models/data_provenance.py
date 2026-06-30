"""
nexa_engine/adapters/data_provenance.py
=========================================
FASE 3 — DataProvenance: Trazabilidad de origen de cada campo en PricingRequest.

Garantiza el invariante de Single Source of Truth:
  Todo valor en PricingRequest debe trazar a:
  - entry_data (input del usuario)
  - parametrization (storage/parametrization/)
  - default_explicit (default documentado, sin silent defaults)
  - calculated (derivado de otros valores con fórmula documentada)

Uso:
    provenance = DataProvenance()
    provenance.record("panel.ciudad", ciudad, DataSource.USER_INPUT, "datos_operativos.ciudad")
    provenance.record("panel.tasa_ica", tasa_ica, DataSource.PARAMETRIZATION, "OP-ICA[ciudad=Bogota]")
    provenance.validate()  # raises si hay campos sin provenance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataSource(str, Enum):
    """
    Fuente de un valor en PricingRequest.

    USER_INPUT:
        El valor proviene del JSON del usuario (entry_data).
        Subcategorías: panel_de_control, condiciones_cadena_a/b/c, polizas.

    PARAMETRIZATION:
        El valor proviene de storage/parametrization/ (HR, OP, GN).
        Ejemplos: salario por rol, tasa ICA por ciudad, constantes operativas.

    USER_OVERRIDE_PARAMETRIZATION:
        El usuario proveyó un valor explícito que sobreescribe la parametrización activa.
        Ejemplo: tasa_ica override en panel_de_control cuando el usuario la especifica.

    DEFAULT_EXPLICIT:
        Default documentado y justificado — NOT un silent default.
        Solo para campos opcionales con justificación en dominio BPO.
        Ejemplos: periodo_pago_dias=90, com_cont=0.0, markup=0.0.

    CALCULATED:
        Valor derivado de otros valores con fórmula documentada.
        Ejemplos: salario_cargado = f(salario_base, comision_pct), pct_aumento = f(factores_indexacion).

    HARDCODE_PENDING_FIX:
        Valor hardcodeado sin justificación documentada — marcado para eliminación en fases futuras.
        No debe existir en producción; solo para documentar deuda técnica durante migración.
    """
    USER_INPUT = "user_input"
    PARAMETRIZATION = "parametrization"
    USER_OVERRIDE_PARAMETRIZATION = "user_override_parametrization"
    DEFAULT_EXPLICIT = "default_explicit"
    CALCULATED = "calculated"
    HARDCODE_PENDING_FIX = "hardcode_pending_fix"


@dataclass
class ProvenanceEntry:
    """Registro de origen de un campo específico en PricingRequest."""
    field_path: str     # Path al campo, ej. "panel.tasa_ica"
    value: Any          # Valor actual del campo
    source: DataSource  # Fuente del valor
    detail: str = ""    # Detalle adicional (ej. "OP-ICA[ciudad=Bogota]", "entry_data.datos_operativos.ciudad")

    def is_problematic(self) -> bool:
        """Retorna True si el origen es un hardcode pendiente de fix."""
        return self.source == DataSource.HARDCODE_PENDING_FIX


@dataclass
class DataProvenance:
    """
    Registro completo de trazabilidad de origen de los valores en PricingRequest.

    Permite verificar que NINGÚN valor llegó al motor sin fuente documentada.
    Se construye durante SimulationContextBuilder.construir() y se incluye
    en SimulationSnapshot (FASE 4).

    Invariante:
        Para todo campo financieramente significativo, debe existir
        una entrada en DataProvenance con source != HARDCODE_PENDING_FIX.
    """
    _entries: Dict[str, ProvenanceEntry] = field(default_factory=dict)

    def record(
        self,
        field_path: str,
        value: Any,
        source: DataSource,
        detail: str = "",
    ) -> None:
        """
        Registra el origen de un campo.

        Args:
            field_path: Ruta al campo en PricingRequest (ej. "panel.tasa_ica")
            value:      Valor del campo
            source:     Fuente del valor
            detail:     Detalle de la fuente (ej. "OP-ICA[ciudad=Bogota]")
        """
        self._entries[field_path] = ProvenanceEntry(field_path, value, source, detail)

    def record_user_input(self, field_path: str, value: Any, source_field: str = "") -> None:
        """Atajo para registrar un valor que viene del user_input."""
        self.record(field_path, value, DataSource.USER_INPUT, source_field)

    def record_parametrization(self, field_path: str, value: Any, source_key: str = "") -> None:
        """Atajo para registrar un valor que viene de parametrization."""
        self.record(field_path, value, DataSource.PARAMETRIZATION, source_key)

    def record_user_override(self, field_path: str, value: Any, parametrization_key: str = "") -> None:
        """Atajo para registrar un override del usuario sobre la parametrización."""
        self.record(field_path, value, DataSource.USER_OVERRIDE_PARAMETRIZATION,
                    f"user_override (parametrization fallback: {parametrization_key})")

    def record_default(self, field_path: str, value: Any, reason: str = "") -> None:
        """Atajo para registrar un default explícito documentado."""
        self.record(field_path, value, DataSource.DEFAULT_EXPLICIT, reason)

    def record_calculated(self, field_path: str, value: Any, formula: str = "") -> None:
        """Atajo para registrar un valor calculado."""
        self.record(field_path, value, DataSource.CALCULATED, formula)

    def record_hardcode_pending(self, field_path: str, value: Any, reason: str = "") -> None:
        """
        Registra un hardcode pendiente de fix.
        Usar durante migración para documentar deuda técnica.
        """
        self.record(field_path, value, DataSource.HARDCODE_PENDING_FIX,
                    f"HARDCODE PENDIENTE: {reason}")

    def get(self, field_path: str) -> Optional[ProvenanceEntry]:
        """Retorna el registro de provenance para un campo, o None si no existe."""
        return self._entries.get(field_path)

    def get_by_source(self, source: DataSource) -> List[ProvenanceEntry]:
        """Retorna todos los registros con la fuente indicada."""
        return [e for e in self._entries.values() if e.source == source]

    def problematic_entries(self) -> List[ProvenanceEntry]:
        """Retorna todos los registros con hardcodes pendientes de fix."""
        return self.get_by_source(DataSource.HARDCODE_PENDING_FIX)

    def validate(self, raise_on_hardcodes: bool = False) -> List[str]:
        """
        Valida que todos los campos registrados tengan fuente documentada.

        Args:
            raise_on_hardcodes: Si True, raise ValueError si hay hardcodes pendientes.

        Returns:
            Lista de field_paths con HARDCODE_PENDING_FIX (puede estar vacía).

        Raises:
            ValueError: Si raise_on_hardcodes=True y hay hardcodes pendientes.
        """
        problematic = [e.field_path for e in self.problematic_entries()]
        if problematic and raise_on_hardcodes:
            raise ValueError(
                f"DataProvenance: {len(problematic)} campos con hardcodes pendientes de fix:\n"
                + "\n".join(f"  - {fp}" for fp in problematic)
            )
        return problematic

    def summary(self) -> str:
        """Resumen textual de la trazabilidad."""
        from collections import Counter
        counts = Counter(e.source.value for e in self._entries.values())
        lines = [f"DataProvenance: {len(self._entries)} campos registrados"]
        for source, count in sorted(counts.items()):
            lines.append(f"  {source}: {count}")
        problematic = self.problematic_entries()
        if problematic:
            lines.append(f"  ⚠️  HARDCODES PENDIENTES ({len(problematic)}):")
            for e in problematic:
                lines.append(f"      {e.field_path}: {e.detail}")
        return "\n".join(lines)

    def as_dict(self) -> Dict[str, Dict]:
        """Serializa el provenance para inclusión en SimulationSnapshot (FASE 4)."""
        return {
            path: {
                "value":  str(entry.value) if not isinstance(entry.value, (int, float, bool, str, type(None))) else entry.value,
                "source": entry.source.value,
                "detail": entry.detail,
            }
            for path, entry in self._entries.items()
        }

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, field_path: str) -> bool:
        return field_path in self._entries
