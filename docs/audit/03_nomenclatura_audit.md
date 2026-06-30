# Auditoría de Consistencia Nomenclatural

**Versión**: 2026-05-21  
**Estado**: Auditoría Fase 3  
**Objetivo**: Identificar y eliminar aliases innecesarios, alinear nombres con Excel y entry_data, estandarizar suffixes.

---

## 1. Resumen Ejecutivo

### Hallazgos Principales

| # | Inconsistencia | Severidad | Ubicaciones Afectadas | Acción |
|---|---|---|---|---|
| 1 | **canal vs producto** (aliasing) | CRÍTICA | entry_data vs endpoints | Usar "canal" siempre |
| 2 | **seguridad vs estudios_seguridad** (aliasing) | CRÍTICA | domain vs endpoints | Usar "estudios_seguridad" |
| 3 | **nomina_loaded_ch sin modelo** | CRÍTICA | vision_tarifas.py sin ResultadoNomina | Agregar a domain |
| 4 | **Campos perdidos de entry_data** | ALTA | context_builder, domain | Guardar o rechazar explícitamente |
| 5 | **Suffixes inconsistentes** (_ch, _total, _mensual) | MEDIA | Endpoints, responses | Estandarizar |
| 6 | **Campos opcionalmente usados** | MEDIA | pct_presencia, vol_cadena_a | Definir regla de uso |

### Impacto

- **Ambigüedad semántica**: "producto" significa diferentes cosas en Cadena B vs responses
- **Pérdida de capacidad**: Campos de entrada (rubro, tipo_de_gasto) se descartan sin opción de recuperación
- **Desacoplamiento**: nomina_loaded_ch se calcula en vision_tarifas sin existir en modelo base
- **Confusión de desarrolladores**: Alias innecesarios hacen código más difícil de entender

---

## 2. Matriz Completa de Nombres

### 2.1 Concepto: Identificador de Perfil/Canal

| Layer | Campo | Valor Típico | Tipo | Documented | Status |
|-------|-------|---|---|---|---|
| **Excel** | Perfil | "Especialista Cobranza" | string | ✓ Sheet "Condiciones CA" Col A | ✓ |
| **entry_data** | `condiciones_cadena_a.perfiles[].nombre` | "Especialista Cobranza" | string | ✓ Contract | ✓ |
| **Domain** | `PerfilCadenaA.nombre` | "Especialista Cobranza" | string | ✓ | ✓ |
| **Calculadora** | — | (no se usa en cálculo) | — | — | ✓ |
| **Endpoint** | `vision_tarifas.canales[].nombre_canal` | "Especialista Cobranza" | string | ✓ | ✓ |

**Conclusión**: ✓ Consistente. Todas las capas usan "nombre".

---

### 2.2 Concepto: Subcanal / Medio de Contacto

| Layer | Campo | Valor Típico | Tipo | Problema |
|-------|-------|---|---|---|
| **Excel** | Canal | "WhatsApp", "Email", "Correo" | enum | — |
| **entry_data** | `condiciones_cadena_a.perfiles[].canal` | "WhatsApp" | enum | — |
| **Domain** | `PerfilCadenaA.canal` | "WhatsApp" | enum | — |
| **Calculadora** | — | (no se usa) | — | — |
| **Endpoint** | **`vision_tarifas.canales[].producto`** | "WhatsApp" | enum | ⚠️ **Alias innecesario** |

**Problema**: "producto" es ambiguo (en Cadena B, "producto" = "Zendesk", "Token IA", etc.)

**Decisión**: ✓ Usar **"canal"** siempre. Cambiar endpoint.

**Impacto**: 1 cambio en endpoint, 1 cambio en serializer.

---

### 2.3 Concepto: Nómina (Total Mensual por Agente)

