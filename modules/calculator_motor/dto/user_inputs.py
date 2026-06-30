"""
nexa_engine/domain/user_inputs.py
===================================
Modelos de entrada del usuario — EXCLUSIVAMENTE lo que parametriza
el usuario desde el frontend / API.

Fuentes válidas:
  - Panel de Control General
  - Condiciones Cadena A
  - Condiciones Cadena B
  - Condiciones Cadena C

NO debe contener:
    - Salarios base (vienen de storage/parametrization/hr/ por rol)
    - Pólizas (storage/parametrization/op/)
    - Costos no-payroll por estación (storage/parametrization/hr/)
    - Parámetros de nómina: tarifa día cap, examen médico (storage/parametrization/hr/)
    - Ramp-up (storage/parametrization/hr/)

Campos con default desde parametrización activa (el usuario puede sobreescribirlos):
  - tasa_ica, tasa_gmf, tasa_mensual_financ (aparecen en Panel de Control General)
  - pct_rotacion, pct_ausentismo (aparecen en Panel de Control General)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Escenarios comerciales (GAP-PCG-1 — Panel!A81:D113)
# ---------------------------------------------------------------------------

@dataclass
class EscenarioComercialInput:
    """
    GAP-PCG-1: Escenario de facturación del Panel de Control General.
    Mapeado a Panel!A81:D113 — hasta 5 escenarios por deal.

    Campos:
      escenario               — número de escenario (1-5)
      modalidad               — "Inbound" | "Outbound"
      canal                   — "Voz" | "WhatsApp" | "WebChat" | etc.
      modelo_cobro            — "Fijo" | "Híbrido" | "Variable"
      componente_fijo_tipo    — "FTE" | "Tiempo" | None
      componente_fijo_pct     — proporción del componente fijo (0-1)
      componente_variable_tipo — "Transacción" | None
      componente_variable_pct — proporción variable (0-1)
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
class CadenasActivasInput:
    """Estado contractual consolidado de activación de cadenas."""
    cadena_a: bool = False
    cadena_b: bool = False
    cadena_c: bool = False


# ---------------------------------------------------------------------------
# Pólizas del deal (nuevas en entry_data)
# ---------------------------------------------------------------------------

@dataclass
class PolizaInput:
    """
    Póliza de seguros configurada por el usuario para este deal.

    Cuando el usuario provee `polizas[]` en entry_data, estas definiciones
    reemplazan las pólizas de storage.
      - null → usar parametrización (storage)
      - []   → cero pólizas (explícito)
      - [...] → pólizas explícitas
    """
    nombre: str
    activa: bool
    pct_poliza: float         # tasa de prima de la póliza (ej. 0.0062 = 0.62%)
    pct_atribuible: float     # fracción atribuible a este deal (ej. 0.20 = 20%)
    aplica_extension: bool = False
    meses_extension: Optional[int] = None
    aplica_a: bool = True
    aplica_b: bool = False
    aplica_c: bool = False
    # True → incluida en cálculo per-canal (Pólizas sheet "Polizas Incluidas" rows 173-185).
    # Solo estas polizas contribuyen a los cargos de primas por canal (ICA base, GMF base).
    per_canal: bool = False
    # True → es la Comisión de Administración (Pólizas sheet row 188, tasa × 1.42).
    is_comision_administracion: bool = False


# ---------------------------------------------------------------------------
# Panel de Control General
# ---------------------------------------------------------------------------

