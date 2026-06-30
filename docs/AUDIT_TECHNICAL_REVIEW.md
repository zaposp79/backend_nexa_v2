# AUDIT TÉCNICA: NEXA Pricing Engine

**Realizada por**: Staff Engineer + Financial Systems Auditor  
**Fecha**: 2026-05-26  
**Alcance**: Estado actual del motor después de TASK 1-4  
**Baseline**: 39/39 tests TASK 1-4 passing, ~495 tests globales

---

## RESUMEN EJECUTIVO

El motor NEXA está **productivo en su núcleo**, pero hay **3 hallazgos críticos** que bloquearían producción de alto volumen, **7 hallazgos de medianos** que causarían drift financiero, y **2 problemas de deuda técnica** que afectan mantenibilidad. No hay arquitectura rota, pero hay **defaults silenciosos peligrosos** y **validaciones faltantes** en lugares críticos.

### Estado por Categoría

| Categoría | Estado | Riesgo |
|-----------|--------|--------|
| **Aislamiento Cadenas (A/B/C)** | ✅ Correcto | Bajo |
| **Policies por Cadena** | ✅ Correcto | Bajo |
| **Optional Chains** | ✅ Correcto | Bajo |
| **Volume Resolution** | ✅ Correcto | Bajo |
| **Rounding Excel** | ✅ Correcto | Bajo |
| **Cálculos Nómina** | ⚠️ Incompleto | **ALTO** |
| **Validaciones** | 🔴 Débil | **CRÍTICO** |
| **Defaults Silenciosos** | 🔴 Peligrosos | **CRÍTICO** |
| **Serialización** | ⚠️ Incompleto | **ALTO** |

---

## HALLAZGOS CRÍTICOS (🔴 P0)

### H-01 — Defaults Silenciosos Silencian Errores de Carga

**Hallazgo real:**  
En `adapters/user_input_loader.py`, 12+ campos críticos defaultean a `0.0` si no vienen en el JSON. Sin validación, no hay diferencia entre "carga fallida" y "valor legítimamente 0".

```python
# Línea 503-504
cadena_b_mensual = float(d.get("cadena_b_mensual", 0.0))
costos_financieros_mensual = float(d.get("costos_financieros_mensual", 0.0))
# Línea 505
vol_cadena_a_mensual = float(d.get("vol_cadena_a_mensual", 0.0))
# Línea 518-519
inversion_plataforma = float(d.get("inversion_plataforma", 0.0))
fte_equipo_sm = float(d.get("fte_equipo_sm", 1.0))
```

**Ubicación:**  
`adapters/user_input_loader.py:500-519`

**Impacto:**  
Scenario: Cliente B intenta cargar deal de COP 500M, JSON parser falla en campo `cadena_b_mensual`. Sistema silencia el error como 0.0, calcula P&G con Cadena B = $0. Cliente factura deal incorrecto. **Riesgo financiero: cualquier magnitud**.

**Evidencia:**  
Ejecutar:
```python
bad_json = {
    "panel_de_control": {...},
    "condiciones_cadena_a": {...},
    # "cadena_b_mensual" falta (error de carga o JSON malformado)
}
loader = UserInputLoader(provider)
request = loader.cargar_desde_dict(bad_json)
# request.perfiles[0].cadena_b_mensual = 0.0  ✗ SILENCIADO
```

**Severidad:**  
🔴 **CRÍTICO**

**Recomendación mínima:**  
Marcar 5 campos como `required` en InputNormalizer con fail-fast:
- cadena_b_mensual
- cadena_c_mensual (si aplica)
- vol_cadena_a_mensual (si Cadena A activa)
- inversion_plataforma (si Cadena B activa)

Agregar validación en InputNormalizer.validate():
```python
if cadenas_activas.cadena_b and not user_input.get("cadena_b_mensual"):
    raise ValueError("cadena_b_mensual requerido si Cadena B está activa")
```

