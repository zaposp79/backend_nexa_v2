# REFACTORIZACIÓN ARQUITECTÓNICA: costos_operativos

## Documento de Diseño Técnico

**Autor:** Arquitectura Backend NEXA  
**Fecha:** 2026-05-27  
**Estado:** DRAFT - Pendiente aprobación  
**Impacto:** ALTO - Cambio arquitectónico completo de fuentes de datos

---

## 1. PROBLEMA ARQUITECTÓNICO ACTUAL

### 1.1 Estado Actual

El sistema actual tiene **confusión de fuentes de verdad**:

```
USER INPUT (datos_operativos) ──┐
                                 ├──→ ??? ──→ Motor
HR PARAMETRIZATION (storage)  ──┤
                                 │
Excel V2-6 (Simulador)         ──┤
                                 │
Excel OP/HR/GN (Parametrización)─┘
```

**Problemas críticos detectados:**

1. **Duplicación de fuentes**: `tarifa_dia_cap` existe en:
   - `datos_operativos.tarifa_diaria_capacitacion` (payload usuario)
   - Excel V2-6 Panel de Control C16 (simulador)
   - Excel HR (parametrización - NO EXISTE)
   - `HR-costos_operativos` storage (parametrización - FALTA)

2. **Campos fantasma**: `opex_ti_por_estacion` NO existe como concepto funcional único:
   - En realidad es una **suma dinámica** de múltiples OPEX (Internet, Licencias, Soporte)
   - Hardcodearlo viola el principio de single source of truth

3. **Valores calculados persistidos**: `capex_recurrente_por_estacion` = PC / 60 meses
   - El cálculo debería vivir en backend, no persistirse

4. **Constantes disfrazadas de parametrización**: `mes_inicio_ajuste_anual = 1`
   - Es una constante fiscal, no un parámetro variable

### 1.2 Impacto

- ❌ Imposibilidad de validar completitud de parametrización
- ❌ 6 tests fallan por `costos_operativos` faltante
- ❌ Motor bloqueado hasta que se resuelva
- ❌ Ambigüedad sobre qué campo proveer y dónde

---

## 2. CLASIFICACIÓN POR NATURALEZA FUNCIONAL

### 2.1 Nuevo Mapa de Ownership

| Campo | Naturaleza | Fuente Correcta | Tipo | Justificación |
|-------|------------|-----------------|------|---------------|
| `tarifa_dia_cap` | **INPUT** | `datos_operativos.tarifa_diaria_capacitacion` | `user_input` | El usuario define cuánto cuesta 1 día de capacitación para su deal específico |
| `opex_ti_por_estacion` | **CALCULADO** | Backend suma `opex_fijo.items[]` | `derived` | No es un concepto atómico — debe derivarse de componentes OPEX |
| `capex_recurrente_por_estacion` | **CALCULADO** | Backend: `PC.precio / PC.meses_amortizacion` | `derived` | Es una fórmula de amortización, no un valor fijo |
| `capex_inicial_por_estacion` | **CALCULADO** | Backend suma `inversiones[]` | `derived` | Es la suma de hardware/software inicial por estación |
| `pct_aumento_tecnologico_anual` | **PARAMETRIZACIÓN** | Excel OP-Componente → IPC del año correspondiente | `parametrization` | Inflación tecnológica viene de parámetros macroeconómicos |
| `mes_inicio_ajuste_anual` | **CONSTANTE** | Backend: `MES_INICIO_AJUSTE_ANUAL = 1` | `constant` | Estándar fiscal (enero) — no varía por deal ni parametrización |

---

## 3. REGLAS DE REFACTORIZACIÓN

### Regla 1: tarifa_dia_cap ← INPUT del usuario

**ANTES:**
```python
# context_builder.py:649
tarifa_dia_cap = self._prov.get_costo_operativo("tarifa_dia_cap")  # ❌ Desde storage
```

**DESPUÉS:**
```python
# context_builder.py
tarifa_dia_cap = panel.tarifa_diaria_capacitacion  # ✅ Desde panel_de_control
```

**Cambios requeridos:**

1. **`adapters/user_input_loader.py`** — Mapeo explícito:
   ```python
   panel_de_control = {
       # ... campos existentes ...
       "tarifa_diaria_capacitacion": UserInputLoader._requerir_float(
           ops, "tarifa_diaria_capacitacion", "datos_operativos"
       ),
   }
   ```

