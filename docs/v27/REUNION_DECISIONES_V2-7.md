# Reunión de Decisiones — NEXA Pricing V2-7

**Fecha sugerida:** semana del 8 de junio 2026  
**Duración estimada:** 60 minutos  
**Preparado por:** Equipo de ingeniería — auditoría de paridad Excel V2-7

---

## Resumen ejecutivo

El simulador NEXA Pricing tiene dos implementaciones paralelas: el Excel V2-7
(fuente de verdad del negocio) y el motor backend (fuente de verdad del sistema).
La auditoría técnica completada verificó campo por campo que ambos producen los
mismos resultados para la mayoría de los cálculos — y detectó cinco puntos donde
existen diferencias que **requieren que negocio decida cuál es la fuente correcta**,
no que ingeniería elija por su cuenta.

Las cinco decisiones son independientes entre sí y pueden tomarse en cualquier orden.
Tres de ellas tienen impacto directo en los números que ve un cliente en una cotización
(salario, pólizas, aprobaciones). Las otras dos afectan la arquitectura interna pero
no cambian lo que el usuario final ve hoy. Sin estas decisiones, el motor no puede
ser certificado como equivalente al Excel, y la Visión Imprimible (el resumen ejecutivo
del deal) puede mostrar cifras distintas a las del Excel para el mismo negocio.

Los próximos pasos dependen directamente de las opciones elegidas: si negocio elige
mantener la lógica actual del backend como canónica, el trabajo de cierre es
documentación y exposición de nuevos campos (2-3 semanas). Si elige alinear el
backend al Excel en todos los puntos, se requiere ajustar el cálculo de salarios y
revisar las reglas de aprobación (4-6 semanas adicionales).

---

## Decisión 1: Metodología de cálculo de salario

**Pregunta para negocio:** ¿El costo de un agente en el simulador debe calcularse
con la tabla salarial del sistema, o replicando exactamente la hoja de nómina del Excel?

**Contexto:** Para un agente Voz/Inbound con salario base de 1.750.905 COP, el Excel
calcula un costo mensual cargado de **3.288.748 COP/FTE** aplicando todas las
prestaciones de ley de forma detallada. El backend calcula **2.900.432 COP/FTE**
usando la tabla de nómina del sistema. La diferencia de 388.316 COP por FTE produce
una divergencia del **1,45% en el costo total de Cadena A** para el deal de referencia
(AMERICAS, 25 FTE Voz, 12 meses), equivalente a **15 M COP** en el período.

**Opciones:**
- **Opción A — Excel como canónico:** el backend replica la secuencia de cargas
  sociales del Excel fila por fila. Resultado: cotizaciones idénticas en ambos sistemas.
  Consecuencia: se requiere ajustar el calculador de nómina del backend (3-4 semanas).
- **Opción B — Backend como canónico:** el sistema usa su propia tabla salarial
  certificada. El Excel puede diferir porque está configurado para un deal específico.
  Consecuencia: cero cambios técnicos; la diferencia se documenta como variación de deal.

**Recomendación técnica:** Opción A. La divergencia detectada es sistemática (no un
caso aislado) y afecta directamente los márgenes cotizados. Usar el Excel como fuente
asegura que lo que el cliente aprueba en el Excel coincide con lo que el sistema factura.

**Impacto si no se decide:** El motor certifica costos de Cadena A con hasta 1,45%
de error respecto al Excel — en deals grandes esto puede ser material.

**Stakeholder sugerido:** Director de Pricing + Gerencia de Operaciones

**Referencias técnicas:** `docs/v27/GAP-SALARIO-CARGADO.md`

---

## Decisión 2: Exposición de pólizas por cadena en el contrato

**Pregunta para negocio:** ¿El sistema debe mostrar el costo de pólizas desagregado
por cadena (A, B, C) o es suficiente con el total del deal?