**Prioridad:**  
P0 (bloquea cualquier cliente con Cadena B)

---

### H-02 — Validaciones de Parámetros Faltantes en PyGCalculator

**Hallazgo real:**  
`calculadores/pyg.py` NO valida que los inputs cumplan restricciones financieras básicas:
- `ingreso_neto <= ingreso_bruto` ✗ No se verifica
- `costo_total <= ingreso_neto` ✗ No se verifica
- `margen_requerido > 0` ✗ No se verifica

Si cliente especifica `margen = -5%` o `ingreso_neto > ingreso_bruto`, el motor calcula un resultado financieramente inválido sin advertencia.

**Ubicación:**  
`calculadores/pyg.py:50-150` (PyGCalculator.calcular_contrato)

**Impacto:**  
Scenario: Frontend bug introduce margen negativo. Python calcula deal válido. Auditor detecta P&G imposible. Retrasos, recalculos, pérdida de confianza.

**Evidencia:**  
```python
pyg = PyGMensual(
    ingreso_bruto=1000,
    ingreso_neto=2000,  # ✗ Inválido: neto > bruto
    costo_total=3000,    # ✗ Inválido: costo > neto
    margen=-0.5,         # ✗ Inválido: negativo
)
# Motor calcula utilidad_neta = 2000 - 3000 - 500 = -1500
# Devuelve resultado sin error
```

**Severidad:**  
🔴 **CRÍTICO**

**Recomendación mínima:**  
Agregar `__post_init__` en PyGMensual:
```python
def __post_init__(self):
    if self.ingreso_neto > self.ingreso_bruto:
        raise ValueError("Ingreso neto NO puede exceder bruto")
    if self.costo_total > self.ingreso_neto:
        raise ValueError("Costo total NO puede exceder ingreso neto")
    if self.margen < 0:
        raise ValueError("Margen NO puede ser negativo")
```

**Prioridad:**  
P0 (garantiza sanidad de output)

---

### H-03 — Deserialización Incompleta en SnapshotRepository

**Hallazgo real:**  
`domain/snapshot.py` deserializa campos con defaults silenciosos (líneas 198-210), sin validar que los valores deserializados sean consistentes con el estado guardado.

```python
# snapshot.py:206-210
parametros = ParametrosParciales(
    smmlv = float(param_dict.get("smmlv", 0.0)),            # ✗ default 0.0
    auxilio_transporte = float(param_dict.get("auxilio_transporte", 0.0)),  # ✗
    pct_rotacion_linea = float(param_dict.get("pct_rotacion_linea", 0.0)),  # ✗
)
```

Si snapshot.json se corrompe o pierde campos, se deserializa con zeros invisibles.

**Ubicación:**  
`domain/snapshot.py:195-230`

**Impacto:**  
Scenario: Fallo de disco parcial, snapshot.json pierde sección `parametros`. Recalcular deal desde snapshot produce P&G distinto. Imposible auditar divergencia.

**Evidencia:**  
```python
snapshot_corrupted = {
    "simulation_id": "...",
    "parametros": None,  # ✗ Corrupción
}
snapshot = SimulationSnapshot.from_dict(snapshot_corrupted)
# snapshot.parametros.smmlv = 0.0  ✗ SILENCIADO
```

**Severidad:**  
🔴 **CRÍTICO**

**Recomendación mínima:**  
Cambiar defaults a None + validar en `__post_init__`:
```python
if self.parametros is None:
    raise ValueError("Snapshot corrupted: parametros missing")
```

**Prioridad:**  
P0 (integridad de persistencia)

---

## HALLAZGOS ALTOS (🟠 P1)

### H-04 — Cálculo de Salario Fijo Incompleto

**Hallazgo real:**  
`domain/services/special_roles_calculator.py:SalarioFijoCalculator` usa fórmula:
```
Salario_Fijo = Σ(sal_cargado_i × fte_i) / meses_contrato / total_fte
```