@dataclass
class PanelDeControlInput:
    """
    Datos del negocio que el usuario configura al crear una cotización.
    Todo lo demás (tasas, pólizas, ramp-up) se resuelve automáticamente
    desde storage/parametrization según ciudad y línea_negocio.
    """
    cliente: str
    tipo_cliente: str           # "Grupo Aval" | "No Grupo Aval"
    linea_negocio: str          # "Cobranzas" | "SAC" | etc.
    ciudad: str                 # lookup → ICA, costos no-payroll
    sede: str                   # lookup → costos no-payroll detallados
    fecha_inicio: str           # "YYYY-MM-DD"
    meses_contrato: int
    # Márgenes — el único input financiero del usuario
    margen: float               # ej. 0.18
    op_cont: float              # contingencia operativa, ej. 0.025
    com_cont: float = 0.0       # contingencia comercial
    markup: float = 0.0
    descuento: float = 0.0
    # Condiciones de pago
    periodo_pago_dias: int = 90
    activa_financiacion: bool = True
    # Contexto del deal
    antiguedad_cliente: str = ""
    # Componente de indexación elegido por el usuario
    # Opciones válidas: "IPC", "SMLV", "70SMMLV_30IPC", "IPC_mas_1pt", etc.
    componente_indexacion_humano: str = "IPC"
    componente_indexacion_tecnologico: str = "IPC"
    # Overrides opcionales — si son None, la parametrización activa provee el valor por defecto.
    # Aparecen en la hoja "Panel de Control General" del Excel como campos configurables.
    tasa_ica: Optional[float] = None           # si None → lookup por ciudad
    tasa_gmf: Optional[float] = None           # si None → parametrización activa
    tasa_mensual_financ: Optional[float] = None # si None → parametrización activa
    pct_rotacion: Optional[float] = None       # si None → lookup por línea de negocio
    pct_ausentismo: Optional[float] = None     # si None → lookup por línea de negocio
    # Ley 1819 de 2016 — DESACTIVADO.
    # Excel V2-4 legacy no implementa exoneración Ley 1819; comportamiento
    # fijado para compatibilidad funcional estricta.
    # Campo retenido para compatibilidad con payloads existentes; valor
    # ignorado en el cálculo de aportes patronales.
    aplica_ley_1819: bool = True
    # REFACTOR costos_operativos: tarifa_dia_cap ahora viene del input
    # Tarifa diaria de capacitación por agente (valor comercial del deal).
    # Fuente: datos_operativos.tarifa_diaria_capacitacion (JSON usuario).
    tarifa_diaria_capacitacion: float = 0.0
    # GAP-PYG-1: Imprevistos (Panel!C73) — porcentaje sobre ingreso bruto. V2-5 nuevo.
    imprevistos: float = 0.0
    # horas_formacion_mes (datos_operativos) — horas de formación mensual por agente.
    # 0 por defecto — se sobreescribe con el valor del JSON oficial si se provee.
    horas_formacion_mensual: int = 0
    # Frecuencia de indexación desde volumetria.indexacion.frecuencia
    # "Anual" es el estándar BPO Colombia. Solo cambiar si el cliente negocia otro ciclo.
    indexacion_frecuencia: str = "Anual"
    # Mes de aplicación de la indexación desde volumetria.indexacion.mes_aplicacion
    # Si None, se usa el valor de la parametrización activa (mes_inicio_ajuste_anual).
    indexacion_mes_aplicacion: Optional[int] = None
    # GAP-PYG-3: Comisión de Administración (Panel!G45). V2-5 nuevo.
    tasa_comision_administracion: float = 0.0
    # ── WAVE 2 (Excel V2-7) — overrides por deal. Si None → default desde
    #    op.v2_7_defaults (ver ParametrizationProvider.get_v27_defaults()).
    margen_b: Optional[float] = None
    margen_c: Optional[float] = None
    mes_ajuste_indexacion: Optional[int] = None
    tasa_interes_mensual: Optional[float] = None
    # Complejidad del Especialista de Proyectos para cálculo salarial.
    # "BAJA" (×0.20) | "MEDIA" (×0.50) | "ALTA" (×0.50 — default).
    complejidad_especialista: str = "ALTA"
    # Tarifa mensual de crucero por agente (Panel!C17 en Excel V2-7). 0 → no aplica crucero.
    tarifa_crucero: float = 0.0
    # Override de pct_examen_anual (Condiciones Cadena A en Excel). None → usa parametrización.
    pct_examen_anual: Optional[float] = None
    # GAP-PCG-1: Escenarios comerciales del Panel!A81:D113. Hasta 5 escenarios.
    # Lista vacía → VisionTarifas usa modelo_cobro/pct_fijo de los perfiles (backward compat).
    escenarios: List[EscenarioComercialInput] = field(default_factory=list)
    cadenas_activas: CadenasActivasInput = field(default_factory=CadenasActivasInput)


# ---------------------------------------------------------------------------
# Condiciones Cadena A
# ---------------------------------------------------------------------------

