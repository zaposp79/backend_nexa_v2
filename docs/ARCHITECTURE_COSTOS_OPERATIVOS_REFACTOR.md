# ARQUITECTURA: Refactor costos_operativos — Motor Financiero Determinístico

**Documento:** Diseño Arquitectónico Definitivo  
**Fecha:** 2026-05-27  
**Autor:** Arquitecto Backend Senior NEXA  
**Estado:** READY FOR IMPLEMENTATION  
**Versión:** 2.0 (Final)

---

## RESUMEN EJECUTIVO

### Problema
El motor financiero NEXA tiene **ambigüedad en las fuentes de datos** del módulo `costos_operativos`. Actualmente el sistema mezcla:
- INPUT del usuario (JSON payload)
- PARAMETRIZACIÓN (storage JSON versionado)
- VALORES CALCULADOS (derivados)
- CONSTANTES BACKEND (hardcodes disfrazados)

Esto causa:
- ❌ **6 tests fallan** por `ParametrizationError: HR-costos_operativos missing`
- ❌ **Imposible validar completitud** de parametrización
- ❌ **Duplicación de fuentes** para un mismo campo
- ❌ **Motor bloqueado** hasta que se resuelva

### Solución
**Eliminar `HR-costos_operativos` por completo** y reclasificar cada campo según su naturaleza funcional:

| **Fuente** | **Campos** | **Acción** |
|------------|-----------|-----------|
| **INPUT USUARIO** | `tarifa_dia_cap` | Mapear desde `datos_operativos.tarifa_diaria_capacitacion` |
| **PARAMETRIZACIÓN** | `pct_aumento_tecnologico_anual` | Obtener desde `OP-Componente` (IPC del año) |
| **CALCULADO BACKEND** | `opex_ti_por_estacion`, `capex_recurrente`, `capex_inicial` | Calcular dinámicamente desde `opex_fijo[]` e `inversiones[]` |
| **CONSTANTE BACKEND** | `mes_inicio_ajuste_anual` | Definir como constante `MES_INICIO_AJUSTE_ANUAL = 1` |

### Resultado Final
✅ **Single source of truth** por campo  
✅ **Trazabilidad financiera completa**  
✅ **Cero hardcodes ocultos**  
✅ **Motor 100% determinístico**

---

## 1. MAPA DE OWNERSHIP — CLASIFICACIÓN DEFINITIVA

### Tabla Maestra

| Campo | Fuente Actual (INCORRECTO) | Fuente Correcta | Tipo | Justificación Arquitectónica |
|-------|---------------------------|-----------------|------|----------------------------|
| **`tarifa_dia_cap`** | `HR-costos_operativos` ❌ | `datos_operativos.tarifa_diaria_capacitacion` ✅ | **USER_INPUT** | El usuario define cuánto cuesta 1 día de capacitación para su deal. Es un parámetro comercial, no una constante de HR. |
| **`opex_ti_por_estacion`** | `HR-costos_operativos` ❌ | Backend calcula desde `opex_fijo.items[]` ✅ | **DERIVED** | NO es un concepto atómico. Es la SUMA de Internet + Licencias CX1 + Plataformas + Soporte. Persistir el total viola DRY. |
| **`capex_recurrente_por_estacion`** | `HR-costos_operativos` ❌ | Backend calcula desde `inversiones[]` ✅ | **DERIVED** | Es `Σ(precio_inversión / meses_amortización)`. Persistir el resultado de una fórmula viola separación cálculo/storage. |
| **`capex_inicial_por_estacion`** | `HR-costos_operativos` ❌ | Backend calcula desde `inversiones[]` ✅ | **DERIVED** | Es `Σ(precio_total_inversión)`. Debe calcularse en tiempo real para reflejar cambios en inversiones. |
| **`pct_aumento_tecnologico_anual`** | `HR-costos_operativos` ❌ | `OP-Componente` → IPC del año ✅ | **PARAMETRIZATION** | La inflación tecnológica proviene de parámetros macroeconómicos oficiales (DANE). Excel OP-Componente es la fuente master. |
| **`mes_inicio_ajuste_anual`** | `HR-costos_operativos` ❌ | Constante backend `MES_INICIO_AJUSTE_ANUAL = 1` ✅ | **CONSTANT** | Es una constante fiscal de Colombia (enero = mes 1). No varía por deal, cliente ni parametrización. |

---

## 2. ANÁLISIS DE DEPENDENCIAS ACTUALES

### 2.1 Archivos que LEEN `costos_operativos`

