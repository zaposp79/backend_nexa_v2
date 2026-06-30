"""
domain/services/special_roles_calculator.py
============================================
Calculadores para roles especiales: Especialista de Proyectos, Aprendiz SENA, Inclusión.

Reglas funcionales oficiales V2-6.

Principios de diseño:
- Ningún nombre de cargo ni multiplicador está hardcodeado aquí.
- Toda clasificación viene de la parametrización HR (clasificacion_cargos).
- Toda constante numérica viene de la parametrización HR (complejidad_especialista).
- Precisión Excel: Decimal + ROUND_HALF_UP.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from nexa_engine.modules.cadena_a.enums.cargo_tipo import CargoTipo
from typing import Dict


def _normalizar_rol(rol: str) -> str:
    """Normaliza nombre de rol para lookup case/accent-insensitive.

    Mismas reglas que context_builder._normalize_rol: NFD, quita acentos,
    quita caracteres especiales, lowercase y colapsa espacios.
    """
    nfd = unicodedata.normalize("NFD", rol)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    sin_especial = sin_acentos.replace("(", "").replace(")", "").replace("%", "")
    return re.sub(r"\s+", " ", sin_especial).strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# Enum de tipos de cargo
# ─────────────────────────────────────────────────────────────────────────────

class CargoClassifier:
    """Clasifica roles de soporte sin hardcodear nombres.

    Lee clasificación desde ParametrizationProvider (HR-clasificacion_cargos).
    Determinístico y desacoplado del frontend.
    """

    def __init__(self, clasificacion: dict):
        """
        Args:
            clasificacion: dict mapeando nombre de rol → tipo (string).
                           Ej: {"Validador": "VALIDADOR", "Supervisor": "OPERATIVO"}
                           Viene de HR-clasificacion_cargos en parametrización.
        """
        # Normalizar claves para lookup case/accent-insensitive.
        # Los ratios_staff del repositorio devuelven claves ya normalizadas,
        # por lo que la búsqueda directa sin normalización siempre falla.
        self._mapa = {_normalizar_rol(k): v for k, v in clasificacion.items()}

    def clasificar(self, rol: str) -> CargoTipo:
        """Retorna el CargoTipo para un rol dado.

        Args:
            rol: Nombre del rol (casing libre, acentos opcionales).

        Returns:
            CargoTipo correspondiente, o CargoTipo.DESCONOCIDO si no está en el mapa.
        """
        tipo_str = self._mapa.get(_normalizar_rol(rol), "DESCONOCIDO")
        try:
            return CargoTipo(tipo_str)
        except ValueError:
            return CargoTipo.DESCONOCIDO

    def es_excluido_sena_base(self, rol: str) -> bool:
        """¿Este rol se excluye del cómputo base de SENA?

        Excluidos: VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION.
        Determinado por el CargoTipo, no por comparación de strings.
        """
        tipo = self.clasificar(rol)
        return tipo in {CargoTipo.VALIDADOR, CargoTipo.ESPECIALISTA,
                        CargoTipo.APRENDIZ, CargoTipo.INCLUSION}

    def es_incluido_inclusion_base(self, rol: str) -> bool:
        """¿Este rol se incluye en el base de Inclusión?

        Incluidos: AGENTE, OPERATIVO, ADMINISTRATIVO, APRENDIZ.
        """
        tipo = self.clasificar(rol)
        return tipo in {CargoTipo.AGENTE, CargoTipo.OPERATIVO,
                        CargoTipo.ADMINISTRATIVO, CargoTipo.APRENDIZ}


# ─────────────────────────────────────────────────────────────────────────────
# EspecialistaCalculator
# ─────────────────────────────────────────────────────────────────────────────

class EspecialistaCalculator:
    """Calcula FTE y salario del Especialista de Proyectos.

    Fórmula salarial (reglas funcionales oficiales V2-6):
        Salario = (sal_base * ratio) + ((sal_base * 3 * complejidad * ratio) / meses_contrato)

    Excel V2-6 referencia:
        Nomina Loaded C66: (INDEX(AM:AM,...) * A66 * 3 * W48) / C11
    """

    MULTIPLICADOR_EXCEL = Decimal("3")  # Fijo por spec. NO cambiar sin actualizar Excel.

    def __init__(self, complejidad_map: dict):
        """
        Args:
            complejidad_map: {"BAJA": 0.20, "MEDIA": 0.50, "ALTA": 0.50}
                             Viene de HR-complejidad_especialista en parametrización.
        """
        self._complejidad_map = {
            k.upper(): Decimal(str(v))
            for k, v in complejidad_map.items()
            if k.upper() not in ("DEFAULT",)  # excluir claves de control
        }

    def get_complejidad_multiplicador(self, complejidad: str) -> Decimal:
        """Resuelve multiplicador desde parametrización.

        Args:
            complejidad: "BAJA", "MEDIA", "ALTA" (case-insensitive)

        Returns:
            Decimal(0.20), Decimal(0.50), o Decimal(0.50)

        Raises:
            ValueError si complejidad no está en el mapa
        """
        key = (complejidad or "ALTA").upper()
        if key not in self._complejidad_map:
            raise ValueError(
                f"Complejidad '{complejidad}' no está en parametrización. "
                f"Valores válidos: {list(self._complejidad_map.keys())}"
            )
        return self._complejidad_map[key]

    def calcular_salario(
        self,
        sal_cargado: float,
        ratio: float,
        complejidad: str,
        meses_contrato: int,
    ) -> float:
        """Calcula el salario mensual cargado del Especialista de Proyectos.

        Fórmula (paridad Excel V2-6 Nomina Loaded C66):
            (sal_cargado * ratio * 3 * complejidad) / meses_contrato

        Donde sal_cargado = costo empresa completamente cargado (nomina_cargada.calcular),
        equivalente a Inputs de Nomina!AM38 en Excel.

        Excel V2-6 referencia exacta:
            = (AM38 × A66 × 3 × W48) / C11
            = (7,478,113.322 × 0.5 × 3 × 1) / 12 = 934,764 COP

        En Python (complejidad ALTA=0.50 actúa como el factor combinado A66×complejidad):
            = (sal_cargado × ratio × 3 × complejidad) / meses_contrato

        Precisión: Decimal con ROUND_HALF_UP (paridad Excel, sin decimales para COP).

        Args:
            sal_cargado: Costo empresa cargado desde nomina_cargada.calcular(sal_base)
                         Equivalente a Inputs de Nomina!AM38. NO pasar sal_base aquí.
            ratio: FTE ratio del Especialista desde HR-Ratios (ej. 1.0 = W48 en Excel)
            complejidad: "BAJA", "MEDIA", "ALTA" — desde Panel de Control o parametrización
            meses_contrato: Duración del contrato (ej. 12, 24)

        Returns:
            Salario mensual cargado del Especialista en COP (redondeado a entero).
            Este es el valor a almacenar como sal_cargado en PerfilCadenaA,
            sin aplicar nomina_cargada.calcular() adicional.
        """
        cargado = Decimal(str(sal_cargado))
        rat = Decimal(str(ratio))
        comp = self.get_complejidad_multiplicador(complejidad)
        dur = Decimal(str(meses_contrato))

        # Fórmula Excel V2-6 C66: (costo_cargado × ratio × 3 × complejidad) / meses
        total = (cargado * rat * self.MULTIPLICADOR_EXCEL * comp) / dur

        # Redondeo Excel-compatible (ROUND_HALF_UP, sin decimales para COP)
        return float(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def calcular_fte(
        self,
        fte_agentes: float,
        fte_validador: float,
        total_fte_agentes: float,
        total_fte_validador: float,
    ) -> float:
        """Calcula el FTE del Especialista de Proyectos para un perfil dado.

        Fórmula FTE (reglas funcionales oficiales):
            ratio_i = (fte_agentes_i + fte_validador_i) / (Σ fte_agentes + Σ fte_validador)
            FTE_esp_i = ratio_i

        Args:
            fte_agentes: FTE agentes del perfil actual
            fte_validador: FTE validador del perfil actual
            total_fte_agentes: Suma FTE agentes de TODOS los perfiles
            total_fte_validador: Suma FTE validador de TODOS los perfiles

        Returns:
            FTE del Especialista para este perfil
        """
        numerador = Decimal(str(fte_agentes)) + Decimal(str(fte_validador))
        denominador = Decimal(str(total_fte_agentes)) + Decimal(str(total_fte_validador))

        if denominador == 0:
            return 0.0

        ratio = numerador / denominador
        return float(ratio)


# ─────────────────────────────────────────────────────────────────────────────
# SENACalculator
# ─────────────────────────────────────────────────────────────────────────────

class SENACalculator:
    """Calcula FTE para Aprendiz SENA con exclusiones correctas.

    Fórmula (reglas funcionales oficiales V2-6):
        FTE_SENA = (fte_agentes + Σ(soporte sin {Validador, Especialista, SENA, Inclusión})) / ratio_sena

    Exclusiones determinadas por CargoClassifier, NO por comparación de strings.
    """

    def __init__(self, classifier: CargoClassifier):
        self._classifier = classifier

    def calcular_fte(
        self,
        fte_agentes: float,
        fte_soporte_base: Dict[str, float],
        ratio_sena: float,
    ) -> float:
        """
        Args:
            fte_agentes: FTE total de agentes del perfil
            fte_soporte_base: dict {rol: fte} de todos los roles de soporte
            ratio_sena: ratio de agentes por Aprendiz SENA desde HR-Ratios

        Returns:
            FTE calculado para Aprendiz SENA
        """
        fte_soporte_neto = Decimal("0")

        for rol, fte in fte_soporte_base.items():
            if not self._classifier.es_excluido_sena_base(rol):
                fte_soporte_neto += Decimal(str(fte))

        total = Decimal(str(fte_agentes)) + fte_soporte_neto
        ratio = Decimal(str(ratio_sena))

        if ratio == 0:
            return 0.0

        return float(total / ratio)


# ─────────────────────────────────────────────────────────────────────────────
# SalarioFijoCalculator
# ─────────────────────────────────────────────────────────────────────────────

class SalarioFijoCalculator:
    """Calcula el Salario Fijo promedio sobre todos los perfiles activados.

    Fórmula (reglas funcionales oficiales):
        Salario_Fijo = Σ(salario_cargado_i × fte_i) / meses_contrato / total_fte

    Equivalente a:
        Costo mensual total activado / duración del contrato / headcount total

    Fuente Excel: Vision Cost To Serve — métrica de salida de costos de nómina.
    Interpretación: costo promedio mensual por FTE en el horizonte del contrato.

    Precisión: Decimal con ROUND_HALF_UP.
    """

    def calcular(
        self,
        perfiles_activos: list,   # list of (sal_cargado: float, fte: float)
        meses_contrato: int,
    ) -> float:
        """Calcula el Salario Fijo promedio.

        Args:
            perfiles_activos: Lista de tuplas (sal_cargado, fte) de TODOS
                              los perfiles activados (agentes + soporte).
                              Ej: [(5_000_000, 10.0), (3_000_000, 2.0)]
            meses_contrato:   Duración del contrato en meses (Panel C11).

        Returns:
            Salario Fijo en COP (redondeado a entero, ROUND_HALF_UP).
            Retorna 0.0 si no hay perfiles o el FTE total es 0.
        """
        if not perfiles_activos or meses_contrato <= 0:
            return 0.0

        suma_costo = Decimal("0")
        suma_fte = Decimal("0")

        for sal_cargado, fte in perfiles_activos:
            sc = Decimal(str(sal_cargado))
            ft = Decimal(str(fte))
            suma_costo += sc * ft
            suma_fte += ft

        if suma_fte == 0:
            return 0.0

        dur = Decimal(str(meses_contrato))
        # Salario_Fijo = Σ(sal × fte) / meses / total_fte
        salario_fijo = suma_costo / dur / suma_fte

        return float(salario_fijo.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ─────────────────────────────────────────────────────────────────────────────
# InclusionCalculator
# ─────────────────────────────────────────────────────────────────────────────

class InclusionCalculator:
    """Calcula FTE para Inclusión (incluye Agente + TODO soporte + SENA).

    Fórmula (reglas funcionales oficiales V2-6):
        FTE_INC = (fte_agentes + fte_soporte_total + fte_sena) / ratio_inclusion

    Sin exclusiones adicionales en fte_soporte_total.
    """

    def calcular_fte(
        self,
        fte_agentes: float,
        fte_soporte_total: float,
        fte_sena: float,
        ratio_inclusion: float,
    ) -> float:
        """
        Args:
            fte_agentes: FTE total de agentes
            fte_soporte_total: FTE total de soporte (sin exclusiones)
            fte_sena: FTE calculado de Aprendiz SENA
            ratio_inclusion: ratio de agentes por persona de Inclusión desde HR-Ratios

        Returns:
            FTE calculado para Inclusión
        """
        total = (
            Decimal(str(fte_agentes))
            + Decimal(str(fte_soporte_total))
            + Decimal(str(fte_sena))
        )
        ratio = Decimal(str(ratio_inclusion))

        if ratio == 0:
            return 0.0

        return float(total / ratio)
