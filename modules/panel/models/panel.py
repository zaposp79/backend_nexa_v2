"""
panel/models/panel.py — Canonical home for deal input models.

⚠️  STABILITY CONTRACT
These are API-facing input contracts. Breaking changes require an API version
bump + schema migration. Do NOT import from business domain modules.

Cross-cutting: consumed by calculator_motor, vision_tarifas, vision_imprimible,
context_builder, cadena_b, cadena_c, audit.
Ownership inversion (2026-06-10): moved here from shared/models/panel.py.
modules/shared/models/panel.py is now a backward-compat adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Tipos de soporte (value objects reutilizables)
# ---------------------------------------------------------------------------

@dataclass
class Indexacion:
    """Configuración de indexación salarial y tecnológica."""
    componente_humano: str = ""
    componente_tecnologico: str = ""
    frecuencia: str = "Anual"
    mes_aplicacion: int = 1


@dataclass
class CadenasActivas:
    """Estado contractual consolidado de activación de cadenas."""
    cadena_a: bool = False
    cadena_b: bool = False
    cadena_c: bool = False

    def is_active(self, cadena: str) -> bool:
        return bool(getattr(self, cadena, False))


@dataclass
class ItemOpexConsumoB:
    """
    Ítem de consumo variable / metering en Cadena B.
    Ej: Token IA, WhatsApp minuto, llamadas por minuto.
    El campo `producto` es libre — soporta cualquier tipo de producto tecnológico.
    """
    nombre: str
    producto: str
    modalidad: str
    canal: str
    valor_unitario: float
    cantidad: float
    tipo_cobro: str = "Unitario"

    @property
    def total_mensual(self) -> float:
        return self.valor_unitario * self.cantidad


@dataclass
class MiembroEquipo:
    """
    Miembro de un equipo operativo (S&M, HITL, Transversal).
    Usado en Cadena B y Cadena C.
    """
    rol: str
    activo: bool
    pct_dedicacion: float
    fte_equivalente: float = 0.0


@dataclass
class DispositivoSM:
    """Dispositivo tecnológico del equipo S&M de Cadena B."""
    tipo: str
    costo_unitario: float
    cantidad: float
    meses_amortizacion: int = 1

    @property
    def costo_mensual(self) -> float:
        return (self.costo_unitario * self.cantidad) / self.meses_amortizacion


# ---------------------------------------------------------------------------
# Helpers de dominio
# ---------------------------------------------------------------------------

def mes_inicio_contrato(fecha_inicio: str) -> int:
    """Extrae el mes de inicio del contrato desde una fecha ISO-8601 (YYYY-MM-DD).

    Centraliza el parsing en un único punto validado para eliminar slicing posicional
    disperso. Lanza ValueError con mensaje descriptivo si el formato no es válido,
    en lugar de producir un resultado silencioso o un error críptico de int().

    Returns:
        Número de mes (1-12).

    Raises:
        ValueError: si fecha_inicio no cumple el formato YYYY-MM-DD estricto.
    """
    if not fecha_inicio:
        raise ValueError(
            "fecha_inicio está vacía. Se requiere formato YYYY-MM-DD."
        )
    # Validate structure: positions 4 and 7 must be '-', length >= 10
    if (len(fecha_inicio) < 10
            or fecha_inicio[4] != "-"
            or fecha_inicio[7] != "-"):
        raise ValueError(
            f"fecha_inicio inválida: '{fecha_inicio}'. "
            f"Se requiere formato YYYY-MM-DD (con guiones en posiciones 4 y 7)."
        )
    try:
        month = int(fecha_inicio[5:7])
    except ValueError:
        raise ValueError(
            f"fecha_inicio inválida: '{fecha_inicio}'. "
            f"Los caracteres 5-6 deben ser el mes en dos dígitos (MM). "
            f"Formato requerido: YYYY-MM-DD."
        )
    if not 1 <= month <= 12:
        raise ValueError(
            f"fecha_inicio inválida: '{fecha_inicio}'. "
            f"Mes extraído ({month}) fuera de rango 1-12."
        )
    return month


# ---------------------------------------------------------------------------
# Entidades de entrada (input) — sin defaults de negocio
# ---------------------------------------------------------------------------

@dataclass
class PanelDeControl:
    """Parámetros maestros del deal."""
    cliente: str
    tipo_cliente: str
    linea_negocio: str
    fecha_inicio: str
    meses_contrato: int
    margen: float
    op_cont: float
    com_cont: float
    markup: float
    descuento: float
    tasa_ica: float
    tasa_gmf: float
    activa_financiacion: bool
    periodo_pago_dias: int
    tasa_mensual_financ: float
    # Campos de contexto del deal
    ciudad: str = ""
    sede: str = ""
    antiguedad_cliente: str = ""
    pct_ausentismo: float = 0.0
    horas_formacion_mensual: int = 0
    indexacion: Optional[Indexacion] = None
    # Ley 1819 de 2016 — DESACTIVADO.
    # Excel V2-4 legacy no implementa exoneración Ley 1819; comportamiento
    # fijado para compatibilidad funcional estricta.
    # Campo retenido para compatibilidad con payloads existentes; valor
    # ignorado en el cálculo de aportes patronales.
    aplica_ley_1819: bool = True
    # GAP-PYG-1: Imprevistos (Panel!C73) — porcentaje que reduce Ingreso Neto. V2-5 nuevo.
    imprevistos: float = 0.0
    # WAVE 2 (Excel V2-7): márgenes objetivo por cadena. Default desde
    # `op.v2_7_defaults.margenes.{margen_b_default, margen_c_default}`.
    # Panel!D63 = 0.30, Panel!E63 = 0.20.
    margen_b: float = 0.30
    margen_c: float = 0.20
    # WAVE 2 (Excel V2-7 Panel!L9): mes del año en que aplica la indexación anual.
    # Reemplaza la constante MES_INICIO_AJUSTE_ANUAL=1 con valor parametrizable (default=6).
    mes_ajuste_indexacion: int = 6
    # WAVE 2 (Excel V2-7 Panel!L10): tasa de interés mensual para financiación.
    # Conceptualmente equivalente a `tasa_mensual_financ`; se conserva como campo
    # independiente para reflejar literalmente el input de usuario del Panel.
    tasa_interes_mensual: float = 0.0153
    # GAP-PYG-3: Comisión de Administración (Panel!C45 activado, G45=1.18%). V2-5 nuevo.
    tasa_comision_administracion: float = 0.0
    # Complejidad del Especialista de Proyectos — determina multiplicador salarial.
    # Valores válidos: "BAJA" (×0.20), "MEDIA" (×0.50), "ALTA" (×0.50 — default).
    # Fuente: HR-complejidad_especialista. NO hardcodeado aquí.
    complejidad_especialista: str = "ALTA"
    cadenas_activas: CadenasActivas = field(default_factory=CadenasActivas)
    # REFACTOR costos_operativos: tarifa_dia_cap ahora viene del input
    tarifa_diaria_capacitacion: float = 0.0
    # Tarifa mensual de crucero por agente (Panel!C17 en Excel V2-7).
    tarifa_crucero: float = 0.0


@dataclass
class PerfilCadenaA:
    """Un perfil operativo de Cadena A."""
    nombre: str
    modalidad: str
    canal: str
    fte: float
    # EXCEL V2-8: 'Condiciones Cadena A'!E26/F26/G26 ("FTEs cargos adicionales" = 12/0/7.384615 por escenario).
    # Aditivo SOLO al numerador del FTE de soporte regular: (fte + cargos_adicionales)/ratio. Default 0.0 = legacy.
    cargos_adicionales: float = 0.0
    # EXCEL V2-8: 'Condiciones Cadena A'!E95 = 9.5 (override manual literal, Supervisor SAC).
    # Override opt-in del FTE de soporte por rol (keyed por nombre de rol). Default vacío = legacy.
    fte_soporte_overrides: dict = field(default_factory=dict)
    pct_presencia: float = 1.0
    salario_base: float = 0.0
    # salario_cargado: costo mensual total por FTE incluyendo aportes patronales,
    # prestaciones y auxilio de transporte (calculado en context_builder).
    # Si es 0 el NominaCalculator usa salario_base sin carga (modo legado).
    salario_cargado: float = 0.0
    comision_pct: float = 0.0
    dias_cap_inicial: int = 0
    dias_cap_rotacion: int = 0
    tmo_segundos: float = 0.0
    incluye_examenes: bool = False
    incluye_seguridad: bool = False
    incluye_crucero: bool = False
    es_soporte: bool = False  # True para roles de staff de soporte (no ocupan estación)
    # FTE efectivo para exámenes: base_fte + supervisor/formadores/monitor FTEs (calculado en context_builder).
    # Cero en perfiles de soporte (exámenes se acumulan en el perfil base).
    fte_examenes: float = 0.0
    # Modelo de facturación para Vision Tarifas
    modelo_cobro: str = "Fijo FTE"   # "Fijo FTE" | "Híbrido" | "Variable"
    pct_fijo: float = 1.0             # Porción de ingreso que se factura como tarifa por FTE
    no_payroll_mensual: float = 0.0          # OPEX Fijo mensual por canal (No payroll Excel R107 región)
    inversiones_mensual: float = 0.0         # CAPEX/inversiones amortizado: promedio aritmético de todos los meses del
                                             # contrato (mes 1 incluye setup; meses 2..N son recurrentes). Usar cuando
                                             # NO hay pólizas deal-wide con aplica_extension=True. 0.0 si sin CAPEX.
    inversiones_mensual_recurrente: float = 0.0  # CAPEX/inversiones del mes recurrente (meses 2..N, sin el costo de setup
                                                  # del mes 1). Requerido ÚNICAMENTE cuando el deal tiene pólizas deal-wide
                                                  # (per_canal=False) con aplica_extension=True: VisionTarifas necesita el
                                                  # costo mensual estable para calcular la base de los meses de extensión.
                                                  # Si se omite o es 0.0, se usa el último mes de esc_months como base
                                                  # (correcto para deals sin amortización de setup).
    costos_fijos_mensual: float = 0.0        # Costos Fijos x Estación mensual (No payroll Excel R248 región)
    cadena_b_mensual: float = 0.0            # Costo Cadena B mensual promedio por canal (de Excel)
    costos_financieros_mensual: float = 0.0  # ICA+GMF+Pólizas+Fin mensual promedio (de Excel)
    # Tipo de carga laboral formal (catálogo HR-tipos_carga).
    # Valores: EMPLEADO_ESTANDAR | APRENDIZ_SENA | EQUIPO_SOPORTE_MANTENIMIENTO |
    #          SOPORTE_COMISIONABLE | IMPLEMENTACION_PROYECTOS
    tipo_carga: str = "EMPLEADO_ESTANDAR"
    # ── K50 — volumen mensual manejado por Cadena A (denominator de CTS_A) ─────
    vol_cadena_a_mensual: float = 0.0        # J×N del Excel PCG [transacciones/mes]
    # Clasificación de tipo de cargo (string de CargoTipo enum).
    # Calculado por CargoClassifier desde HR-clasificacion_cargos.
    cargo_tipo: str = "DESCONOCIDO"
    # Per-channel opex TI total monthly — from input opex_fijo.items (populated in context_builder).
    # Used by VisionTarifasCalculator for channel-specific nop decomposition.
    opex_fijo_mensual: float = 0.0
    # Per-channel CAPEX investment items for term-based amortization.
    # Same dict format as ParametrosNoPayroll.inversiones_amortizables.
    inversiones_amortizables: List[dict] = field(default_factory=list)


@dataclass
class CanalCadenaB:
    """
    Canal digital de Cadena B con tarifa y volumen.
    El campo `producto` es libre — soporta cualquier tipo de producto tecnológico.
    """
    nombre: str
    modalidad: str
    producto: str = ""
    tarifa_unitaria: float = 0.0
    volumen_mensual: float = 0.0
    opex_fijo: float = 0.0
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0
    vol_escalamiento: float = 0.0  # volumen adicional por escalamiento (Excel Panel!N51)


@dataclass
class CanalCadenaC:
    """Canal de IA / integración de Cadena C."""
    nombre: str
    modalidad: str
    tarifa_proveedor: float = 0.0
    volumen_mensual: float = 0.0
    opex_fijo_integ: float = 0.0
    opex_var_integ: float = 0.0
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0


@dataclass
class ParametrosNomina:
    """Parámetros de nómina compartidos."""
    mes_inicio: int
    mes_fin: int
    pct_aumento_salarial: float
    mes_aplicacion_aumento: int
    tarifa_dia_cap: float
    costo_examen_medico: float
    costo_estudio_seg: float = 0.0
    # Factor acumulado del componente de indexación en el año de inicio del contrato.
    # Multiplica todos los costos de nómina desde el mes 1 (salarios base están en año 2025).
    factor_indexacion_base: float = 1.0
    # Meses del contrato — necesario para amortizar capacitacion_inicial y costos de selección inicial.
    meses_contrato: int = 1
    # Tarifa mensual de crucero por agente (Panel!C17 en Excel V2-7).
    tarifa_crucero: float = 0.0


@dataclass
class ParametrosNoPayroll:
    """Costos no-nómina de Cadena A por estación."""
    opex_ti_por_estacion: float
    capex_por_estacion: float
    arriendo_por_estacion: float
    energia_por_estacion: float
    vigilancia_por_estacion: float
    aseo_por_estacion: float
    otros_fijos_por_estacion: float = 0.0
    capex_inicial_por_estacion: float = 0.0
    # Excel V2-7 CAPEX term-based amortization (No payroll K167/K168). Each item:
    # {"precio_mensual": float, "cantidad": float, "meses": int, "factor": float}.
    # CAPEX(mes) = Σ_items[precio_mensual×cantidad×factor] para items con mes ≤ meses.
    # Cuando esta lista es no vacía, reemplaza el modelo capex_por_estacion.
    inversiones_amortizables: List[dict] = field(default_factory=list)


@dataclass
class ParametrosCadenaB:
    """
    Parámetros completos de Cadena B.
    Incluye tanto los datos de negocio detallados como los agregados
    que consume el motor de cálculo.
    """
    canales: List[CanalCadenaB] = field(default_factory=list)
    opex_consumo_variable: List[ItemOpexConsumoB] = field(default_factory=list)
    equipo_sm: List[MiembroEquipo] = field(default_factory=list)
    dispositivos_sm: List[DispositivoSM] = field(default_factory=list)
    # Valores agregados que usa el motor de cálculo
    costo_personal_sm: float = 0.0
    opex_herramientas_sm: float = 0.0
    costo_personal_hitl: float = 0.0
    opex_herramientas_hitl: float = 0.0
    inversion_mensual: float = 0.0
    pct_aumento_personal: float = 0.0
    mes_aplicacion_aumento: int = 1


@dataclass
class ParametrosCadenaC:
    """
    Parámetros completos de Cadena C.
    Incluye datos detallados y agregados para el motor.
    """
    canales: List[CanalCadenaC] = field(default_factory=list)
    equipo_transversal: List[MiembroEquipo] = field(default_factory=list)
    # Valores agregados que usa el motor de cálculo
    costo_equipo_integ: float = 0.0
    opex_herramientas_integ: float = 0.0
    costo_personal_hitl: float = 0.0
    opex_herramientas_hitl: float = 0.0
    inversion_anual: float = 0.0
    pct_aumento_tecnologico: float = 0.0
    mes_aplicacion_aumento: int = 1
    # EXCEL V2-8: Panel!L11 — factor para amortización CAPEX Cadena C
    tasa_interes_mensual: float = 0.0


@dataclass
class ParametrosCalculo:
    """Parámetros técnicos de los algoritmos de cálculo."""
    pct_rotacion: float
    pct_examen_anual: float
    pct_cumplimiento_variable: float = 0.7


@dataclass
class PolizaConfiguracion:
    """
    GAP-PCG-2: Póliza de seguros con configuración completa por cadena y extensión temporal.
    Modelo rico que replica la estructura de la hoja Pólizas - Costo Financiacion.
    """
    nombre: str
    activa: bool
    porcentaje_poliza: float      # % de prima (ej. 0.0062 = 0.62%)
    porcentaje_atribuible: float  # fracción atribuible al deal (ej. 0.20 = 20%)
    aplica_a: bool = True
    aplica_b: bool = False
    aplica_c: bool = False
    se_extiende: bool = False
    meses_extension: int = 0

    @property
    def tasa_efectiva(self) -> float:
        return self.porcentaje_poliza * self.porcentaje_atribuible if self.activa else 0.0

    @property
    def tasa_efectiva_a(self) -> float:
        return self.tasa_efectiva if self.aplica_a else 0.0

    @property
    def tasa_efectiva_b(self) -> float:
        return self.tasa_efectiva if self.aplica_b else 0.0


@dataclass
class PolizaContractual:
    """
    Póliza del deal tal como la configura el usuario en entry_data.
    Reemplaza las pólizas de storage cuando el usuario las provee.
    """
    nombre: str
    activa: bool
    pct_poliza: float
    pct_atribuible: float
    aplica_extension: bool = False
    meses_extension: Optional[int] = None
    aplica_a: bool = True
    aplica_b: bool = False
    aplica_c: bool = False
    per_canal: bool = False
    is_comision_administracion: bool = False

    @property
    def tasa_efectiva(self) -> float:
        return self.pct_poliza * self.pct_atribuible if self.activa else 0.0


@dataclass
class EscenarioComercial:
    """
    GAP-PCG-1: Escenario de facturación definido en Panel de Control General.
    Excel: Panel!A81:D113 — hasta 5 escenarios por deal.
    """
    escenario: int
    modalidad: str
    canal: str
    modelo_cobro: str
    componente_fijo_tipo: Optional[str] = None
    componente_fijo_pct: float = 1.0
    componente_variable_tipo: Optional[str] = None
    componente_variable_pct: float = 0.0


@dataclass
class PricingRequest:
    """
    Objeto de solicitud que agrupa todos los datos de entrada del motor.
    Punto de entrada único al motor de precios (Facade pattern).
    """
    panel: PanelDeControl
    perfiles_cadena_a: List[PerfilCadenaA]
    parametros_nomina: ParametrosNomina
    parametros_no_payroll: ParametrosNoPayroll
    cadena_b: ParametrosCadenaB
    cadena_c: ParametrosCadenaC
    parametros_calculo: ParametrosCalculo
    # None → usar parametrización; [] → cero pólizas; [...] → pólizas explícitas.
    polizas_usuario: Optional[List[PolizaContractual]] = None
    escenarios: List[EscenarioComercial] = field(default_factory=list)
    cadenas_activas: CadenasActivas = field(default_factory=CadenasActivas)


__all__ = [
    "Indexacion", "CadenasActivas", "ItemOpexConsumoB", "MiembroEquipo", "DispositivoSM",
    "mes_inicio_contrato",
    "PanelDeControl", "PerfilCadenaA", "CanalCadenaB", "CanalCadenaC",
    "ParametrosNomina", "ParametrosNoPayroll", "ParametrosCadenaB", "ParametrosCadenaC",
    "ParametrosCalculo", "PolizaConfiguracion", "PolizaContractual",
    "EscenarioComercial", "PricingRequest",
]
