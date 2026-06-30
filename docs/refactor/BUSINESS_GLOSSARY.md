# GLOSARIO FUNCIONAL — NEXA Simulator
**Fecha:** 2026-05-31 | **Versión:** 1.0 | **Referencia Excel:** V2-7

Este glosario mapea cada término técnico del backend a su significado de negocio,
su origen en Excel y la visión donde aparece.

---

## ABREVIATURAS ACEPTADAS (no expandir)

| Término técnico | Término de negocio | Definición | Excel | Módulo backend | Visión |
|---|---|---|---|---|---|
| `fte` | FTE (Full-Time Equivalent) | Equivalente de jornada completa; 1 FTE = 1 persona a tiempo completo. Fraccionario cuando el rol no ocupa jornada entera. | Panel Control → FTE | `PerfilCadenaA.fte` | CTS, Tarifas, Imprimible |
| `hitl` | HITL (Human-in-the-Loop) | Costo de personal humano que interviene en flujos automatizados de Cadena B/C para validación o escalamiento. | Cadena B/C → HITL | `ResultadoCadenaB.hitl`, `ResultadoCadenaC.hitl` | CTS → B, CTS → C |
| `opex` | OPEX (Operational Expenditure) | Gasto operativo recurrente mensual (tecnología, herramientas, licencias). Excluye inversiones de capital. | Cadenas B/C → OPEX Fijo | `opex_fijo`, `opex_ti` | CTS, Tarifas |
| `capex` | CAPEX (Capital Expenditure) | Inversión de capital amortizable en el período del contrato. Se distribuye mensualmente. | NoPayroll → CAPEX | `ResultadoNoPayroll.capex` | CTS → A, Tarifas |
| `ica` | ICA (Impuesto de Industria y Comercio) | Impuesto municipal sobre ingresos brutos. Tasa configurable por tasa_ica en Panel. | Costos Financieros → ICA | `CostosFinancierosMes.ica` | P&G → Costos Fin. |
| `gmf` | GMF (Gravamen a Movimientos Financieros) | Impuesto 4x1000 sobre transacciones financieras en Colombia. | Costos Financieros → GMF | `CostosFinancierosMes.gmf` | P&G → Costos Fin. |
| `cts` | CTS (Costo por Transacción / Cost-to-Serve) | Costo total del servicio por unidad de volumen (transacción, FTE o interacción digital). Métrica central de eficiencia operativa. | Vision Cost To Serve | `ResultadoCostToServe.cts_*` | Vision CTS |
| `tmo` | TMO (Tiempo Medio de Operación) | Average Handle Time en segundos por interacción. Determina capacidad del agente. | Hoja Maestra Escenarios | `PerfilCadenaA.tmo_segundos` | (interno) |
| `pct` | Porcentaje | Prefijo uniforme para cualquier campo de tipo porcentaje (0.0–1.0 salvo indicación). | Múltiples | Campo prefijado `pct_` | Múltiples |

---

## TERMINOLOGÍA DE NEGOCIO

### CADENAS (Estratos de servicio)

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| Cadena A | **Operación Humana** | Centro de contacto: agentes humanos con sus costos de nómina, infraestructura y equipamiento. | Panel Control → Cadena A |
| Cadena B | **Plataforma Digital** | Automatización y canales digitales: chatbots, APIs, plataformas de mensajería. Costos fijos + variables por volumen. | Panel Control → Cadena B |
| Cadena C | **IA / Integración Avanzada** | Servicios de inteligencia artificial, modelos de lenguaje, integraciones complejas. Incluye proveedores externos. | Panel Control → Cadena C |
| `es_soporte` | Rol de soporte | El perfil es staff de soporte (Supervisor, Formador, etc.), no agente que factura directamente. | (interno) |

### NÓMINA (Cadena A)

| Término técnico | Término de negocio | Definición | Excel (Nomina Loaded) |
|---|---|---|---|
| `salario_base` | Salario Base | Salario mensual bruto del rol sin cargas sociales. | Nomina Loaded → Salario Base |
| `salario_cargado` | Salario Cargado (Costo Empresa) | Salario base + aportes patronales + prestaciones. Costo real mensual para la empresa. | Nomina Loaded → Costo Empresa |
| `salario_fijo` | Nómina Fija | Componente fijo del costo de nómina mensual total del canal (fte × salario_cargado). | Nomina Loaded → col Salario Fijo |
| `comisiones` | Nómina Variable | Componente variable: comisiones sobre ventas/gestión del rol. | Nomina Loaded → col Comisiones |
| `capacitacion_inicial` ✨ | Capacitación Inicial | Costo de formación en el inicio del contrato. Se amortiza distribuyendo el gasto en la primera factura. Antes: `cap_inicial`. | Nomina Loaded → Capacitación Inicial |
| `capacitacion_rotacion` ✨ | Capacitación por Rotación | Costo recurrente de re-capacitación por rotación de personal. Se aplica mensualmente. Antes: `cap_rotacion`. | Nomina Loaded → Capacitación Rotación |
| `examenes` | Exámenes Médicos de Ingreso | Costo de exámenes médicos obligatorios al contratar nuevos agentes. | Nomina Loaded → Exámenes |
| `seguridad` / `estudios_seguridad` | Estudios de Seguridad | Costo de estudios de confiabilidad/seguridad al contratar. | Nomina Loaded → Seguridad |
| `crucero` | Tiempo Crucero (Idle Time) | Costo de tiempo no productivo facturado (agentes en espera de interacciones). Tarifa mensual fija por agente. | Panel Control → Tarifa Crucero |

