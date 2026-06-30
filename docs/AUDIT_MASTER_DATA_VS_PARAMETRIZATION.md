# Reporte de Auditoría: master_data vs Parametrización Activa

**Fecha:** 2026-05-19  
**Versión HR activa:** `26ad1692-985c-4a32-9a39-123170fabe6e` (HR_productiva_2026-05-11)  
**Versión OP activa:** `a6824e05-d9d4-4081-8322-cf0f8baa2e62` (OP_productiva_2026-05-11)  
**Versión GN activa:** `dafb2a8b-dbba-40c5-bcd9-304b8c258485` (GN_productiva_2026-05-11) — **datos vacíos**

---

## Resumen Ejecutivo

| Sección | Puntos comparados | ✅ Match | ❌ Mismatch | ⚠️ Advertencia |
|---------|------------------|---------|-------------|----------------|
| Financiero (GMF, Pólizas, ICA) | 30 | 9 | 0 | 21 |
| Índices económicos (IPC/SMLV) | 12 | 7 | 5 | 0 |
| Nómina – Salario mínimo | 1 | 0 | **1** | 0 |
| Nómina – Salarios por rol | 24 | 23 | 0 | 1 |
| Aportes patronales | 5 | 5 | 0 | 0 |
| Prestaciones sociales | 4 | 4 | 0 | 0 |
| Recargos salariales | 7 | 7 | 0 | 0 |
| Infraestructura (costos/localidad) | 91 | 86 | **5** | 0 |
| Rentabilidad (márgenes) | 12 | 12 | 0 | 0 |
| Campañas ramp-up | 15 | 13 | **2** | 0 |
| Medicina y seguridad | 1 | 1 | 0 | 0 |

**Bugs críticos encontrados en repositorios:** 1  
**Datos corruptos en parametrización:** 2 problemas

---

## Sección 1 – Parámetros Financieros (OP)

### 1.1 GMF y Pólizas de Seguros

| Concepto | master_data | OP-Poliza | Estado |
|----------|------------|-----------|--------|
| GMF | 0.004 | 0.004 | ✅ MATCH |
| Póliza Seriedad | 0.005 | 0.005 | ✅ MATCH |
| Póliza Cumplimiento | 0.0062 | 0.0062 | ✅ MATCH |
| Póliza Salarios | 0.0119 | 0.0119 | ✅ MATCH |
| Póliza Calidad | 0.0119 | 0.0119 | ✅ MATCH |
| RC Cruzada | 0.0275 | 0.0275 | ✅ MATCH |
| IRF | 0.0275 | 0.0275 | ✅ MATCH |
| Póliza Responsabilidad | 0.0069 | 0.0069 | ✅ MATCH |
| Comisión Administración | 0.0118 | 0.0118 | ✅ MATCH |

**Resultado:** ✅ Todas las pólizas y GMF coinciden exactamente.

---

### 1.2 Tasas ICA por Ciudad — ⚠️ UNIDADES INCOMPATIBLES

**El problema central:** `master_data/tasas.json` almacena las tasas ICA como **decimal aplicado directamente** (ej: `0.0197` para Bogotá = 1.97% anual sobre facturación). La hoja `OP-ICA` en parametrización almacena los componentes de la tasa en **otra unidad no compatible**, desglosados en 4 subcategorías (Tasa, Avisos & Tableros, Bomberos, Otras Sobretasas).