| Layer | Campo | Fórmula/Valor | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Payroll | salario + comisiones + capacitación + exámenes | float | ✓ |
| **entry_data** | (derivado de role) | — | — | (no existe) |
| **Domain** | `ResultadoNomina.salario_fijo + comisiones + cap_inicial + seguridad` | sum | float | ✓ |
| **Domain** | `ResultadoNomina.total` (property) | sum de campos | float | ✓ |
| **Endpoint** | `vision_tarifas.canales[].payroll_ch` | monthly per agent | float | ✓ |

**Conclusión**: ✓ Consistente en nombre "payroll" / "total".

---

### 2.4 Concepto: Nómina Cargada (Nómina × Factor de Carga)

| Layer | Campo | Fórmula | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Nomina Cargada | payroll × (1 + aportes + prestaciones) | float | ✓ Sheet "Nómina" Col G |
| **entry_data** | — | (derivada de salario_base) | — | (no existe) |
| **Domain** | **`ResultadoNomina` — NO EXISTE CAMPO** | — | — | ⚠️ **FALTA** |
| **Calculadora** | — | NominaCargadaService.calcular() | — | ✓ (está en service, no model) |
| **Endpoint** | `vision_tarifas.canales[].nomina_loaded_ch` | monthly per agent | float | ⚠️ **Calculada ad-hoc en vision_tarifas** |

**Problema**:
1. Concepto existe y es importante (Excel, endpoint)
2. No tiene modelo en domain
3. Se calcula en vision_tarifas sin referencia a un campo base
4. Dificulta auditoria (¿de dónde viene nomina_loaded_ch?)

**Solución**: Agregar `nomina_loaded: float` a `ResultadoNomina`:
```python
@dataclass
class ResultadoNomina:
    salario_fijo: float
    comisiones: float
    cap_inicial: float
    seguridad: float
    nomina_loaded: float  # ← NUEVO: salario_fijo × factor_carga
    
    @property
    def total(self) -> float:
        return self.salario_fijo + self.comisiones + self.cap_inicial + self.seguridad + (...)
```

**Impacto**: 
- 1 campo en domain model
- 1 cambio en NominaCalculator
- 1 cambio en vision_tarifas (usar modelo en lugar de recalcular)
- Tests +2

---

### 2.5 Concepto: Seguridad (Exámenes Médicos + Seguros)

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Estudios Seguridad | exámenes + seguros | float | ✓ |
| **entry_data** | `condiciones_cadena_a.perfiles[].incluye_seguridad` | bool | bool | ✓ |
| **Domain** | `ResultadoNomina.seguridad` | float | float | ✓ |
| **Calculadora** | NominaCalculator.seguridad | examen_anual + póliza | float | ✓ |
| **Endpoint** | **`vision_tarifas.canales[].estudios_seguridad_ch`** | float | float | ⚠️ **Alias** |

**Problema**: 
- Domain y calculadora usan "seguridad"
- Endpoint usa "estudios_seguridad_ch"
- Ambos se refieren al mismo concepto

**Decisión**: 
- ✓ Usar **"estudios_seguridad"** en domain (más específico)
- Alias en serializer si es necesario

**Impacto**: 1 renombrado en domain models + tests.

---

### 2.6 Concepto: Salario Variable (Comisiones)

| Layer | Campo | Fórmula | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Comisiones | salario_base × comision_pct | float | ✓ |
| **entry_data** | `condiciones_cadena_a.perfiles[].comision_pct` | 0.15 | float | ✓ |
| **Domain** | `ResultadoNomina.comisiones` | float | float | ✓ |
| **Calculadora** | NominaCalculator.comisiones | float | float | ✓ |
| **Endpoint** | **`vision_tarifas.canales[].salario_variable_ch`** | float | float | ⚠️ **Alias innecesario** |

**Problema**: "salario_variable" es ambiguo (¿todo lo que varía o solo comisiones?).

**Decisión**: 
- ✓ Usar **"comisiones"** en endpoint (más específico)
- O mantener "salario_variable_ch" pero documentar explícitamente = comisiones

**Impacto**: 1 cambio en endpoint + 1 doc update.

---

