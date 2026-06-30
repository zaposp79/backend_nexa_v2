# Layout de la hoja "Inputs de Nomina" — Excel V2-7

**Origen**: WAVE 4 Bug #5 — la sección "Empleado" usa columnas distintas a las
otras 3 secciones. Documentado formalmente en WAVE 5.

## 1. Estructura general

La hoja "Inputs de Nomina" del Excel `Nexa - Pricing - Simulador - V2-7.xlsx`
no es una tabla única: contiene **4 secciones independientes**, cada una con
su propia fila de encabezado y su propio set de columnas.

| # | Sección                              | Fila encabezado | Filas datos | Cantidad de roles |
|---|--------------------------------------|-----------------|--------------|-------------------|
| 1 | Empleado                             | Row 15          | R16–R40      | 25                |
| 2 | Equipo de Soporte y Mantenimiento    | Row 59          | R60–R71      | 12                |
| 3 | Equipo de HITL                        | Row 76          | R77–R82      | 6                 |
| 4 | Roles de Implementación              | Row 88          | R89–R102     | 14                |
|   | **Total**                             |                 |              | **57**            |

## 2. Columnas por sección

### 2.1 Sección "Empleado" (Row 15)

Contiene la columna `% Comisión recibido` (columna E) que **no aparece en las
otras secciones**:

| Col | Header (Row 15)                  |
|-----|----------------------------------|
| A   | (vacía / agrupador)              |
| B   | Rol                              |
| C   | Salario base                     |
| D   | Auxilios / bonificaciones        |
| E   | **% Comisión recibido**          |
| F   | Costo cargado empresa            |
| G+  | Otros campos auxiliares          |

### 2.2 Sección "Equipo de Soporte y Mantenimiento" (Row 59)

Layout simplificado, **sin columna de comisión**:

| Col | Header (Row 59) |
|-----|------------------|
| B   | Rol              |
| C   | Salario base     |
| D   | Costo empresa    |

### 2.3 Sección "Equipo de HITL" (Row 76)

Idéntico layout a (2.2), **sin comisión**.

### 2.4 Sección "Roles de Implementación" (Row 88)

Idéntico layout a (2.2), **sin comisión**.

## 3. Implicaciones para extracción

* El script `scripts/wave4_resync_nomina.py` itera **una sección a la vez**
  porque cada una requiere ofsets de fila distintos.
* La columna `comision_pct` en `hr.json[nomina]` solo se rellena para los
  25 roles de la sección "Empleado". Los demás 32 roles tienen
  `comision_pct = 0.0` por construcción.
* Cualquier futura sección que se añada al Excel debe actualizar el script.

## 4. Roles únicos por sección (V2-7)

### Empleado (25)
Director de cuentas, Director de Performance, Jefe Comercial Regional,
Analista profesional AFAC, Lider de Entrenamiento, Lider de Experiencia de
Cliente y Performance, Lider de Planeación Operativa, Jefe de Operación,
Works force, Reporting, GTR, Analista Prof. De Selección (Inicial),
Analista 1 de Reclutamiento (Inicial), Analista Prof. De Selección (Rotación),
Analista 1 de Reclutamiento (Rotación), Analista 2 Service Desk, Formadores,
Monitor de Calidad, Supervisor, Validador, Aprendiz SENA, Inclusión,
Especialista de Proyectos, Inbound 25, inboun Whatsapp.

### Equipo de Soporte y Mantenimiento (12)
Roles operativos de soporte tecnológico — sin comisión.

### Equipo de HITL (6)
Roles human-in-the-loop para IA — sin comisión.

### Roles de Implementación (14)
Roles temporales asignados a fases iniciales del contrato.

## 5. Backport WAVE 2

`hr.json[nomina]` también contiene la fila adicional `Agente Básico 1`
(backport de WAVE 2), que **no** existe en el Excel V2-7 pero se preserva por
compatibilidad con tests legacy. Total: 58 filas en JSON vs. 57 en Excel.