**Contexto:** En el Excel, la hoja Vision Tarifas muestra el costo de pólizas
específico del canal cotizado (por ejemplo, las pólizas de Cadena A para Voz/Inbound).
El backend calcula las pólizas correctamente pero las muestra como total del deal sin
separar por cadena. Cuando se intenta comparar el campo de pólizas entre Excel y
backend, los números no son directamente comparables porque representan universos
distintos: el Excel muestra solo las pólizas del canal del escenario seleccionado,
el backend muestra todas las pólizas del negocio agregadas.

**Opciones:**
- **Opción A — Mantener total deal:** el costo total de pólizas está correcto y se
  muestra agregado. La desagregación por cadena/canal se delega al frontend si se
  necesita. Cero cambios técnicos.
- **Opción B — Exponer pólizas por cadena:** agregar `polizas_cadena_a`,
  `polizas_cadena_b`, `polizas_cadena_c` al contrato del API. Permite comparación
  directa con el Excel. Consecuencia: 1-2 semanas de trabajo técnico.

**Recomendación técnica:** Opción A en el corto plazo. El total es correcto y el
impact comercial de la desagregación es bajo. Revisar en Fase 2 si el frontend
necesita mostrar el desglose por cadena en la Visión Imprimible.

**Impacto si no se decide:** El campo de pólizas por cadena no es comparable con
el Excel; permanece marcado como "no verificable" en la auditoría.

**Stakeholder sugerido:** Product Manager + Líder Técnico

**Referencias técnicas:** `docs/v27/VISION_TRACEABILITY_MATRIX.md` (GAP-ORACLE-C45)

---

## Decisión 3: Reglas de aprobación de deals

**Pregunta para negocio:** ¿Cuántos niveles de aprobación tiene un deal y cuáles
son los umbrales exactos?

**Contexto:** El Excel V2-7 define **tres niveles de aprobación** según la facturación
mensual proyectada y el valor total del deal:

| Nivel | Umbral Excel | Resultado actual del sistema |
|---|---|---|
| Gerencia Financiera | Facturación mensual ≥ 100 M COP | ❌ No modelado |
| Gerencia General | Facturación mensual ≥ 200 M COP | ❌ No modelado |
| Alta Dirección | Valor total deal ≥ **1.000 M COP fijo** | Parcial — el sistema usa 1.000 × SMMLV ≈ 1.423 M COP (umbral 42% más alto) |

El sistema actual solo tiene un indicador binario de aprobación usando un umbral
basado en el SMMLV que difiere del umbral fijo del Excel. Un deal entre 1.000 M y
1.423 M COP que **el Excel marca como "Requiere Alta Dirección"** puede pasar
**sin alerta** en el sistema actual.

**Opciones:**
- **Opción A — Alinear al Excel:** implementar los tres niveles con los umbrales
  literales (100 M, 200 M, 1.000 M COP fijo). Consecuencia: 1-2 semanas técnicas;
  garantiza que el sistema bloquea los mismos deals que el Excel.
- **Opción B — Mantener lógica actual:** el umbral SMMLV es una decisión de política
  diferente al Excel y puede ser intencional. Documentar la divergencia.
- **Opción C — Diseñar nuevos umbrales:** si ni el Excel ni el backend reflejan la
  política actual, definir los tres niveles correctos desde cero.

**Recomendación técnica:** Opción A o C. La divergencia del umbral de Alta Dirección
(423 M COP) es suficientemente grande para tener impacto real en deals medianos.
Necesitamos que negocio confirme si 1.000 M COP fijo es la política vigente.

**Impacto si no se decide:** Deals entre 1.000 M y 1.423 M COP pueden aprobarse
en el sistema sin escalar a Alta Dirección, contrario a lo que indica el Excel.

**Stakeholder sugerido:** Gerencia General + Director de Pricing

**Referencias técnicas:** `docs/v27/VISION_IMPRIMIBLE_AUDIT_V2-7.md` (GAP-IMP-04), `calculators/riesgo.py:213`

---

## Decisión 4: Comparativo de escenarios en la Visión Imprimible

**Pregunta para negocio:** ¿El resumen ejecutivo del deal (Visión Imprimible) debe
mostrar las tarifas de cada escenario alternativo, o solo el escenario seleccionado?