### INFRAESTRUCTURA / NO-PAYROLL (Cadena A)

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `opex_ti` | OPEX TI por Estación | Licencias de software, conectividad y herramientas por puesto de trabajo. | NoPayroll → OPEX TI |
| `capex` | CAPEX Amortizado | Inversión inicial en equipos e infraestructura física por puesto, distribuida en meses del contrato. | NoPayroll → CAPEX |
| `costos_fijos` | Costos Fijos de Instalación | Arriendo, energía, vigilancia, aseo y otros costos fijos por puesto de trabajo. | NoPayroll → Costos Fijos |
| `arriendo_por_estacion` | Arriendo por Puesto | Parte proporcional del arriendo de instalaciones por puesto activo. | NoPayroll → Arriendo |

### CADENA B — PLATAFORMA DIGITAL

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `opex_fijo` | OPEX Fijo Plataforma | Costos fijos mensuales de la plataforma digital (licencias, hosting). | Cadena B → OPEX Fijo |
| `inversiones` | Inversiones Amortizadas | Inversiones en plataforma digital distribuidas en meses del contrato. | Cadena B → Inversiones |
| `soporte_mantenimiento` ✨ | Soporte y Mantenimiento | Costo mensual del equipo de S&M que opera y mantiene la plataforma digital. Antes: `sm` / `s_m`. | Cadena B → S&M |
| `costo_variable` | Costo Variable de Plataforma | Costo por transacción/interacción en la plataforma digital. | Cadena B → Variable |
| `escalamiento` | Escalamiento de Capacidad | Costo adicional por escalar capacidad en picos de demanda. | Cadena B → Escalamiento |
| `hitl` | HITL | Ver ABREVIATURAS. | Cadena B → HITL |

### CADENA C — IA / INTEGRACIÓN

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `tarifa_proveedor` | Tarifa Proveedor IA | Costo mensual del proveedor de IA/LLM (API calls, suscripciones). | Cadena C → Tarifa Proveedor |
| `opex_fijo_integ` | OPEX Fijo Integración | Costos fijos de las herramientas de integración y middleware. | Cadena C → OPEX Fijo |
| `opex_var_integ` | OPEX Variable Integración | Costo variable por volumen de llamadas/integraciones. | Cadena C → OPEX Variable |
| `equipo_integ` | Equipo de Integración | Costo mensual del equipo técnico que construye y opera las integraciones. | Cadena C → Equipo |
| `escalamiento` | Escalamiento IA | Costo adicional por escalar capacidad del modelo IA en picos. | Cadena C → Escalamiento |

### FINANCIEROS

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `financiacion` | Costo de Financiación | Costo del crédito para financiar el float del contrato (días de pago del cliente). | Costos Financieros → Financiación |
| `polizas` | Pólizas de Seguro | Costos de pólizas contractuales (responsabilidad civil, cumplimiento, etc.). | Costos Financieros → Pólizas |
| `comision_administracion` | Comisión de Administración | Fee de administración del contrato aplicado sobre ingreso bruto. | Vision Tarifas → Comisión Adm. |
| `comision_admin_cadena_a` ✨ | Comisión Adm. Cadena A | Porción de la comisión de administración atribuible a Cadena A para base de Vision Tarifas. Antes: `comadm_a`. | Vision Tarifas → Comisión Adm. A |
| `costo_financiero_vt_cadena_a` ✨ | Costo Financiero VT Cadena A | Costo financiero de Cadena A que entra como denominador en cálculo de tarifa (Vision Tarifas). Antes: `costo_fin_a_vt`. | Vision Tarifas → Financiero A |

### INGRESOS Y MÁRGENES

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `ingreso_bruto` | Ingreso Bruto | Facturación antes de descontar contingencias, markup/descuento e impuestos. | P&G → Ingreso Bruto |
| `ingreso_neto` | Ingreso Neto | Ingreso bruto menos descuentos, contingencias y markup aplicados. | P&G → Ingreso Neto |
| `contribucion` | Contribución | Ingreso neto − costo operativo total. Margen antes de costos financieros e imprevistos. | P&G → Contribución |
| `utilidad_neta` | Utilidad Neta | Contribución − costos financieros − imprevistos. Resultado final del deal. | P&G → Utilidad Neta |
| `margen` | Margen Objetivo | Porcentaje de margen mínimo requerido configurado en Panel de Control. | Panel Control → Margen |
| `markup` | Markup | Porcentaje adicional sobre costos para cubrir overhead corporativo. | Panel Control → Markup |
| `descuento` | Descuento por Volumen | Rebaja porcentual sobre ingreso por volumen comprometido. | Panel Control → Descuento |