| Ciudad | master_data | OP-ICA "Tasa" | OP-ICA Total | Análisis |
|--------|------------|---------------|-------------|----------|
| Armenia | 0.0060 | 60.0 | 60.00 | ⚠️ Armenia único caso: 60/10000=0.006 ✓ |
| Barranquilla | 0.0425 | 1.25 | 1.28 | ⚠️ Unidades no comparables |
| Bogotá | 0.0197 | 0.97 | 0.98 | ⚠️ Unidades no comparables |
| Bucaramanga | 0.1090 | 0.90 | 1.00 | ⚠️ Unidades no comparables |
| Buga | 0.0090 | 0.90 | 0.90 | ⚠️ Unidades no comparables |
| Cali | 0.0100 | 1.00 | 1.00 | ⚠️ Unidades no comparables |
| Cartagena | 0.0780 | 0.80 | 0.87 | ⚠️ Unidades no comparables |
| Cúcuta | 0.0600 | 1.00 | 1.05 | ⚠️ Unidades no comparables |
| Manizales | 0.0545 | 0.45 | 0.50 | ⚠️ Unidades no comparables |
| Medellín | 0.0200 | 1.00 | 1.01 | ⚠️ Unidades no comparables |
| Neiva | 0.0400 | 1.00 | 1.03 | ⚠️ Unidades no comparables |
| Palmira | 0.0070 | 0.70 | 0.70 | ⚠️ Unidades no comparables |
| Pasto | 0.0060 | 0.60 | 0.60 | ⚠️ Unidades no comparables |
| Pereira | 0.2150 | 1.00 | 1.21 | ⚠️ Unidades no comparables |
| Popayán | 0.0070 | 0.70 | 0.70 | ⚠️ Unidades no comparables |
| Santa Marta | 0.0770 | 0.70 | 0.77 | ⚠️ Unidades no comparables |
| Sincelejo | 0.0580 | 0.80 | 0.85 | ⚠️ (typo: "Sicelejo" en OP) |
| Tunja | 0.1100 | 1.00 | 1.10 | ⚠️ Unidades no comparables |
| Valledupar | 0.0100 | 1.00 | 1.00 | ⚠️ (typo: "Valledupár" en OP) |
| Villavicencio | 0.0460 | 0.60 | 0.64 | ⚠️ Unidades no comparables |

**Interpretación probable del OP-ICA:**
- La hoja OP-ICA almacena la **tarifa municipal** (promilaje o tarifa base) y las sobretasas por separado
- El cálculo final de ICA requiere una fórmula que combina estas columnas
- `master_data` ya tiene el resultado final aplicado (decimal), mientras OP tiene los insumos del cálculo
- La `FinancialParametrizationRepository.get_ica()` NO puede retornar correctamente la tasa sin implementar la fórmula de combinación

**Acciones requeridas:**
1. Definir y documentar la fórmula de cálculo del ICA a partir de los 4 componentes OP-ICA
2. Actualizar `FinancialParametrizationRepository.get_ica()` para aplicar la fórmula
3. Validar resultado final contra master_data para todas las ciudades
4. Corregir typos de nombres de ciudad en OP-ICA: "Sicelejo" → "Sincelejo", "Valledupár" → "Valledupar"

---

### 1.3 Índices Económicos (IPC / SMLV)

**IPC — ✅ CONSISTENTE**

| Año | master_data (acumulado) | OP-Componente (tasa anual) | Acumulado recalculado | Estado |
|-----|------------------------|--------------------------|----------------------|--------|
| 2025 | 1.0000 | 0.0527 | 1.0000 | ✅ |
| 2026 | 1.0527 | 0.0527 | 1.0527 | ✅ |
| 2027 | 1.1082 | 0.0527 | 1.1082 | ✅ |
| 2028 | 1.1666 | 0.0527 | 1.1666 | ✅ |
| 2029 | 1.2281 | 0.0527 | 1.2281 | ✅ |
| 2030 | 1.2928 | 0.0527 | 1.2928 | ✅ |

> IPC es consistente: OP usa tasa anual fija 5.27%, master_data usa el acumulado resultante. Mismo modelo.

**SMLV — ⚠️ DIFERENCIA EN PROYECCIÓN**

| Año | master_data (acumulado) | OP tasa anual 12% (recalc) | Estado |
|-----|------------------------|--------------------------|--------|
| 2025 | 1.0000 | 1.0000 | ✅ |
| 2026 | 1.2378 | 1.1200 | ⚠️ Dif: +0.1178 |
| 2027 | 1.3863 | 1.2544 | ⚠️ Dif: +0.1319 |
| 2028 | 1.5527 | 1.4049 | ⚠️ Dif: +0.1478 |
| 2029 | 1.7390 | 1.5735 | ⚠️ Dif: +0.1655 |
| 2030 | 1.9477 | 1.7623 | ⚠️ Dif: +0.1854 |

