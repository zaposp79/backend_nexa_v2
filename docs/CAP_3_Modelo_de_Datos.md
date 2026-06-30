# CAPÍTULO 3: MODELO DE DATOS

**Autor:** Equipo de Ingeniería NEXA  
**Versión:** 2.7 (Excel V2-7, API v1, Engine v2)  
**Última actualización:** 31 de mayo de 2026  
**Scope:** 10-12 páginas | ~7500 palabras

---

## Tabla de Contenidos

- [3.1 Contratos de Entrada (Request DTOs)](#31-contratos-de-entrada-request-dtos)
- [3.2 Modelos de Dominio (Representaciones Internas)](#32-modelos-de-dominio-representaciones-internas)
- [3.3 Modelos de Resultado (Outputs del Calculador)](#33-modelos-de-resultado-outputs-del-calculador)
- [3.4 Modelos de Visión (Outputs Estructurados)](#34-modelos-de-visión-outputs-estructurados)
- [3.5 Contratos de Salida (Response DTOs)](#35-contratos-de-salida-response-dtos)
- [3.6 Enums y Objetos de Valor](#36-enums-y-objetos-de-valor)

---

## 3.1 Contratos de Entrada (Request DTOs)

### Propósito

Los contratos de entrada definen la estructura que recibe el endpoint `POST /api/v1/simulation/calculate`. Son **frozen** (inmutables), **strict** (sin campos extra) y aplican **validadores cross-field** para garantizar consistencia semántica.

**Ubicación:** `/contracts/api_v1/request/`

### 3.1.1 EntryDataV1 — Raíz de la Solicitud

```python
class EntryDataV1(BaseModel):
    """
    Frozen public request contract.
    Punto de entrada único del motor de precios.
    """
    panel: PanelDeControlRequestV1         # Requerido
    cadena_a: Optional[CadenaARequestV1]   # Opcional
    cadena_b: Optional[CadenaBRequestV1]   # Opcional
    cadena_c: Optional[CadenaCRequestV1]   # Opcional
    cadenas_activas: Set[Literal["A","B","C"]]  # Inferido si falta
    escenarios: List[EscenarioComercialV1]      # Opcional
    metadata: Optional[ContractMetadataV1]      # Opcional
```

| Campo | Tipo | Requerido | Descripción | Origen | Ejemplo |
|-------|------|-----------|-------------|--------|---------|
| `panel` | `PanelDeControlRequestV1` | Sí | Parámetros maestros del deal | Excel Panel | `{...}` |
| `cadena_a` | `CadenaARequestV1` | No | Condiciones de Cadena A (nómina + staff) | Excel Condiciones | `{perfiles: [...]}` |
| `cadena_b` | `CadenaBRequestV1` | No | Condiciones de Cadena B (plataforma digital) | Excel Condiciones | `{canales: [...]}` |
| `cadena_c` | `CadenaCRequestV1` | No | Condiciones de Cadena C (IA/integración) | Excel Condiciones | `{canales: [...]}` |
| `cadenas_activas` | `Set[ChainLiteral]` | No* | Set de cadenas activas (inferido si omite) | Deducido de estructura | `{"A", "B"}` |
| `escenarios` | `List[EscenarioComercialV1]` | No | Escenarios de prueba | Excel Escenarios | `[{nombre: "...", canal: "..."}]` |
| `metadata` | `ContractMetadataV1` | No | Metadata de solicitud (client_id, request_id, etc.) | Cliente | `{client_id: "ABC"}` |

**Validación Cross-Field:**
1. **Al menos una cadena activa:** Si omite `cadenas_activas`, el validador infiere del contenido de `cadena_a`/`b`/`c`. Si todas son null, error.
2. **Escenarios consistentes:** Cada escenario referencia un `canal`/`modalidad` declarado en `cadena_a.perfiles`. Si no existe, error.
3. **Margen B requerido cuando Cadena B activa:** Si `cadenas_activas` contiene "B" y `panel.margen_b` es None, warning soft (motor tiene default).

**Ejemplo JSON:**
```json
{
  "panel_de_control": {
    "cliente": "Acme Corp",
    "meses_contrato": 36,
    "margen": 0.25,
    "margen_b": 0.30,
    "margen_c": 0.20,
    "imprevistos": 0.05
  },
  "condiciones_cadena_a": {
    "perfiles": [
      {
        "nombre": "Agente Inbound",
        "canal": "WhatsApp",
        "modalidad": "Inbound",
        "fte": 5.0,
        "salario_base": 1200000,
        "comision_pct": 0.10,
        "incluye_examenes": true,
        "incluye_seguridad": false
      }
    ]
  },
  "cadenas_activas": ["A", "B"]
}
```

### 3.1.2 PanelDeControlRequestV1 — Parámetros Maestros

**Ubicación:** `contracts/api_v1/request/panel.py`

| Campo | Tipo | Rango | Descripción | V2-7 | Ejemplo |
|-------|------|-------|-------------|------|---------|
| `cliente` | `str` | - | Nombre del cliente | Excel Panel C5 | "Acme Corp" |
| `tipo_cliente` | `str` | - | Clasificación (PJ/PME/Startup) | Panel C7 | "PJ" |
| `linea_negocio` | `str` | - | Línea de negocio | Panel C8 | "BPO Inbound" |
| `ciudad` | `str` | - | Ciudad | Panel C9 | "Bogotá" |
| `sede` | `str` | - | Nombre de sede | Panel C10 | "Centro" |
| `fecha_inicio` | `str` | - | Fecha inicio (YYYY-MM-DD) | Panel C11 | "2025-06-01" |
| `meses_contrato` | `int` | 1-120 | Duración del contrato | Panel C11 | 36 |
| `margen` | `float` | -1.0 to 1.0 | Margen objetivo Cadena A | Panel C63 | 0.25 |
| `op_cont` | `float` | 0.0 to 1.0 | Contingencia operativa | Panel C67 | 0.05 |
| `com_cont` | `float` | 0.0 to 1.0 | Contingencia comercial | Panel C68 | 0.05 |
| `markup` | `float` | -1.0 to 10.0 | Markup adicional a ingreso | Panel C69 | 0.10 |
| `descuento` | `float` | 0.0 to 1.0 | Descuento por volumen | Panel C70 | 0.05 |
| `periodo_pago_dias` | `int` | 0-365 | Días de payment terms | Panel C72 | 90 |
| `activa_financiacion` | `bool` | - | ¿Activar financiación? | Panel C44 | true |
| `antiguedad_cliente` | `str` | - | Riesgo (Nuevo/Existente) | Panel C13 | "Existente" |
| `componente_indexacion_humano` | `str` | - | Índice de salarios | Panel C14 | "IPC" |
| `componente_indexacion_tecnologico` | `str` | - | Índice tecnología | Panel C15 | "IPC" |
| `tasa_ica` | `float` | 0.0 to 1.0 | Tasa ICA | Panel C55 | 0.004 |
| `tasa_gmf` | `float` | 0.0 to 1.0 | Tasa GMF | Panel C56 | 0.004 |
| `tasa_mensual_financ` | `float` | 0.0 to 1.0 | Tasa mensual financiación | Panel C57 | 0.0153 |
| `pct_rotacion` | `float` | 0.0 to 1.0 | % rotación anual | Panel C58 | 0.30 |
| `pct_ausentismo` | `float` | 0.0 to 1.0 | % ausentismo | Panel C59 | 0.10 |
| `aplica_ley_1819` | `bool` | - | [LEGADO] Ignorado | - | true |
| **V2-7 NUEVOS** |
| `margen_b` | `float` | 0.0 to 1.0 | Margen objetivo Cadena B **NEW** | Panel D63 | 0.30 |
| `margen_c` | `float` | 0.0 to 1.0 | Margen objetivo Cadena C **NEW** | Panel E63 | 0.20 |
| `mes_ajuste_indexacion` | `int` | 1-12 | Mes de ajuste anual **NEW** | Panel L9 | 6 |
| `tasa_interes_mensual` | `float` | 0.0 to 1.0 | Tasa de interés mensual **NEW** | Panel L10 | 0.0153 |
| `imprevistos` | `float` | 0.0 to 1.0 | % imprevistos de ingreso **NEW** | Panel C73 | 0.05 |

**Post-Refactor** (campos renombrados en V2-7):
- `tasa_mensual_financ` → ahora validado como `0.0 to 1.0` (antes sin límite)
- Nuevos campos reemplazan constantes hardcodeadas del engine v1

**Validaciones:**
```
meses_contrato: 1 <= valor <= 120
margen, margen_b, margen_c: -1.0 <= valor <= 1.0
tasa_*: 0.0 <= valor <= 1.0
periodo_pago_dias: 0 <= valor <= 365
mes_ajuste_indexacion: 1 <= valor <= 12 (cuando presente)
```

### 3.1.3 CadenaARequestV1 — Perfiles Operativos

**Ubicación:** `contracts/api_v1/request/cadena_a.py`

```python
class PerfilCadenaAV1(BaseModel):
    """Un operador / perfil de Cadena A."""
    nombre: str
    rol: str = "Agente Basico"
    canal: str
    modalidad: str = "Inbound"
    fte: float               # 0.0 o mayor
    pct_presencia: float     # 0.0 a 1.0
    comision_pct: float      # 0.0 a 1.0
    salario_base: Optional[float]   # ge=0.0
    incluye_examenes: bool
    incluye_seguridad: bool
    incluye_crucero: bool
    no_payroll_mensual: float       # ge=0.0
    dias_cap_inicial: int    # 0-365
    dias_cap_rotacion: int   # 0-365
    tmo_segundos: float      # ge=0.0
    modelo_cobro: ModeloCobroLiteral  # ver enum
    pct_fijo: float          # 0.0 a 1.0
    vol_cadena_a_mensual: float      # transacciones/mes
```

| Campo | Tipo | Rango | Descripción | Origen | Ejemplo |
|-------|------|-------|-------------|--------|---------|
| `nombre` | `str` | - | Nombre descriptivo | Excel | "Agente Inbound" |
| `rol` | `str` | - | Rol laboral | HR Catálogo | "Agente Basico" |
| `canal` | `str` | - | Canal operativo (WhatsApp, Email, etc.) | Excel Inputs | "WhatsApp" |
| `modalidad` | `str` | - | Tipo de flujo (Inbound/Outbound) | Excel | "Inbound" |
| `fte` | `float` | >=0.0 | Full-Time Equivalents | Excel Panel M19:M25 | 5.0 |
| `pct_presencia` | `float` | 0.0-1.0 | % de tiempo en estación | Excel | 0.90 |
| `comision_pct` | `float` | 0.0-1.0 | % comisión sobre volumen | Excel | 0.10 |
| `salario_base` | `float` | >=0.0 | Salario mensual base (COP) | Excel W39-W40 | 1200000 |
| `incluye_examenes` | `bool` | - | ¿Realiza exámenes médicos? | Excel | true |
| `incluye_seguridad` | `bool` | - | ¿Costo estudio seguridad? | Excel | false |
| `incluye_crucero` | `bool` | - | ¿Tarifa de crucero? | Excel C17 | false |
| `no_payroll_mensual` | `float` | >=0.0 | No-payroll asignado a este perfil (COP/mes) | Excel | 50000 |
| `dias_cap_inicial` | `int` | 0-365 | Días de capacitación inicial | Excel P5 | 10 |
| `dias_cap_rotacion` | `int` | 0-365 | Días de capacitación anual | Excel P6 | 10 |
| `tmo_segundos` | `float` | >=0.0 | Tiempo medio de operación (segundos) | Excel | 180.0 |
| `modelo_cobro` | `ModeloCobroLiteral` | Enum | Modo de facturación | Excel Inputs C34 | "Fijo FTE" |
| `pct_fijo` | `float` | 0.0-1.0 | Porción fija en modelo híbrido | Excel | 0.80 |
| `vol_cadena_a_mensual` | `float` | >=0.0 | Volumen mensual de transacciones | Excel J51×N51 | 5000.0 |

**ModeloCobroLiteral Enum:**
```python
Literal[
    "Fijo FTE",        # Tarifa fija por FTE
    "Variable",        # Variable según volumen
    "Híbrido",         # Combinación fija+variable
    "Volumen",         # Alias: Por Volumen
    "Por Volumen",     # Facturación por volumen
    "Por Comisión",    # Puro comisional
]
```

### 3.1.4 CadenaBRequestV1 — Plataforma Digital

**Ubicación:** `contracts/api_v1/request/cadena_b.py`

```python
class CadenaBRequestV1(BaseModel):
    canales: List[CanalCadenaBV1]
    opex_consumo_variable: List[ItemOpexConsumoV1]
    equipo_sm: List[MiembroEquipoSMV1]
    dispositivos_sm: List[DispositivoSMV1]
    inversion_plataforma: float
    fte_equipo_sm: float
    amortizar_dispositivos_sm: bool
```

**CanalCadenaBV1:**

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `nombre` | `str` | - | Nombre del canal (SMS, WhatsApp API, etc.) | "WhatsApp API" |
| `modalidad` | `str` | - | Modalidad (Sync/Async) | "Async" |
| `producto` | `str` | - | Producto asociado (libre) | "Mensajería" |
| `volumen_mensual` | `float` | >=0.0 | Volumen transaccional (msgs/mes) | 100000.0 |
| `activo` | `bool` | - | ¿Canal activo? | true |
| `opex_fijo` | `float` | >=0.0 | OPEX fijo mensual (COP) | 500000 |
| `tarifa_unitaria` | `float` | >=0.0 | Tarifa por unidad (COP/msg) | 150.0 |
| `pct_escalamiento` | `float` | 0.0-1.0 | % escalamiento volumen | 0.20 |
| `costo_escalamiento` | `float` | >=0.0 | Costo por escalamiento (COP) | 100000 |

**ItemOpexConsumoV1:** (Consumos variables / metering)

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `nombre` | `str` | - | Nombre del item (Token IA, minutos, etc.) | "Tokens GPT" |
| `producto` | `str` | - | Tipo de producto (libre) | "IA" |
| `modalidad` | `str` | - | Modalidad (metering strategy) | "Unitario" |
| `canal` | `str` | - | Canal afectado | "WhatsApp" |
| `valor_unitario` | `float` | >=0.0 | Costo unitario (COP/unit) | 10.0 |
| `cantidad` | `float` | >=0.0 | Cantidad mensual | 50000.0 |
| `tipo_cobro` | `str` | - | Tipo (Unitario, Fijo, Variable) | "Unitario" |

**MiembroEquipoSMV1 & DispositivoSMV1:**

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `rol` (equipo) | `str` | - | Rol del miembro | "Tech Lead" |
| `activo` (equipo) | `bool` | - | ¿Activo? | true |
| `pct_dedicacion` (equipo) | `float` | 0.0-1.0 | % dedicación | 0.50 |
| `tipo` (dispositivo) | `str` | - | Tipo (Laptop, Monitor, etc.) | "Laptop" |
| `costo_unitario` (dispositivo) | `float` | >=0.0 | Costo unitario | 5000000 |
| `cantidad` (dispositivo) | `float` | >=0.0 | Cantidad | 2.0 |
| `meses_amortizacion` (dispositivo) | `int` | 1-360 | Período de amortización | 60 |

### 3.1.5 CadenaCRequestV1 — IA e Integración

**Ubicación:** `contracts/api_v1/request/cadena_c.py`

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `canales[]` | `List[CanalCadenaCV1]` | - | Canales de integración IA | [...] |
| `equipo_transversal[]` | `List[MiembroEquipoTransversalV1]` | - | Equipo de integración | [...] |
| `inversion_anual` | `float` | >=0.0 | Inversión anual en infraestructura (COP) | 10000000 |

**CanalCadenaCV1:**

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `nombre` | `str` | - | Nombre canal IA (Claude API, GPT-4, etc.) | "Claude API" |
| `modalidad` | `str` | - | Modalidad (Realtime/Batch) | "Realtime" |
| `volumen_mensual` | `float` | >=0.0 | Volumen de llamadas/tokens | 1000000.0 |
| `activo` | `bool` | - | ¿Activo? | true |
| `opex_fijo_integ` | `float` | >=0.0 | OPEX fijo integración (COP/mes) | 1000000 |
| `opex_var_integ` | `float` | >=0.0 | OPEX variable integración (COP/mes) | 500000 |
| `pct_escalamiento` | `float` | 0.0-1.0 | % escalamiento | 0.15 |
| `costo_escalamiento` | `float` | >=0.0 | Costo escalamiento (COP) | 200000 |

### 3.1.6 EscenarioComercialV1 — Escenarios de Prueba

**Ubicación:** `contracts/api_v1/request/escenarios.py`

| Campo | Tipo | Rango | Descripción | Ejemplo |
|-------|------|-------|-------------|---------|
| `nombre` | `str` | - | Nombre del escenario | "Base Case" |
| `canal` | `str` | - | Canal referenciado | "WhatsApp" |
| `modalidad` | `str` | - | Modalidad | "Inbound" |
| `modelo_cobro` | `Optional[str]` | - | Modelo (override) | "Híbrido" |
| `margen` | `Optional[float]` | -1.0 to 1.0 | Margen scenario-specific | 0.20 |
| `parametros` | `Dict[str, Any]` | - | Parámetros libres | `{...}` |

---

## 3.2 Modelos de Dominio (Representaciones Internas)

### Propósito

Después de validar `EntryDataV1`, el sistema construye **modelos de dominio** (dataclasses) que representan el estado interno del deal. Estos son **mutables** y contienen agregaciones necesarias para el cálculo.

**Ubicación:** `/domain/models/` (panel.py, resultados.py, visions.py)

### 3.2.1 PanelDeControl (Dominio)

```python
@dataclass
class PanelDeControl:
    """Parámetros maestros del deal (parseados)."""
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
    # Campos de contexto
    ciudad: str = ""
    sede: str = ""
    antiguedad_cliente: str = ""
    pct_ausentismo: float = 0.0
    indexacion: Optional[Indexacion] = None
    # V2-7 NUEVOS
    imprevistos: float = 0.0
    margen_b: float = 0.30
    margen_c: float = 0.20
    mes_ajuste_indexacion: int = 6
    tasa_interes_mensual: float = 0.0153
    tasa_comision_administracion: float = 0.0
    complejidad_especialista: str = "ALTA"
    tarifa_diaria_capacitacion: float = 0.0
    tarifa_crucero: float = 0.0
```

### 3.2.2 PerfilCadenaA (Dominio)

```python
@dataclass
class PerfilCadenaA:
    """Un perfil operativo con agregaciones de cálculo."""
    nombre: str
    modalidad: str
    canal: str
    fte: float
    pct_presencia: float = 1.0
    salario_base: float = 0.0
    salario_cargado: float = 0.0  # salario_base + aportes patronales
    comision_pct: float = 0.0
    dias_cap_inicial: int = 0
    dias_cap_rotacion: int = 0
    tmo_segundos: float = 0.0
    incluye_examenes: bool = False
    incluye_seguridad: bool = False
    incluye_crucero: bool = False
    es_soporte: bool = False
    fte_examenes: float = 0.0
    modelo_cobro: str = "Fijo FTE"
    pct_fijo: float = 1.0
    no_payroll_mensual: float = 0.0         # Asignado a este canal
    cadena_b_mensual: float = 0.0           # Costo B asignado
    costos_financieros_mensual: float = 0.0 # Fin asignado
    tipo_carga: str = "EMPLEADO_ESTANDAR"
    vol_cadena_a_mensual: float = 0.0       # Transacciones/mes
    cargo_tipo: str = "DESCONOCIDO"
    opex_fijo_mensual: float = 0.0
    inversiones_amortizables: List[dict] = field(default_factory=list)
```

### 3.2.3 Parametros* (Dominio)

**ParametrosNomina:**

| Campo | Tipo | Descripción | Origen |
|-------|------|-------------|--------|
| `mes_inicio` | `int` | Mes inicial de cálculo | PanelDeControl |
| `mes_fin` | `int` | Mes final | meses_contrato |
| `pct_aumento_salarial` | `float` | % ajuste anual | HR Storage |
| `mes_aplicacion_aumento` | `int` | Mes de aplicación | HR Storage |
| `tarifa_dia_cap` | `float` | Tarifa diaria capacitación | Panel o HR |
| `costo_examen_medico` | `float` | Costo examen (COP) | HR Storage |
| `costo_estudio_seg` | `float` | Costo estudio seguridad (COP) | HR Storage |
| `factor_indexacion_base` | `float` | Factor acumulado año 1 | Cálculo de indexación |
| `meses_contrato` | `int` | Duración | Panel |
| `tarifa_crucero` | `float` | Tarifa crucero/agente/mes | Panel C17 |

**ParametrosNoPayroll:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `opex_ti_por_estacion` | `float` | OPEX TI mensual/estación (COP) |
| `capex_por_estacion` | `float` | CAPEX mensual/estación (COP) |
| `arriendo_por_estacion` | `float` | Arriendo mensual/estación (COP) |
| `energia_por_estacion` | `float` | Energía mensual/estación (COP) |
| `vigilancia_por_estacion` | `float` | Vigilancia mensual/estación (COP) |
| `aseo_por_estacion` | `float` | Aseo mensual/estación (COP) |
| `otros_fijos_por_estacion` | `float` | Otros costos fijos (COP) |
| `capex_inicial_por_estacion` | `float` | CAPEX inicial (COP) |
| `inversiones_amortizables` | `List[dict]` | **NEW V2-7**: Term-based CAPEX items (Excel K167/K168) |

**inversiones_amortizables** (estructura):
```python
[
  {
    "precio_mensual": 50000.0,   # Costo unitario
    "cantidad": 2.0,             # Cantidad de items
    "meses": 36,                 # Período amortización
    "factor": 1.0                # Factor aplicado
  }
]
```

**ParametrosCadenaB:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `canales` | `List[CanalCadenaB]` | Canales digitales |
| `opex_consumo_variable` | `List[ItemOpexConsumoB]` | Consumos variables (tokens, etc.) |
| `equipo_sm` | `List[MiembroEquipo]` | Equipo Support & Maintenance |
| `dispositivos_sm` | `List[DispositivoSM]` | Dispositivos SM (amortizables) |
| `costo_personal_sm` | `float` | Agregado: costo FTE (COP/mes) |
| `opex_herramientas_sm` | `float` | Agregado: herramientas (COP/mes) |
| `costo_personal_hitl` | `float` | Agregado: costo HITL (COP/mes) |
| `opex_herramientas_hitl` | `float` | Agregado: herramientas HITL (COP/mes) |
| `inversion_mensual` | `float` | Agregado: inversión amortizada (COP/mes) |

**ParametrosCadenaC:** (análogo)

### 3.2.4 PricingRequest (Contexto de Agregación)

```python
@dataclass
class PricingRequest:
    """Facade: todos los datos de entrada del motor."""
    panel: PanelDeControl
    perfiles_cadena_a: List[PerfilCadenaA]
    parametros_nomina: ParametrosNomina
    parametros_no_payroll: ParametrosNoPayroll
    cadena_b: ParametrosCadenaB
    cadena_c: ParametrosCadenaC
    parametros_calculo: ParametrosCalculo
    polizas_usuario: Optional[List[PolizaContractual]] = None
    escenarios: List[EscenarioComercial] = field(default_factory=list)
    cadenas_activas: CadenasActivas = field(default_factory=CadenasActivas)
```

---

## 3.3 Modelos de Resultado (Outputs del Calculador)

### Propósito

El calculador produce **ResultadoNomina**, **ResultadoNoPayroll**, **ResultadoCadenaB/C**, que se agregan en **CostosTotalesMes** y **PyGMensual** (P&L mensual).

**Ubicación:** `/domain/models/results.py`

### 3.3.1 ResultadoNomina — Desglose de Nómina

```python
@dataclass
class ResultadoNomina:
    salario_fijo: float = 0.0
    comisiones: float = 0.0
    capacitacion_inicial: float = 0.0      # post-refactor (V2-7)
    capacitacion_rotacion: float = 0.0     # post-refactor (V2-7)
    examenes: float = 0.0
    seguridad: float = 0.0
    crucero: float = 0.0

    @property
    def total(self) -> float:
        return (self.salario_fijo + self.comisiones + 
                self.capacitacion_inicial + self.capacitacion_rotacion + 
                self.examenes + self.seguridad + self.crucero)
```

| Campo | Tipo | Descripción | Fuente | Ejemplo |
|-------|------|-------------|--------|---------|
| `salario_fijo` | `float` | Salario base cargado (COP/mes) | NominaCalculator | 1350000 |
| `comisiones` | `float` | Comisiones sobre volumen (COP/mes) | NominaCalculator | 50000 |
| `capacitacion_inicial` | `float` | Amortización cap. inicial (COP/mes) **post-refactor** | NominaCalculator | 10000 |
| `capacitacion_rotacion` | `float` | Cap. rotación anual (COP/mes) **post-refactor** | NominaCalculator | 8000 |
| `examenes` | `float` | Exámenes médicos (COP/mes) | NominaCalculator | 5000 |
| `seguridad` | `float` | Estudio seguridad (COP/mes) | NominaCalculator | 0 |
| `crucero` | `float` | Tarifa crucero (COP/mes) | NominaCalculator | 3000 |

### 3.3.2 ResultadoNoPayroll — Infraestructura

```python
@dataclass
class ResultadoNoPayroll:
    opex_ti: float = 0.0
    capex: float = 0.0
    costos_fijos: float = 0.0

    @property
    def total(self) -> float:
        return self.opex_ti + self.capex + self.costos_fijos
```

| Campo | Tipo | Descripción | Fuente | Ejemplo |
|-------|------|-------------|--------|---------|
| `opex_ti` | `float` | OPEX infraestructura TI (COP/mes) | NoPayrollCalculator | 500000 |
| `capex` | `float` | CAPEX amortizado (COP/mes) | Term-based amortization | 50000 |
| `costos_fijos` | `float` | Otros costos fijos (arriendo, energía, etc.) (COP/mes) | NoPayrollCalculator | 200000 |

### 3.3.3 ResultadoCadenaB — Plataforma Digital

```python
@dataclass
class ResultadoCadenaB:
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    soporte_mantenimiento: float = 0.0      # post-refactor (V2-7)
    costo_variable: float = 0.0
    escalamiento: float = 0.0
    hitl: float = 0.0

    @property
    def total(self) -> float:
        return (self.opex_fijo + self.inversiones + self.soporte_mantenimiento +
                self.costo_variable + self.escalamiento + self.hitl)
```

| Campo | Tipo | Descripción | Fuente | Ejemplo |
|-------|------|-------------|--------|---------|
| `opex_fijo` | `float` | OPEX plataforma (COP/mes) | CadenaBCalculator | 500000 |
| `inversiones` | `float` | Inversión amortizada (COP/mes) | CadenaBCalculator | 100000 |
| `soporte_mantenimiento` | `float` | Equipo S&M (COP/mes) **post-refactor** | CadenaBCalculator | 200000 |
| `costo_variable` | `float` | Costo variable (tokens, msgs) (COP/mes) | CadenaBCalculator | 50000 |
| `escalamiento` | `float` | Costo escalamiento (COP/mes) | CadenaBCalculator | 30000 |
| `hitl` | `float` | Human-in-the-loop (COP/mes) | CadenaBCalculator | 100000 |

### 3.3.4 ResultadoCadenaC — IA e Integración

```python
@dataclass
class ResultadoCadenaC:
    tarifa_proveedor: float = 0.0
    opex_fijo_integ: float = 0.0
    opex_var_integ: float = 0.0
    inversiones: float = 0.0
    equipo_integ: float = 0.0
    escalamiento: float = 0.0
    hitl: float = 0.0

    @property
    def total(self) -> float:
        return (self.tarifa_proveedor + self.opex_fijo_integ + self.opex_var_integ +
                self.inversiones + self.equipo_integ + self.escalamiento + self.hitl)

    @property
    def total_pyg(self) -> float:
        """P&G value: excluye hitl, equipo_integ, opex_var_integ."""
        return (self.tarifa_proveedor + self.opex_fijo_integ +
                self.inversiones + self.escalamiento)
```

| Campo | Tipo | Descripción | Fuente | Ejemplo |
|-------|------|-------------|--------|---------|
| `tarifa_proveedor` | `float` | Tarifa IA (Claude, GPT, etc.) (COP/mes) | CadenaCCalculator | 1000000 |
| `opex_fijo_integ` | `float` | OPEX fijo integración (COP/mes) | CadenaCCalculator | 500000 |
| `opex_var_integ` | `float` | OPEX variable integración (COP/mes) | CadenaCCalculator | 200000 |
| `inversiones` | `float` | Inversión amortizada (COP/mes) | CadenaCCalculator | 100000 |
| `equipo_integ` | `float` | Equipo integración (COP/mes) | CadenaCCalculator | 150000 |
| `escalamiento` | `float` | Escalamiento (COP/mes) | CadenaCCalculator | 50000 |
| `hitl` | `float` | HITL (COP/mes) | CadenaCCalculator | 80000 |

**Nota importante:** `total_pyg` excluye `opex_var_integ`, `equipo_integ` y `hitl` porque esos componentes se incluyen en la base financiera (ICA/GMF) pero no en P&G operativo. El `total` completo se usa para cálculos financieros.

### 3.3.5 CostosTotalesMes — Agregación Mensual

```python
@dataclass
class CostosTotalesMes:
    mes: int = 0
    payroll_a: float = 0.0
    no_payroll_a: float = 0.0
    costo_b: float = 0.0
    costo_c: float = 0.0
    costo_c_fin: float = 0.0  # Full C para financieros

    @property
    def costo_a(self) -> float:
        return self.payroll_a + self.no_payroll_a

    @property
    def total(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def total_fin(self) -> float:
        """Total usando Cadena C completa para cálculos financieros."""
        return self.costo_a + self.costo_b + self.costo_c_fin
```

| Campo | Descripción |
|-------|-------------|
| `mes` | Mes del contrato (1-120) |
| `payroll_a` | Nómina Cadena A (COP) |
| `no_payroll_a` | No-payroll Cadena A (COP) |
| `costo_b` | Total Cadena B (COP) |
| `costo_c` | Total Cadena C (P&G) (COP) |
| `costo_c_fin` | Total Cadena C (financiero, incluye hidden costs) (COP) |

### 3.3.6 CostosFinancierosMes — Componente Financiero

```python
@dataclass
class CostosFinancierosMes:
    financiacion: float = 0.0
    polizas: float = 0.0
    polizas_a: float = 0.0
    polizas_b: float = 0.0
    polizas_c: float = 0.0
    ica: float = 0.0
    ica_a: float = 0.0
    ica_c: float = 0.0
    gmf: float = 0.0
    gmf_a: float = 0.0
    gmf_c: float = 0.0
    comision_administracion: float = 0.0  # NEW V2-7
    comision_admin_cadena_a: float = 0.0  # NEW V2-7
    costo_financiero_vt_cadena_a: float = 0.0  # Vision Tarifas wide

    @property
    def total(self) -> float:
        return (self.financiacion + self.polizas + self.ica + self.gmf + 
                self.comision_administracion)
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `financiacion` | `float` | Costo financiación (COP/mes) |
| `polizas` | `float` | Total pólizas (COP/mes) |
| `polizas_a` | `float` | Pólizas Cadena A (COP/mes) |
| `polizas_b` | `float` | Pólizas Cadena B (COP/mes) |
| `polizas_c` | `float` | Pólizas Cadena C (COP/mes) |
| `ica` | `float` | ICA total (COP/mes) |
| `ica_a` | `float` | ICA Cadena A (COP/mes) |
| `ica_c` | `float` | ICA Cadena C (COP/mes) |
| `gmf` | `float` | GMF total (COP/mes) |
| `gmf_a` | `float` | GMF Cadena A (COP/mes) |
| `gmf_c` | `float` | GMF Cadena C (COP/mes) |
| `comision_administracion` | `float` | Comisión admin total (COP/mes) **NEW** |
| `comision_admin_cadena_a` | `float` | Comisión admin Cadena A (COP/mes) **NEW** |
| `costo_financiero_vt_cadena_a` | `float` | VT-specific: poliza + ICA + GMF Cadena A (wider tasa) **post-refactor** |

### 3.3.7 PyGMensual — Estado de Resultados Mensual

```python
@dataclass
class PyGMensual:
    mes: int = 0
    rampup: float = 1.0
    # Ingresos por cadena
    ingreso_bruto_a: float = 0.0
    ingreso_bruto_b: float = 0.0
    ingreso_bruto_c: float = 0.0
    # Contingencias y ajustes
    contingencia_op: float = 0.0
    contingencia_com: float = 0.0
    markup_ingreso: float = 0.0
    descuento_ingreso: float = 0.0
    # Costos operativos
    payroll_a: float = 0.0
    no_payroll_a: float = 0.0
    costo_b: float = 0.0
    costo_c: float = 0.0
    costo_c_fin: float = 0.0
    # Costos financieros (detallado)
    ica: float = 0.0
    ica_a: float = 0.0
    ica_c: float = 0.0
    gmf_a: float = 0.0
    gmf_c: float = 0.0
    gmf: float = 0.0
    polizas: float = 0.0
    polizas_a: float = 0.0
    polizas_b: float = 0.0
    polizas_c: float = 0.0
    financiacion: float = 0.0
    imprevistos_ingreso: float = 0.0      # NEW V2-7
    comision_administracion: float = 0.0  # NEW V2-7
    comision_admin_cadena_a: float = 0.0  # NEW V2-7
    costo_financiero_vt_cadena_a: float = 0.0
    # Acumulados
    acum_ingreso_bruto: float = 0.0
    acum_ingreso_neto: float = 0.0
    acum_costo_total: float = 0.0
    acum_costos_financieros: float = 0.0
    acum_contribucion: float = 0.0

    @property
    def ingreso_bruto(self) -> float:
        return self.ingreso_bruto_a + self.ingreso_bruto_b + self.ingreso_bruto_c

    @property
    def ingreso_neto(self) -> float:
        return (self.ingreso_bruto + self.contingencia_op + self.contingencia_com +
                self.markup_ingreso - self.descuento_ingreso - self.imprevistos_ingreso)

    @property
    def costo_a(self) -> float:
        return self.payroll_a + self.no_payroll_a

    @property
    def costo_operativo(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def costo_total(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def costos_financieros(self) -> float:
        return self.ica + self.gmf + self.polizas + self.financiacion + self.comision_administracion

    @property
    def contribucion(self) -> float:
        return self.ingreso_neto - self.costo_total

    @property
    def utilidad_neta(self) -> float:
        return self.contribucion
```

**Diagrama de Flujo:**

```
Ingreso Bruto (A+B+C)
  + Contingencia Op
  + Contingencia Com
  + Markup
  - Descuento
  - Imprevistos
  = Ingreso Neto
  - Costo A (Payroll + No-Payroll)
  - Costo B
  - Costo C
  = Contribución
  - Financieros (ICA+GMF+Pólizas+Fin)
  = Utilidad Neta
```

### 3.3.8 KPIsDeal — Métricas del Deal

```python
@dataclass
class KPIsDeal:
    costo_mensual_promedio: float = 0.0
    costo_cadena_a_promedio: float = 0.0
    ingreso_mensual: float = 0.0
    facturacion_mensual_proyectada: float = 0.0
    ingreso_bruto_total: float = 0.0
    ingreso_neto_total: float = 0.0
    costo_total_contrato: float = 0.0
    contribucion_total: float = 0.0
    utilidad_neta_total: float = 0.0
    pct_utilidad_neta_total: float = 0.0
    valor_total_deal: float = 0.0
    margen_minimo_requerido: float = 0.0
    cumple_margen_minimo: bool = True
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `costo_mensual_promedio` | `float` | Promedio costo operativo (COP/mes) |
| `costo_cadena_a_promedio` | `float` | Promedio costo A (COP/mes) |
| `ingreso_mensual` | `float` | Promedio ingreso bruto (COP/mes) |
| `facturacion_mensual_proyectada` | `float` | Facturación proyectada (COP/mes) |
| `ingreso_bruto_total` | `float` | Total ingreso bruto (COP) |
| `ingreso_neto_total` | `float` | Total ingreso neto (COP) |
| `costo_total_contrato` | `float` | Total costo operativo (COP) |
| `contribucion_total` | `float` | Total contribución (COP) |
| `utilidad_neta_total` | `float` | Total utilidad neta (COP) |
| `pct_utilidad_neta_total` | `float` | % utilidad neta (0..1) |
| `valor_total_deal` | `float` | Valor total del contrato (COP) |
| `margen_minimo_requerido` | `float` | Margen mínimo corporativo (0..1) |
| `cumple_margen_minimo` | `bool` | ¿Cumple límite? |

---

## 3.4 Modelos de Visión (Outputs Estructurados)

### Propósito

Las visiones transforman los resultados del calculador en estructuras jerárquicas optimizadas para Excel/frontend.

**Ubicación:** `/domain/models/visions.py`

### 3.4.1 ResultadoCostToServe — Costo por Unidad

```python
@dataclass
class ResultadoCostToServe:
    cts_cadena_a: float = 0.0                           # COP/FTE/mes
    cts_cadena_b: float = 0.0                           # COP/volumen/mes
    cts_cadena_c: float = 0.0                           # COP/volumen/mes
    cts_ponderado: float = 0.0                          # Promedio ponderado
    participacion_a: float = 0.0                        # % (0..1)
    participacion_b: float = 0.0
    participacion_c: float = 0.0
    fte_cadena_a: float = 0.0                           # Denominador K50
    vol_cadena_b: float = 0.0                           # Denominador L50
    vol_cadena_c: float = 0.0                           # Denominador M50
    costo_total_acumulado: float = 0.0                  # Total contrato
    desglose_a: DesgloseCTSCadenaA = field(default_factory=DesgloseCTSCadenaA)
    desglose_b: DesgloseCTSCadenaB = field(default_factory=DesgloseCTSCadenaB)
    canal_view_habilitado: bool = False                 # Excel C58/C87 gate
    canales_detalle: List[CanalCTSDetalle] = field(default_factory=list)
```

**DesgloseCTSCadenaA:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nomina` | `float` | Total nómina (COP/FTE/mes) |
| `no_payroll` | `float` | Total no-payroll (COP/FTE/mes) |
| `nomina_loaded` | `float` | Nómina con carga (COP/FTE/mes) |
| `salario_fijo` | `float` | Salario base (COP/FTE/mes) |
| `salario_variable` | `float` | Comisiones (COP/FTE/mes) |
| `capacitacion_inicial` | `float` | Cap. inicial amortizado (COP/FTE/mes) |
| `capacitacion_rotacion` | `float` | Cap. rotación (COP/FTE/mes) |
| `examenes` | `float` | Exámenes (COP/FTE/mes) |
| `estudios_seguridad` | `float` | Seguridad (COP/FTE/mes) |
| `crucero` | `float` | Crucero (COP/FTE/mes) |
| `opex_fijo` | `float` | OPEX (COP/FTE/mes) |
| `inversiones` | `float` | Inversiones (COP/FTE/mes) |
| `costos_fijos_estacion` | `float` | Fijos estación (COP/FTE/mes) |

**CanalCTSDetalle:** (per-channel breakdown, Excel CTS rows 90-125)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `canal` | `str` | Nombre canal (WhatsApp, Email, etc.) |
| `modalidad` | `str` | Inbound/Outbound |
| `fte` | `float` | FTE para este canal (Panel!M19:M25) |
| `participacion_cadena_a` | `float` | Vol participation % |
| `cts` | `float` | CTS total (COP/FTE/mes) |
| `payroll` | `float` | Nómina total (COP/FTE/mes) |
| `nomina_loaded` | `float` | Nómina cargada (COP/FTE/mes) |
| `salario_fijo` | `float` | Salario base (COP/FTE/mes) |
| ... (payroll sub-components) | |
| `no_payroll` | `float` | No-payroll total (COP/FTE/mes) |
| `opex_fijo` | `float` | OPEX (COP/FTE/mes) |
| `inversiones` | `float` | Inversiones (COP/FTE/mes) |
| `costos_fijos` | `float` | Costos fijos (COP/FTE/mes) |

### 3.4.2 ResultadoVisionTarifas — Tarifas por Canal

```python
@dataclass
class ResultadoVisionTarifas:
    canales: List[TarifaCanal] = field(default_factory=list)
    costo_cadena_a_total: float = 0.0
    costo_cadena_b_total: float = 0.0
    costo_cadena_c_total: float = 0.0
    costo_total: float = 0.0
    ingreso_mensual: float = 0.0
    ingreso_cadena_a: float = 0.0
    ingreso_cadena_b: float = 0.0
    ingreso_cadena_c: float = 0.0
    escenarios_detalle: List[EscenarioTarifasDetalle] = field(default_factory=list)
    desglose_producto_opex: List[DesgloseProductoOpex] = field(default_factory=list)
```

**TarifaCanal:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre_canal` | `str` | Nombre (WhatsApp, Email, etc.) |
| `modalidad` | `str` | Inbound/Outbound |
| `producto` | `str` | Producto |
| `fte` | `float` | FTE asignado |
| `vol_mensual` | `float` | Volumen transaccional (unidades/mes) |
| `modelo_cobro` | `str` | Modo de facturación |
| `pct_fijo` | `float` | Porción fija (0..1) |
| `pct_variable` | `float` | Porción variable (0..1) |
| `componente_fijo` | `str` | Label (FTE, Hora, etc.) |
| `componente_variable` | `str` | Label (Transacción, etc.) |
| `costo_atribuible` | `float` | Costo asignado a este canal (COP/mes) |
| `ingreso_bruto` | `float` | Ingreso bruto (COP/mes) |
| `facturacion` | `float` | Facturación al cliente (COP/mes) |
| `tarifa_fijo_fte` | `float` | Tarifa FTE (COP/FTE/mes) |
| `tarifa_variable` | `float` | Tarifa variable (COP/unidad) |
| `vol_minimo_transaccion` | `float` | Vol mínimo |
| **Descomposición** |
| `payroll_ch` | `float` | Nómina asignada (COP/mes) |
| `no_payroll_ch` | `float` | No-payroll asignado (COP/mes) |
| `costo_cadena_a_ch` | `float` | Costo A total (COP/mes) |
| `nomina_loaded_ch` | `float` | Nómina cargada (COP/mes) |
| `salario_fijo_ch` | `float` | Salario base (COP/mes) |
| ... (payroll sub-components) | |
| `opex_it_ch` | `float` | OPEX TI (COP/mes) |
| `inversiones_ch` | `float` | Inversiones (COP/mes) |
| `costos_fijos_ch` | `float` | Costos fijos (COP/mes) |
| `cadena_b_atribuible` | `float` | Costo B atribuido (COP/mes) |
| `financieros_atribuible` | `float` | Financieros atribuidos (COP/mes) |
| `tarifa_hora_loggeada` | `float` | Tarifa por hora loggeada (COP/hora) |
| `tarifa_hora_pagada` | `float` | Tarifa por hora pagada (COP/hora) |

### 3.4.3 VisionPyG — Estado de Resultados Visual

```python
@dataclass
class VisionPyG:
    resumen: PyGResumen                    # Agregado mensual
    filas: List[FilaPyG]                   # Detalle por rubro
    filas_detalle: List[FilaPyGDetalle]    # Sub-componentes
    meses_contrato: int                    # Duración
    fechas_meses: List[str]                # YYYY-MM por mes
```

---

## 3.5 Contratos de Salida (Response DTOs)

### Propósito

Los contratos de salida son **frozen** Pydantic models que serializan las visiones a JSON.

**Ubicación:** `/contracts/api_v1/response/`

### 3.5.1 SimulationResultV1 — Envolvente Principal

```python
class SimulationResultV1(BaseModel):
    simulation_id: str
    api_version: Literal["api-v1"] = "api-v1"
    engine_version: str = "unknown"
    parametrization_version: str = "unknown"
    baseline_version: Optional[str] = None
    formula_set: str = "formula-set-v2-7"
    parametrization_hashes: Dict[str, str] = Field(default_factory=dict)
    visions: VisionsBundleV1 = Field(default_factory=VisionsBundleV1)
    kpis: KpisV1 = Field(default_factory=KpisV1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 3.5.2 VisionsBundleV1 — 4 Visiones Oficiales

```python
class VisionsBundleV1(BaseModel):
    tarifas: Optional[VisionTarifasV1] = None
    pyg: Optional[VisionPyGV1] = None
    cost_to_serve: Optional[CostToServeV1] = None
    waterfall: Optional[WaterfallV1] = None
```

### 3.5.3 KpisV1 — Métricas del Deal

```python
class KpisV1(BaseModel):
    costo_mensual_promedio: float = 0.0
    costo_cadena_a_promedio: float = 0.0
    ingreso_mensual: float = 0.0
    facturacion_mensual_proyectada: float = 0.0
    ingreso_bruto_total: float = 0.0
    ingreso_neto_total: float = 0.0
    costo_total_contrato: float = 0.0
    contribucion_total: float = 0.0
    utilidad_neta_total: float = 0.0
    pct_utilidad_neta_total: float = 0.0
    valor_total_deal: float = 0.0
    margen_minimo_requerido: float = 0.0
    cumple_margen_minimo: bool = True
```

---

## 3.6 Enums y Objetos de Valor

### 3.6.1 ModeloCobroLiteral

```python
Literal[
    "Fijo FTE",           # Tarifa fija por Full-Time Equivalent
    "Variable",           # Completamente variable (volumen)
    "Híbrido",            # Hibrido (80% fijo + 20% variable)
    "Hibrido",            # ASCII variant (tolerated)
    "Volumen",            # Alias: Por Volumen
    "Por Volumen",        # Por volumen de transacciones
    "Por Comisión",       # Comisional puro
    "Por Comision",       # ASCII variant (tolerated)
]
```

**Uso:** Determina cómo se factura el servicio en VisionTarifas. Impacta cálculo de tarifa_fijo_fte vs. tarifa_variable.

### 3.6.2 CargoTipo (NEW V2-5)

```python
Literal[
    "AGENTE",                           # Operador base
    "OPERATIVO",                        # Personal operativo
    "ADMINISTRATIVO",                   # Soporte administrativo
    "VALIDADOR",                        # Validación de calidad
    "ESPECIALISTA",                     # Experto funcional
    "APRENDIZ",                         # Aprendiz SENA
    "INCLUSION",                        # Inclusión laboral
    "DESCONOCIDO",                      # No clasificado
]
```

**Fuente:** HR Storage (`hr/clasificacion_cargos`)

### 3.6.3 TipoCarga (NEW V2-5)

```python
Literal[
    "EMPLEADO_ESTANDAR",               # Contratación estándar
    "APRENDIZ_SENA",                   # Aprendiz SENA
    "EQUIPO_SOPORTE_MANTENIMIENTO",    # S&M team
    "SOPORTE_COMISIONABLE",             # Support comisional
    "IMPLEMENTACION_PROYECTOS",         # Project implementation
]
```

**Fuente:** HR Storage (`hr/tipos_carga`)  
**Impacto:** Determina tasa de aportes patronales y prestaciones.

### 3.6.4 Indexacion (Value Object)

```python
@dataclass
class Indexacion:
    componente_humano: str = ""         # "IPC", "UVR", "Salario Mínimo", etc.
    componente_tecnologico: str = ""    # "IPC", "DTF", etc.
    frecuencia: str = "Anual"           # "Anual", "Semestral", "Mensual"
    mes_aplicacion: int = 1             # Mes del año (1-12)
```

### 3.6.5 CadenasActivas (Value Object)

```python
@dataclass
class CadenasActivas:
    cadena_a: bool = False
    cadena_b: bool = False
    cadena_c: bool = False

    def is_active(self, cadena: str) -> bool:
        return bool(getattr(self, cadena, False))
```

---

## Resumen de Mapeos Excel → Código

| Excel | Código | Tipo |
|-------|--------|------|
| Panel!C5-C70 | `PanelDeControlRequestV1` | Request DTO |
| Panel!D63 | `panel.margen_b` | NEW V2-7 |
| Panel!E63 | `panel.margen_c` | NEW V2-7 |
| Panel!L9 | `panel.mes_ajuste_indexacion` | NEW V2-7 |
| Panel!L10 | `panel.tasa_interes_mensual` | NEW V2-7 |
| Panel!C73 | `panel.imprevistos` | NEW V2-7 |
| Panel!C17 | `panel.tarifa_crucero` | NEW V2-7 |
| Inputs!W39-W40 | `PerfilCadenaA.salario_base` | Domain model |
| K167/K168 | `ParametrosNoPayroll.inversiones_amortizables` | NEW V2-7 |
| VCS rows 36-43 | `DesgloseCTSCadenaA` | Vision model |
| VCS rows 90-125 | `CanalCTSDetalle` | Vision model |
| Tarifas rows 10-21 | `EscenarioTarifasResumen` | Vision model |
| Tarifas rows 104-127 | `ComponenteFijo` | Vision model |
| Tarifas rows 130-143 | `ComponenteVariable` | Vision model |

---

## Notas Técnicas

### Backward Compatibility

- `EntryDataV1` acepta ambos alias: `panel` y `panel_de_control`
- `aplica_ley_1819` retenido por compatibilidad, ignorado en cálculo
- `tasa_mensual_financ` es alias de `tasa_interes_mensual` en algunos contextos

### Validaciones Post-Refactor

- Campos con `Optional[...]` requieren chequeo null en el motor
- `inversiones_amortizables` reemplaza el modelo simple `capex_por_estacion` cuando no está vacío
- Cadena C: `total_pyg` excluye componentes financieros internos; usar `total` para base de ICA/GMF

### Convenciones de Unidades

- Monetario: **COP** (Colombian Pesos)
- Porcentajes: **0..1** (0% = 0.0, 100% = 1.0)
- FTE: **headcount-equivalent** (1.0 = 1 persona)
- Tiempo: **meses** (1-120)
- Volumen: **transacciones/mes**

---

**FIN DEL CAPÍTULO 3**

---

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 31-05-2026 | Documentación inicial v2-7 |

**Próximos capítulos:**
- Cap. 4: Algoritmos de Cálculo (Nómina, No-Payroll, Cadena B/C)
- Cap. 5: Pipeline de Visiones (CTS, Tarifas, P&G)
- Cap. 6: Orquestación y API