### 2.7 Concepto: Volumen Mensual por Perfil

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Vol (Cadena A) | 1000 | float | ✓ Sheet "Condiciones CA" |
| **entry_data** | `condiciones_cadena_a.perfiles[].vol_cadena_a_mensual` | 1000 | float | ✓ |
| **Domain** | `PerfilCadenaA.vol_cadena_a_mensual` | 1000 | float | ✓ |
| **Calculadora** | PyGCalculator | usado para tarifa | float | ✓ |
| **Endpoint** | **NOT EXPOSED** | — | — | ⚠️ **Ocultado** |

**Problema**: vol_cadena_a_mensual se usa en cálculos pero no se expone en response.

**Decisión**: 
- Decidir si exponer en endpoint (para trazabilidad)
- Si se expone: `vision_tarifas.canales[].vol_cadena_a_mensual`

**Impacto**: 1 cambio en endpoint (o documentar por qué NO se expone).

---

### 2.8 Concepto: Producto Cadena B (¡AMBIGUO!)

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Producto | "Zendesk", "Twilio", "Token IA" | enum | ✓ |
| **entry_data** | `condiciones_cadena_b.opex.items[].producto` | "Zendesk" | enum | ✓ |
| **Domain** | `ItemOpexConsumoB.producto` | "Zendesk" | string | ✓ (se almacena) |
| **Calculadora** | CadenaBCalculator | **NUNCA SE USA** | — | ⚠️ **IGNORADO** |
| **Endpoint** | (no expuesto) | — | — | — |

**Problema**: 
1. Se almacena pero nunca se usa (capacidad perdida)
2. Nombre "producto" es ambiguo (también se usa para canal en vision_tarifas)
3. ¿Se puede segmentar costo por producto? (Hoy no)

**Decisión**: 
- Opción A: Eliminar campo (es inútil)
- Opción B: Guardar y permitir segmentación por producto en resultados
- Recomendación: ✓ **Opción B** (mantiene capacidad futura)

**Impacto**: 
- Agregar a `ResultadoVisionTarifas` si se expone
- O documentar explícitamente que se ignora (por ahora)

---

### 2.9 Concepto: Rubro de Cadena B

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Rubro | "Plataformas y Licencias", "Infraestructura" | enum | ✓ |
| **entry_data** | `condiciones_cadena_b.opex.items[].rubro` | "Plataformas" | enum | ✓ |
| **Domain** | `ItemOpexConsumoB.rubro` | **NO EXISTE** | — | ⚠️ **PERDIDO** |
| **Calculadora** | CadenaBCalculator | — | — | — |
| **Endpoint** | (no expuesto) | — | — | — |

**Problema**: Rubro contiene información valiosa (segmentación de costos), pero se pierde en contexto.

**Decisión**: 
- Opción A: Guardar en domain → exponer en endpoint
- Opción B: Rechazar en validación (no es necesario)
- Recomendación: ✓ **Opción A** (permite auditoría)

**Impacto**: 
- 1 cambio en domain model (ItemOpexConsumoB)
- 1 cambio en context_builder (mapeo)
- 1 cambio en serializer (exposición)

---

### 2.10 Concepto: Tipo de Cobro

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Tipo de Cobro | "Unitario", "Mensual", "Evento" | enum | ✓ |
| **entry_data** | `condiciones_cadena_b.opex.items[].tipo_de_cobro` | "Unitario" | enum | ✓ |
| **Domain** | `ItemOpexConsumoB.tipo_de_cobro` | **NO EXISTE** | — | ⚠️ **PERDIDO** |
| **Calculadora** | — | — | — | — |
| **Endpoint** | — | — | — | — |

**Problema**: Define cómo se factura el costo (impacta flujo de caja), pero se pierde.

**Decisión**: 
- ✓ Guardar en domain + documentar propósito
- No necesita ser usado en cálculos (es metadata)

**Impacto**: 1 cambio en domain + context_builder.

---

### 2.11 Concepto: Tipo de Gasto (CAPEX vs OPEX)