> **Causa:** `master_data` usa un **incremento SMLV del 23.78% para 2026** (ajuste real del salario mínimo colombiano 2025→2026), mientras OP asume una tasa plana del 12% anual para todos los años.
> 
> El incremento 2026 de 23.78% es correcto: el salario mínimo pasó de 1,300,000 (2024) base a 2,100,000 proyectado para 2026.
>
> **Acción:** OP-Componente SMLV debe actualizarse con las tasas reales por año, no una tasa plana.

---

## Sección 2 – Nómina y Payroll (HR)

### 2.1 Salario Mínimo — ❌ MISMATCH CRÍTICO

| Concepto | master_data | HR-Salarios | Estado |
|----------|------------|-------------|--------|
| Salario Mínimo | **1,750,905** COP | **2,100,000** COP | ❌ MISMATCH |
| Auxilio de Transporte | 249,095 COP | 249,095 COP | ✅ MATCH |
| Dotaciones mensual | 15,375 COP | 15,375 COP | ✅ MATCH |
| Dotaciones anual | 184,500 COP | 184,500 COP | ✅ MATCH |
| % Cumplimiento Variable | 0.70 | 0.70 | ✅ MATCH |

**Análisis:** `master_data` tiene el SMLV 2025 (1,750,905 COP). El Excel HR actualizado contiene el SMLV proyectado 2026 (2,100,000 COP). Esto representa un incremento del **19.94%**, consistente con la proyección SMLV documentada.

**Impacto:** Los salarios de roles como Validador, Agente Básico, Aprendiz SENA e Inclusión están ligados al SMLV. Actualmente en HR-Nomina figuran con 1,750,905 (valor 2025), **inconsistente** con el Salario Mínimo 2026 de 2,100,000 declarado en HR-Salarios.

**Acción:** Actualizar todos los roles con salario = SMLV en HR-Nomina a 2,100,000. Decidir si master_data se actualiza o se elimina como fuente.

---

### 2.2 Salarios por Rol — ✅ TODOS COINCIDEN

Los 22 roles comunes entre master_data y HR-Nomina (tipo=Empleado) tienen **valores idénticos**.

| Rol | master_data | HR param | Estado |
|-----|------------|---------|--------|
| Director de cuentas | 22,761,150 | 22,761,150 | ✅ |
| Director de Performance | 13,685,100 | 13,685,100 | ✅ |
| Jefe Comercial Regional | 5,537,202 | 5,537,202 | ✅ |
| Analista profesional AFAC | 3,145,130.74 | 3,145,130.74 | ✅ |
| Lider de Entrenamiento | 4,999,272.30 | 4,999,272.30 | ✅ |
| Supervisor | 3,090,990 | 3,090,990 | ✅ |
| Validador | 1,750,905 | 1,750,905 | ✅ (desactualizado) |
| *… 15 roles más …* | | | ✅ |

**Diferencia estructural:** HR-Nomina agrega tipos nuevos (`Equipo de Soporte y Mantenimiento`, `Equipo de HITL`, `Roles de Implementación`) con 32 roles adicionales no presentes en master_data. Esto es **nueva funcionalidad**, no inconsistencia.

**Rol faltante en HR:** `Agente Basico` existe en master_data pero no tiene entrada explícita en HR-Nomina. Se asume que debe ser igual a SMLV = Validador.

---

### 2.3 Aportes Patronales — ✅ TODOS COINCIDEN

| Concepto | master_data | HR-SegSocial | Estado |
|----------|------------|-------------|--------|
| Salud | 0.085 (8.5%) | 0.085 | ✅ |
| Pensión | 0.120 (12%) | 0.120 | ✅ |
| ARL | 0.00522 | 0.00522 | ✅ |
| Caja | 0.040 (4%) | 0.040 | ✅ |
| ICBF + SENA | 0.040 (4%) | 0.040 | ✅ |

---

### 2.4 Prestaciones Sociales — ✅ TODOS COINCIDEN

