"""DTOs para guardar y recuperar borradores de simulación."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Primitivos compartidos
# ---------------------------------------------------------------------------

class CiudadRecurso(BaseModel):
    model_config = {"extra": "allow"}
    ciudad: Optional[str] = None
    proporcion: Optional[float] = None


class ValorMinMax(BaseModel):
    model_config = {"extra": "allow"}
    valor: Optional[float] = None
    minimo: Optional[float] = None
    maximo: Optional[float] = None


class ActualMinMax(BaseModel):
    model_config = {"extra": "allow"}
    actual: Optional[float] = None
    minimo: Optional[float] = None
    maximo: Optional[float] = None


class TipoValue(BaseModel):
    model_config = {"extra": "allow"}
    tipo: Optional[str] = None
    value: Optional[float] = None


class TarifaCanal(BaseModel):
    model_config = {"extra": "allow"}
    canal: Optional[str] = None
    tarifa: Optional[float] = None


# ---------------------------------------------------------------------------
# DatosOperativos
# ---------------------------------------------------------------------------

class DatosOperativos(BaseModel):
    model_config = {"extra": "allow"}
    servicio: Optional[str] = None
    cliente: Optional[str] = None
    tipo_cliente: Optional[str] = None
    antiguedad_cliente: Optional[str] = None
    periodo_pago: Optional[Any] = None
    fecha_inicio: Optional[str] = None
    duracion_meses: Optional[int] = None
    ciudad: Optional[str] = None
    sede: Optional[str] = None
    tarifa_diaria_capacitacion: Optional[float] = None
    crucero: Optional[float] = None
    horas_formacion_mes: Optional[float] = None
    pct_ausentismo: Optional[float] = None
    pct_rotacion: Optional[float] = None
    cons_costo_de_financiacion: Optional[float] = None
    sede_combinada_costo_formacion: Optional[bool] = None
    ciudades_recurso: Optional[List[CiudadRecurso]] = None
    tasa_ica: Optional[float] = None
    tasa_gmf: Optional[float] = None
    interacciones_gestionadas_por_fte_promedio: Optional[float] = None


# ---------------------------------------------------------------------------
# Polizas
# ---------------------------------------------------------------------------

class Poliza(BaseModel):
    model_config = {"extra": "allow"}
    nombre: Optional[str] = None
    activa: Optional[bool] = None
    pct_poliza: Optional[float] = None
    pct_atribuible: Optional[float] = None
    aplica_extension: Optional[bool] = None
    meses_extension: Optional[int] = None


# ---------------------------------------------------------------------------
# ReglasNegocio
# ---------------------------------------------------------------------------

class ReglasNegocio(BaseModel):
    model_config = {"extra": "allow"}
    margen_objetivo_cadena_a: Optional[float] = None
    margen_objetivo_cadena_b: Optional[float] = None
    contingencia_operativa: Optional[ValorMinMax] = None
    contingencia_comercial: Optional[ValorMinMax] = None
    markup: Optional[ValorMinMax] = None
    descuento_volumen: Optional[float] = None
    imprevistos: Optional[float] = None
    porcentaje_acumulado: Optional[ActualMinMax] = None
    margen_objetivo_cadena_c: Optional[float] = None
    descuento_volumen_minimo: Optional[float] = None
    descuento_volumen_maximo: Optional[float] = None


# ---------------------------------------------------------------------------
# Volumetria
# ---------------------------------------------------------------------------

class CadenasActivas(BaseModel):
    model_config = {"extra": "allow"}
    cadena_a: Optional[bool] = None
    cadena_b: Optional[bool] = None
    cadena_c: Optional[bool] = None


class ValorCanalVolumetria(BaseModel):
    model_config = {"extra": "allow"}
    unidad: Optional[str] = None
    valor: Optional[float] = None
    participacion: Optional[float] = None


class CanalVolumetria(BaseModel):
    model_config = {"extra": "allow"}
    canal: Optional[str] = None
    cadena_a: Optional[ValorCanalVolumetria] = None
    cadena_b: Optional[ValorCanalVolumetria] = None
    cadena_c: Optional[ValorCanalVolumetria] = None


class SentidoVolumetria(BaseModel):
    model_config = {"extra": "allow"}
    cadenas_activas: Optional[CadenasActivas] = None
    canales: Optional[List[CanalVolumetria]] = None


class Indexacion(BaseModel):
    model_config = {"extra": "allow"}
    componente_humano: Optional[str] = None
    componente_tecnologico: Optional[str] = None
    frecuencia: Optional[str] = None
    mes_aplicacion: Optional[int] = None
    tasa_interes_mensual: Optional[float] = None
    aplica_indexacion_tarifa: Optional[bool] = None


class Volumetria(BaseModel):
    model_config = {"extra": "allow"}
    indexacion: Optional[Indexacion] = None
    inbound: Optional[SentidoVolumetria] = None
    outbound: Optional[SentidoVolumetria] = None


# ---------------------------------------------------------------------------
# EscenariosComerciales
# ---------------------------------------------------------------------------

class EscenarioComercial(BaseModel):
    model_config = {"extra": "allow"}
    escenario: Optional[Any] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    modelo_cobro: Optional[str] = None
    componente_fijo: Optional[str] = None
    proporcion_componente_fijo: Optional[float] = None
    componente_variable: Optional[str] = None
    proporcion_componente_variable: Optional[float] = None


# ---------------------------------------------------------------------------
# CondicionesCadenaA
# ---------------------------------------------------------------------------

class CalculoConversionFte(BaseModel):
    model_config = {"extra": "allow"}
    tmo: Optional[float] = None
    tmo_promedio_seg: Optional[float] = None
    horas: Optional[float] = None
    interacciones_por_fte_promedio: Optional[float] = None


class CargoAdicional(BaseModel):
    model_config = {"extra": "allow"}
    cargo: Optional[str] = None
    salario_base: Optional[float] = None
    ratio: Optional[float] = None


class RolOperativo(BaseModel):
    model_config = {"extra": "allow"}
    incluye_en_deal: Optional[bool] = None
    rol: Optional[str] = None
    ratio: Optional[float] = None
    fte_calculado: Optional[float] = None
    salario_base_rol: Optional[float] = None
    comision_rol: Optional[float] = None


class CapacitacionPerfil(BaseModel):
    model_config = {"extra": "allow"}
    dias_capacitacion_perfil: Optional[int] = None
    por_capacitacion_mes: Optional[float] = None
    incluye_costo_examenes_ingreso: Optional[bool] = None
    incluye_costo_examenes_rotacion: Optional[bool] = None
    incluye_costo_capacitacion_anual: Optional[bool] = None
    incluye_estudio_seguridad_ingreso: Optional[bool] = None
    incluye_estudio_seguridad_rotacion: Optional[bool] = None
    incluye_estudio_seguridad_final_ingreso: Optional[bool] = None
    incluye_estudio_seguridad_final_rotacion: Optional[bool] = None
    crucero_mensual: Optional[float] = None


class ItemOpexFijo(BaseModel):
    model_config = {"extra": "allow"}
    concepto: Optional[str] = None
    costo: Optional[float] = None
    cantidad: Optional[float] = None
    costo_totalizado: Optional[float] = None


class CalcHorasStaffing(BaseModel):
    model_config = {"extra": "allow"}
    semanas_mes: Optional[float] = None
    horas_semanales: Optional[float] = None
    ausentismo_pago: Optional[float] = None


class Staffing(BaseModel):
    model_config = {"extra": "allow"}
    analista_staffing: Optional[float] = None
    supervisores: Optional[float] = None
    ausentismo_cem: Optional[float] = None
    calculo_horas_staffing: Optional[CalcHorasStaffing] = None


class OpexFijo(BaseModel):
    model_config = {"extra": "allow"}
    items: Optional[List[ItemOpexFijo]] = None
    staffing: Optional[Staffing] = None


class InversionCadenaA(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    meses_a_diferir: Optional[int] = None
    precio_mensual: Optional[float] = None
    es_precio_total: Optional[bool] = None
    cantidad: Optional[int] = None


class PerfilCadenaA(BaseModel):
    model_config = {"extra": "allow"}
    nombre: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    fte: Optional[float] = None
    cargos_adicionales: Optional[List[CargoAdicional]] = None
    fte_soporte_overrides: Optional[Dict[str, Any]] = None
    pct_presencia: Optional[float] = None
    salario_base: Optional[float] = None
    comision_pct: Optional[float] = None
    comision_mensual: Optional[float] = None
    estaciones_presenciales: Optional[float] = None
    roles_operativos: Optional[List[RolOperativo]] = None
    capacitacion: Optional[CapacitacionPerfil] = None
    opex_fijo: Optional[OpexFijo] = None
    inversiones: Optional[List[InversionCadenaA]] = None
    vol_cadena_a_mensual: Optional[float] = None
    incluye_crucero: Optional[bool] = None
    no_payroll_mensual: Optional[float] = None


class DetalleRecursoHumano(BaseModel):
    model_config = {"extra": "allow"}
    cargo: Optional[str] = None
    salario_base: Optional[float] = None
    comisiones: Optional[float] = None


class CondicionesCadenaA(BaseModel):
    model_config = {"extra": "allow"}
    Calculo_conversion_fte_interacciones: Optional[CalculoConversionFte] = None
    perfiles: Optional[List[PerfilCadenaA]] = None
    detalles_recursos_humanos: Optional[List[DetalleRecursoHumano]] = None


# ---------------------------------------------------------------------------
# CondicionesCadenaB
# ---------------------------------------------------------------------------

class ItemOpexB(BaseModel):
    model_config = {"extra": "allow"}
    rubro: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    producto: Optional[str] = None
    tipo_de_cobro: Optional[str] = None
    tipo_de_gasto: Optional[str] = None
    valor: Optional[float] = None
    cantidad: Optional[float] = None
    valor_total: Optional[float] = None


class OpexCadenaB(BaseModel):
    model_config = {"extra": "allow"}
    items: Optional[List[ItemOpexB]] = None


class InversionCapexB(BaseModel):
    model_config = {"extra": "allow"}
    rubro: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    tipo_de_cobro: Optional[str] = None
    valor: Optional[float] = None
    cantidad: Optional[float] = None
    meses_a_diferir_inversion: Optional[int] = None
    valor_total: Optional[float] = None
    valor_mes_actual: Optional[float] = None


class RolEquipo(BaseModel):
    model_config = {"extra": "allow"}
    rol: Optional[str] = None
    activado: Optional[bool] = None
    dedicacion: Optional[float] = None
    fte: Optional[float] = None


class DispositivoRequeridoB(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    cantidad_atribuible_a_la_operacion: Optional[float] = None


class EquipoSoporteMantenimiento(BaseModel):
    model_config = {"extra": "allow"}
    fte: Optional[float] = None
    roles: Optional[List[RolEquipo]] = None
    dispositivos_requeridos: Optional[List[DispositivoRequeridoB]] = None


class TarifasPorCanal(BaseModel):
    model_config = {"extra": "allow"}
    inbound: Optional[List[TarifaCanal]] = None
    outbound: Optional[List[TarifaCanal]] = None


class TasaEscalItem(BaseModel):
    model_config = {"extra": "allow"}
    canal: Optional[str] = None
    tasa: Optional[float] = None
    cts_cadena_a: Optional[float] = None


class TasaEscalamiento(BaseModel):
    model_config = {"extra": "allow"}
    tarifa_de_escalamiento_indbound: Optional[TipoValue] = None
    tarifa_de_escalamiento_outbound: Optional[TipoValue] = None
    inbound: Optional[List[TasaEscalItem]] = None
    outbound: Optional[List[TasaEscalItem]] = None


class CostoVariableCadenaB(BaseModel):
    model_config = {"extra": "allow"}
    tarifas_por_canal: Optional[TarifasPorCanal] = None
    tasa_escalamiento: Optional[TasaEscalamiento] = None


class RolHitl(BaseModel):
    model_config = {"extra": "allow"}
    rol: Optional[str] = None
    activado: Optional[bool] = None
    ratio: Optional[float] = None
    personas: Optional[float] = None


class DispositivoHitlB(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    cantidad_atribuible: Optional[float] = None


class HitlCadenaB(BaseModel):
    model_config = {"extra": "allow"}
    total_volumen_cadena_b: Optional[float] = None
    equipo: Optional[List[RolHitl]] = None
    dispositivos_requeridos: Optional[List[DispositivoHitlB]] = None


class CondicionesCadenaB(BaseModel):
    model_config = {"extra": "allow"}
    opex: Optional[OpexCadenaB] = None
    inversiones_capex: Optional[List[InversionCapexB]] = None
    equipo_soporte_mantenimiento: Optional[EquipoSoporteMantenimiento] = None
    costo_variable: Optional[CostoVariableCadenaB] = None
    hitl: Optional[HitlCadenaB] = None


# ---------------------------------------------------------------------------
# CondicionesCadenaC
# ---------------------------------------------------------------------------

class ItemTarifaProveedor(BaseModel):
    model_config = {"extra": "allow"}
    proveedor: Optional[str] = None
    servicio: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    tipo_de_cobro: Optional[str] = None
    valor: Optional[float] = None
    cantidad: Optional[float] = None
    valor_total: Optional[float] = None


class TarifaProveedorCanal(BaseModel):
    model_config = {"extra": "allow"}
    items: Optional[List[ItemTarifaProveedor]] = None


class InversionCapexC(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    tipo_de_cobro: Optional[str] = None
    tipo_de_gasto: Optional[str] = None
    valor: Optional[float] = None
    cantidad: Optional[float] = None
    meses_a_diferir: Optional[int] = None
    valor_total: Optional[float] = None
    valor_mensual: Optional[float] = None


class RolRecursoHumano(BaseModel):
    model_config = {"extra": "allow"}
    rol: Optional[str] = None
    activado: Optional[bool] = None
    dedicacion: Optional[float] = None
    fte: Optional[float] = None
    salario_cargado: Optional[float] = None


class ItemOpexRHT(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    cantidad_atribuible: Optional[float] = None


class RecursoHumanoTransversal(BaseModel):
    model_config = {"extra": "allow"}
    fte: Optional[float] = None
    roles: Optional[List[RolRecursoHumano]] = None
    opex: Optional[List[ItemOpexRHT]] = None


class ItemOpexCadenaC(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    tipo_de_cobro: Optional[str] = None
    tipo_de_gasto: Optional[str] = None
    valor: Optional[float] = None
    cantidad: Optional[float] = None
    valor_total: Optional[float] = None


class CostoVariableCadenaC(BaseModel):
    model_config = {"extra": "allow"}
    tarifas_por_canal: Optional[TarifasPorCanal] = None
    tasa_escalamiento: Optional[TasaEscalamiento] = None
    opex_items: Optional[List[ItemOpexCadenaC]] = None


class ItemOpexHitlC(BaseModel):
    model_config = {"extra": "allow"}
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    cantidad_atribuible: Optional[float] = None


class HitlCadenaC(BaseModel):
    model_config = {"extra": "allow"}
    total_volumen_cadena_c: Optional[float] = None
    equipo: Optional[List[RolHitl]] = None
    opex: Optional[List[ItemOpexHitlC]] = None


class CondicionesCadenaC(BaseModel):
    model_config = {"extra": "allow"}
    tarifa_proveedor_canal: Optional[TarifaProveedorCanal] = None
    inversiones_capex: Optional[List[InversionCapexC]] = None
    recurso_humano_transversal: Optional[RecursoHumanoTransversal] = None
    costo_variable: Optional[CostoVariableCadenaC] = None
    hitl: Optional[HitlCadenaC] = None


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class SimulationDraftRequest(BaseModel):
    """Body para POST /simulation/draft — crea un nuevo borrador."""

    client_id: Optional[str] = None
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    user_id: str = "anonymous"
    datos_operativos: Optional[DatosOperativos] = None
    polizas: Optional[List[Poliza]] = None
    reglas_negocio: Optional[ReglasNegocio] = None
    volumetria: Optional[Volumetria] = None
    escenarios_comerciales: Optional[List[EscenarioComercial]] = None
    condiciones_cadena_a: Optional[CondicionesCadenaA] = None
    condiciones_cadena_b: Optional[CondicionesCadenaB] = None
    condiciones_cadena_c: Optional[CondicionesCadenaC] = None


class SimulationDraftUpdateRequest(BaseModel):
    """Body para PUT /simulation/draft/{id} — actualiza secciones del borrador.

    Solo las secciones presentes (no-None) reemplazan la versión almacenada.
    Las secciones ausentes o None se conservan tal como estaban.
    """

    client_id: Optional[str] = None
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    user_id: Optional[str] = None
    datos_operativos: Optional[DatosOperativos] = None
    polizas: Optional[List[Poliza]] = None
    reglas_negocio: Optional[ReglasNegocio] = None
    volumetria: Optional[Volumetria] = None
    escenarios_comerciales: Optional[List[EscenarioComercial]] = None
    condiciones_cadena_a: Optional[CondicionesCadenaA] = None
    condiciones_cadena_b: Optional[CondicionesCadenaB] = None
    condiciones_cadena_c: Optional[CondicionesCadenaC] = None


class SimulationDraftResponse(BaseModel):
    """Response del draft — pass-through de lo almacenado, sin re-validar secciones."""
    model_config = {"extra": "allow"}

    id: str
    client_id: Optional[str] = None
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    status: str
    user_id: str
    version: int
    created_at: str
    updated_at: str
    # Secciones como Any: el draft almacena cualquier estructura sin re-validar tipos.
    # La validación ocurre solo en el Request (POST/PUT), no en la lectura.
    datos_operativos: Optional[Any] = None
    polizas: Optional[Any] = None
    reglas_negocio: Optional[Any] = None
    volumetria: Optional[Any] = None
    escenarios_comerciales: Optional[Any] = None
    condiciones_cadena_a: Optional[Any] = None
    condiciones_cadena_b: Optional[Any] = None
    condiciones_cadena_c: Optional[Any] = None


__all__ = [
    # Primitivos
    "CiudadRecurso", "ValorMinMax", "ActualMinMax", "TipoValue", "TarifaCanal",
    # DatosOperativos
    "DatosOperativos",
    # Polizas
    "Poliza",
    # ReglasNegocio
    "ReglasNegocio",
    # Volumetria
    "CadenasActivas", "ValorCanalVolumetria", "CanalVolumetria",
    "SentidoVolumetria", "Indexacion", "Volumetria",
    # EscenariosComerciales
    "EscenarioComercial",
    # CadenaA
    "CalculoConversionFte", "CargoAdicional", "RolOperativo",
    "CapacitacionPerfil", "ItemOpexFijo", "CalcHorasStaffing",
    "Staffing", "OpexFijo", "InversionCadenaA", "PerfilCadenaA",
    "DetalleRecursoHumano", "CondicionesCadenaA",
    # CadenaB
    "ItemOpexB", "OpexCadenaB", "InversionCapexB", "RolEquipo",
    "DispositivoRequeridoB", "EquipoSoporteMantenimiento",
    "TarifasPorCanal", "TasaEscalItem", "TasaEscalamiento",
    "CostoVariableCadenaB", "RolHitl", "DispositivoHitlB",
    "HitlCadenaB", "CondicionesCadenaB",
    # CadenaC
    "ItemTarifaProveedor", "TarifaProveedorCanal", "InversionCapexC",
    "RolRecursoHumano", "ItemOpexRHT", "RecursoHumanoTransversal",
    "ItemOpexCadenaC", "CostoVariableCadenaC", "ItemOpexHitlC",
    "HitlCadenaC", "CondicionesCadenaC",
    # Request / Response
    "SimulationDraftRequest",
    "SimulationDraftUpdateRequest",
    "SimulationDraftResponse",
]