### CONTINGENCIAS E IMPREVISTOS

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `op_cont` | Contingencia Operativa | Reserva porcentual sobre costos operativos para imprevistos operativos. | Panel Control → Cont. Op. |
| `com_cont` | Contingencia Comercial | Reserva porcentual sobre ingresos para imprevistos comerciales (riesgo de churn, volumen). | Panel Control → Cont. Com. |
| `imprevistos_ingreso` | Imprevistos | Reserva mensual calculada sobre el ingreso bruto. Protege margen ante eventos no planificados. | P&G → Imprevistos |

### FACTURACIÓN Y MODELOS DE COBRO

| Término técnico | Término de negocio | Definición | Excel (Vision Tarifas) |
|---|---|---|---|
| `facturacion` | Facturación Total | Monto total a facturar al cliente en el período (ingreso bruto + ajustes). | Vision Tarifas → Facturación |
| `modelo_cobro` | Modelo de Cobro | Estructura de facturación: Fijo FTE / Híbrido / Variable. | Vision Tarifas → Modelo |
| `tarifa_fijo_fte` | Tarifa por FTE | Precio unitario mensual por FTE en modelo Fijo o componente fijo de Híbrido. | Vision Tarifas → Tarifa FTE |
| `tarifa_variable` | Tarifa por Transacción | Precio por transacción en modelo Variable o componente variable de Híbrido. | Vision Tarifas → Tarifa Variable |
| `tarifa_hora_loggeada` | Tarifa Hora Loggeada | Equivalente de tarifa por hora en que el agente está en sistema (incluye espera). | Vision Tarifas → Tarifa/Hora Log |
| `tarifa_hora_pagada` | Tarifa Hora Pagada | Equivalente de tarifa por hora efectivamente remunerada al agente. | Vision Tarifas → Tarifa/Hora Pag |
| `pct_fijo` | Porcentaje Fijo | En modelo Híbrido: fracción del ingreso que se cobra como tarifa fija por FTE. | Vision Tarifas → % Fijo |

### RIESGO

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `evaluacion_riesgo` | Evaluación de Riesgo | Scoring multidimensional del deal (margen, volumen, cliente, plazo). | Riesgo |
| `score` (en riesgo) | Puntaje de Riesgo | Puntaje numérico 0–5 del nivel de riesgo del deal. | Riesgo → Score |
| `nivel_riesgo` | Nivel de Riesgo | Clasificación cualitativa: Bajo / Medio / Alto. | Riesgo → Nivel |

### ROLES Y CLASIFICACIÓN

| Término técnico | Término de negocio | Definición | Excel |
|---|---|---|---|
| `cargo_tipo` | Tipo de Cargo | Clasificación del rol según HR-clasificacion_cargos: AGENTE, OPERATIVO, ADMINISTRATIVO, VALIDADOR, ESPECIALISTA, APRENDIZ, INCLUSION, DESCONOCIDO. | HR-clasificacion_cargos |
| `tipo_carga` | Tipo de Carga Laboral | Categoría de vínculo laboral: EMPLEADO_ESTANDAR, APRENDIZ_SENA, SOPORTE_COMISIONABLE, etc. | HR-tipos_carga |
| `es_soporte` | Es Rol de Soporte | `True` si el perfil corresponde a staff de soporte (Supervisor, Formador, GTR, etc.), `False` si es agente base. | (interno context_builder) |

---

## TÉRMINOS PROHIBIDOS (nunca usar como nombres de campo)

| Prohibido | Usar en cambio |
|---|---|
| `data` | Nombre descriptivo del contenido |
| `info` | Campo específico (`ficha_comercial`, `resumen_ejecutivo`) |
| `result` | `resultado_nomina`, `resultado_cadena_b`, etc. |
| `value` | El campo que contiene el valor (`ingreso_bruto`, `costo_total`) |
| `item` | El concepto específico (`perfil`, `escenario`, `canal`) |
| `detail` | `detalle_canal`, `desglose_cadena_a`, etc. |

---

## CAMPOS RENOMBRADOS EN ESTA REFACTOR ✨

| Antes | Después | Motivo |
|---|---|---|
| `cap_inicial` | `capacitacion_inicial` | "cap" es ambiguo (capital, capacidad, capacitación) |
| `cap_rotacion` | `capacitacion_rotacion` | Mismo motivo |
| `ResultadoCadenaB.sm` | `ResultadoCadenaB.soporte_mantenimiento` | Sigla de un solo campo no documentada |
| `DesgloseCTSCadenaB.s_m` | `DesgloseCTSCadenaB.soporte_mantenimiento` | Unificar inconsistencia `sm` vs `s_m` |
| `comadm_a` | `comision_admin_cadena_a` | Abreviación críptica sin guía |
| `costo_fin_a_vt` | `costo_financiero_vt_cadena_a` | Tres abreviaciones concatenadas sin separación |