@dataclass
class PerfilCadenaAInput:
    """
    Un perfil operativo definido por el usuario.
    El salario base se resuelve automáticamente desde la parametrización activa
    usando el campo `rol`. El usuario solo elige el rol y configura
    los parámetros de ese perfil en este deal.
    """
    nombre: str                  # nombre libre del perfil (ej. "Inbound Cobranzas")
    rol: str                     # clave en la parametrización activa
    canal: str                   # "Voz" | "WhatsApp" | "WebChat" | etc.
    modalidad: str               # "Inbound" | "Outbound"
    fte: float                   # número de agentes
    # EXCEL V2-8: 'Condiciones Cadena A'!E26/F26/G26 ("FTEs cargos adicionales" = 12/0/7.384615 por escenario)
    # Aditivo al numerador del FTE de soporte: (fte + cargos_adicionales)/ratio. Default 0.0 = legacy.
    cargos_adicionales: float = 0.0
    # EXCEL V2-8: 'Condiciones Cadena A'!E95 = 9.5 (override manual literal, Supervisor SAC).
    # Override opt-in del FTE de soporte por rol (keyed por nombre de rol). Default vacío = legacy.
    # Valor puede ser float (todas las cadenas) o dict {canal: float} (override por canal).
    # EXCEL V2-8 CCA!G78: Director de Performance / WhatsApp = 1.0 (literal manual, canal específico).
    fte_soporte_overrides: dict = field(default_factory=dict)
    # EXCEL V2-8 CCA!C79/C80/C87: roles con incluye_en_deal=False se excluyen del FTE de soporte.
    # Derivado de roles_operativos[].incluye_en_deal en el request; nunca hardcodeado en módulos.
    roles_excluidos_deal: frozenset = field(default_factory=frozenset)
    pct_presencia: float = 1.0   # fracción que ocupa estación física en sede
    comision_pct: float = 0.0
    salario_base: Optional[float] = None  # override del salario resuelto desde parametrización activa
    incluye_examenes: bool = True
    incluye_seguridad: bool = False
    incluye_crucero: bool = False
    dias_cap_inicial: int = 10
    dias_cap_rotacion: int = 10
    tmo_segundos: float = 0.0    # tiempo medio de operación (informativo)
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
                                                  # Si se omite o es 0.0, VisionTarifas usa el último mes de esc_months como
                                                  # base de extensión (correcto para deals sin amortización de setup).
    costos_fijos_mensual: float = 0.0        # Costos Fijos x Estación mensual (No payroll Excel R248 región)
    cadena_b_mensual: float = 0.0            # Costo Cadena B mensual promedio por canal (de Excel)
    costos_financieros_mensual: float = 0.0  # ICA+GMF+Pólizas+Fin mensual promedio (de Excel)
    # K50 — volumen mensual manejado por Cadena A (denominator de CTS_A).
    # Solo inbound: J_inbound × N_inbound = J_inbound - L_cadena_b_automation (Excel PCG).
    # Para outbound se ignora — K50 usa fte directamente (convención Excel).
    # 0.0 por defecto → perfil inbound no contribuye a K50 si no se especifica.
    vol_cadena_a_mensual: float = 0.0        # J×N del Excel PCG [transacciones/mes]
    # REFACTOR costos_operativos: OPEX/TI e inversiones por perfil (No payroll sheet).
    # `opex_fijo` es un dict {"items": [...]}; `inversiones` una lista de dicts.
    # context_builder los consume para derivar opex_ti/capex por estación.
    opex_fijo: Optional[dict] = None
    inversiones: Optional[list] = None


@dataclass
class StaffRolInput:
    """
    Per-deal staff role configuration (from Condiciones Cadena A).
    Controls which support roles are active and their per-deal ratio override.
    Empty list → use parametrization defaults for all roles.
    """
    nombre: str
    activo: bool = True
    ratio_override: Optional[float] = None  # None → use parametrization default


@dataclass
class DetalleRecursoHumanoInput:
    """Valor editable que reemplaza salario y comisión HR para un cargo."""

    cargo: str
    salario_base: float
    comisiones: float = 0.0


@dataclass
class CondicionesCadenaAInput:
    perfiles: List[PerfilCadenaAInput] = field(default_factory=list)
    staff_config: List[StaffRolInput] = field(default_factory=list)
    detalles_recursos_humanos: List[DetalleRecursoHumanoInput] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Condiciones Cadena B
# ---------------------------------------------------------------------------

@dataclass
class CanalCadenaBInput:
    """Canal digital activado por el usuario con su volumen proyectado."""
    nombre: str
    modalidad: str          # "Inbound" | "Outbound" | "Digital"
    producto: str           # "Voz" | "WhatsApp" | "Token IA" | etc. (string libre)
    volumen_mensual: float
    activo: bool = True
    opex_fijo: float = 0.0  # OPEX fijo adicional específico del canal (si aplica)
    tarifa_unitaria: float = 0.0  # tarifa variable por unidad de volumen
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0
    vol_escalamiento: float = 0.0  # volumen adicional por escalamiento (Excel Panel!N51)