2. **`domain/models/panel.py`** — Agregar campo:
   ```python
   @dataclass
   class PanelDeControl:
       # ... campos existentes ...
       tarifa_diaria_capacitacion: float
   ```

3. **`input/context_builder.py:649`** — Cambiar fuente:
   ```python
   tarifa_dia_cap = panel.tarifa_diaria_capacitacion
   ```

4. **`validators/parametrization_completeness_validator.py`** — Eliminar de REQUIRED_COSTOS_OPERATIVOS:
   ```python
   REQUIRED_COSTOS_OPERATIVOS = [
       # "tarifa_dia_cap",  ← ELIMINAR (ahora viene del input)
       "pct_aumento_tecnologico_anual",
       "mes_inicio_ajuste_anual",
   ]
   ```

**Validación:**
- ✅ `datos_operativos.tarifa_diaria_capacitacion` es REQUERIDO (no opcional)
- ✅ Motor falla early si falta
- ✅ Sin fallback a parametrización

---

### Regla 2: opex_ti_por_estacion ← CALCULADO dinámicamente

**PROBLEMA ACTUAL:**  
El motor espera `opex_ti_por_estacion` como un solo valor, pero en realidad representa **la suma de múltiples OPEX TI** (Internet, Licencias CX1, Soporte, etc.)

**ANTES:**
```python
# context_builder.py:669
opex_ti_por_estacion = self._prov.get_costo_operativo("opex_ti_por_estacion")  # ❌ Valor único
```

**DESPUÉS:**
```python
# context_builder.py
opex_ti_por_estacion = self._calcular_opex_ti_total(perfiles_a)  # ✅ Calculado desde opex_fijo
```

**Cambios requeridos:**

1. **`input/context_builder.py`** — Nuevo método:
   ```python
   def _calcular_opex_ti_total(self, perfiles: List[PerfilCadenaAInput]) -> float:
       """
       Calcula el OPEX TI total por estación desde los items OPEX configurados.
       
       Suma todos los items de opex_fijo.items[] que sean:
       - Tipo tecnológico (Internet, Licencias, Plataformas, Soporte)
       - Costo NO totalizado (costo_totalizado=false → dividir entre cantidad)
       
       Returns:
           OPEX TI promedio ponderado por estación
       """
       total_opex_ti = 0.0
       total_estaciones = 0.0
       
       for perfil in perfiles:
           if not perfil.opex_fijo or not perfil.opex_fijo.items:
               continue
           
           estaciones_perfil = perfil.estaciones_presenciales
           if estaciones_perfil <= 0:
               continue
           
           total_estaciones += estaciones_perfil
           
           for item in perfil.opex_fijo.items:
               if item.costo_totalizado:
                   # Costo ya totalizado → dividir entre estaciones del perfil
                   total_opex_ti += item.costo / estaciones_perfil
               else:
                   # Costo unitario → usar directamente
                   total_opex_ti += item.costo
       
       return total_opex_ti / total_estaciones if total_estaciones > 0 else 0.0
   ```

2. **`input/context_builder.py:669`** — Reemplazar:
   ```python
   opex_ti_por_estacion = self._calcular_opex_ti_total(perfiles_a)
   ```

3. **Eliminar de parametrización:**
   - `opex_ti_por_estacion` NO debe existir en `HR-costos_operativos`
   - Eliminar de `REQUIRED_COSTOS_OPERATIVOS`

**Validación:**
- ✅ Si `opex_fijo.items` está vacío → opex_ti = 0.0 (válido)
- ✅ Trazabilidad: cada item OPEX es auditable
- ✅ Sin hardcodes ocultos

---

### Regla 3: pct_aumento_tecnologico_anual ← PARAMETRIZACIÓN

**ANTES:**
```python
# context_builder.py:859
pct_aumento_tecnologico = self._prov.get_costo_operativo("pct_aumento_tecnologico_anual")  # ❌ Storage
```

**DESPUÉS:**
```python
# context_builder.py:859
año_contrato = extraer_año(panel.fecha_inicio)
pct_aumento_tecnologico = self._prov.get_componente_indexacion("IPC", año_contrato)  # ✅ Excel OP
```

**Cambios requeridos:**