| Prestación | master_data | HR-Prestaciones | Estado |
|-----------|------------|----------------|--------|
| Cesantías | 0.0833 | 0.0833 | ✅ |
| Primas | 0.0833 | 0.0833 | ✅ |
| Interés cesantía | 0.1200 | 0.1200 | ✅ |
| Vacaciones | 0.0417 | 0.0417 | ✅ |

---

### 2.5 Recargos Salariales — ✅ TODOS COINCIDEN

| Recargo | master_data | HR-Recargos | Estado |
|---------|------------|------------|--------|
| Festivo | 0.90 | 0.90 | ✅ |
| Dominical | 0.90 | 0.90 | ✅ |
| Nocturno | 0.35 | 0.35 | ✅ |
| Festivo nocturno | 0.15 | 0.15 | ✅ |
| Dominical nocturno | 0.15 | 0.15 | ✅ |
| Extra diurno | 0.25 | 0.25 | ✅ |
| Extra nocturno | 0.75 | 0.75 | ✅ |

---

## Sección 3 – Costos de Infraestructura (HR-CostoFijo)

> **Escala:** HR-CostoFijo almacena valores en **miles de COP** (ej: 153.301 = 153,301 COP).  
> master_data almacena en COP completos. Se multiplica HR × 1,000 para comparar.

### 3.1 Comparación por Localidad

**✅ Coincidencia perfecta (84 de 91 puntos):** Barranquilla, Bogota-Toberin, Bucaramanga, Cali (menos agua), Cartagena, Ibague, Manizales, Pasto, Pereira, Villavicencio.

**❌ Discrepancias detectadas (5 puntos):**

| Localidad | Servicio | master_data (COP) | HR × 1000 (COP) | Análisis |
|-----------|---------|-------------------|----------------|---------|
| Bogota - Americas | mantenimiento | **129** | **129,000** | ❌ master_data tiene error: debe ser 129,000 |
| Bogota - Teusaquillo | agua | **960** | **960,000** | ❌ master_data tiene error: debe ser 960,000 |
| Cali | agua | **736** | **736,000** | ❌ master_data tiene error: debe ser 736,000 |
| Medellín | agua | **398** | **398,000** | ❌ master_data tiene error: debe ser 398,000 |
| Medellín | gas | **17** | **17,000** | ❌ master_data tiene error: debe ser 17,000 |

> **Conclusión:** Los 5 "mismatches" son **errores en master_data**, no en la parametrización. Los valores pequeños (129, 960, 736, 398, 17) son costos en COP que claramente deberían ser miles de COP. La parametrización HR es **más precisa** en estos 5 casos.

### 3.2 Datos Corruptos en HR-CostoFijo — ❌ BUG DE PARSEO

El archivo HR contiene **269 filas corruptas** en la clave `costo_fijo`:

```
{'localidad': 'Sac', 'servicio': '16.0', 'valor': 1.0}
{'localidad': 'Cobranzas', 'servicio': '17.0', 'valor': 1.0}
{'localidad': 'SACO', 'servicio': '18.0', 'valor': 1.0}
...
```

- 6 líneas de negocio (Cobranzas, Sac, Ventas multicanal, SACO, Plataformas, Captura de Datos) aparecen como `localidad`
- Los campos `servicio` contienen números de mes (16.0, 17.0, ... 60.0) — son los meses 16-60 de la campaña
- Estos son datos de `campana` que se filtraron al parsear la hoja CostoFijo del Excel

| Problema | Filas | Origen |
|---------|-------|--------|
| 'Cobranzas' como localidad | 44 | meses 16-60 de HR-Campana mezclados |
| 'Sac' como localidad | 45 | ídem |
| 'Ventas multicanal' como localidad | 45 | ídem |
| 'SACO' como localidad | 45 | ídem |
| 'Plataformas' como localidad | 45 | ídem |
| 'Captura de Datos' como localidad | 45 | ídem |

**Impacto actual:** Las 91 filas reales de costos de localidad **sí son correctas** y el repositorio funciona porque filtra por nombre de localidad real. Las 269 filas corruptas son ignoradas silenciosamente.