@dataclass
class ItemOpexConsumoInput:
    """Ítem de consumo variable / metering (Token IA, WhatsApp minuto, etc.)."""
    nombre: str
    producto: str
    modalidad: str
    canal: str
    valor_unitario: float
    cantidad: float
    tipo_cobro: str = "Unitario"


@dataclass
class MiembroEquipoSMInput:
    """Miembro del equipo S&M asignado al deal por el usuario."""
    rol: str                  # clave en master_data.salarios_por_rol
    activo: bool
    pct_dedicacion: float     # fracción de tiempo asignada a este deal


@dataclass
class DispositivoSMInput:
    tipo: str
    costo_unitario: float
    cantidad: float
    meses_amortizacion: int = 1


@dataclass
class CondicionesCadenaBInput:
    canales: List[CanalCadenaBInput] = field(default_factory=list)
    opex_consumo_variable: List[ItemOpexConsumoInput] = field(default_factory=list)
    equipo_sm: List[MiembroEquipoSMInput] = field(default_factory=list)
    dispositivos_sm: List[DispositivoSMInput] = field(default_factory=list)
    inversion_plataforma: float = 0.0   # inversión mensual amortizada en plataforma
    # FTE base del equipo S&M (Excel V2-4 "Condiciones Cadena B" celda B79).
    # El costo por rol se calcula como: salario_cargado_unitario × pct_dedicacion × fte_equipo_sm
    # Default 1.0 (modo legacy: dedicación absoluta sin multiplicador de equipo).
    fte_equipo_sm: float = 1.0
    # Amortización de dispositivos S&M.
    # True (default contable): costo = costo_unitario × cantidad / meses_amortizacion
    # False (modo Excel V2-4): costo = costo_unitario × cantidad (sin amortizar)
    # El Excel V2-4 simulador NO amortiza los dispositivos en el S&M (los suma directos).
    amortizar_dispositivos_sm: bool = True


# ---------------------------------------------------------------------------
# Condiciones Cadena C
# ---------------------------------------------------------------------------

@dataclass
class CanalCadenaCInput:
    """Canal de IA / integración activado por el usuario."""
    nombre: str
    modalidad: str
    volumen_mensual: float
    activo: bool = True
    tarifa_unitaria: float = 0.0    # tarifa por unidad de volumen facturada al cliente
    opex_fijo_integ: float = 0.0
    opex_var_integ: float = 0.0
    pct_escalamiento: float = 0.0
    costo_escalamiento: float = 0.0


@dataclass
class MiembroEquipoTransversalInput:
    rol: str
    activo: bool
    pct_dedicacion: float
    # Costo mensual por persona (override). None → lookup parametrización por rol.
    salario_cargado: Optional[float] = None


@dataclass
class EquipoHITLItemInput:
    """
    Rol del equipo HITL de Cadena C definido por ratio de cobertura.
    personas = volumen_total / ratio
    Costo = personas × salario_cargado
    """
    rol: str
    activado: bool
    ratio: float            # transacciones/mes por persona (denominador)
    salario_cargado: float  # costo mensual total por persona (base + cargas sociales)


@dataclass
class CondicionesCadenaCInput:
    canales: List[CanalCadenaCInput] = field(default_factory=list)
    equipo_transversal: List[MiembroEquipoTransversalInput] = field(default_factory=list)
    equipo_hitl: List[EquipoHITLItemInput] = field(default_factory=list)
    opex_dispositivos_por_persona: float = 0.0  # costo mensual de dispositivos por persona HITL
    inversion_anual: float = 0.0
    opex_herramientas_transversal: float = 0.0  # costo mensual herramientas equipo transversal


# ---------------------------------------------------------------------------
# Input completo del usuario — punto de entrada al motor
# ---------------------------------------------------------------------------

@dataclass
class UserInput:
    """
    Agregado raíz de todos los inputs del usuario.
    Este objeto + MasterDataRepository = SimulationContext → Motor.
    """
    panel: PanelDeControlInput
    cadena_a: CondicionesCadenaAInput
    cadena_b: CondicionesCadenaBInput
    cadena_c: CondicionesCadenaCInput
    # FASE D / Gap C3: pólizas configuradas por el usuario.
    # None → usar parametrización; [] → cero pólizas; [...] → pólizas explícitas.
    polizas: Optional[List[PolizaInput]] = None