```
input/context_builder.py
├─ Línea 287:  mes_inicio_ajuste_anual → indexacion.mes_aplicacion
├─ Línea 424:  mes_inicio_ajuste_anual → reglas_staff
├─ Línea 644:  mes_inicio_ajuste_anual + tarifa_dia_cap → parametros_nomina
├─ Línea 670:  capex_recurrente_por_estacion → parametros_no_payroll
├─ Línea 678:  capex_inicial_por_estacion → parametros_no_payroll
├─ Línea 669:  opex_ti_por_estacion → parametros_no_payroll
├─ Línea 792:  mes_inicio_ajuste_anual → cadena_b
└─ Línea 860:  mes_inicio_ajuste_anual + pct_aumento_tecnologico_anual → cadena_c
```

### 2.2 Repositorios Involucrados

```
repositories/payroll_parametrization_repository.py
└─ get_costo_operativo(clave) → Línea 287-325
   └─ Lee desde self._hr_data.get("costos_operativos")
      └─ Fuente: storage/parametrization/hr/{version_id}.json

repositories/parametrization_provider.py
└─ get_costo_operativo(clave) → Línea 637-662 (facade)
   └─ Delega a PayrollParametrizationRepository

validators/parametrization_completeness_validator.py
└─ REQUIRED_COSTOS_OPERATIVOS = [...]
   └─ Valida existencia de sección "costos_operativos" en HR
```

### 2.3 Flujo Actual (PROBLEMÁTICO)

```
┌──────────────────────────────────────┐
│  Usuario NO envía tarifa_dia_cap     │ ❌ Ambiguo
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  SimulationContextBuilder            │
│  └─ self._prov.get_costo_operativo() │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  ParametrizationProvider             │
│  └─ PayrollParametrizationRepository │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  storage/parametrization/hr/         │
│  {version_id}.json                   │
│  "costos_operativos": []  ← NO EXISTE│ ❌ ERROR
└──────────────────────────────────────┘
```

---

## 3. ARQUITECTURA OBJETIVO

### 3.1 Nuevo Flujo Determinístico

```
╔══════════════════════════════════════════════════════════╗
║                    USER INPUT (JSON)                      ║
╚══════════════════════════════════════════════════════════╝
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
┌──────────┐      ┌──────────────┐     ┌──────────────┐
│tarifa_   │      │opex_fijo[]   │     │inversiones[] │
│diaria_cap│      │  items       │     │              │
└────┬─────┘      └──────┬───────┘     └──────┬───────┘
     │                   │                     │
     │ (DIRECTO)         │ (CALCULAR)          │ (CALCULAR)
     │                   │                     │
     ▼                   ▼                     ▼
╔══════════════════════════════════════════════════════════╗
║          SIMULATION CONTEXT BUILDER                       ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ _construir_parametros_nomina()                   │    ║
║  │   tarifa_dia_cap = panel.tarifa_diaria_capacit.  │    ║
║  └──────────────────────────────────────────────────┘    ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ _construir_no_payroll()                          │    ║
║  │   opex_ti = _calcular_opex_ti_total(perfiles)   │    ║
║  │   capex_r = _calcular_capex_recurrente(perfiles)│    ║
║  │   capex_i = _calcular_capex_inicial(perfiles)   │    ║
║  └──────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║           PARAMETRIZATION PROVIDER                        ║
║  ┌──────────────────────────────────────────────────┐    ║
║  │ get_componente_indexacion("IPC", año_inicio)     │    ║
║  │   → Fuente: OP-Componente                        │    ║
║  └──────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║                 BACKEND CONSTANTS                         ║
║  MES_INICIO_AJUSTE_ANUAL = 1                              ║
╚══════════════════════════════════════════════════════════╝
                          │
                          ▼
╔══════════════════════════════════════════════════════════╗
║                   PRICING REQUEST                         ║
║  → ParametrosNomina(tarifa_dia_cap=...)                   ║
║  → ParametrosNoPayroll(opex_ti=..., capex=...)            ║
║  → ParametrosCadenaC(pct_aumento_tecnologico=...)         ║
╚══════════════════════════════════════════════════════════╝
```