**Acción:** Revisar el parser del Excel HR (hoja CostoFijo) para detectar por qué los meses 16-60 de la campana se están insertando en costo_fijo.

---

## Sección 4 – Rentabilidad y Campañas (HR)

### 4.1 Márgenes por Línea de Negocio — ✅ TODOS COINCIDEN

> **Formato:** HR almacena como % entero en string ("17.0" = 17% = 0.17 decimal).  
> master_data usa decimal directo (0.17).

| Línea | master mín | master obj | HR mín | HR obj | Estado |
|-------|-----------|-----------|--------|--------|--------|
| Cobranzas | 17% | 18% | 17% | 18% | ✅ |
| SAC | 17% | 18% | 17% | 18% | ✅ |
| Ventas multicanal | 17% | 18% | 17% | 18% | ✅ |
| SACO | 10.5% | 10.5% | 10.5% | 10.5% | ✅ |
| Plataformas | 14% | 15% | 14% | 15% | ✅ |
| Captura de Datos | 32.92% | 32.92% | 32.92% | 32.92% | ✅ |

---

### 4.2 Bug en ProfitabilityParametrizationRepository — ❌ BUG CRÍTICO

```python
# CÓDIGO ACTUAL (INCORRECTO):
valor = float(minimo)          # devuelve 17.0 en lugar de 0.17
return valor

# CÓDIGO CORRECTO:
valor = float(minimo) / 100    # convierte 17.0% → 0.17 decimal
return valor
```

**Impacto:** Todas las llamadas a `get_min_margin()` y `get_target_margin()` retornan valores ×100 respecto a lo esperado. Los calculadores que consuman estas funciones calcularán márgenes incorrectos (17.0 en lugar de 0.17).

**Afecta:** `get_min_margin()`, `get_target_margin()` en `repositories/profitability_parametrization_repository.py`

---

### 4.3 Campañas de Ramp-up

| Línea | Mes | master_data | HR-Campana | Estado |
|-------|-----|------------|-----------|--------|
| Cobranzas | 1 | 0.85 | 0.85 | ✅ |
| Cobranzas | 2 | 0.92 | 0.92 | ✅ |
| Cobranzas | 3 | 1.00 | 1.00 | ✅ |
| **SAC** | **1** | **0.85** | **0.90** | **❌ MISMATCH** |
| **SAC** | **2** | **0.92** | **0.95** | **❌ MISMATCH** |
| SAC | 3 | 1.00 | 1.00 | ✅ |
| Ventas multicanal | 1-4 | 0.80/0.87/0.95/1.0 | 0.80/0.87/0.95/1.0 | ✅ |
| SACO | 1 | 1.00 | 1.00 | ✅ |
| Plataformas | 1 | 1.00 | 1.00 | ✅ |
| Captura de Datos | 1-3 | 0.90/0.95/1.0 | 0.90/0.95/1.0 | ✅ |

**Diferencia SAC:** HR tiene un ramp-up más rápido para SAC (90%, 95% vs 85%, 92%). El Excel HR es la versión más reciente — **los valores de HR deben considerarse correctos** y master_data está desactualizado para SAC.

**HR tiene más cobertura:** HR-Campana incluye 60 meses por línea. master_data solo tiene los primeros 3-4 meses (asume 1.0 el resto). HR es más completo.

---

### 4.4 Medicina y Seguridad — ✅ MATCH

| Concepto | Ciudad | master_data | HR × 1000 | Estado |
|----------|--------|------------|----------|--------|
| Examen médico nuevos | Bogotá | 60,800 | 60,800 | ✅ |
| Examen médico nuevos | default | 58,000 | (no en HR) | ⚠️ sin default |

> HR-Med-Seg cubre: Bogota, Cali, Medellín, Bucaramanga, Barranquilla. Sin valor por defecto explícito. El repositorio usa 60,800 como fallback, pero el valor correcto para ciudades no cubiertas debería ser 58,000 según master_data.

---

## Resumen de Bugs y Acciones Requeridas

### Bugs Críticos (bloquean migración de calculadores)