1. **`repositories/infrastructure_parametrization_repository.py`** — Nuevo método:
   ```python
   def get_componente_indexacion(self, componente: str, año: int) -> float:
       """
       Obtiene la tasa de un componente de indexación para un año específico.
       
       Args:
           componente: "IPC", "SMLV", "IPC+1", etc.
           año: Año fiscal (2025, 2026, ...)
       
       Returns:
           Tasa de indexación (e.g., 0.0527 para IPC 2026)
       
       Fuente: OP-Componente
       
       Raises:
           ParametrizationError: si no existe el componente/año
       """
       self._ensure_op_loaded()
       tabla = self._op_data.get("componente", [])
       
       for row in tabla:
           if row.get("componente") == componente and row.get("año") == año:
               return float(row.get("valor", 0.0))
       
       raise ParametrizationError(
           f"Componente indexación '{componente}' año {año} not found in OP-Componente",
           module="op"
       )
   ```

2. **`repositories/parametrization_provider.py`** — Facade:
   ```python
   def get_componente_indexacion(self, componente: str, año: int) -> float:
       """Obtiene componente de indexación desde OP-Componente."""
       return self._infrastructure.get_componente_indexacion(componente, año)
   ```

3. **`input/context_builder.py`** — Usar nuevo método:
   ```python
   from datetime import datetime
   
   def _construir_cadena_c(self, cadena_c, panel):
       año_inicio = datetime.strptime(panel.fecha_inicio, "%Y-%m-%d").year
       pct_aumento_tecnologico = self._prov.get_componente_indexacion("IPC", año_inicio)
       
       return ParametrosCadenaC(
           # ...
           pct_aumento_tecnologico = pct_aumento_tecnologico,
           # ...
       )
   ```

**Validación:**
- ✅ Fuente única: Excel OP-Componente
- ✅ Actualización anual de IPC → parametrización OP
- ✅ Sin duplicación de valores

---

### Regla 4: capex_recurrente_por_estacion ← CALCULADO

**PROBLEMA ACTUAL:**  
`capex_recurrente_por_estacion = 58,471` es el resultado de `PC(3,508,260) / 60 meses`.  
Persistir el resultado viola el principio de derivación dinámica.

**ANTES:**
```python
# context_builder.py:670
capex_por_estacion = self._prov.get_costo_operativo("capex_recurrente_por_estacion")  # ❌ Valor fijo
```

**DESPUÉS:**
```python
# context_builder.py:670
capex_por_estacion = self._calcular_capex_recurrente(perfiles_a)  # ✅ Calculado desde inversiones
```

**Cambios requeridos:**

1. **`input/context_builder.py`** — Nuevo método:
   ```python
   def _calcular_capex_recurrente(self, perfiles: List[PerfilCadenaAInput]) -> float:
       """
       Calcula el CAPEX recurrente mensual por estación desde inversiones configuradas.
       
       Para cada perfil, suma:
           inversiones[] donde es_precio_total=false → precio_mensual * cantidad / estaciones
           inversiones[] donde es_precio_total=true  → precio_mensual / estaciones
       
       Returns:
           CAPEX recurrente promedio ponderado por estación
       """
       total_capex = 0.0
       total_estaciones = 0.0
       
       for perfil in perfiles:
           if not perfil.inversiones:
               continue
           
           estaciones_perfil = perfil.estaciones_presenciales
           if estaciones_perfil <= 0:
               continue
           
           total_estaciones += estaciones_perfil
           
           for inversion in perfil.inversiones:
               # Calcular precio mensual si no está ya calculado
               precio_mensual = (
                   inversion.precio_mensual
                   if inversion.precio_mensual > 0
                   else inversion.precio / inversion.meses_a_diferir
               )
               
               if inversion.es_precio_total:
                   # Total para todas las estaciones → dividir
                   total_capex += precio_mensual / estaciones_perfil
               else:
                   # Precio unitario × cantidad
                   total_capex += precio_mensual * inversion.cantidad / estaciones_perfil
       
       return total_capex / total_estaciones if total_estaciones > 0 else 0.0
   ```

2. **`input/context_builder.py:670`** — Reemplazar:
   ```python
   capex_por_estacion = self._calcular_capex_recurrente(perfiles_a)
   ```

3. **Eliminar de parametrización:**
   - `capex_recurrente_por_estacion` NO debe existir en `HR-costos_operativos`

**Validación:**
- ✅ Cambios en `inversiones[]` → reflejo inmediato en cálculo
- ✅ Sin mantener dos fuentes (parametrización + input)
- ✅ Trazabilidad total del origen

---

### Regla 5: capex_inicial_por_estacion ← CALCULADO