### 3.2 Separación de Capas

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: USER INPUT                                     │
│ ─────────────────────────────────────────────────────   │
│ ✅ tarifa_diaria_capacitacion (datos_operativos)        │
│ ✅ opex_fijo.items[] (conceptos TI detallados)          │
│ ✅ inversiones[] (CAPEX hardware/software)              │
│ ✅ indexacion.mes_aplicacion (OPCIONAL)                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: PARAMETRIZATION (storage JSON versionado)     │
│ ─────────────────────────────────────────────────────   │
│ ✅ OP-Componente → IPC, SMLV, 70%SMMLV-30%IPC (por año) │
│ ✅ HR-CostoFijo → arriendo, energía, vigilancia (por    │
│                   sede)                                 │
│ ✅ HR-Med-Seg → costo_examen_medico (por ciudad)        │
│ ❌ costos_operativos ← ELIMINADO COMPLETAMENTE          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 3: DERIVED CALCULATIONS (backend en runtime)     │
│ ─────────────────────────────────────────────────────   │
│ ✅ opex_ti_por_estacion = Σ(opex_fijo[tipo='TI'])      │
│ ✅ capex_recurrente = Σ(precio / meses_amortización)    │
│ ✅ capex_inicial = Σ(precio_total_inversión)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ LAYER 4: CONSTANTS (código fuente inmutable)           │
│ ─────────────────────────────────────────────────────   │
│ ✅ MES_INICIO_AJUSTE_ANUAL = 1  (enero estándar fiscal) │
│ ✅ DIAS_LABORALES_POR_MES = 20                          │
│ ✅ HORAS_LABORALES_POR_DIA = 8                          │
└─────────────────────────────────────────────────────────┘
```

---

## 4. PLAN DE IMPLEMENTACIÓN DETALLADO

### FASE 1: Preparar Constantes y DTOs (30 min)

#### 1.1 Crear `domain/constants.py`

```python
"""
Constantes del motor financiero NEXA.

Valores que NO varían por deal, parametrización ni cliente.
Cambios aquí impactan TODOS los cálculos globalmente.
"""

# Mes en que aplica el ajuste anual (indexación salarial/tecnológica)
# Valor: 1 = enero (estándar fiscal Colombia)
# Fuente: Ley 1393 de 2010 Art. 3 (reajuste SMMLV)
MES_INICIO_AJUSTE_ANUAL = 1

# Constantes laborales estándar Colombia
DIAS_LABORALES_POR_MES = 20
HORAS_LABORALES_POR_DIA = 8
SEMANAS_POR_MES = 4.33  # Promedio ponderado (52 semanas / 12 meses)
```

#### 1.2 Agregar `tarifa_diaria_capacitacion` a DTOs

**Archivo:** `domain/user_inputs.py`

```python
@dataclass
class PanelDeControlInput:
    """
    Datos del negocio configurados por el usuario.
    """
    # ... campos existentes ...
    
    # NUEVO: Tarifa diaria de capacitación por agente (valor comercial del deal)
    tarifa_diaria_capacitacion: float
```

**Archivo:** `domain/models/panel.py`

```python
@dataclass
class PanelDeControl:
    """Parámetros maestros del deal."""
    # ... campos existentes ...
    
    # NUEVO: Tarifa diaria de capacitación (COP / día / agente)
    tarifa_diaria_capacitacion: float
```

**Archivo:** `simulation/panel/dto.py`

```python
class PcgInput(BaseModel):
    """Panel de Control General — entrada REST API."""
    # ... campos existentes ...
    
    # NUEVO: Tarifa capacitación
    tarifa_cap: float = Field(
        alias="tarifaCap",
        description="Tarifa diaria de capacitación por agente (COP)",
    )
