"""
config/business_rules/loader.py
================================
GAP-RULES-1: Cargador de reglas de negocio desde YAML.

Centraliza el acceso a las constantes operativas del Contact Center
(operaciones.yaml) y los márgenes mínimos/objetivo por línea de negocio
(margenes.yaml).

Las constantes son leídas una sola vez y cacheadas (singleton por módulo).
Los calculadores consumen estas constantes en lugar de hardcodear valores.

Uso:
    from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
    rules = get_business_rules()
    horas_semanales = rules.horas_semanales          # 42
    margen_min = rules.margen_minimo("Cobranzas")    # 0.17

    # Carga genérica de cualquier YAML bajo este directorio:
    from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules
    riesgo = load_business_rules("riesgo")

Excel trazabilidad:
    horas_semanales    → denominador "tarifa por hora loggeada" (Hoja Maestra)
    semanas_al_mes     → multiplicador costo mensual → horas totales mes
    breaks_diarios_min → diferencia horas pagadas vs loggeadas (V2-5)
    margen_minimo      → Rot, Ausent y Rentabilidad B29:B34
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional

# Intenta importar pyyaml; si no está disponible, usa parser manual mínimo
try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

_RULES_DIR = os.path.dirname(__file__)


def _parse_yaml_simple(path: str) -> dict:
    """
    Parser YAML mínimo para archivos sin anclajes complejos.
    Soporta: comentarios (#), claves escalares, valores numéricos/bool/string y listas de dicts.
    Usado como fallback cuando pyyaml no está instalado.
    """
    result: dict = {}
    current_root: Optional[str] = None
    # List tracking: when a top-level key contains a YAML sequence (list of dicts)
    current_list: Optional[list] = None
    current_list_item: Optional[dict] = None
    list_base_indent: Optional[int] = None

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip()
            # Strip inline comments (avoid stripping '#' inside quoted strings — good enough for our YAMLs)
            if "#" in line:
                line = line[:line.index("#")]
            line = line.rstrip()
            if not line:
                continue
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # ── Root-level key (no indentation) ─────────────────────────────
            if indent == 0:
                if ":" not in stripped:
                    continue
                key_raw, _, val_raw = stripped.partition(":")
                key = key_raw.strip()
                val = val_raw.strip()
                if val == "":
                    current_root = key
                    result[key] = {}
                    current_list = None
                    current_list_item = None
                    list_base_indent = None
                else:
                    current_root = None
                    current_list = None
                    current_list_item = None
                    list_base_indent = None
                    result[key] = _coerce(val)
                continue

            # ── Indented content ─────────────────────────────────────────────
            if current_root is None:
                continue

            # List item marker: line begins with "- "
            if stripped.startswith("- "):
                item_content = stripped[2:].strip()  # content after "- "
                if current_list is None:
                    # First list item — convert current_root value from {} to []
                    current_list = []
                    result[current_root] = current_list
                    list_base_indent = indent

                # Start a new dict item (each "- " at the list indent level = new entry)
                if indent == list_base_indent:
                    current_list_item = {}
                    current_list.append(current_list_item)

                # Parse the inline key:value on the same line as "- "
                if ":" in item_content:
                    key_raw, _, val_raw = item_content.partition(":")
                    k = key_raw.strip()
                    v = val_raw.strip()
                    if current_list_item is not None and k:
                        current_list_item[k] = _coerce(v)
                elif item_content and current_list_item is not None:
                    # Plain scalar list item (e.g. "- some string")
                    # Store as a simple string directly in the list
                    current_list[-1] = _coerce(item_content)
                    current_list_item = None
                continue

            # Regular key: value line inside an indented block
            if ":" not in stripped:
                continue
            key_raw, _, val_raw = stripped.partition(":")
            key = key_raw.strip()
            val = val_raw.strip()

            if current_list_item is not None:
                # We're inside a list item dict — add attribute
                current_list_item[key] = _coerce(val)
            elif isinstance(result.get(current_root), dict):
                # We're inside a plain nested dict
                result[current_root][key] = _coerce(val)

    return result


def _coerce(val: str):
    """Convierte string a int, float, bool o deja como string."""
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val.strip("'\"")


def _load_yaml(filename: str) -> dict:
    path = os.path.join(_RULES_DIR, filename)
    if _HAS_YAML:
        with open(path, encoding="utf-8") as f:
            return _yaml.safe_load(f) or {}
    return _parse_yaml_simple(path)


class BusinessRulesConfig:
    """
    Configuración centralizada de reglas de negocio del Contact Center.

    Atributos (operaciones.yaml):
        horas_semanales         — jornada laboral semanal en horas (42)
        semanas_al_mes          — semanas promedio por mes (4.33)
        breaks_diarios_min      — breaks operativos en minutos/día (30)
        deslogueos_min          — tiempo conexión/desconexión en min/día (5)
        coaching_min            — sesiones de coaching en min/día (5)
        pausa_activa_min        — pausas activas en min/día (5)

    Propiedades derivadas:
        total_breaks_min        — suma de todos los breaks en min/día
        horas_loggeadas_semanales — horas loggeadas por semana = jornada - breaks/día × días

    Métodos (margenes.yaml):
        margen_minimo(linea)    — margen mínimo por línea de negocio
        margen_objetivo(linea)  — margen objetivo por línea de negocio
    """

    def __init__(self) -> None:
        op = _load_yaml("operaciones.yaml")
        mg = _load_yaml("margenes.yaml")

        self.horas_semanales: float = float(op.get("horas_semanales", 42))
        self.semanas_al_mes: float = float(op.get("semanas_al_mes", 4.33))
        self.breaks_diarios_min: float = float(op.get("breaks_diarios_min", 30))
        # GAP-RULES-1: formacion (capacitaciones) = 20 min/día (HM R14C10=20)
        self.formacion_min: float = float(op.get("formacion_min", 20))
        self.deslogueos_min: float = float(op.get("deslogueos_min", 5))
        self.coaching_min: float = float(op.get("coaching_min", 5))
        self.pausa_activa_min: float = float(op.get("pausa_activa_min", 5))
        # Días hábiles por semana: 5 (convención BPO Colombia para tarifa hora)
        self.dias_habiles_semana: float = float(op.get("dias_habiles_semana", 5))

        self._margen_minimo: Dict[str, float] = {
            k: float(v)
            for k, v in (mg.get("margen_minimo_por_linea") or {}).items()
        }
        self._margen_objetivo: Dict[str, float] = {
            k: float(v)
            for k, v in (mg.get("margen_objetivo_por_linea") or {}).items()
        }

    @property
    def total_breaks_min(self) -> float:
        """
        Suma de todos los minutos improductivos por día.
        Excel V2-5 HM R18C10 = 65 = 30+20+5+5+5 (breaks+formación+deslogueos+coaching+pausa).
        """
        return (self.breaks_diarios_min + self.formacion_min + self.deslogueos_min
                + self.coaching_min + self.pausa_activa_min)

    @property
    def horas_loggeadas_semanales(self) -> float:
        """
        Horas loggeadas por semana = jornada semanal - (total_breaks_min × días_hábiles / 60).

        Fórmula Excel V2-5 Hoja Maestra Escenarios R26:
          horas_loggeadas_mes = horas_presentes_mes × (1 - pct_improductivo)
          donde: pct_improductivo ≈ total_breaks_min / (horas_diarias × 60)
          y horas_diarias = horas_semanales / dias_habiles_semana

        Convención BPO Colombia: 42h/semana, 5 días hábiles → 8.4h/día.
        total_breaks = 65min/día → loggeadas/día = 8.4h - 65/60 = 7.317h
        → loggeadas/semana = 7.317h × 5 = 36.583h

        Excel V2-5 fuente: HM R26C11 = 1477.72h para 10 FTE × 4.33w × loggeadas/sem.
        """
        horas_diarias = self.horas_semanales / self.dias_habiles_semana
        breaks_diarios_h = self.total_breaks_min / 60
        loggeadas_por_dia = horas_diarias - breaks_diarios_h
        return loggeadas_por_dia * self.dias_habiles_semana

    def margen_minimo(self, linea_negocio: str) -> Optional[float]:
        """Margen mínimo requerido para la línea de negocio dada."""
        return self._margen_minimo.get(linea_negocio)

    def margen_objetivo(self, linea_negocio: str) -> Optional[float]:
        """Margen objetivo para la línea de negocio dada."""
        return self._margen_objetivo.get(linea_negocio)


@lru_cache(maxsize=1)
def get_business_rules() -> BusinessRulesConfig:
    """
    Retorna la instancia singleton de BusinessRulesConfig.
    Cargada una sola vez desde disk; cacheada para toda la vida del proceso.
    """
    return BusinessRulesConfig()


def load_business_rules(rule_name: str) -> dict:
    """Carga cualquier YAML bajo este directorio por nombre base (sin extensión).

    Args:
        rule_name: Nombre del archivo YAML sin extensión (e.g. 'riesgo').

    Returns:
        Diccionario con la configuración cargada.

    Raises:
        FileNotFoundError: Si no existe el archivo YAML solicitado.
        ValueError: Si el YAML no contiene un dict en la raíz.
    """
    loaded = _load_yaml(f"{rule_name}.yaml")
    if not isinstance(loaded, dict):
        raise ValueError(
            f"El archivo de reglas de negocio {rule_name}.yaml debe contener un dict"
        )
    return loaded


@lru_cache(maxsize=16)
def load_business_rules_cached(rule_name: str) -> dict:
    """Versión cacheada de load_business_rules para uso productivo."""
    return load_business_rules(rule_name)