**ANTES:**
```python
# context_builder.py:678
capex_inicial_por_estacion = self._prov.get_costo_operativo("capex_inicial_por_estacion")  # ❌ Valor fijo
```

**DESPUÉS:**
```python
# context_builder.py:678
capex_inicial_por_estacion = self._calcular_capex_inicial(perfiles_a)  # ✅ Calculado desde inversiones
```

**Cambios requeridos:**

1. **`input/context_builder.py`** — Nuevo método:
   ```python
   def _calcular_capex_inicial(self, perfiles: List[PerfilCadenaAInput]) -> float:
       """
       Calcula el CAPEX inicial total por estación desde inversiones.
       
       Suma el precio total (sin amortizar) de todas las inversiones.
       
       Returns:
           CAPEX inicial promedio ponderado por estación
       """
       total_capex_inicial = 0.0
       total_estaciones = 0.0
       
       for perfil in perfiles:
           if not perfil.inversiones:
               continue
           
           estaciones_perfil = perfil.estaciones_presenciales
           if estaciones_perfil <= 0:
               continue
           
           total_estaciones += estaciones_perfil
           
           for inversion in perfil.inversiones:
               if inversion.es_precio_total:
                   total_capex_inicial += inversion.precio / estaciones_perfil
               else:
                   total_capex_inicial += inversion.precio * inversion.cantidad / estaciones_perfil
       
       return total_capex_inicial / total_estaciones if total_estaciones > 0 else 0.0
   ```

2. **`input/context_builder.py:678`** — Reemplazar:
   ```python
   capex_inicial_por_estacion = self._calcular_capex_inicial(perfiles_a)
   ```

3. **Eliminar de parametrización:**
   - `capex_inicial_por_estacion` NO debe existir en `HR-costos_operativos`

**Validación:**
- ✅ CAPEX inicial es la suma completa de `inversiones[].precio`
- ✅ CAPEX recurrente es la amortización mensual
- ✅ No duplicar definiciones

---

### Regla 6: mes_inicio_ajuste_anual ← CONSTANTE BACKEND

**ANTES:**
```python
# context_builder.py:287,424,644,792,860 (5 lugares)
mes_ajuste = int(self._prov.get_costo_operativo("mes_inicio_ajuste_anual"))  # ❌ Desde storage
```

**DESPUÉS:**
```python
# domain/constants.py (NUEVO ARCHIVO)
MES_INICIO_AJUSTE_ANUAL = 1  # Enero (estándar fiscal Colombia)
```

```python
# context_builder.py
from nexa_engine.domain.constants import MES_INICIO_AJUSTE_ANUAL

# ... en todos los lugares:
mes_ajuste = MES_INICIO_AJUSTE_ANUAL  # ✅ Constante
```

**Cambios requeridos:**

1. **`domain/constants.py`** — CREAR archivo:
   ```python
   """
   Constantes del motor financiero NEXA.
   
   Valores que NO varían por deal, parametrización ni cliente.
   """
   
   # Mes en que aplica el ajuste anual (indexación salarial/tecnológica)
   # Valor: 1 = enero (estándar fiscal Colombia)
   MES_INICIO_AJUSTE_ANUAL = 1
   
   # Otros valores constantes del motor
   DIAS_LABORALES_POR_MES = 20
   HORAS_LABORALES_POR_DIA = 8
   ```

2. **`input/context_builder.py`** — Reemplazar en 5 ubicaciones:
   ```python
   from nexa_engine.domain.constants import MES_INICIO_AJUSTE_ANUAL
   
   # Línea 287
   mes_aplicacion = (
       panel.indexacion_mes_aplicacion
       if panel.indexacion_mes_aplicacion is not None
       else MES_INICIO_AJUSTE_ANUAL
   )
   
   # Línea 424
   mes_ajuste = MES_INICIO_AJUSTE_ANUAL
   
   # Línea 644, 792, 860 (similar)
   ```

3. **Eliminar de parametrización:**
   - `mes_inicio_ajuste_anual` NO debe existir en `HR-costos_operativos`
   - Eliminar de `REQUIRED_COSTOS_OPERATIVOS`

**Validación:**
- ✅ Es una constante fiscal (enero = mes 1)
- ✅ NO varía por cliente, deal ni parametrización
- ✅ Si el usuario quiere override → `panel.indexacion_mes_aplicacion`

---