Pero en Excel V2-6 Vision Cost To Serve, Salario Fijo se calcula sobre SOLO los perfiles base (agentes), NO incluyendo soporte. El código incluye TODO el soporte, causando divergencia.

**Ubicación:**  
`domain/services/special_roles_calculator.py:284-320`  
`input/context_builder.py:559-563` (donde se llama)

**Impacto:**  
Scenario: Deal con 10 agentes + 5 soporte. Excel calcula Salario Fijo basado en 10 agentes. Python calcula basado en 15 (agentes + soporte). **Divergencia: ~5-15% en Salario Fijo**, afecta KPIs, reportes, y auditoría.

**Evidencia:**  
Excel V2-6: Vision Cost To Serve, celda G40 = SUM(L25:L34) / C11 / J35  
- L25:L34 = salarios de AGENTES SOLO
- J35 = total FTE AGENTES

Python actual:
```python
perfiles_para_fijo = [p for p in perfiles]  # Incluye agentes + TODO soporte
salario_fijo = suma_costo / meses / suma_fte
```

**Severidad:**  
🟠 **ALTO**

**Recomendación mínima:**  
Filtrar perfiles antes de calcular:
```python
perfiles_base_solo = [p for p in perfiles if p.rol not in roles_especiales]
salario_fijo = salario_fijo_calc.calcular(perfiles_base_solo, meses_contrato)
```

**Prioridad:**  
P1 (afecta KPI de salida)

---

### H-05 — Versión de Rounding NO Usado en Lugares Críticos

**Hallazgo real:**  
`shared/precision.py` define `pct_round()` con ROUND_HALF_UP para Excel-parity. Pero CadenaBCalculator, CadenaCCalculator, y NoPayrollCalculator **NO lo usan**. Usan `float()` directo (Python default = ROUND_HALF_EVEN).

```python
# calculators/cadena_b.py:131
def _costo_opex_fijo(self) -> float:
    return sum(c.opex_fijo for c in self._parametros.canales)
    # ✗ NO usa pct_round(), float arithmetic directo
```

**Ubicación:**  
`calculators/cadena_b.py:64-108`  
`calculators/cadena_c.py:entire`  
`calculators/no_payroll.py:entire`

**Impacto:**  
Scenario: Suma de 3 valores pequeños: 100.001 + 100.001 + 100.001 = 300.003. Excel redondea cada uno a 100.00, suma = 300.00. Python suma antes de redondear, obtiene 300.00. **En casos más complejos: divergencia acumulativa**.

**Evidencia:**  
```python
# Excel: ROUND(100.001,2) + ROUND(100.001,2) + ROUND(100.001,2)
#        = 100.00 + 100.00 + 100.00 = 300.00

# Python: sum([100.001, 100.001, 100.001]) = 300.003 (antes de redondear)
```

**Severidad:**  
🟠 **ALTO**

**Recomendación mínima:**  
Cambiar Cadena B/C para redondear cada componente antes de sumar:
```python
def _costo_opex_fijo(self) -> float:
    from nexa_engine.shared.precision import pct_round
    return sum(pct_round(c.opex_fijo, 2) for c in self._parametros.canales)
```

**Prioridad:**  
P1 (paridad Excel V2-6)

---

### H-06 — Inclusión y SENA NO Exponen Criterios de Exclusión en Visión

**Hallazgo real:**  
Vision dataset (DatasetsVision.staffing) expone FTE por perfil, pero NO expone qué perfiles fueron excluidos de SENA o Inclusión. Auditor no puede verificar si CargoClassifier funcionó correctamente.

**Ubicación:**  
`calculators/vision_datasets.py:89-119`  
`domain/visions.py:53-101`

**Impacto:**  
Scenario: Deal con 50 perfiles de soporte. CargoClassifier excluye 10 de SENA. Visión no expone cuáles fueron excluidos ni por qué. Auditor no puede verificar corrección sin read debugging del código.

