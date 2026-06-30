# EJEMPLOS DE CÓDIGO: Refactor costos_operativos

**Documento de Implementación Práctica**  
**Versión:** 1.0  
**Fecha:** 2026-05-27

---

## ÍNDICE

1. [Crear `domain/constants.py`](#1-crear-domainconstantspy)
2. [Agregar Campo a DTOs](#2-agregar-campo-a-dtos)
3. [Métodos de Cálculo (Context Builder)](#3-métodos-de-cálculo-context-builder)
4. [Parametrización IPC](#4-parametrización-ipc)
5. [Adapters (Input Mapping)](#5-adapters-input-mapping)
6. [Reemplazar Constante en 5 Ubicaciones](#6-reemplazar-constante-en-5-ubicaciones)
7. [Eliminar Código Legacy](#7-eliminar-código-legacy)

---

## 1. CREAR `domain/constants.py`

### Nuevo Archivo

**Ubicación:** `/nexa_engine/domain/constants.py`

```python
"""
Constantes del motor financiero NEXA.

Valores que NO varían por deal, parametrización ni cliente.
Cambios aquí impactan TODOS los cálculos globalmente.

Regla arquitectónica: Si un valor NO cambia entre deals, NO debe estar
en parametrización ni en input — debe ser una constante aquí.
"""

# ────────────────────────────────────────────────────────────────────────────
# Indexación y Ajustes Anuales
# ────────────────────────────────────────────────────────────────────────────

# Mes en que aplica el ajuste anual (indexación salarial/tecnológica)
# Valor: 1 = enero (estándar fiscal Colombia)
# Fuente Legal: Ley 1393 de 2010 Art. 3 (reajuste SMMLV)
# Usado en: SimulationContextBuilder, NominaCalculator, CadenaCCalculator
MES_INICIO_AJUSTE_ANUAL = 1


# ────────────────────────────────────────────────────────────────────────────
# Constantes Laborales (Colombia)
# ────────────────────────────────────────────────────────────────────────────

# Días laborales promedio por mes (calendario Colombia)
DIAS_LABORALES_POR_MES = 20

# Horas laborales estándar por día (jornada laboral Colombia)
HORAS_LABORALES_POR_DIA = 8

# Semanas promedio por mes (52 semanas / 12 meses)
SEMANAS_POR_MES = 4.33


# ────────────────────────────────────────────────────────────────────────────
# Umbrales Salariales (Ley 1819 de 2016)
# ────────────────────────────────────────────────────────────────────────────

# Umbral de alto salario en múltiplos de SMMLV (Art. 114-1)
# Salarios >= 10 SMMLV tienen tratamiento diferenciado en Salud
# NOTA: Este valor puede moverse a parametrización si la ley cambia
FACTOR_ALTO_SALARIO_SMMLV = 10.0

# Factor corrector para salud en altos salarios (70% del excedente)
FACTOR_CORRECTOR_ALTO_SALARIO = 0.70
```

---

## 2. AGREGAR CAMPO A DTOs

### 2.1 `domain/user_inputs.py`

**ANTES:**
```python
@dataclass
class PanelDeControlInput:
    """Datos del negocio configurados por el usuario."""
    cliente: str
    tipo_cliente: str
    linea_negocio: str
    ciudad: str
    # ... otros campos ...
    pct_ausentismo: Optional[float] = None
    # FIN
```

**DESPUÉS:**
```python
@dataclass
class PanelDeControlInput:
    """Datos del negocio configurados por el usuario."""
    cliente: str
    tipo_cliente: str
    linea_negocio: str
    ciudad: str
    # ... otros campos ...
    pct_ausentismo: Optional[float] = None
    
    # ───────────────────────────────────────────────────────────────────────
    # REFACTOR costos_operativos: tarifa_dia_cap ahora viene del input
    # ───────────────────────────────────────────────────────────────────────
    # Tarifa diaria de capacitación por agente (valor comercial del deal).
    # Reemplaza la antigua lectura desde HR-costos_operativos.
    # Fuente: datos_operativos.tarifa_diaria_capacitacion (JSON usuario).
    tarifa_diaria_capacitacion: float
```

### 2.2 `domain/models/panel.py`

**ANTES:**
```python
@dataclass
class PanelDeControl:
    """Parámetros maestros del deal."""
    # ... campos existentes ...
    complejidad_especialista: str = "ALTA"
    cadenas_activas: CadenasActivas = field(default_factory=CadenasActivas)
```

**DESPUÉS:**
```python
@dataclass
class PanelDeControl:
    """Parámetros maestros del deal."""
    # ... campos existentes ...
    complejidad_especialista: str = "ALTA"
    cadenas_activas: CadenasActivas = field(default_factory=CadenasActivas)
    
    # REFACTOR costos_operativos
    tarifa_diaria_capacitacion: float = 0.0
```

### 2.3 `simulation/panel/dto.py`

**ANTES:**
```python
class PcgInput(BaseModel):
    """Panel de Control General — entrada REST API."""
    cliente: str = Field(alias="clienteNuevo")
    # ... otros campos ...
    tarifa_cap: str = "0"             # tarifaCap (por día) ← STRING, sin usar
```

**DESPUÉS:**
```python
class PcgInput(BaseModel):
    """Panel de Control General — entrada REST API."""
    cliente: str = Field(alias="clienteNuevo")
    # ... otros campos ...
    
    # REFACTOR costos_operativos: ahora es float REQUERIDO
    tarifa_cap: float = Field(
        alias="tarifaCap",
        description="Tarifa diaria de capacitación por agente (COP)",
        ge=0.0,  # Validación: debe ser >= 0
    )
```

---

## 3. MÉTODOS DE CÁLCULO (Context Builder)

### 3.1 Método `_calcular_opex_ti_total()`

**Ubicación:** `input/context_builder.py` (agregar después de línea ~640)

```python
def _calcular_opex_ti_total(self, perfiles_a: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el OPEX TI total promedio por estación desde opex_fijo.items[].
    
    REGLA ARQUITECTÓNICA:
    opex_ti_por_estacion NO es un concepto atómico en el modelo de datos.
    Es la SUMA de todos los costos OPEX de tecnología (Internet, Licencias, 
    Plataformas, Soporte) dividido por el número de estaciones.
    
    Conceptos incluidos (filtro dinámico):
      - tipo = "Tecnología" o 
      - concepto contiene ["Internet", "Licencia", "Plataforma", "CX1", "Soporte TI"]
    
    Args:
        perfiles_a: Lista de perfiles de Cadena A con opex_fijo configurado.
    
    Returns:
        OPEX TI promedio ponderado por estación presencial.
        Retorna 0.0 si no hay perfiles con OPEX TI o estaciones = 0.
    
    Ejemplo Excel V2-6:
        perfil_voz: 10 estaciones, OPEX = [Internet 450k/10, Licencias 1.2M/10]
        perfil_chat: 5 estaciones, OPEX = [Internet 450k/10]
        
        opex_ti_total = (450k + 1.2M + 450k) / 15 estaciones
                      = 2.1M / 15
                      = 140,000 COP/estación/mes
    """
    from nexa_engine.audit.trace import trace as _audit_trace
    
    total_opex_ti = 0.0
    total_estaciones = 0.0
    
    # Palabras clave para identificar costos TI
    KEYWORDS_TI = ["internet", "licencia", "plataforma", "cx1", "soporte", "software", "saas"]
    
    for perfil in perfiles_a:
        if not hasattr(perfil, 'opex_fijo') or not perfil.opex_fijo:
            continue
        
        items = perfil.opex_fijo.get('items', []) if isinstance(perfil.opex_fijo, dict) else []
        if not items:
            continue
        
        # Estaciones presenciales (FTE × pct_presencia)
        estaciones_perfil = perfil.fte * getattr(perfil, 'pct_presencia', 1.0)
        if estaciones_perfil <= 0:
            continue
        
        total_estaciones += estaciones_perfil
        
        for item in items:
            concepto = str(item.get('concepto', '')).lower()
            tipo = str(item.get('tipo', '')).lower()
            
            # Filtrar solo costos TI
            es_ti = (
                tipo == "tecnología" or
                any(kw in concepto for kw in KEYWORDS_TI)
            )
            
            if not es_ti:
                continue
            
            costo = float(item.get('costo', 0.0))
            cantidad = float(item.get('cantidad', 1.0))
            costo_totalizado = item.get('costo_totalizado', False)
            
            if costo_totalizado:
                # Costo ya está totalizado para todas las estaciones
                opex_unitario = costo / estaciones_perfil
            else:
                # Costo unitario × cantidad / estaciones
                opex_unitario = (costo * cantidad) / estaciones_perfil
            
            total_opex_ti += opex_unitario * estaciones_perfil
    
    resultado = total_opex_ti / total_estaciones if total_estaciones > 0 else 0.0
    
    _audit_trace(
        component="context_builder",
        rule="OPEX_TI.calcular_desde_opex_fijo",
        formula="Σ(opex_fijo[tipo='TI']) / total_estaciones",
        inputs={
            "total_estaciones": total_estaciones,
            "perfiles_evaluados": len(perfiles_a),
        },
        result=resultado,
        source="USER_INPUT.opex_fijo[]",
    )
    
    return resultado
```

### 3.2 Método `_calcular_capex_recurrente()`

**Ubicación:** `input/context_builder.py` (agregar después de `_calcular_opex_ti_total()`)

```python
def _calcular_capex_recurrente(self, perfiles_a: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el CAPEX recurrente mensual promedio por estación desde inversiones[].
    
    REGLA ARQUITECTÓNICA:
    capex_recurrente = Σ(precio_inversión / meses_amortización) / estaciones
    
    El CAPEX recurrente es la cuota mensual amortizada de todas las inversiones
    en hardware, software y periféricos que se renuevan periódicamente.
    
    Ejemplo de inversiones típicas (Excel V2-6):
      - PC Desktop: 3,508,260 COP / 60 meses = 58,471 COP/mes/estación
      - Licencia Office: 300,000 COP / 12 meses = 25,000 COP/mes/estación
      - Monitor: 800,000 COP / 48 meses = 16,667 COP/mes/estación
      
      TOTAL: 58,471 + 25,000 + 16,667 = 100,138 COP/mes/estación
    
    Args:
        perfiles_a: Lista de perfiles con inversiones configuradas.
    
    Returns:
        CAPEX recurrente promedio ponderado por estación.
    """
    from nexa_engine.audit.trace import trace as _audit_trace
    
    total_capex_mensual = 0.0
    total_estaciones = 0.0
    
    for perfil in perfiles_a:
        if not hasattr(perfil, 'inversiones') or not perfil.inversiones:
            continue
        
        # Para CAPEX usamos FTE bruto (no pct_presencia) porque el hardware
        # se asigna por agente, no por estación física
        estaciones_perfil = perfil.fte
        if estaciones_perfil <= 0:
            continue
        
        total_estaciones += estaciones_perfil
        
        inversiones = perfil.inversiones if isinstance(perfil.inversiones, list) else []
        
        for inversion in inversiones:
            precio = float(inversion.get('precio', 0.0))
            cantidad = float(inversion.get('cantidad', 1.0))
            meses_amortizacion = float(inversion.get('meses_amortizacion', 1))
            es_precio_total = inversion.get('es_precio_total', False)
            
            if meses_amortizacion <= 0:
                # Evitar división por cero — asignar default contable
                meses_amortizacion = 1
            
            # Calcular cuota mensual
            if es_precio_total:
                # Precio total para todas las estaciones
                cuota_mensual_total = precio / meses_amortizacion
                cuota_mensual_unitaria = cuota_mensual_total / estaciones_perfil
            else:
                # Precio unitario × cantidad
                cuota_mensual_unitaria = (precio * cantidad) / meses_amortizacion / estaciones_perfil
            
            total_capex_mensual += cuota_mensual_unitaria * estaciones_perfil
    
    resultado = total_capex_mensual / total_estaciones if total_estaciones > 0 else 0.0
    
    _audit_trace(
        component="context_builder",
        rule="CAPEX_RECURRENTE.calcular_desde_inversiones",
        formula="Σ(precio / meses_amortizacion) / total_estaciones",
        inputs={
            "total_estaciones": total_estaciones,
            "perfiles_evaluados": len(perfiles_a),
        },
        result=resultado,
        source="USER_INPUT.inversiones[]",
    )
    
    return resultado
```

### 3.3 Método `_calcular_capex_inicial()`

**Ubicación:** `input/context_builder.py` (agregar después de `_calcular_capex_recurrente()`)

```python
def _calcular_capex_inicial(self, perfiles_a: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el CAPEX inicial total por estación desde inversiones[].
    
    REGLA ARQUITECTÓNICA:
    capex_inicial = Σ(precio_total_inversión) / estaciones
    
    El CAPEX inicial es la inversión up-front completa (sin amortizar) que se
    debe realizar para equipar todas las estaciones del contrato.
    
    Este valor se usa en el cálculo de financiación inicial (mes 1) y NO se
    incluye en los costos recurrentes mensuales.
    
    Ejemplo (Excel V2-6):
        PC Desktop: 3,508,260 × 10 qty = 35,082,600 COP
        Monitor: 800,000 × 10 qty = 8,000,000 COP
        TOTAL: 43,082,600 / 10 estaciones = 4,308,260 COP/estación
    
    Args:
        perfiles_a: Lista de perfiles con inversiones configuradas.
    
    Returns:
        CAPEX inicial promedio ponderado por estación.
    """
    from nexa_engine.audit.trace import trace as _audit_trace
    
    total_capex_inicial = 0.0
    total_estaciones = 0.0
    
    for perfil in perfiles_a:
        if not hasattr(perfil, 'inversiones') or not perfil.inversiones:
            continue
        
        estaciones_perfil = perfil.fte
        if estaciones_perfil <= 0:
            continue
        
        total_estaciones += estaciones_perfil
        
        inversiones = perfil.inversiones if isinstance(perfil.inversiones, list) else []
        
        for inversion in inversiones:
            precio = float(inversion.get('precio', 0.0))
            cantidad = float(inversion.get('cantidad', 1.0))
            es_precio_total = inversion.get('es_precio_total', False)
            
            if es_precio_total:
                # Precio total para todas las estaciones
                precio_unitario = precio / estaciones_perfil
            else:
                # Precio unitario × cantidad
                precio_unitario = (precio * cantidad) / estaciones_perfil
            
            total_capex_inicial += precio_unitario * estaciones_perfil
    
    resultado = total_capex_inicial / total_estaciones if total_estaciones > 0 else 0.0
    
    _audit_trace(
        component="context_builder",
        rule="CAPEX_INICIAL.calcular_desde_inversiones",
        formula="Σ(precio_total) / total_estaciones",
        inputs={
            "total_estaciones": total_estaciones,
            "perfiles_evaluados": len(perfiles_a),
        },
        result=resultado,
        source="USER_INPUT.inversiones[]",
    )
    
    return resultado
```

### 3.4 Integrar en `_construir_no_payroll()`

**Ubicación:** `input/context_builder.py` (línea ~650)

**ANTES:**
```python
def _construir_no_payroll(self, panel, sede: str) -> ParametrosNoPayroll:
    """Construye ParametrosNoPayroll con valores desde parametrización."""
    costos_sede = self._prov.get_costo_no_payroll(sede)
    
    # ❌ INCORRECTO: leer desde costos_operativos
    opex_ti = self._prov.get_costo_operativo("opex_ti_por_estacion")
    capex = self._prov.get_costo_operativo("capex_recurrente_por_estacion")
    capex_inicial = self._prov.get_costo_operativo("capex_inicial_por_estacion")
    
    return ParametrosNoPayroll(
        opex_ti_por_estacion       = opex_ti,
        capex_por_estacion         = capex,
        arriendo_por_estacion      = costos_sede["arriendo"],
        energia_por_estacion       = costos_sede["energia"],
        vigilancia_por_estacion    = costos_sede["vigilancia"],
        aseo_por_estacion          = costos_sede["aseo"],
        otros_fijos_por_estacion   = costos_sede.get("mantenimiento", 0.0),
        capex_inicial_por_estacion = capex_inicial,
    )
```

**DESPUÉS:**
```python
def _construir_no_payroll(
    self, 
    panel, 
    sede: str, 
    perfiles_a: List[PerfilCadenaAInput]  # <-- NUEVO PARÁMETRO
) -> ParametrosNoPayroll:
    """
    Construye ParametrosNoPayroll calculando dinámicamente OPEX TI y CAPEX.
    
    CAMBIO ARQUITECTÓNICO: ya NO se lee costos_operativos de parametrización.
    Todos los valores se calculan desde el input del usuario o se obtienen
    de parametrización específica (HR-CostoFijo por sede).
    """
    # Costos de infraestructura por sede (arriendo, energía, vigilancia, aseo)
    costos_sede = self._prov.get_costo_no_payroll(sede)
    
    # ✅ CORRECTO: Calcular dinámicamente desde el input del usuario
    opex_ti = self._calcular_opex_ti_total(perfiles_a)
    capex = self._calcular_capex_recurrente(perfiles_a)
    capex_inicial = self._calcular_capex_inicial(perfiles_a)
    
    return ParametrosNoPayroll(
        opex_ti_por_estacion       = opex_ti,
        capex_por_estacion         = capex,
        arriendo_por_estacion      = costos_sede["arriendo"],
        energia_por_estacion       = costos_sede["energia"],
        vigilancia_por_estacion    = costos_sede["vigilancia"],
        aseo_por_estacion          = costos_sede["aseo"],
        otros_fijos_por_estacion   = costos_sede.get("mantenimiento", 0.0),
        capex_inicial_por_estacion = capex_inicial,
    )
```

**IMPORTANTE:** Actualizar la llamada en `construir()`:

```python
# Línea ~219 en construir()
return PricingRequest(
    # ...
    parametros_no_payroll = self._construir_no_payroll(
        panel, 
        sede,
        user_input.cadena_a.perfiles  # <-- NUEVO ARGUMENTO
    ),
    # ...
)
```

---

## 4. PARAMETRIZACIÓN IPC

### 4.1 Nuevo Método en `FinancialParametrizationRepository`

**Ubicación:** `repositories/financial_parametrization_repository.py`

**Agregar después del último método:**

```python
def get_economic_component(self, componente: str, anio: int) -> float:
    """
    Obtiene la tasa de un componente económico para un año específico.
    
    Fuente: OP-Componente (hoja de parametrización de indexación).
    
    Componentes disponibles:
      - "IPC": Índice de Precios al Consumidor
      - "SMLV": Salario Mínimo Legal Vigente
      - "70% SMMLV - 30% IPC": Mixto ponderado
      - "IPC + 1 PUNTO": IPC con incremento adicional
    
    Args:
        componente: Nombre del componente (debe coincidir exactamente con OP).
        anio: Año fiscal (e.g., 2025, 2026, 2027).
    
    Returns:
        Tasa de indexación como decimal (e.g., 0.0527 = 5.27%).
    
    Raises:
        ParametrizationError: si el componente/año no existe en OP-Componente.
    
    Ejemplo:
        >>> repo.get_economic_component("IPC", 2026)
        0.0527  # 5.27% IPC 2026
    """
    self._ensure_op_loaded()
    tabla = self._get_sheet(self._op_data, "componente")
    
    if not tabla or "rows" not in tabla:
        raise ParametrizationError(
            "OP-Componente sheet not found in OP parametrization. "
            "Verify storage/parametrization/op/{version_id}.json contains 'componente' sheet.",
            module="op",
        )
    
    for row in tabla["rows"]:
        if row.get("componente") == componente and int(row.get("ano", 0)) == anio:
            valor = row.get("valor")
            if valor is None:
                raise ParametrizationError(
                    f"Valor missing for componente '{componente}' año {anio} in OP-Componente",
                    module="op",
                )
            return float(valor)
    
    # Si no se encuentra, generar error con mensaje útil
    componentes_disponibles = sorted(set(
        r.get("componente") for r in tabla["rows"] if r.get("componente")
    ))
    anios_disponibles = sorted(set(
        int(r.get("ano", 0)) for r in tabla["rows"] if r.get("ano")
    ))
    
    raise ParametrizationError(
        f"Componente económico '{componente}' año {anio} not found in OP-Componente.\n"
        f"Componentes disponibles: {componentes_disponibles}\n"
        f"Años disponibles: {anios_disponibles}\n"
        f"Solución: Agregar fila a Excel OP → sheet 'Componente' con:\n"
        f"  componente='{componente}', ano={anio}, valor=<tasa_decimal>",
        module="op",
    )
```

### 4.2 Facade en `ParametrizationProvider`

**Ubicación:** `repositories/parametrization_provider.py`

**Agregar después de `get_margen_minimo()`:**

```python
def get_componente_indexacion(self, componente: str, anio: int) -> float:
    """
    Obtiene componente de indexación desde OP-Componente.
    
    Usado para calcular pct_aumento_tecnologico_anual (IPC del año contrato).
    
    Args:
        componente: Nombre del componente (e.g., "IPC", "SMLV").
        anio: Año fiscal.
    
    Returns:
        Tasa de indexación como decimal.
    
    Raises:
        ParametrizationError: si no existe.
    """
    value = self._financial.get_economic_component(componente, anio)
    logger.debug(
        "[REPOSITORY] repository=FinancialParametrizationRepository "
        "operation=get_componente_indexacion componente=%s anio=%d value=%s source=OP-Componente",
        componente, anio, value,
    )
    return value
```

### 4.3 Usar en `_construir_cadena_c()`

**Ubicación:** `input/context_builder.py` (línea ~850)

**ANTES:**
```python
def _construir_cadena_c(self, cadena_c, panel):
    """Construye ParametrosCadenaC."""
    # ... código existente ...
    
    # ❌ INCORRECTO: leer desde costos_operativos
    pct_aumento_tecnologico = self._prov.get_costo_operativo("pct_aumento_tecnologico_anual")
    mes_ajuste = int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))
    
    return ParametrosCadenaC(
        # ...
        pct_aumento_tecnologico = pct_aumento_tecnologico,
        mes_aplicacion_aumento  = mes_ajuste,
        # ...
    )
```

**DESPUÉS:**
```python
from datetime import datetime
from nexa_engine.domain.constants import MES_INICIO_AJUSTE_ANUAL

def _construir_cadena_c(self, cadena_c, panel):
    """Construye ParametrosCadenaC resolviendo pct_aumento_tecnologico desde OP."""
    # Extraer año de inicio del contrato
    try:
        año_inicio = datetime.strptime(panel.fecha_inicio, "%Y-%m-%d").year
    except ValueError:
        # Fallback si formato inesperado
        año_inicio = 2026
        logger.warning(
            "Failed to parse fecha_inicio '%s', using default year %d",
            panel.fecha_inicio, año_inicio
        )
    
    # ✅ CORRECTO: Obtener IPC del año desde parametrización OP-Componente
    try:
        pct_aumento_tecnologico = self._prov.get_componente_indexacion("IPC", año_inicio)
    except Exception as exc:
        logger.warning(
            "Failed to get IPC for year %d from OP-Componente: %s. Using 0.0.",
            año_inicio, exc
        )
        pct_aumento_tecnologico = 0.0
    
    # ✅ CORRECTO: mes_ajuste desde constante backend
    mes_ajuste = MES_INICIO_AJUSTE_ANUAL
    
    # Resto del método sin cambios...
    return ParametrosCadenaC(
        # ... campos existentes ...
        pct_aumento_tecnologico = pct_aumento_tecnologico,
        mes_aplicacion_aumento  = mes_ajuste,
        # ...
    )
```

---

## 5. ADAPTERS (Input Mapping)

### 5.1 `adapters/unified_input_adapter.py`

**Ubicación:** Método `_panel_from_dict()` (línea ~145)

**ANTES:**
```python
@classmethod
def _panel_from_dict(cls, pcg: Dict) -> PanelDeControlInput:
    """Convierte pcg (dict del frontend) a PanelDeControlInput."""
    return PanelDeControlInput(
        cliente                           = cliente,
        tipo_cliente                      = pcg.get("tipoCliente") or "",
        linea_negocio                     = pcg.get("servicio", ""),
        # ... otros campos ...
        pct_ausentismo                    = _a_fraccion(pcg.get("ausentismo", "0")),
        # FIN (falta tarifa_diaria_capacitacion)
    )
```

**DESPUÉS:**
```python
@classmethod
def _panel_from_dict(cls, pcg: Dict) -> PanelDeControlInput:
    """Convierte pcg (dict del frontend) a PanelDeControlInput."""
    # Mapear tarifa capacitación (frontend puede enviar como "tarifaCap" o "tarifa_cap")
    tarifa_cap_raw = pcg.get("tarifaCap") or pcg.get("tarifa_cap") or "0"
    
    return PanelDeControlInput(
        cliente                           = cliente,
        tipo_cliente                      = pcg.get("tipoCliente") or "",
        linea_negocio                     = pcg.get("servicio", ""),
        # ... otros campos ...
        pct_ausentismo                    = _a_fraccion(pcg.get("ausentismo", "0")),
        
        # NUEVO: Mapear tarifa_diaria_capacitacion desde input usuario
        tarifa_diaria_capacitacion        = _a_float(tarifa_cap_raw),
    )
```

---

## 6. REEMPLAZAR CONSTANTE EN 5 UBICACIONES

**Ubicación:** `input/context_builder.py`

**AGREGAR IMPORT AL INICIO:**
```python
from nexa_engine.domain.constants import MES_INICIO_AJUSTE_ANUAL
```

### 6.1 Línea ~287 (método `_construir_panel`)

**ANTES:**
```python
mes_aplicacion = (
    panel.indexacion_mes_aplicacion
    if panel.indexacion_mes_aplicacion is not None
    else int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))
)
```

**DESPUÉS:**
```python
mes_aplicacion = (
    panel.indexacion_mes_aplicacion
    if panel.indexacion_mes_aplicacion is not None
    else MES_INICIO_AJUSTE_ANUAL
)
```

### 6.2 Línea ~424 (método `_construir_perfiles_soporte`)

**ANTES:**
```python
mes_ajuste = int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))
```

**DESPUÉS:**
```python
mes_ajuste = MES_INICIO_AJUSTE_ANUAL
```

### 6.3 Línea ~644 (método `_construir_parametros_nomina`)

**ANTES:**
```python
mes_aplicacion_aumento = int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))
```

**DESPUÉS:**
```python
mes_aplicacion_aumento = MES_INICIO_AJUSTE_ANUAL
```

### 6.4 Línea ~792 (método `_construir_cadena_b`)

**ANTES:**
```python
mes_aplicacion_aumento = int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))
```

**DESPUÉS:**
```python
mes_aplicacion_aumento = MES_INICIO_AJUSTE_ANUAL
```

### 6.5 Línea ~860 (método `_construir_cadena_c`)

**Ya implementado en FASE 4** (ver sección anterior)

---

## 7. ELIMINAR CÓDIGO LEGACY

### 7.1 Eliminar `get_costo_operativo()` en PayrollParametrizationRepository

**Ubicación:** `repositories/payroll_parametrization_repository.py` (líneas ~287-325)

**ELIMINAR COMPLETO:**
```python
# ───────────────────────────────────────────────────────────────────────────
# Costos Operativos (HR-costos_operativos)
# ───────────────────────────────────────────────────────────────────────────

def get_costo_operativo(self, clave: str) -> float:
    """Retorna un costo/parámetro operativo del motor por su clave.

    Fuente: HR-costos_operativos (sección en storage JSON).

    Claves disponibles:
      tarifa_dia_cap, opex_ti_por_estacion,
      capex_recurrente_por_estacion, capex_inicial_por_estacion,
      pct_aumento_tecnologico_anual, mes_inicio_ajuste_anual

    Raises:
        ParametrizationError: si la sección o clave no existe.
    """
    self._ensure_hr_loaded()
    tabla = self._hr_data.get("costos_operativos")
    if not tabla:
        raise ParametrizationError(
            "HR-costos_operativos section missing. "
            "Add 'costos_operativos' key to active HR parametrization JSON.",
            module="hr",
        )
    for row in tabla:
        if row.get("clave") == clave:
            val = row.get("valor")
            if val is None:
                raise ParametrizationError(
                    f"Valor missing for costo_operativo '{clave}' in HR",
                    module="hr",
                )
            v = float(val)
            logger.info(
                "[PARAMETRIZATION] costo_operativo=%s value=%s source=HR-costos_operativos",
                clave, v,
            )
            return v
    raise ParametrizationError(
        f"Clave '{clave}' not found in HR-costos_operativos",
        module="hr",
    )
```

### 7.2 Eliminar Facade en `ParametrizationProvider`

**Ubicación:** `repositories/parametrization_provider.py` (líneas ~637-662)

**ELIMINAR COMPLETO:**
```python
def get_costo_operativo(self, clave: str) -> float:
    """Retorna un costo/parámetro operativo por su clave.

    Fuente: HR-costos_operativos.

    Claves disponibles:
        tarifa_dia_cap, opex_ti_por_estacion,
        capex_recurrente_por_estacion, capex_inicial_por_estacion,
        pct_aumento_tecnologico_anual, mes_inicio_ajuste_anual.

    Args:
        clave: Clave del parámetro.

    Returns:
        Valor como float.

    Raises:
        ParametrizationError: si la sección o clave no existe en HR.
    """
    value = self._payroll.get_costo_operativo(clave)
    logger.debug(
        "[REPOSITORY] repository=PayrollParametrizationRepository "
        "operation=get_costo_operativo clave=%s value=%s source=HR-costos_operativos",
        clave, value,
    )
    return value
```

### 7.3 Actualizar Validator

**Ubicación:** `validators/parametrization_completeness_validator.py`

**ANTES:**
```python
REQUIRED_PARAMETRIZATION_SECTIONS = [
    "costos_operativos",  # ← ELIMINAR
    "nomina",
    "seg_social",
    "prestaciones",
    "recargos",
    "costo_fijo",
    "ratios",
    "reglas_staff",
    "salarios",
]

REQUIRED_COSTOS_OPERATIVOS = [
    "tarifa_dia_cap",
    "opex_ti_por_estacion",
    "capex_recurrente_por_estacion",
    "mes_inicio_ajuste_anual",
    "pct_aumento_tecnologico_anual",
]
```

**DESPUÉS:**
```python
REQUIRED_PARAMETRIZATION_SECTIONS = [
    # "costos_operativos",  ← ELIMINADO (sección obsoleta)
    "nomina",
    "seg_social",
    "prestaciones",
    "recargos",
    "costo_fijo",
    "ratios",
    "reglas_staff",
    "salarios",
]

# REQUIRED_COSTOS_OPERATIVOS eliminado por completo
# Los campos migraron a:
#   - tarifa_dia_cap → USER INPUT (panel.tarifa_diaria_capacitacion)
#   - opex_ti_por_estacion → CALCULADO (context_builder._calcular_opex_ti_total)
#   - capex_recurrente → CALCULADO (context_builder._calcular_capex_recurrente)
#   - pct_aumento_tecnologico → PARAMETRIZATION (OP-Componente)
#   - mes_inicio_ajuste_anual → CONSTANTE (domain/constants.py)
```

**Eliminar método de validación de costos_operativos:**

```python
# BUSCAR Y ELIMINAR (líneas ~50-70):
def _validar_costos_operativos(self, hr_data: dict):
    """Valida completitud de HR-costos_operativos."""
    # ... código a eliminar ...
```

**Eliminar llamada en método principal:**

```python
# EN validate() (línea ~30):
# self._validar_costos_operativos(hr_data)  ← ELIMINAR ESTA LÍNEA
```

---

## ✅ CHECKLIST FINAL

Una vez completados todos los cambios, verificar:

- [ ] `domain/constants.py` creado con `MES_INICIO_AJUSTE_ANUAL = 1`
- [ ] DTOs actualizados (`PanelDeControlInput`, `PanelDeControl`, `PcgInput`)
- [ ] 3 métodos de cálculo agregados a `SimulationContextBuilder`
- [ ] `_construir_no_payroll()` actualizado (nuevo parámetro `perfiles_a`)
- [ ] `get_economic_component()` agregado a `FinancialParametrizationRepository`
- [ ] Facade `get_componente_indexacion()` agregado a `ParametrizationProvider`
- [ ] `_construir_cadena_c()` usa IPC desde OP-Componente
- [ ] `UnifiedInputAdapter` mapea `tarifaCap`
- [ ] Constante reemplazada en 5 ubicaciones de `context_builder.py`
- [ ] `get_costo_operativo()` eliminado de `PayrollParametrizationRepository`
- [ ] Facade `get_costo_operativo()` eliminado de `ParametrizationProvider`
- [ ] Validator actualizado (sección `costos_operativos` removida)
- [ ] Tests actualizados (fixtures, imports)
- [ ] Suite completa de tests ejecutada y pasando

---

**FIN DE EJEMPLOS DE CÓDIGO**