## 4. ELIMINACIÓN COMPLETA DE `HR-costos_operativos`

**Resultado final:**  
La sección `HR-costos_operativos` debe **ELIMINARSE POR COMPLETO** del sistema.

**Justificación:**  
Después de aplicar las 6 reglas, ningún campo requiere storage en `HR-costos_operativos`:

- ✅ `tarifa_dia_cap` → viene del input
- ✅ `opex_ti_por_estacion` → calculado desde opex_fijo
- ✅ `capex_recurrente_por_estacion` → calculado desde inversiones
- ✅ `capex_inicial_por_estacion` → calculado desde inversiones
- ✅ `pct_aumento_tecnologico_anual` → viene de OP-Componente
- ✅ `mes_inicio_ajuste_anual` → constante backend

**Cambios requeridos:**

1. **`repositories/payroll_parametrization_repository.py`** — ELIMINAR método completo:
   ```python
   # ELIMINAR: get_costo_operativo() (líneas 287-325)
   ```

2. **`repositories/parametrization_provider.py`** — ELIMINAR facade:
   ```python
   # ELIMINAR: get_costo_operativo() wrapper
   ```

3. **`validators/parametrization_completeness_validator.py`** — ELIMINAR sección:
   ```python
   REQUIRED_PARAMETRIZATION_SECTIONS = [
       # "costos_operativos",  ← ELIMINAR COMPLETO
       "nomina",
       "seg_social",
       "prestaciones",
       "recargos",
       "costo_fijo",
       "ratios",
       "reglas_staff",
       "salarios",
   ]
   
   # ELIMINAR COMPLETO:
   # REQUIRED_COSTOS_OPERATIVOS = [...]
   ```

4. **Tests** — Actualizar fixtures:
   - Eliminar referencias a `costo_operativo` en tests
   - Actualizar fixtures de parametrización para NO incluir `costos_operativos`

---

## 5. ARCHIVOS A MODIFICAR

### 5.1 Capa de Dominio

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `domain/constants.py` | **CREAR** — definir `MES_INICIO_AJUSTE_ANUAL = 1` | Constantes backend centralizadas |
| `domain/models/panel.py` | **MODIFICAR** — agregar `tarifa_diaria_capacitacion: float` | Campo del input usuario |
| `domain/user_inputs.py` | **MODIFICAR** — agregar `tarifa_diaria_capacitacion: float` | DTO de entrada |

### 5.2 Capa de Adaptadores

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `adapters/user_input_loader.py` | **MODIFICAR** — mapear `tarifa_diaria_capacitacion` | Normalización input |
| `adapters/json_loader.py` | **MODIFICAR** — leer `tarifa_diaria_capacitacion` | Legacy loader |

### 5.3 Capa de Input (Context Builder)

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `input/context_builder.py` | **MODIFICAR EXTENSIVO** — 6 cambios principales:<br/>1. Línea 287, 424, 644, 792, 860: `MES_INICIO_AJUSTE_ANUAL`<br/>2. Línea 649: `panel.tarifa_diaria_capacitacion`<br/>3. Línea 669: `_calcular_opex_ti_total()`<br/>4. Línea 670: `_calcular_capex_recurrente()`<br/>5. Línea 678: `_calcular_capex_inicial()`<br/>6. Línea 859: `get_componente_indexacion("IPC", año)` | Single source of truth por campo |

### 5.4 Capa de Repositorios

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `repositories/payroll_parametrization_repository.py` | **ELIMINAR** — método `get_costo_operativo()` completo | Ya no se necesita |
| `repositories/parametrization_provider.py` | **ELIMINAR** — facade `get_costo_operativo()` | Ya no se necesita |
| `repositories/infrastructure_parametrization_repository.py` | **AGREGAR** — método `get_componente_indexacion(componente, año)` | IPC desde OP-Componente |

### 5.5 Validadores

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `validators/parametrization_completeness_validator.py` | **MODIFICAR** — eliminar `costos_operativos` de secciones requeridas | Sección ya no existe |

### 5.6 Tests

| Archivo | Cambios | Justificación |
|---------|---------|---------------|
| `tests/unit/test_context_builder.py` | **MODIFICAR** — fixtures sin `costos_operativos` | Reflejar nueva arquitectura |
| `tests/integration/test_parametrization_*.py` | **MODIFICAR** — eliminar aserciones de `costos_operativos` | Sección eliminada |

---

## 6. FLUJO FINAL ESPERADO

