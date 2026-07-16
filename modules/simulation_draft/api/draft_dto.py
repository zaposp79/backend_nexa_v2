"""DTOs para guardar y recuperar borradores de simulación (Panel + Cadenas A/B/C)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CadenasActivas(BaseModel):
    cadena_a: bool = False
    cadena_b: bool = False
    cadena_c: bool = False


class PanelDeControlInput(BaseModel):
    model_config = {"extra": "allow"}

    cliente: Optional[str] = None
    tipo_cliente: Optional[str] = None
    linea_negocio: Optional[str] = None
    ciudad: Optional[str] = None
    sede: Optional[str] = None
    fecha_inicio: Optional[str] = None
    meses_contrato: Optional[int] = None
    margen: Optional[float] = None
    op_cont: Optional[float] = None
    com_cont: Optional[float] = None
    markup: Optional[float] = None
    descuento: Optional[float] = None
    periodo_pago_dias: Optional[int] = None
    activa_financiacion: Optional[bool] = None
    antiguedad_cliente: Optional[str] = None
    componente_indexacion_humano: Optional[str] = None
    componente_indexacion_tecnologico: Optional[str] = None
    tasa_ica: Optional[float] = None
    tasa_gmf: Optional[float] = None
    tasa_mensual_financ: Optional[float] = None
    pct_rotacion: Optional[float] = None
    pct_ausentismo: Optional[float] = None
    aplica_ley_1819: Optional[bool] = None
    cadenas_activas: Optional[CadenasActivas] = None


class PerfilCadenaA(BaseModel):
    # extra="allow" preserva campos de anotación (_comment, _k50_contrib, etc.)
    model_config = {"extra": "allow"}

    nombre: Optional[str] = None
    rol: Optional[str] = None
    canal: Optional[str] = None
    modalidad: Optional[str] = None
    fte: Optional[float] = None
    pct_presencia: Optional[float] = None
    comision_pct: Optional[float] = None
    salario_base: Optional[float] = None
    incluye_examenes: Optional[bool] = None
    incluye_seguridad: Optional[bool] = None
    incluye_crucero: Optional[bool] = None
    dias_cap_inicial: Optional[int] = None
    dias_cap_rotacion: Optional[int] = None
    modelo_cobro: Optional[str] = None
    pct_fijo: Optional[float] = None
    no_payroll_mensual: Optional[float] = None
    vol_cadena_a_mensual: Optional[float] = None


class CondicionesCadenaA(BaseModel):
    perfiles: Optional[List[PerfilCadenaA]] = None


class CanalCadenaB(BaseModel):
    model_config = {"extra": "allow"}

    nombre: Optional[str] = None
    modalidad: Optional[str] = None
    producto: Optional[str] = None
    volumen_mensual: Optional[float] = None
    tarifa_unitaria: Optional[float] = None
    pct_escalamiento: Optional[float] = None
    costo_escalamiento: Optional[float] = None
    opex_fijo: Optional[float] = None
    activo: Optional[bool] = None


class CondicionesCadenaB(BaseModel):
    canales: Optional[List[CanalCadenaB]] = None
    fte_equipo_sm: Optional[float] = None
    amortizar_dispositivos_sm: Optional[bool] = None


class CanalCadenaC(BaseModel):
    model_config = {"extra": "allow"}

    nombre: Optional[str] = None
    modalidad: Optional[str] = None
    producto: Optional[str] = None
    volumen_mensual: Optional[float] = None
    tarifa_unitaria: Optional[float] = None
    pct_escalamiento: Optional[float] = None
    costo_escalamiento: Optional[float] = None
    opex_fijo: Optional[float] = None
    activo: Optional[bool] = None


class CondicionesCadenaC(BaseModel):
    canales: Optional[List[CanalCadenaC]] = None
    fte_equipo_sm: Optional[float] = None
    amortizar_dispositivos_sm: Optional[bool] = None


class SimulationDraftRequest(BaseModel):
    """Body para POST /simulation/draft — crea un nuevo borrador."""

    user_id: str = "anonymous"
    client_id: str
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    panel_de_control: Optional[PanelDeControlInput] = None
    condiciones_cadena_a: Optional[CondicionesCadenaA] = None
    condiciones_cadena_b: Optional[CondicionesCadenaB] = None
    condiciones_cadena_c: Optional[CondicionesCadenaC] = None


class SimulationDraftUpdateRequest(BaseModel):
    """Body para PUT /simulation/draft/{id} — actualiza secciones del borrador.

    Solo las secciones presentes (no-None) reemplazan la versión almacenada.
    Las secciones ausentes o None se conservan tal como estaban.

    client_id es opcional: si se envía, permite cambiar la partición del documento.
    El client_id final siempre se sincroniza con panel_de_control.cliente si existe.
    """

    user_id: Optional[str] = None
    client_id: Optional[str] = None
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    panel_de_control: Optional[PanelDeControlInput] = None
    condiciones_cadena_a: Optional[CondicionesCadenaA] = None
    condiciones_cadena_b: Optional[CondicionesCadenaB] = None
    condiciones_cadena_c: Optional[CondicionesCadenaC] = None


class SimulationDraftResponse(BaseModel):
    id: str
    user_id: str
    client_id: str
    id_hr: Optional[str] = None
    id_gn: Optional[str] = None
    id_op: Optional[str] = None
    version: int
    status: str
    created_at: str
    updated_at: str
    panel_de_control: Optional[PanelDeControlInput] = None
    condiciones_cadena_a: Optional[CondicionesCadenaA] = None
    condiciones_cadena_b: Optional[CondicionesCadenaB] = None
    condiciones_cadena_c: Optional[CondicionesCadenaC] = None


__all__ = [
    "CadenasActivas",
    "PanelDeControlInput",
    "PerfilCadenaA",
    "CondicionesCadenaA",
    "CanalCadenaB",
    "CondicionesCadenaB",
    "CanalCadenaC",
    "CondicionesCadenaC",
    "SimulationDraftRequest",
    "SimulationDraftUpdateRequest",
    "SimulationDraftResponse",
]