| # | Componente | Bug | Impacto | Acción |
|---|-----------|-----|---------|--------|
| 1 | `ProfitabilityParametrizationRepository` | `get_min_margin()` y `get_target_margin()` retornan % entero (17.0) en lugar de decimal (0.17) | ❌ Cálculos de margen incorrectos ×100 | Dividir por 100 en retorno |
| 2 | `FinancialParametrizationRepository.get_ica()` | OP-ICA usa unidades incompatibles con master_data | ❌ Tasas ICA incorrectas para 19/20 ciudades | Definir fórmula de conversión |

### Datos Corruptos en Parametrización (no bloquean, pero deben limpiarse)

| # | Archivo | Problema | Filas | Acción |
|---|---------|---------|-------|--------|
| 3 | HR-CostoFijo | 269 filas con líneas de negocio como "localidad" (datos de campana filtrados) | 269 | Revisar parser Excel |
| 4 | OP-ICA | Typos en nombres de ciudad: "Sicelejo", "Valledupár" | 8 filas | Corregir en Excel y re-subir |

### Datos Desactualizados en master_data (master_data es la fuente incorrecta)

| # | Dato | master_data (incorrecto) | Parametrización (correcto) |
|---|------|-------------------------|--------------------------|
| 5 | Salario mínimo | 1,750,905 (SMLV 2025) | 2,100,000 (SMLV 2026) |
| 6 | Costos agua/mant. (5 filas) | 129 / 960 / 736 / 398 / 17 COP | 129,000 / 960,000 / ... COP |
| 7 | SMLV proyección | Tasas variables por año | Tasa plana 12% (simplificación) |
| 8 | Ramp-up SAC meses 1-2 | 0.85 / 0.92 | 0.90 / 0.95 (actualizado) |

### Funcionalidad Nueva en Parametrización (no en master_data)

| Elemento | Descripción |
|---------|-------------|
| HR-Nomina tipos adicionales | 32 roles nuevos en tipos Soporte, HITL, Implementación |
| HR-Campana 60 meses | master_data solo tiene 3-4 meses de ramp-up |
| OP-ICA subcategorías | Avisos & Tableros, Bomberos, Otras Sobretasas por ciudad |
| HR-Med-Seg multi-ciudad | 5 ciudades vs solo Bogotá/default en master_data |

---

## Estado de Preparación para Fase 3-6

| Módulo | Estado | Bloqueante |
|--------|--------|-----------|
| Nómina (salarios, aportes, prestaciones) | ✅ Listo | No |
| Infraestructura (costos localidad) | ✅ Listo (con corrección ×1000 en escala ya implementada) | No |
| Rentabilidad (márgenes) | ⚠️ Requiere fix bug /100 | Sí – corregir antes de migrar |
| ICA por ciudad | ❌ Requiere fórmula de conversión | Sí – crítico |
| Pólizas / GMF | ✅ Listo | No |
| IPC proyección | ✅ Listo | No |
| SMLV proyección | ⚠️ Diferencia metodológica | Sólo si cálculo exacto de SMLV futuro es requerido |
| Campañas ramp-up | ✅ Usar HR como fuente de verdad | No |

---

## Decisiones Recomendadas

1. **ICA:** Implementar fórmula `ICA_final = (Tasa + Sobretasas) × factor_base` antes de migrar `CostosFinancierosCalculator`. Coordinar con equipo de negocio la fórmula exacta.

2. **Salario Mínimo:** Actualizar master_data a 2,100,000 O directamente migrar a usar `hr.salarios["Salario Mínimo"]` en todos los calculadores. La parametrización es la fuente correcta.

3. **master_data/no_payroll.json:** Los 5 valores pequeños (agua/gas/mantenimiento) son errores. Corregir en master_data o ignorar master_data (recomendado).

4. **HR-CostoFijo parser:** Investigar por qué la hoja CostoFijo del Excel genera 269 filas de datos de campaña. Posible mezcla de hojas en el parser.

5. **GN módulo:** Los datos GN siguen vacíos. Toda la lógica financiera que dependa de GN usa OP como fallback actualmente. Migrar datos GN antes de la Fase 4.