```
╔════════════════════════════════════════════════════════════════╗
║                        USER INPUT                               ║
╚════════════════════════════════════════════════════════════════╝
                            │
                            │ datos_operativos.tarifa_diaria_capacitacion
                            │ condiciones_cadena_a[].opex_fijo.items[]
                            │ condiciones_cadena_a[].inversiones[]
                            │ volumetria.indexacion.mes_aplicacion (opt)
                            ▼
╔════════════════════════════════════════════════════════════════╗
║                  NORMALIZATION LAYER                            ║
║             (UserInputLoader / InputNormalizer)                 ║
╚════════════════════════════════════════════════════════════════╝
                            │
                            │ panel.tarifa_diaria_capacitacion
                            │ perfiles[].opex_fijo
                            │ perfiles[].inversiones
                            ▼
╔════════════════════════════════════════════════════════════════╗
║                PARAMETRIZATION RESOLVER                         ║
║                  (ParametrizationProvider)                      ║
╚════════════════════════════════════════════════════════════════╝
                            │
                            │ get_componente_indexacion("IPC", 2026)
                            │ get_costo_no_payroll(sede)
                            │ get_examen_medico(ciudad)
                            ▼
╔════════════════════════════════════════════════════════════════╗
║                  DERIVED CALCULATIONS                           ║
║                    (SimulationContextBuilder)                   ║
╚════════════════════════════════════════════════════════════════╝
                            │
                            │ tarifa_dia_cap = panel.tarifa_diaria_capacitacion
                            │ opex_ti = _calcular_opex_ti_total(perfiles)
                            │ capex_rec = _calcular_capex_recurrente(perfiles)
                            │ capex_ini = _calcular_capex_inicial(perfiles)
                            │ pct_aum = get_componente_indexacion("IPC", año)
                            │ mes_ini = MES_INICIO_AJUSTE_ANUAL (constante)
                            ▼
╔════════════════════════════════════════════════════════════════╗
║                    FINANCIAL ENGINE                             ║
║    (NominaCalculator / NoPayrollCalculator / CadenaCCalculator) ║
╚════════════════════════════════════════════════════════════════╝
                            │
                            │ _cap_inicial(), _cap_rotacion()
                            │ _costo_opex_ti(), _costo_capex()
                            │ _factor_ajuste_tecnologico()
                            ▼
╔════════════════════════════════════════════════════════════════╗
║                         VISIONES                                ║
║      (Vision Imprimible / Vision P&G / Vision Tarifas / CTS)    ║
╚════════════════════════════════════════════════════════════════╝
```

**Ventajas del nuevo flujo:**

1. ✅ **Single Source of Truth** — cada campo tiene exactamente una fuente
2. ✅ **Trazabilidad Completa** — cada valor es auditable hasta su origen
3. ✅ **Cero Hardcodes** — sin valores "mágicos" ocultos en parametrización
4. ✅ **Separación de Capas** — INPUT ≠ PARAMETRIZACIÓN ≠ CALCULADO ≠ CONSTANTE
5. ✅ **Validación Early** — si falta `tarifa_diaria_capacitacion` → error inmediato
6. ✅ **Mantenibilidad** — cambio en inversiones[] → reflejo automático en CAPEX

---

## 7. PLAN DE IMPLEMENTACIÓN

### Fase 1: Preparación (30 min)
- [ ] Crear `domain/constants.py`
- [ ] Agregar `tarifa_diaria_capacitacion` a DTOs (`PanelDeControl`, `PanelDeControlRequest`)
- [ ] Crear tests unitarios para métodos nuevos (`_calcular_opex_ti_total`, `_calcular_capex_recurrente`, `_calcular_capex_inicial`)

### Fase 2: Refactor Context Builder (2 horas)
- [ ] Implementar `_calcular_opex_ti_total()`
- [ ] Implementar `_calcular_capex_recurrente()`
- [ ] Implementar `_calcular_capex_inicial()`
- [ ] Reemplazar `get_costo_operativo()` por nuevas fuentes en 6 ubicaciones
- [ ] Ejecutar tests de integración

### Fase 3: Refactor Repositories (1 hora)
- [ ] Implementar `InfrastructureParametrizationRepository.get_componente_indexacion()`
- [ ] Eliminar `PayrollParametrizationRepository.get_costo_operativo()`
- [ ] Eliminar facade en `ParametrizationProvider`
- [ ] Actualizar tests de repositories