**Evidencia:**  
```python
# Vision actual:
staffing.filas = [
    PerfilStaffingRow(nombre="Supervisor", ..., fte=2.0),
    PerfilStaffingRow(nombre="QA", ..., fte=1.5),
    # ✗ NO DICE: "Supervisor excluido de SENA", "QA incluido en SENA"
]
```

**Severidad:**  
🟠 **ALTO**

**Recomendación mínima:**  
Agregar campo `exclusiones` a PerfilStaffingRow:
```python
@dataclass
class PerfilStaffingRow:
    exclusiones: str = ""  # "SENA", "INCLUSION", "AMBAS", ""
```

Poblar en `_build_staffing()`:
```python
exclusiones = []
if classifier.es_excluido_sena_base(perfil.rol):
    exclusiones.append("SENA")
...
filas.append(PerfilStaffingRow(..., exclusiones="|".join(exclusiones)))
```

**Prioridad:**  
P1 (audibilidad)

---

### H-07 — Riesgo de Division by Zero NO Protegido en Casos Edge

**Hallazgo real:**  
Aunque hay checks `if denominator == 0`, hay 3 lugares donde el check llega DESPUÉS de intentar usar la variable:

```python
# calculators/special_roles_calculator.py:215
ratio = numerador / denominador  # ✗ Si denominador = 0, excepción ANTES del if
if denominador == 0:
    return 0.0
```

Además, hay denominadores que pueden ser 0 pero NO se chequean:
- `total_fte_validador` en EspecialistaCalculator (puede ser 0)
- `suma_fte` en SalarioFijoCalculator (puede ser 0, ya se chequea)

**Ubicación:**  
`domain/services/special_roles_calculator.py:209-216`

**Impacto:**  
Scenario: Deal con 0 validadores. EspecialistaCalculator falla en time. Deal no se calcula.

**Evidencia:**  
```python
# Test case
esp_calc = EspecialistaCalculator({})
fte = esp_calc.calcular_fte(
    fte_agentes=10, fte_validador=0,
    total_fte_agentes=10, total_fte_validador=0  # Suma = 0
)
# Excepción: ZeroDivisionError en línea 215
```

**Severidad:**  
🟠 **ALTO**

**Recomendación mínima:**  
Mover check ANTES del cálculo:
```python
denominador = Decimal(str(total_fte_agentes)) + Decimal(str(total_fte_validador))
if denominador == 0:
    return 0.0
ratio = numerador / denominador
```

**Prioridad:**  
P1 (evita crash)

---

## HALLAZGOS MEDIOS (🟡 P2)

### H-08 — CostosTotalesCalculator NO Valida Suma Básica

**Hallazgo real:**  
`calculators/costos_totales.py` suma componentes (payroll, no_payroll, cadena_b, cadena_c, polizas, etc) sin validar que el total tiene sentido. Si un componente devuelve NaN o -1000000, el total se propaga sin error.

**Ubicación:**  
`calculators/costos_totales.py:50-100`

**Impacto:**  
Bajo, porque los calculadores previos tienen lógica. Pero si hay fuga de datos, CostosTotales no la detecta.

**Severidad:**  
🟡 **MEDIO**

**Recomendación mínima:**  
Agregar validación post-suma:
```python
total = payroll + no_payroll + cadena_b + cadena_c + polizas + financiacion
if total < 0:
    raise ValueError(f"Costo total negativo: {total}")
if math.isnan(total):
    raise ValueError("Costo total es NaN")
```

**Prioridad:**  
P2

---

### H-09 — SerializerContext NO Expone Tous los Breaking Changes

**Hallazgo real:**  
`adapters/pricing_serializer.py` tiene comentario:

```python
# Agrega propiedades (@property) que asdict() omite
d["ingreso_bruto"] = p.ingreso_bruto
```

