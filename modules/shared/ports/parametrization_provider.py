"""
modules.shared.ports.parametrization_provider
=============================================
Canonical port: Protocol que define la interfaz de acceso a datos de
parametrización que todos los calculadores del motor deben usar.

Responsabilidad
---------------
Abstraer la fuente de datos de los calculadores.

Principio de Inversión de Dependencias (DIP):
  - Los calculadores dependen de esta abstracción, NO de implementaciones concretas.
  - Esto permite reemplazar la fuente de datos sin modificar ningún calculador:
      ParametrizationProvider (producción — storage/parametrization/*)
      MockParametrizationProvider (tests)

Uso en calculadores:
    from nexa_engine.modules.shared.ports.parametrization_provider import (
        IParametrizationProvider,
    )

    class MiCalculador:
        def __init__(self, ..., parametrizacion: IParametrizationProvider) -> None:
            self._p = parametrizacion
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class IParametrizationProvider(Protocol):
    """
    Interfaz completa de datos de parametrización requerida por el motor NEXA.

    Define los puntos de acceso que calculadores y context builders necesitan:

    Calculadores (5 métodos):
      1. tasa_mensual_financiacion  — amortización de inversiones (CadenaC)
      2. get_rampup()               — factor operacional mensual (PyG)
      3. get_tasa_polizas_efectiva()— prima de pólizas de seguros (CostosFinancieros)
      4. get_factor_periodo()       — meses de financiación (KPIs, CostosFinancieros)
      5. get_margen_minimo()        — rentabilidad mínima (KPIs)

    Context builders (métodos adicionales):
      6. get_gmf()                  — Gravamen Movimientos Financieros
      7. get_ica()                  — tasa ICA por ciudad
      8. get_factor_indexacion()    — factor de indexación acumulado
      9. get_salario_rol()          — salario base por rol
     10. get_costo_no_payroll()     — costos de infraestructura por sede
     11. get_examen_medico()        — costo examen médico por ciudad
     12. get_nomina_laboral_params()— parámetros completos de nómina laboral
     13. get_pct_rotacion()         — % rotación mensual por línea
     14. get_pct_ausentismo()       — % ausentismo por línea
     15. get_pct_examen_anual()     — % exámenes anuales por línea
     16. get_costo_operativo()      — constante operativa por clave
     17. get_reglas_staff()         — reglas de categorización de roles
     18. get_ratios_staff()         — ratios de staff por línea

    Nota: get_billing_indexacion_rate() eliminado — fuente OP-BillingComponente
    no existe en el Excel OP real. Ver modules/parametrizacion/op/contracts.py.

    Toda lógica de carga, versionado, caché y transformación es responsabilidad
    de las implementaciones, NO de esta interfaz.
    """

    def tasa_mensual_financiacion(self) -> float:
        """
        Tasa mensual de financiación para amortización de inversiones.

        Fuente esperada: OP parametrización (tasa_mensual_financiacion)
        Valor típico: 0.0088 (0.88% mensual)

        Returns:
            Tasa como decimal (ej. 0.0088).
        """
        ...

    def get_rampup(self, linea_negocio: str, mes: int) -> float:
        """
        Factor de ramp-up operacional para el mes dado.

        Durante los primeros meses de un contrato la operación no alcanza
        su capacidad plena. El ramp-up escala el ingreso proyectado.

        Fuente esperada: HR-Campana (60 meses por línea)
        Rango válido: [0.0, 1.0] donde 1.0 = plena capacidad.

        Args:
            linea_negocio: Línea de negocio (ej. "Cobranzas", "SAC").
            mes:           Número de mes del contrato (1-based).

        Returns:
            Factor en [0.0, 1.0].
        """
        ...

    def get_tasa_polizas_efectiva(self, mes: int) -> float:
        """
        Tasa efectiva de pólizas de seguros activas en el mes dado.

        Calcula SUMPRODUCT(tasa × atribución) para pólizas cuyo mes_desde
        sea ≤ al mes evaluado.

        Fuente esperada: OP-Poliza (tasas) + config de atribución

        Args:
            mes: Número de mes del contrato.

        Returns:
            Tasa efectiva como decimal (tipicamente 0.01..0.03).
        """
        ...

    def get_factor_periodo(self, dias: int) -> int:
        """
        Factor de período de pago: convierte días de crédito en meses.

        30 días → 1 mes
        60 días → 2 meses
        90 días → 3 meses
        120 días → 4 meses

        Fuente esperada: lógica pura (dias // 30) o tabla en parametrización.

        Args:
            dias: Período de pago en días (30, 60, 90, 120).

        Returns:
            Número entero de meses equivalentes.
        """
        ...

    def get_margen_minimo(self, linea_negocio: str) -> float:
        """
        Margen mínimo requerido para una línea de negocio.

        Fuente esperada: HR-Rentabilidad
        Rango válido: [0.0, 1.0] donde 0.17 = 17%.

        Args:
            linea_negocio: Línea de negocio (ej. "Cobranzas", "SAC").

        Returns:
            Margen mínimo como decimal (ej. 0.17 = 17%).
        """
        ...

    # ── Context-builder methods ───────────────────────────────────────────────

    def get_gmf(self) -> float:
        """Tasa GMF (Gravamen a los Movimientos Financieros). Fuente: OP-Poliza."""
        ...

    def get_ica(self, ciudad: str) -> float:
        """Tasa ICA para una ciudad. Fuente: OP-ICA."""
        ...

    def get_factor_indexacion(self, componente: str, anio: int) -> float:
        """Factor de indexación acumulado. Fuente: OP-ComponenteAcumulado."""
        ...

    def get_componente_indexacion(self, componente: str, anio: int) -> float:
        """Tasa anual de crecimiento de un componente económico. Fuente: OP-Componente."""
        ...

    def get_salario_rol(self, rol: str) -> float:
        """Salario base para un rol. Fuente: HR-Nomina."""
        ...

    def get_costo_no_payroll(self, sede: str) -> Dict[str, Any]:
        """Costos de infraestructura por estación para una sede. Fuente: HR-CostoFijo."""
        ...

    def get_examen_medico(self, ciudad: str) -> float:
        """Costo del examen médico de ingreso. Fuente: HR-Med-Seg."""
        ...

    def get_nomina_laboral_params(self) -> Dict[str, Any]:
        """Parámetros completos de nómina laboral. Fuente: HR-Salarios/SegSocial/Prestaciones + OP-Config."""
        ...

    def get_smmlv(self) -> float:
        """SMMLV vigente — Salario Mínimo Mensual Legal Vigente.

        Fuente canónica: HR-Salarios → fila 'Salario Mínimo'.
        Esta es la única fuente autoritativa del SMMLV para el motor NEXA.

        El valor en business_rules.constantes_regulatorias.smmlv es LEGACY_NON_CANONICAL
        (valor 2025, desactualizado). No debe usarse como fuente de cálculo.

        Returns:
            SMMLV como float en COP (ej. 1_750_905.0 para 2026).
        """
        ...

    def get_pct_rotacion(self, linea: str) -> float:
        """Porcentaje de rotación mensual por línea. Fuente: HR-rotacion_ausentismo."""
        ...

    def get_pct_ausentismo(self, linea: str) -> float:
        """Porcentaje de ausentismo por línea. Fuente: HR-rotacion_ausentismo."""
        ...

    def get_pct_examen_anual(self, linea: str) -> float:
        """Porcentaje de exámenes médicos anuales por línea. Fuente: HR-rotacion_ausentismo."""
        ...

    def get_costo_operativo(self, clave: str) -> float:
        """Constante operativa por clave. Fuente: HR-costos_operativos."""
        ...

    def get_reglas_staff(self) -> Dict[str, Any]:
        """Reglas de categorización de roles de soporte. Fuente: HR-reglas_staff."""
        ...

    def get_ratios_staff(self, linea: str) -> Dict[str, float]:
        """Ratios de staff (cargo → agentes) para una línea. Fuente: HR-Ratios.

        Returns float (no int) para preservar ratios fraccionarios usados por
        roles con cálculo volumétrico (ej. Especialista de Proyectos = 24.76).
        """
        ...

    # ── Business rules & risk config ─────────────────────────────────────────

    def get_politicas_comerciales(self) -> list:
        """Policy min/max ranges for contingencies, markup, descuento.

        Fuente: modules/shared/config/business_rules/politicas_comerciales.yaml

        Returns:
            List of dicts with keys: nombre, label, min, max.
        """
        ...

    def get_riesgo_config(self) -> Dict[str, Any]:
        """Risk model configuration: thresholds, weights, criteria, and limits.

        Fuente: modules/shared/config/business_rules/riesgo.yaml

        Returns:
            Dict with keys: constantes_regulatorias, pesos_categorias,
            clasificacion_score, criterios, umbrales, tipos_cliente_alto,
            antiguedad_alto.
        """
        ...

    def get_portfolio_clientes(self) -> Optional[Dict[str, Any]]:
        """Portfolio reference data for graph band calculations.

        Fuente: active OP parametrization — OP-MargenBruto sheet (key="margenbruto").
        Excel V2-8 · Graficos!A5:C93 / OP-MargenBruto

        Returns:
            Dict with keys:
              - clientes: List[Dict] with keys categoria, cliente, margen_bruto
              - promedios_por_categoria: Dict[str, float]
            Returns None if portfolio data is not available.
        """
        ...


__all__ = ["IParametrizationProvider"]