### Fase 4: Adapters (30 min)
- [ ] Mapear `tarifa_diaria_capacitacion` en `UserInputLoader`
- [ ] Agregar validación de campo requerido
- [ ] Actualizar `json_loader.py` (legacy)

### Fase 5: Validadores (15 min)
- [ ] Eliminar `costos_operativos` de `ParametrizationCompletenessValidator`
- [ ] Eliminar `REQUIRED_COSTOS_OPERATIVOS`

### Fase 6: Tests (1 hora)
- [ ] Actualizar fixtures (eliminar `costos_operativos`)
- [ ] Ejecutar suite completa de tests
- [ ] Verificar 0 regresiones

### Fase 7: Certificación (30 min)
- [ ] Ejecutar tests de certificación (L1, L2, L3)
- [ ] Validar con payload real del usuario
- [ ] Confirmar 0 dependencias de `costos_operativos`

**Total estimado:** 5.5 horas

---

## 8. CRITERIOS DE ACEPTACIÓN

### 8.1 Funcional
- [ ] Motor ejecuta simulación completa sin errores
- [ ] `tarifa_dia_cap` proviene exclusivamente de `datos_operativos.tarifa_diaria_capacitacion`
- [ ] OPEX TI calculado dinámicamente desde `opex_fijo.items[]`
- [ ] CAPEX calculado dinámicamente desde `inversiones[]`
- [ ] IPC obtenido desde `OP-Componente` (no hardcoded)
- [ ] `MES_INICIO_AJUSTE_ANUAL` es constante de backend
- [ ] Validador NO requiere `costos_operativos`

### 8.2 Arquitectónico
- [ ] Cero duplicación de fuentes de verdad
- [ ] Cero valores hardcoded en parametrización
- [ ] Cero cálculos derivados persistidos
- [ ] Separación estricta: INPUT | PARAMETRIZACIÓN | CALCULADO | CONSTANTE
- [ ] Trazabilidad completa (cada valor auditable hasta origen)

### 8.3 Tests
- [ ] 100% tests de certificación pasan (L1, L2, L3)
- [ ] 100% tests unitarios pasan
- [ ] 100% tests de integración pasan
- [ ] Nuevos tests para métodos calculados (`_calcular_opex_ti_total`, etc.)

### 8.4 Documentación
- [ ] Este documento actualizado con cambios finales
- [ ] Comentarios en código explican decisiones arquitectónicas
- [ ] README actualizado si necesario

---

## 9. RIESGOS Y MITIGACIONES

| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Tests fallan por cambios en fixtures | ALTO | Actualizar fixtures en Fase 6, ejecutar suite completa |
| Usuario ya envía `tarifa_diaria_capacitacion` pero motor no lo consume | MEDIO | Agregar validación early, error claro si falta |
| Cálculo dinámico de OPEX/CAPEX no coincide con valores previos | ALTO | Tests unitarios exhaustivos, comparar con valores Excel V2-6 |
| OP-Componente no tiene IPC del año solicitado | MEDIO | Manejar error explícito, sugerir agregar año a parametrización OP |
| Performance: cálculos dinámicos ralentizan motor | BAJO | Métodos son O(n) lineales, cacheable si necesario |

---

## 10. ROLLBACK PLAN

Si el refactor causa regresiones críticas:

1. Revertir commit completo del refactor
2. Restaurar `HR-costos_operativos` temporal con valores de Excel V2-6:
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
3. Ejecutar tests para confirmar estado previo
4. Análisis post-mortem del fallo
5. Re-planificar refactor con nuevas restricciones

---

## 11. APROBACIÓN REQUERIDA

**Antes de proceder con la implementación, este documento requiere aprobación de:**

- [ ] Product Owner / Arquitecto Backend
- [ ] Lead Developer
- [ ] QA Lead (para plan de tests)

**Firma de aprobación:**

```
Aprobado por: _______________________
Fecha: _______________________
```

---

## 12. CONCLUSIÓN

Este refactor elimina **ambigüedad de fuentes de datos** y establece una arquitectura determinística con:

- ✅ Single source of truth por campo
- ✅ Separación estricta de capas
- ✅ Trazabilidad financiera completa
- ✅ Cero hardcodes ocultos
- ✅ Validación early de datos requeridos

**Resultado final:** Motor financiero 100% auditable, mantenible y determinístico.

---

**FIN DEL DOCUMENTO**