| Layer | Campo | Valor Típico | Tipo | Status |
|-------|-------|---|---|---|
| **Excel** | Tipo de Gasto | "Fijo", "Variable", "CAPEX" | enum | ✓ |
| **entry_data** | `condiciones_cadena_b.opex.items[].tipo_de_gasto` | "Fijo" | enum | ✓ |
| **Domain** | `ItemOpexConsumoB.tipo_de_gasto` | **NO EXISTE** | — | ⚠️ **PERDIDO** |
| **Calculadora** | — | — | — | — |
| **Endpoint** | — | — | — | — |

**Problema**: Clasificación CAPEX/OPEX importante para auditoría financiera, pero se pierde.

**Decisión**: 
- ✓ Guardar en domain (es metadata crítica)
- Opcional: exponer en endpoint para auditoría

**Impacto**: 1 cambio en domain + context_builder.

---

## 3. Campos Opcionalmente Usados

### 3.1 pct_presencia

| Campo | Documentación | Ubicación | Uso Actual |
|-------|---|---|---|
| `PerfilCadenaA.pct_presencia` | % de horas presencia vs remoto | domain/models.py | ⚠️ **No se usa en calculadora** |

**Pregunta**: ¿Debería afectar a cálculos? (ej. reducir costo de infraestructura si remote)

**Recomendación**: Documentar decisión explícitamente en código o rechazar campo.

---

## 4. Suffixes Inconsistentes

### 4.1 _ch (Canal/Hora/?)

| Campo | Ubicación | Significado | Documenta |
|-------|-----------|-----------|---|
| `payroll_ch` | vision_tarifas | Cost per channel | ❌ Significado no documentado |
| `salario_variable_ch` | vision_tarifas | Commission per channel | ❌ |
| `estudios_seguridad_ch` | vision_tarifas | Security cost per channel | ❌ |
| `no_payroll_ch` | vision_tarifas | Non-payroll per channel | ❌ |
| `cadena_b_ch` | vision_tarifas | Platform cost per channel | ❌ |

**Problema**: Suffix "_ch" no está documentado. ¿Significa "por canal" (per channel)?

**Decisión**: 
- ✓ Mantener "_ch" pero documentar en código:
  ```python
  # Suffix convention: _ch = "costo por hora" OR "costo por canal"
  # Clarificar cuál es para este proyecto
  ```

---

## 5. Plan de Estandarización

### Fase A: Documentación de Decisiones

```python
# docs/naming_conventions.md
[NUEVO]

## Nomenclatura Estándar

### Canales y Perfiles
- **canal**: Medio de contacto (WhatsApp, Email, etc.) — único source
- **No usar**: "producto" para canales (ambiguo)

### Nómina y Costos
- **payroll**: Total de nómina cargada (salario + comisiones + beneficios)
- **nomina_loaded**: Factor de carga aplicado (almacenado en domain)
- **comisiones**: Salario variable
- **estudios_seguridad**: Exámenes médicos y pólizas
- **no_payroll**: Costos no salariales
- **cadena_b**: Costos de plataforma
- **cadena_c**: Costos de IA

### Metadata de Cadena B
- **rubro**: Categoría de gasto (Plataformas, Infraestructura, etc.)
- **tipo_de_cobro**: Unitario, Mensual, Evento
- **tipo_de_gasto**: Fijo, Variable, CAPEX
- **producto**: Nombre del producto/servicio (Zendesk, AWS, etc.)

### Suffixes
- **_ch**: Costo por canal (PER CHANNEL) — documentar claramente
- **_total**: Agregado total
- **_mensual**: Valor mensual
- **_acumulado**: Acumulado en contrato

### Campos que pueden perderse
- ❌ No aceptar: rubro, tipo_de_cobro, tipo_de_gasto sin almacenar
- ✓ Guardar siempre: metadata importante para auditoría
```

### Fase B: Cambios en Domain Models