**Contexto:** El Excel V2-7 tiene una sección (§05, filas 74-78) que muestra una
tabla comparativa con hasta cinco escenarios de facturación, incluyendo la tarifa
fija y variable de cada uno, y cuál está seleccionado ("★ SELECCIONADO"). El backend
construye esa tabla pero **no la incluye en la respuesta del API** — solo la calcula
internamente. El frontend no puede renderizar la comparación de escenarios porque
los datos no llegan en el JSON.

**Opciones:**
- **Opción A — Exponer la tabla comparativa:** conectar la estructura ya calculada
  internamente al JSON de respuesta. Consecuencia: 1 semana técnica; el frontend puede
  renderizar la tabla de escenarios igual que el Excel.
- **Opción B — Mantener estado actual:** la tabla no se muestra en el API; el usuario
  ve solo el escenario seleccionado. Cero cambios técnicos.

**Recomendación técnica:** Opción A. La estructura ya existe en el backend; solo
falta "conectar el cable". Es el cambio de menor esfuerzo con mayor impacto visual
para equipos comerciales que hoy usan el Excel para comparar escenarios.

**Impacto si no se decide:** La Visión Imprimible del sistema muestra menos información
que el Excel para el mismo deal; los equipos comerciales seguirán usando el Excel.

**Stakeholder sugerido:** Product Manager + Equipo Comercial

**Referencias técnicas:** `docs/v27/GAP_REGISTRY_PRIORIZADO_V2-7.md` (GAP-IMP-01, GAP-IMP-11)

---

## Decisión 5: Base de costo de Cadena C (tecnología / automatización)

**Pregunta para negocio:** Para deals con automatización (Cadena C), ¿el ingreso
debe calcularse sobre el costo de infraestructura tecnológica del escenario
seleccionado, o sobre el costo operativo acumulado del contrato?

**Contexto:** En el Excel, la hoja de tarifas calcula el ingreso de Cadena C
usando una región de costos diferente a la que usa la hoja P&G para el mismo concepto.
Esta diferencia produce que el ingreso total mostrado en la Visión Imprimible
(Excel: 38.600 M COP) sea casi el doble del ingreso calculado por el motor backend
(≈ 21.000 M COP) para el mismo deal con automatización activa. Actualmente el 100%
de los deals en producción no tienen Cadena C activa, por lo que el impacto es cero
hoy. Cuando se active el primer deal con automatización, la divergencia será crítica.

**Opciones:**
- **Opción A — Excel como canónico:** el ingreso de Cadena C se calcula sobre la
  región de costos de la hoja Tarifas (escenario-específica). Requiere refactorizar
  el calculador de Vision Tarifas en backend (4-6 semanas, riesgo medio).
- **Opción B — Backend como canónico:** el ingreso se calcula sobre el costo
  operativo acumulado del P&G (deal-wide). El Excel puede estar sobreestimando por
  diseño del escenario de demostración V2-7.
- **Opción C — Auditar primero:** antes de decidir, auditar un deal real con
  Cadena C activa para confirmar cuál de los dos valores el negocio considera correcto.

**Recomendación técnica:** Opción C. La divergencia es del 46% — demasiado grande
para resolverla sin evidencia de un deal real. No existe ningún deal con Cadena C
activa en producción que permita verificar cuál es el comportamiento correcto.

**Impacto si no se decide:** Al activar el primer deal con automatización, el sistema
puede cotizar el doble o la mitad del precio correcto. Bloquea la comercialización
de deals de automatización.

**Stakeholder sugerido:** Director de Pricing + Gerencia de Tecnología/Automatización

**Referencias técnicas:** `docs/v27/GAP_REGISTRY_PRIORIZADO_V2-7.md` (GAP-TAR-08), `docs/v27/VISION_TARIFAS_AUDIT_V2-7.md`

---

*Documento generado desde evidencia de auditoría técnica. Cada afirmación numérica
está respaldada por extracción literal del Excel V2-7 y ejecución del motor backend
contra el mismo deal (AMERICAS / Captura de Datos, 12 meses).*