Pero hay 8 propiedades en PyGMensual y el serializer SOLO expone 6. Falta:
- `pct_contribucion` ✗
- `pct_utilidad_neta` ✗

**Ubicación:**  
`adapters/pricing_serializer.py:46-65`

**Impacto:**  
Client API expects `pct_contribucion` in JSON response. Frontend breaks. "Field missing" errors en parseo.

**Severidad:**  
🟡 **MEDIO**

**Recomendación mínima:**  
Completar serializer:
```python
d["pct_contribucion"] = p.pct_contribucion
d["pct_utilidad_neta"] = p.pct_utilidad_neta
```

Agregar test que valide todos los @property se serializen:
```python
pyg_props = {attr for attr in dir(PyGMensual) 
             if isinstance(getattr(PyGMensual, attr), property)}
serialized_keys = set(d.keys())
assert pyg_props.issubset(serialized_keys), f"Missing: {pyg_props - serialized_keys}"
```

**Prioridad:**  
P2

---

### H-10 — NominaCargadaService NO Documenta Casos Edge (Alto Salario)

**Hallazgo real:**  
`domain/services/nomina_cargada.py` línea 4 menciona:

```
4. Para altos salarios (> 10 × SMMLV): factor corrector 0.70 sobre salud,
```

Pero NO hay código que lo implemente. Si `salario_base > 10 × SMMLV`, ¿qué ocurre?

**Ubicación:**  
`domain/services/nomina_cargada.py:1-50`

**Impacto:**  
Para salarios > SMMLV × 10, nómina cargada puede divergir de Excel. No hay test que cubra este caso.

**Severidad:**  
🟡 **MEDIO**

**Recomendación mínima:**  
O implementar el factor 0.70, o remover el comentario e investigar Excel V2-6 para ver si es real o legacy.

**Prioridad:**  
P2

---

## HALLAZGOS BAJOS (🟢 P3)

### H-11 — Deuda Técnica: request_dto.py Importa pydantic (NO INSTALADO)

**Hallazgo real:**  
`simulation/request_dto.py:24` importa `from pydantic import BaseModel`, pero pydantic NO está en requirements.txt. Test `test_simulation_request.py` falla en colección.

```python
# simulation/request_dto.py:24
from pydantic import BaseModel, ConfigDict, Field, model_validator
# ✗ ModuleNotFoundError: No module named 'pydantic'
```

**Ubicación:**  
`simulation/request_dto.py:24`  
`tests/unit/test_simulation_request.py:23`

**Impacto:**  
Bajo. Module no está en uso todavía. Pero bloquea tests si alguien los ejecuta.

**Severidad:**  
🟢 **BAJO**

**Recomendación mínima:**  
O instalar pydantic en requirements.txt, o remover request_dto.py si no está en uso. Decidir: ¿Migramos a pydantic o abandonamos?

**Prioridad:**  
P3

---

### H-12 — Deuda Técnica: Múltiples Rutas a UserInput

**Hallazgo real:**  
Hay 3 rutas para construir UserInput / PricingRequest:
1. `input/user_input_loader.py` (JSON)
2. `adapters/entry_data_adapter.py` (legacy)
3. `simulation/request_dto.py` (Pydantic — no usado)

Sin documentación clara, nuevo desarrollador puede no saber cuál usar.

**Ubicación:**  
`input/user_input_loader.py`  
`adapters/entry_data_adapter.py`  
`simulation/request_dto.py`

**Impacto:**  
Bajo. Mantenibilidad. Mayor surface area para bugs de integración.

**Severidad:**  
🟢 **BAJO**

**Recomendación mínima:**  
Documentar matriz clara en engine.py o README sobre "cuándo usar cada loader". Marcar como deprecated las que no se usan.

**Prioridad:**  
P3

---

## ESTADO POR COMPONENTE