```python
# domain/models.py

@dataclass
class ResultadoNomina:
    salario_fijo: float
    comisiones: float  # ← Keep (=salario_variable)
    cap_inicial: float
    estudios_seguridad: float  # ← RENAME from seguridad
    nomina_loaded: float  # ← ADD: factor de carga aplicado
    
    @property
    def total(self) -> float:
        return self.salario_fijo + self.comisiones + self.cap_inicial + self.estudios_seguridad

@dataclass
class ItemOpexConsumoB:
    # ... campos existentes ...
    rubro: str  # ← ADD
    tipo_de_cobro: str  # ← ADD
    tipo_de_gasto: str  # ← ADD
    # producto: str  # ← KEEP (aunque no se usa, es metadata)
```

### Fase C: Cambios en Endpoints

**Archivo**: `api/v1/simulation/results_router.py`

```python
# vision_tarifas response

TarifaCanal {
    nombre_canal: str  # Keep
    canal: str  # ← ADD (en lugar de "producto")
    fte: float
    volumen_mensual: float
    tarifa_unitaria: float
    
    # Desglose de costos:
    payroll_ch: float
    nomina_loaded_ch: float  # ← Now backed by ResultadoNomina.nomina_loaded
    comisiones_ch: float  # ← RENAME from salario_variable_ch
    estudios_seguridad_ch: float  # ← KEEP (es correcto)
    no_payroll_ch: float
    cadena_b_ch: float
}
```

### Fase D: Validación de entry_data

```python
# adapters/input_validator.py

def validate_cadena_b_opex_items(items: List[dict]) -> List[ItemOpexConsumoB]:
    """
    Valida y mapea items de Cadena B.
    
    Campos REQUERIDOS:
    - costo_unitario, cantidad (para cálculo)
    
    Campos OPCIONALES pero GUARDADOS (metadata):
    - rubro, tipo_de_cobro, tipo_de_gasto, producto
    
    Campo IGNORADO (no es útil):
    - ninguno (todos se guardan)
    """
    validated = []
    for item in items:
        validated.append(ItemOpexConsumoB(
            # ... campos de cálculo ...
            rubro=item.get("rubro"),  # ← Guardar metadata
            tipo_de_cobro=item.get("tipo_de_cobro"),
            tipo_de_gasto=item.get("tipo_de_gasto"),
            producto=item.get("producto"),
        ))
    return validated
```

---

## 6. Matriz de Cambios

| Cambio | Severidad | Impacto | Files | Tests |
|--------|---|---|---|---|
| **Add nomina_loaded to ResultadoNomina** | CRÍTICA | calculators, vision_tarifas, tests | 3 | +2 |
| **Rename seguridad → estudios_seguridad** | CRÍTICA | domain, calculators, tests | 4 | +1 |
| **canal field in endpoint (not producto)** | CRÍTICA | endpoint, serializer | 2 | +1 |
| **Add rubro, tipo_de_cobro, tipo_de_gasto** | ALTA | domain, context_builder | 3 | +1 |
| **Rename comisiones to comisiones_ch** | MEDIA | endpoint, serializer | 2 | 0 |
| **Document _ch suffix** | BAJA | docs | 1 | 0 |
| **Expose vol_cadena_a_mensual (optional)** | BAJA | endpoint, serializer | 1 | 0 |

---

## 7. Conclusiones

| Aspecto | Hallazgo | Acción |
|--------|---|---|
| **Aliases innecesarios** | canal/producto, comisiones/salario_variable | Estandarizar |
| **Campos faltantes en domain** | nomina_loaded, rubro, tipo_de_cobro, tipo_de_gasto | Agregar |
| **Campos ignorados** | producto Cadena B (se almacena pero no usa) | Documentar uso futuro |
| **Suffixes inconsistentes** | _ch no documentado | Documentar regla |
| **Campos opcionalmente usados** | pct_presencia (no se usa) | Rechazar o usar |

---

**Siguiente**: Fase 4 — Auditoría de Cadenas (A, B, C) - Validación de Activación