```

---

### FASE 2: Implementar Cálculos Derivados (2 horas)

#### 2.1 Métodos en `input/context_builder.py`

**Método 1: `_calcular_opex_ti_total()`**

```python
def _calcular_opex_ti_total(self, perfiles: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el OPEX TI total promedio por estación desde opex_fijo.items[].
    
    REGLA: opex_ti_por_estacion NO es un concepto atómico en el modelo de datos.
    Es la SUMA de todos los costos OPEX de tecnología (Internet, Licencias, 
    Plataformas, Soporte) dividido por el número de estaciones.
    
    Conceptos incluidos (filtro dinámico):
      - tipo = "Tecnología" o concepto contiene ["Internet", "Licencia", 
        "Plataforma", "CX1", "Soporte TI"]
    
    Args:
        perfiles: Lista de perfiles de Cadena A con opex_fijo configurado.
    
    Returns:
        OPEX TI promedio ponderado por estación presencial.
        Retorna 0.0 si no hay perfiles con OPEX TI o estaciones = 0.
    
    Ejemplo:
        perfil_1: 10 estaciones, OPEX = [Internet 450k/10, Licencias 1.2M/10]
        perfil_2: 5 estaciones, OPEX = [Internet 450k/10]
        
        opex_ti_total = (450k + 1.2M + 450k) / 15 estaciones
                      = 2.1M / 15
                      = 140,000 COP/estación/mes
    """
    total_opex_ti = 0.0
    total_estaciones = 0.0
    
    # Palabras clave para identificar costos TI
    KEYWORDS_TI = ["internet", "licencia", "plataforma", "cx1", "soporte", "software", "saas"]
    
    for perfil in perfiles:
        if not hasattr(perfil, 'opex_fijo') or not perfil.opex_fijo:
            continue
        
        items = perfil.opex_fijo.get('items', []) if isinstance(perfil.opex_fijo, dict) else []
        if not items:
            continue
        
        # Estaciones presenciales (FTE × pct_presencia)
        estaciones_perfil = perfil.fte * perfil.pct_presencia
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
    
    return total_opex_ti / total_estaciones if total_estaciones > 0 else 0.0
```

**Método 2: `_calcular_capex_recurrente()`**

```python
def _calcular_capex_recurrente(self, perfiles: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el CAPEX recurrente mensual promedio por estación desde inversiones[].
    
    REGLA: capex_recurrente = Σ(precio_inversión / meses_amortización) / estaciones
    
    El CAPEX recurrente es la cuota mensual amortizada de todas las inversiones
    en hardware, software y periféricos que se renuevan periódicamente.
    
    Ejemplo de inversiones típicas:
      - PC Desktop: 3,508,260 COP / 60 meses = 58,471 COP/mes/estación
      - Licencia Office: 300,000 COP / 12 meses = 25,000 COP/mes/estación
      - Monitor: 800,000 COP / 48 meses = 16,667 COP/mes/estación
    
    Args:
        perfiles: Lista de perfiles con inversiones configuradas.
    
    Returns:
        CAPEX recurrente promedio ponderado por estación.
    """
    total_capex_mensual = 0.0
    total_estaciones = 0.0
    
    for perfil in perfiles:
        if not hasattr(perfil, 'inversiones') or not perfil.inversiones:
            continue
        
        # Para CAPEX usamos FTE bruto (no pct_presencia) porque el hardware
        # se asigna por agente, no por estación física
        estaciones_perfil = perfil.fte
        if estaciones_perfil <= 0:
            continue
        
        total_estaciones += estaciones_perfil
        
        for inversion in perfil.inversiones:
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
    
    return total_capex_mensual / total_estaciones if total_estaciones > 0 else 0.0
```

**Método 3: `_calcular_capex_inicial()`**

```python
def _calcular_capex_inicial(self, perfiles: List[PerfilCadenaAInput]) -> float:
    """
    Calcula el CAPEX inicial total por estación desde inversiones[].
    
    REGLA: capex_inicial = Σ(precio_total_inversión) / estaciones
    
    El CAPEX inicial es la inversión up-front completa (sin amortizar) que se
    debe realizar para equipar todas las estaciones del contrato.
    
    Este valor se usa en el cálculo de financiación inicial (mes 1) y NO se
    incluye en los costos recurrentes mensuales.
    
    Args:
        perfiles: Lista de perfiles con inversiones configuradas.
    
    Returns:
        CAPEX inicial promedio ponderado por estación.
    """
    total_capex_inicial = 0.0
    total_estaciones = 0.0
    
    for perfil in perfiles:
        if not hasattr(perfil, 'inversiones') or not perfil.inversiones:
            continue
        
        estaciones_perfil = perfil.fte
        if estaciones_perfil <= 0:
            continue
        
        total_estaciones += estaciones_perfil
        
        for inversion in perfil.inversiones:
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
    
    return total_capex_inicial / total_estaciones if total_estaciones > 0 else 0.0
```

#### 2.2 Integrar en `_construir_no_payroll()`

**Archivo:** `input/context_builder.py` (línea ~650)

```python
def _construir_no_payroll(self, panel, sede: str, perfiles_a: List[PerfilCadenaAInput]) -> ParametrosNoPayroll:
    """
    Construye ParametrosNoPayroll calculando dinámicamente OPEX TI y CAPEX.
    
    CAMBIO ARQUITECTÓNICO: ya NO se lee costos_operativos de parametrización.
    Todos los valores se calculan desde el input del usuario o se obtienen
    de parametrización específica (HR-CostoFijo por sede).
    """
    # Costos de infraestructura por sede (arriendo, energía, vigilancia, aseo)
    costos_sede = self._prov.get_costo_no_payroll(sede)
    
    # NUEVO: Calcular dinámicamente desde el input del usuario
    opex_ti_por_estacion = self._calcular_opex_ti_total(perfiles_a)
    capex_por_estacion = self._calcular_capex_recurrente(perfiles_a)
    capex_inicial_por_estacion = self._calcular_capex_inicial(perfiles_a)
    
    return ParametrosNoPayroll(
        opex_ti_por_estacion       = opex_ti_por_estacion,
        capex_por_estacion         = capex_por_estacion,
        arriendo_por_estacion      = costos_sede["arriendo"],
        energia_por_estacion       = costos_sede["energia"],
        vigilancia_por_estacion    = costos_sede["vigilancia"],
        aseo_por_estacion          = costos_sede["aseo"],
        otros_fijos_por_estacion   = costos_sede.get("mantenimiento", 0.0),
        capex_inicial_por_estacion = capex_inicial_por_estacion,
    )
```

---

### FASE 3: Parametrización IPC desde OP-Componente (1 hora)

#### 3.1 Nuevo método en `FinancialParametrizationRepository`

**Archivo:** `repositories/financial_parametrization_repository.py`

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
    """
    self._ensure_op_loaded()
    tabla = self._get_sheet(self._op_data, "componente")
    
    if not tabla or "rows" not in tabla:
        raise ParametrizationError(
            "OP-Componente sheet not found in OP parametrization. "
            "Verify storage/parametrization/op/{version_id}.json",
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
    
    raise ParametrizationError(
        f"Componente económico '{componente}' año {anio} not found in OP-Componente. "
        f"Add row to Excel OP → sheet Componente with: componente='{componente}', ano={anio}",
        module="op",
    )
```

#### 3.2 Facade en `ParametrizationProvider`

**Archivo:** `repositories/parametrization_provider.py`

```python
def get_componente_indexacion(self, componente: str, anio: int) -> float:
    """
    Obtiene componente de indexación desde OP-Componente.
    
    Usado para calcular pct_aumento_tecnologico_anual (IPC del año contrato).
    
    Args:
        componente: Nombre del componente (e.g., "IPC").
        anio: Año fiscal.
    
    Returns:
        Tasa de indexación.
    
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

#### 3.3 Usar en `_construir_cadena_c()`

**Archivo:** `input/context_builder.py` (línea ~850)

```python
from datetime import datetime

def _construir_cadena_c(self, cadena_c, panel):
    """Construye ParametrosCadenaC resolviendo pct_aumento_tecnologico desde OP."""
    # Extraer año de inicio del contrato
    try:
        año_inicio = datetime.strptime(panel.fecha_inicio, "%Y-%m-%d").year
    except ValueError:
        # Fallback si formato inesperado
        año_inicio = 2026
    
    # NUEVO: Obtener IPC del año desde parametrización OP-Componente
    try:
        pct_aumento_tecnologico = self._prov.get_componente_indexacion("IPC", año_inicio)
    except Exception as exc:
        logger.warning(
            "Failed to get IPC for year %d from OP-Componente: %s. Using 0.0.",
            año_inicio, exc
        )
        pct_aumento_tecnologico = 0.0
    
    # Resto del método sin cambios...
    return ParametrosCadenaC(
        # ... campos existentes ...
        pct_aumento_tecnologico = pct_aumento_tecnologico,
        mes_aplicacion_aumento  = MES_INICIO_AJUSTE_ANUAL,  # <-- CONSTANTE
        # ...
    )
```

---

### FASE 4: Adapters — Mapear Input (30 min)

#### 4.1 UnifiedInputAdapter

**Archivo:** `adapters/unified_input_adapter.py` (método `_panel_from_dict`)

```python
@classmethod
def _panel_from_dict(cls, pcg: Dict) -> PanelDeControlInput:
    """Convierte pcg (dict del frontend) a PanelDeControlInput."""
    # ... campos existentes ...
    
    # NUEVO: Mapear tarifa capacitación
    tarifa_cap_raw = pcg.get("tarifaCap") or pcg.get("tarifa_cap") or "0"
    
    return PanelDeControlInput(
        # ... campos existentes ...
        tarifa_diaria_capacitacion = _a_float(tarifa_cap_raw),
        # ...
    )
```

#### 4.2 JsonCaseLoader (legacy)

**Archivo:** `adapters/json_loader.py` (método `_parametros_nomina`)

```python
def _parametros_nomina(self, data: Dict) -> ParametrosNomina:
    """Busca en condiciones_cadena_a.parametros_nomina o en raíz."""
    cad_a = data.get("condiciones_cadena_a", {})
    d = cad_a.get("parametros_nomina") or data.get("parametros_nomina", {})
    
    # ELIMINAR: tarifa_dia_cap desde aquí (ahora viene de panel_de_control)
    # tarifa_dia_cap = float(d["tarifa_dia_cap"])  ← BORRAR
    
    # NUEVO: Obtener desde panel_de_control
    panel = data.get("panel_de_control", {})
    tarifa_dia_cap = float(panel.get("tarifa_diaria_capacitacion", 0.0))
    
    return ParametrosNomina(
        mes_inicio             = int(d.get("mes_inicio", 1)),
        mes_fin                = int(d["mes_fin"]),
        pct_aumento_salarial   = float(d["pct_aumento_salarial"]),
        mes_aplicacion_aumento = int(d["mes_aplicacion_aumento"]),
        tarifa_dia_cap         = tarifa_dia_cap,  # <-- DESDE PANEL
        costo_examen_medico    = float(d["costo_examen_medico"]),
        costo_estudio_seg      = float(d.get("costo_estudio_seg", 0.0)),
    )
```

---

### FASE 5: Reemplazar Constante en 5 Ubicaciones (15 min)

**Archivo:** `input/context_builder.py`

```python
from nexa_engine.domain.constants import MES_INICIO_AJUSTE_ANUAL

# Línea 287 (método _construir_panel)
mes_aplicacion = (
    panel.indexacion_mes_aplicacion
    if panel.indexacion_mes_aplicacion is not None
    else MES_INICIO_AJUSTE_ANUAL
)

# Línea 424 (método _construir_perfiles_soporte)
mes_ajuste = MES_INICIO_AJUSTE_ANUAL

# Línea 644 (método _construir_parametros_nomina)
mes_aplicacion_aumento = MES_INICIO_AJUSTE_ANUAL

# Línea 792 (método _construir_cadena_b)
mes_aplicacion_aumento = MES_INICIO_AJUSTE_ANUAL

# Línea 860 (método _construir_cadena_c) — ya implementado en Fase 3
mes_aplicacion_aumento = MES_INICIO_AJUSTE_ANUAL
```

---

### FASE 6: Eliminar Código Legacy (30 min)

#### 6.1 Eliminar método `get_costo_operativo()`

**Archivo:** `repositories/payroll_parametrization_repository.py`

```python
# ELIMINAR COMPLETO (líneas 287-325):
# def get_costo_operativo(self, clave: str) -> float:
#     ...
```

**Archivo:** `repositories/parametrization_provider.py`

```python
# ELIMINAR COMPLETO (líneas 637-662):
# def get_costo_operativo(self, clave: str) -> float:
#     ...
```

#### 6.2 Actualizar Validator

**Archivo:** `validators/parametrization_completeness_validator.py`

```python
# BEFORE:
REQUIRED_PARAMETRIZATION_SECTIONS = [
    "costos_operativos",  # ← ELIMINAR
    "nomina",
    "seg_social",
    # ...
]

REQUIRED_COSTOS_OPERATIVOS = [  # ← ELIMINAR SECCIÓN COMPLETA
    "tarifa_dia_cap",
    "opex_ti_por_estacion",
    "capex_recurrente_por_estacion",
    "mes_inicio_ajuste_anual",
    "pct_aumento_tecnologico_anual",
]

# AFTER:
REQUIRED_PARAMETRIZATION_SECTIONS = [
    # "costos_operativos",  ← ELIMINADO
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
```

---

### FASE 7: Tests (1.5 horas)

#### 7.1 Tests Unitarios Nuevos

**Archivo:** `tests/unit/test_context_builder_calculations.py` (NUEVO)

```python
"""Tests unitarios para métodos de cálculo de costos_operativos."""

import pytest
from nexa_engine.input.context_builder import SimulationContextBuilder
from nexa_engine.domain.user_inputs import PerfilCadenaAInput


class TestCostosOperativosCalculations:
    """Suite de tests para cálculos dinámicos de OPEX/CAPEX."""
    
    def test_calcular_opex_ti_total_con_un_perfil(self):
        """Caso básico: 1 perfil con OPEX TI definido."""
        builder = SimulationContextBuilder()
        perfiles = [
            PerfilCadenaAInput(
                nombre="Inbound Voz",
                rol="Agente Basico",
                modalidad="Inbound",
                canal="Voz",
                fte=10.0,
                pct_presencia=1.0,
                opex_fijo={
                    "items": [
                        {
                            "concepto": "Internet dedicado",
                            "tipo": "Tecnología",
                            "costo": 450000,
                            "cantidad": 10,
                            "costo_totalizado": False
                        }
                    ]
                }
            )
        ]
        
        resultado = builder._calcular_opex_ti_total(perfiles)
        
        # 450k × 10 qty / 10 estaciones = 450,000 COP/estación
        assert resultado == 450000.0
    
    def test_calcular_capex_recurrente_pc_desktop(self):
        """Caso Excel V2-6: PC Desktop 3.5M / 60 meses."""
        builder = SimulationContextBuilder()
        perfiles = [
            PerfilCadenaAInput(
                nombre="Inbound Voz",
                rol="Agente Basico",
                modalidad="Inbound",
                canal="Voz",
                fte=10.0,
                inversiones=[
                    {
                        "concepto": "PC Desktop",
                        "precio": 3508260,
                        "cantidad": 10,
                        "meses_amortizacion": 60,
                        "es_precio_total": False
                    }
                ]
            )
        ]
        
        resultado = builder._calcular_capex_recurrente(perfiles)
        
        # 3,508,260 / 60 = 58,471 COP/mes/estación
        assert abs(resultado - 58471.0) < 1.0  # Tolerancia float
    
    def test_calcular_capex_inicial_suma_total(self):
        """Caso: CAPEX inicial = suma completa de inversiones."""
        builder = SimulationContextBuilder()
        perfiles = [
            PerfilCadenaAInput(
                nombre="Inbound Voz",
                rol="Agente Basico",
                modalidad="Inbound",
                canal="Voz",
                fte=10.0,
                inversiones=[
                    {"precio": 3508260, "cantidad": 10, "es_precio_total": False},
                    {"precio": 800000, "cantidad": 10, "es_precio_total": False},
                ]
            )
        ]
        
        resultado = builder._calcular_capex_inicial(perfiles)
        
        # (3,508,260 + 800,000) × 10 / 10 estaciones = 4,308,260 COP/estación
        assert abs(resultado - 4308260.0) < 1.0
```

#### 7.2 Actualizar Fixtures de Tests Existentes

**Acción:** Buscar todos los tests que llaman `get_costo_operativo()` y reemplazar:

```bash
grep -r "get_costo_operativo" tests/ --include="*.py"
```

Para cada match, actualizar:
- Si es `tarifa_dia_cap` → agregar a panel_de_control fixture
- Si es `mes_inicio_ajuste_anual` → reemplazar por `MES_INICIO_AJUSTE_ANUAL`
- Si es OPEX/CAPEX → mockear `_calcular_opex_ti_total()`, etc.

---

## 5. LISTA COMPLETA DE ARCHIVOS A MODIFICAR

### 5.1 CREAR (3 archivos)

| Archivo | Propósito |
|---------|-----------|
| `domain/constants.py` | Constantes backend (`MES_INICIO_AJUSTE_ANUAL = 1`) |
| `tests/unit/test_context_builder_calculations.py` | Tests unitarios para métodos de cálculo |
| `docs/ARCHITECTURE_COSTOS_OPERATIVOS_REFACTOR.md` | Este documento (arquitectura) |

### 5.2 MODIFICAR (11 archivos)

| Archivo | Cambios | Líneas Aprox |
|---------|---------|--------------|
| `domain/models/panel.py` | Agregar `tarifa_diaria_capacitacion: float` | +1 |
| `domain/user_inputs.py` | Agregar `tarifa_diaria_capacitacion: float` | +1 |
| `simulation/panel/dto.py` | Agregar `tarifa_cap: float` con alias | +3 |
| `adapters/unified_input_adapter.py` | Mapear `tarifaCap` → `tarifa_diaria_capacitacion` | +2 |
| `adapters/json_loader.py` | Leer `tarifa_diaria_capacitacion` de panel | ~5 |
| `input/context_builder.py` | 6 cambios principales (ver FASE 2 y 5) | ~150 |
| `repositories/financial_parametrization_repository.py` | Agregar `get_economic_component()` | +40 |
| `repositories/parametrization_provider.py` | Agregar facade `get_componente_indexacion()` | +15 |
| `validators/parametrization_completeness_validator.py` | Eliminar `costos_operativos` de REQUIRED | -15 |
| `tests/unit/test_calculators_nomina.py` | Actualizar fixtures (tarifa_dia_cap de panel) | ~10 |
| `tests/integration/test_payroll_components.py` | Actualizar fixtures | ~5 |

### 5.3 ELIMINAR (2 métodos)

| Archivo | Método | Líneas |
|---------|--------|--------|
| `repositories/payroll_parametrization_repository.py` | `get_costo_operativo()` | ~40 |
| `repositories/parametrization_provider.py` | `get_costo_operativo()` wrapper | ~25 |

**Total:** 3 creados, 11 modificados, 2 eliminaciones = **16 archivos** impactados.

---

## 6. CRITERIOS DE ACEPTACIÓN

### 6.1 Funcional

- [ ] Motor ejecuta simulación completa sin `ParametrizationError`
- [ ] `tarifa_dia_cap` proviene de `panel.tarifa_diaria_capacitacion`
- [ ] OPEX TI calculado dinámicamente desde `opex_fijo.items[]`
- [ ] CAPEX recurrente e inicial calculados desde `inversiones[]`
- [ ] IPC obtenido desde `OP-Componente` (no hardcoded)
- [ ] `MES_INICIO_AJUSTE_ANUAL` es constante de backend
- [ ] Validador NO requiere sección `costos_operativos`

### 6.2 Arquitectónico

- [ ] Cero duplicación de fuentes de verdad
- [ ] Cero valores hardcoded en parametrización
- [ ] Cero cálculos derivados persistidos en storage
- [ ] Separación estricta: `INPUT | PARAMETRIZATION | DERIVED | CONSTANT`
- [ ] Trazabilidad completa (cada valor auditable hasta origen)
- [ ] Logs estructurados de cada cálculo derivado

### 6.3 Tests

- [ ] 100% tests de certificación pasan (L1, L2, L3)
- [ ] 100% tests unitarios pasan
- [ ] Nuevos tests para `_calcular_opex_ti_total()`, `_calcular_capex_recurrente()`, `_calcular_capex_inicial()`
- [ ] Tests de integración actualizados (fixtures sin `costos_operativos`)

### 6.4 Documentación

- [ ] Este documento completo y actualizado
- [ ] Comentarios en código explican decisiones arquitectónicas
- [ ] Docstrings completos en métodos nuevos (formato Google Style)

---

## 7. RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|-----------|
| Usuario NO envía `tarifa_diaria_capacitacion` en payload | MEDIA | ALTO | Agregar validación early en `UserInputLoader` con error explícito |
| Cálculo dinámico OPEX/CAPEX no coincide con Excel V2-6 | BAJA | ALTO | Tests exhaustivos comparando con valores conocidos (certificación) |
| OP-Componente no tiene IPC del año solicitado | MEDIA | MEDIO | Manejar `ParametrizationError` con mensaje claro (agregar año a OP) |
| Regresión en tests existentes por cambios en fixtures | ALTA | MEDIO | Actualizar fixtures antes de merge, ejecutar suite completa |
| Performance: cálculos en cada simulación | BAJA | BAJO | Métodos son O(n) lineales, cacheable si necesario |

---

## 8. ROLLBACK PLAN

Si el refactor causa regresiones críticas bloqueantes:

1. **Revertir commit:**
   ```bash
   git revert <commit_hash_refactor>
   ```

2. **Restaurar `HR-costos_operativos` temporal** (emergency fallback):
   ```json
   {
     "costos_operativos": [
       {"clave": "tarifa_dia_cap", "valor": 20000.0},
       {"clave": "opex_ti_por_estacion", "valor": 180400.0},
       {"clave": "capex_recurrente_por_estacion", "valor": 58471.0},
       {"clave": "capex_inicial_por_estacion", "valor": 3628212.0},
       {"clave": "pct_aumento_tecnologico_anual", "valor": 0.0527},
       {"clave": "mes_inicio_ajuste_anual", "valor": 1}
     ]
   }
   ```

3. **Ejecutar tests de regresión**
4. **Post-mortem:** Identificar causa raíz del fallo
5. **Re-planificar refactor** con nuevas restricciones descubiertas

---

## 9. TIMELINE ESTIMADO

| Fase | Duración | Responsable | Dependencias |
|------|----------|-------------|--------------|
| FASE 1: Preparación | 30 min | Backend Dev | - |
| FASE 2: Cálculos Derivados | 2 horas | Backend Dev | FASE 1 |
| FASE 3: Parametrización IPC | 1 hora | Backend Dev | - |
| FASE 4: Adapters | 30 min | Backend Dev | FASE 1 |
| FASE 5: Constantes | 15 min | Backend Dev | FASE 1 |
| FASE 6: Eliminaciones | 30 min | Backend Dev | FASE 2-5 |
| FASE 7: Tests | 1.5 horas | QA + Backend | FASE 2-6 |
| **TOTAL** | **6 horas** | | |

---

## 10. CONCLUSIÓN

Este refactor **elimina la ambigüedad de fuentes de datos** del módulo `costos_operativos` y establece una arquitectura determinística basada en:

✅ **Single Source of Truth** — cada campo tiene exactamente una fuente  
✅ **Separación de Capas** — INPUT ≠ PARAMETRIZACIÓN ≠ CALCULADO ≠ CONSTANTE  
✅ **Trazabilidad Completa** — cada valor auditable hasta su origen  
✅ **Cero Hardcodes Ocultos** — sin valores "mágicos" en parametrización  
✅ **Validación Early** — errores detectados inmediatamente en input  
✅ **Mantenibilidad** — cambios en inversiones[] reflejados automáticamente

**Resultado Final:** Motor financiero 100% auditable, mantenible y determinístico.

---

**APROBACIÓN REQUERIDA**

- [ ] Arquitecto Backend NEXA  
- [ ] Lead Developer  
- [ ] QA Lead

**Firma:**  
```
Aprobado por: _______________________
Fecha: _______________________
```

---

**FIN DEL DOCUMENTO**