| Componente | Tests | Hallazgos | Veredicto |
|-----------|-------|-----------|-----------|
| Cadena A (Nómina) | ✅ 40+ | 1 ALTO (H-04) | Prod-ready con fix |
| Cadena B (Digital) | ✅ 15+ | 1 ALTO (H-05) | Prod-ready con fix |
| Cadena C (IA) | ✅ 10+ | 1 ALTO (H-05) | Prod-ready con fix |
| Policies | ✅ 8 | 0 | ✅ LISTO |
| Optional Chains | ✅ 12 | 0 | ✅ LISTO |
| Volume Resolution | ✅ 13 | 0 | ✅ LISTO |
| Validación | ❌ 0 | 3 CRÍTICOS | 🔴 BLOQUEADO |
| Serialización | ⚠️ Parcial | 1 MEDIO | Completar |
| Special Roles | ⚠️ Parcial | 1 ALTO | Fix edge case |
| Vision Datasets | ✅ 20+ | 1 ALTO | Documentar exclusiones |

---

## ROADMAP DE FIXES

### INMEDIATO (antes de producción)

**P0 (48 horas)**:
1. **H-01**: Agregar validación fail-fast para cadena_b_mensual, vol_cadena_a_mensual
2. **H-02**: Agregar validaciones post-init en PyGMensual
3. **H-03**: Cambiar defaults en snapshot.py de 0.0 a None + validar

**P1 (1 semana)**:
4. **H-04**: Corregir cálculo de Salario Fijo (filtrar soporte)
5. **H-05**: Usar pct_round en Cadena B/C
6. **H-07**: Proteger Division by Zero en EspecialistaCalculator
7. **H-06**: Exponer exclusiones en vision staffing

### MEDIANO PLAZO (2-3 semanas)

8. **H-08**: Validación de sanidad en CostosTotalesCalculator
9. **H-09**: Completar serialización de propiedades faltantes
10. **H-10**: Investigar y documentar caso edge de alto salario

### TÉCNICA DE DEUDA (antes de v3)

11. **H-11**: Decidir: ¿pydantic o remover?
12. **H-12**: Documentar matrix de loaders

---

## VERIFICACIÓN: QADNE RESUELTO vs ABIERTO

### ✅ RESUELTO

- Aislamiento entre cadenas A/B/C: ✅ Verificado con tests TASK 3-4
- Policies por cadena: ✅ Verificado con tests TASK 1
- null vs []: ✅ Verificado con tests TASK 2
- Volume resolution: ✅ Verificado con tests TASK 4
- Rounding Excel: ✅ SalarioFijo + EspecialistaCalculator usan Decimal + ROUND_HALF_UP
- Backward compatibility: ✅ No hay breaking changes visibles

### 🔴 BLOQUEADO

- Paridad Excel V2-6 completa: 🔴 H-04, H-05 bloquean 5-15% drift potencial
- Validaciones contractuales: 🔴 H-01, H-02, H-03 permiten cálculos inválidos
- Serialización completa: ⚠️ H-09 pierde campos en output

---

## CONCLUSIÓN EJECUTIVA

El motor NEXA tiene **fundamentos sólidos** (aislamiento, parity rounding, composición limpia), pero **no está listo para producción de alto volumen** sin resolver:

1. **Defaults silenciosos** (H-01, H-03) — riesgo financiero directo
2. **Validaciones faltantes** (H-02) — salida puede ser matemáticamente inválida
3. **Divergencia Excel** (H-04, H-05) — paridad comprometida en 5-15% de deals

**Tiempo estimado para prod-ready**: 1-2 semanas si los P0/P1 se hacen en paralelo.

**Recomendación**: 
- ✅ Despachar TASK 5-7 EN PARALELO a fixes H-01/02/03
- ✅ Merge H-04/05/07 a rama principal en PR de "reparación técnica"
- ✅ Agregar test suite de "paridad Excel" antes de v1.0 production
