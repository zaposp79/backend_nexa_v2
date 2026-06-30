# DOCUMENTO DE DISEÑO TÉCNICO
# Simulador de Precios — Proyecto NEXA

---

| | |
|---|---|
| **Proyecto** | Simulador de Precios Nexa |
| **Cliente** | NexaBPO |
| **Versión** | 1.0.0 |
| **Fecha** | 2026-05-22 |
| **Estado** | Para validación técnica con el cliente |
| **Clasificación** | Confidencial — Uso interno |
| **Elaborado por** | Equipo de Arquitectura — Accenture |
| **Revisores** | Arquitecto NEXA · Responsable de Infraestructura · Responsable de Seguridad |

---

**Propósito del documento**

Presentar la arquitectura funcional y técnica del Simulador de Precios Nexa para su validación con el cliente, incluyendo diseño de frontend, backend, seguridad, modelo de datos, persistencia y observabilidad sobre la plataforma Azure Cloud.

---

## Tabla de Contenidos

1. Objetivo del Documento
2. Alcance
3. Arquitectura de la Solución
4. Componentes Frontend
5. Componentes Backend
6. Integraciones y Servicios Azure
7. Seguridad
8. Modelo de Datos
9. Interfaces de Programación (APIs)
10. Observabilidad y Monitoreo
11. Rendimiento y Escalabilidad
12. DevOps y Despliegue
13. Supuestos y Restricciones
14. Riesgos
15. Criterios de Aceptación
16. Visión Imprimible
17. Motor de Datos
18. Anexos
19. Conclusiones

---

## 1. Objetivo del Documento

### 1.1 Alcance Funcional del Simulador

El Simulador de Precios Nexa permite a los equipos comerciales y técnicos de NexaBPO calcular, validar y proyectar el precio de venta de contratos de operaciones BPO (Business Process Outsourcing) y Contact Center. La plataforma reemplaza el proceso actual basado en hojas de cálculo Excel (versión V2-4), proporcionando una solución web centralizada, auditable y trazable.

El simulador procesa entradas estructuradas —perfiles de agentes, canales de atención, parámetros financieros, reglas de negocio— y produce resultados financieros detallados: estado de resultados mensual (P&G), economics del deal, visión de tarifas por canal, análisis de costo por servicio (Cost-to-Serve) y evaluación de riesgo.

### 1.2 Objetivo de Negocio

Proporcionar a NexaBPO una plataforma centralizada, segura y escalable que garantice los siguientes atributos de calidad:

| Atributo | Descripción |
|---|---|
| Reproducibilidad | Los mismos datos de entrada producen exactamente el mismo resultado en cualquier ejecución |
| Trazabilidad | Cada campo del resultado es rastreable hasta su fórmula de origen |
| Auditabilidad | Historial completo de simulaciones y cambios de parametrización |
| Colaboración | Soporte para múltiples usuarios simultáneos con roles diferenciados |
| Escalabilidad | Arquitectura serverless que se adapta a la demanda sin gestión manual de infraestructura |

### 1.3 Validaciones Esperadas por el Cliente

El presente documento está estructurado para respaldar las siguientes validaciones formales:

- Validación de arquitectura de solución
- Validación funcional del simulador
- Validación técnica de componentes
- Validación del modelo de seguridad
- Validación del esquema de observabilidad y monitoreo

---

## 2. Alcance

### 2.1 Funcionalidades Incluidas

| Funcionalidad | Descripción |
|---|---|
| Simulación de precios | Motor de cálculo que procesa nómina, OPEX, CAPEX, costos financieros, P&G, economics y visiones |
| Persistencia de simulaciones | Almacenamiento en Cosmos DB con historial completo por usuario y deal |
| Integración frontend/backend | Aplicación SPA React conectada a API REST en Azure Functions |
| Seguridad mediante Azure | Autenticación SSO con Azure AD / Entra ID, sin gestión propia de contraseñas |
| Observabilidad | Azure Monitor + Application Insights con correlación end-to-end |
| Parametrización versionada | Reglas de nómina (HR), generales (GN) y operativos (OP) con versionado por dominio |
| Evaluación de riesgo | Motor de scoring con 10 criterios agrupados en 2 categorías |
| Visiones de resultados | P&G mensual, tarifas por canal, waterfall de márgenes y Visión Imprimible consolidada |

### 2.2 Funcionalidades Fuera del Alcance

Las siguientes funcionalidades no forman parte de la Fase 1 del proyecto:

- Integraciones con sistemas ERP o CRM externos
- Facturación y cobro automatizado
- Reportería avanzada o Business Intelligence
- Administración de usuarios y contraseñas (delegada a Azure AD)
- Cálculos actuariales fuera del motor de pricing definido

### 2.3 Ambientes

| Ambiente | Propósito | Acceso |
|---|---|---|
| DEV | Desarrollo continuo y pruebas unitarias e integración del equipo técnico | Equipo de desarrollo |
| QA | Validación funcional con usuarios finales de NexaBPO y ejecución de suites automatizadas | Equipo QA + Dev + Usuarios de negocio |
| PROD | Operación productiva con acceso controlado y cambios auditados | Usuarios finales autorizados |

---

## 3. Arquitectura de la Solución

### 3.1 Diagrama General de Arquitectura

```
+-------------------------------------------------------------------------+
|                  AZURE CLOUD — NEXA PRICING SIMULATOR                   |
|                                                                         |
|  +------------+   +-----------------+   +----------+   +-------------+ |
|  | Azure DNS  |   | Azure Front Door|   | Azure WAF|   |    APIM     | |
|  | Resolución |-->| Entrada global  |-->| OWASP    |-->| Auth JWT    | |
|  | de dominio |   | SSL offloading  |   | DDoS     |   | Rate limit  | |
|  +------------+   | Balanceo        |   | Filtrado |   | Policies    | |
|                   +-----------------+   +----------+   +------+------+ |
|                                                                |        |
|                                                         +------v------+ |
|                                                         |   Azure     | |
|                              +--------------------------+ Functions   | |
|                              |                          | Python 3.12 | |
|                              |                          | FastAPI     | |
|                              |                          +------+------+ |
|                              |                                 |        |
|              +---------------+------+            +------------+------+ |
|              |   Azure Key Vault    |            |     Cosmos DB     | |
|              |   Secretos por       |            |     Core SQL API  | |
|              |   ambiente           |            |     Simulaciones  | |
|              +----------------------+            +-------------------+ |
|                                                                         |
|              +----------------------+                                   |
|              |  Azure Blob Storage  |                                   |
|              |  Logs · Trazas ·     |                                   |
|              |  Exportaciones       |                                   |
|              +----------------------+                                   |
|                                                                         |
|   +-------------------------------------------------------------------+ |
|   |         Azure Monitor + Application Insights                       | |
|   |         Logs · Metricas · Alertas · Dashboards · Trazas           | |
|   +-------------------------------------------------------------------+ |
|                                                                         |
|   +-------------------------------------------------------------------+ |
|   |  Azure DevOps  CI/CD  (Build -> QA -> Prod con slot swap)         | |
|   +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

### 3.2 Flujo de Petición End-to-End

Describe el recorrido completo de una solicitud desde que el usuario interactúa con el frontend hasta la respuesta final del backend y el almacenamiento de resultados.

**Objetivos del flujo:**

El análisis de este flujo permite explicar la interacción entre componentes, validar la arquitectura y las responsabilidades asignadas, e identificar con precisión los puntos de seguridad, monitoreo y persistencia.

---

#### 3.2.1 Paso 1 — Usuario accede al frontend

El usuario ingresa al simulador mediante HTTPS desde su navegador corporativo. La petición llega al DNS configurado, que resuelve el dominio público de la aplicación.

| Aspecto | Detalle |
|---|---|
| Protocolo | HTTPS con TLS 1.2 como mínimo |
| Resolución | DNS corporativo resuelve el dominio hacia Azure Front Door |
| Certificados | SSL/TLS gestionados automáticamente por Azure Front Door |

Puntos de validación: dominio oficial publicado, certificados vigentes y auto-renovables, redirección HTTP a HTTPS forzada.

---

#### 3.2.2 Paso 2 — Azure Front Door recibe la petición

Azure Front Door actúa como punto de entrada global de la solución.

| Responsabilidad | Descripción |
|---|---|
| Balanceo de carga | Distribuye el tráfico entre instancias de Azure Functions |
| Enrutamiento inteligente | Dirige al backend más cercano y disponible por ambiente |
| Optimización de tráfico | Caché de recursos estáticos del frontend, compresión gzip |
| Protección perimetral | Integrado con el WAF para inspección previa al enrutamiento |

Puntos de validación: reglas de enrutamiento por ambiente (dev/qa/prod), health probes activos hacia APIM, integración con WAF habilitada.

---

#### 3.2.3 Paso 3 — Azure Web Application Firewall (WAF)

El WAF inspecciona todo el tráfico entrante antes de que llegue a los servicios internos.

| Tipo de amenaza | Acción |
|---|---|
| Inyección SQL | Bloqueo automático mediante reglas OWASP CRS 3.2+ |
| Cross-Site Scripting (XSS) | Bloqueo automático |
| Tráfico malicioso y bots | Bloqueo por firma de amenaza conocida |
| Requests no autorizados | Bloqueo por restricción de IP o rate limit |

Puntos de validación: reglas OWASP en modo Prevention, rate limiting por IP habilitado, logs de seguridad integrados con Azure Monitor.

---

#### 3.2.4 Paso 4 — Frontend consume APIs mediante API Management

El frontend envía solicitudes REST al backend a través de API Management (APIM), que centraliza la exposición y el gobierno de las APIs.

| Responsabilidad | Descripción |
|---|---|
| Seguridad | Validación del JWT emitido por Azure AD en cada request |
| Versionamiento | Prefijo `/api/v1/` — cambios breaking incrementan versión major |
| Rate limiting | Control de requests por usuario por ventana de tiempo |
| Transformación | Normalización de headers y formato de respuestas de error |
| Trazabilidad | Correlation ID propagado en cada request hacia Functions |

Puntos de validación: catálogo de APIs publicado, políticas configuradas (`validate-jwt`, `rate-limit-by-key`, `cors`), timeouts definidos por tipo de operación.

---

#### 3.2.5 Paso 5 — API Management enruta hacia Azure Functions

APIM envía la petición autenticada a Azure Functions, que ejecuta la lógica de negocio del simulador de forma serverless.

| Responsabilidad | Descripción |
|---|---|
| Procesamiento del simulador | Motor de cálculo que genera todas las visiones del deal |
| Validación de datos | Triple capa: Pydantic, InputValidator, ContextBuilder |
| Integraciones | Acceso a Cosmos DB, Key Vault, Blob Storage y App Insights |
| Persistencia | Serialización del resultado completo a Cosmos DB |

Puntos de validación: triggers HTTP configurados, estrategia de escalamiento definida, manejo de errores con códigos HTTP estructurados, retries con backoff exponencial en operaciones de persistencia.

---

#### 3.2.6 Paso 6 — Azure Functions obtiene secretos desde Key Vault

Las Functions consultan Azure Key Vault para obtener secretos y configuraciones sensibles, usando Managed Identity sin credenciales en código.

| Secreto | Descripción |
|---|---|
| `COSMOS_DB_CONNECTION_STRING` | Cadena de conexión a Cosmos DB del ambiente |
| `BLOB_STORAGE_CONNECTION_STRING` | Acceso a Blob Storage para trazas y logs |
| `APP_INSIGHTS_CONNECTION_STRING` | Clave de instrumentación de Application Insights |
| `APIM_SUBSCRIPTION_KEY` | Clave de suscripción para llamadas autorizadas |

Puntos de validación: Managed Identity habilitada, rol `Key Vault Secrets User` asignado a la Function App, auditoría de accesos activa en Azure Monitor.

---

#### 3.2.7 Paso 7 — Persistencia en Cosmos DB

Los resultados del simulador y la información operacional se almacenan en Cosmos DB (NoSQL, Core SQL API).

| Datos almacenados | Colección | Clave de partición |
|---|---|---|
| Resultado completo de simulaciones | `simulations` | `result_id` |
| Historial de simulaciones por usuario | `simulations` | `user_id` |
| Parámetros y reglas de negocio versionadas | `pricingRules` | `domain` |
| Configuración dinámica del sistema | `configuration` | `environment` |

Puntos de validación: modelo de partición sin hot partitions, consistencia Session, throughput dimensionado, índices compuestos para consultas de historial.

---

#### 3.2.8 Paso 8 — Almacenamiento en Azure Blob Storage

Se almacenan archivos y artefactos generados durante la simulación o requeridos para auditoría.

| Contenedor | Contenido almacenado |
|---|---|
| `simulation-traces` | Logs detallados por simulación (nivel debug) |
| `exports` | Reportes generados por usuarios (PDF, Excel) |
| `temp-files` | Archivos temporales de procesamiento |
| `parametrization-backups` | Copias de respaldo de versiones de parametrización |

Puntos de validación: naming convention definido, accesos públicos deshabilitados, lifecycle policies configuradas (retención a confirmar con el cliente).

---

#### 3.2.9 Paso 9 — Observabilidad y monitoreo

Azure Monitor y Application Insights capturan telemetría en tiempo real de todos los componentes.

**Azure Monitor:** métricas de infraestructura, alertas operativas, dashboards por ambiente con indicadores de disponibilidad y rendimiento.

**Application Insights:** trazabilidad de requests end-to-end con `operation_id`, excepciones con stack trace completo, dependencias (Cosmos DB, Key Vault) trazadas automáticamente, Live Metrics Stream para monitoreo en tiempo real.

Puntos de validación: `operation_id` presente en todos los logs, alertas configuradas para errores críticos, dashboards operativos por ambiente.

---

#### 3.2.10 Paso 10 — Respuesta al frontend

Una vez completada la simulación y la persistencia, la respuesta recorre el camino inverso hacia el usuario.

| Paso | Componente | Acción |
|---|---|---|
| 10a | Azure Functions | Retorna el resultado serializado a APIM |
| 10b | APIM | Aplica políticas de respuesta y retorna al frontend |
| 10c | Frontend | Presenta resultados: P&G, tarifas, evaluación de riesgo |

El frontend presenta el resultado del cálculo, errores controlados con mensajes por tipo y mensajes de validación con campos resaltados. Puntos de validación: tiempo de respuesta p95 inferior a 3,000 ms, formato estándar de respuesta, manejo de errores HTTP diferenciado.

---

### 3.3 Diagrama Secuencial del Flujo Completo

```
Usuario  Frontend   DNS  Front Door   WAF    APIM   Functions  Key Vault  CosmosDB  Blob   Monitor
   |        |        |       |          |       |        |          |          |       |        |
   |--HTTPS->|        |       |          |       |        |          |          |       |        |
   |        |--req-->|       |          |       |        |          |          |       |        |
   |        |        |--DNS->|          |       |        |          |          |       |        |
   |        |        |       |--inspect->|       |        |          |          |       |        |
   |        |        |       |<--allow--|        |        |          |          |       |        |
   |        |        |       |-------------------->|       |          |          |       |        |
   |        |        |       |          |  JWT  ->|        |          |          |       |        |
   |        |        |       |          |  valid  |        |          |          |       |        |
   |        |        |       |          |       |-invoke->|           |          |       |        |
   |        |        |       |          |       |        |-secrets-->|           |       |        |
   |        |        |       |          |       |        |<--creds---|           |       |        |
   |        |        |       |          |       |        |-calcular  |           |       |        |
   |        |        |       |          |       |        |---------------------->|       |        |
   |        |        |       |          |       |        |-------------------------------->|      |
   |        |        |       |          |       |        |-telemetry------------------------------> |
   |        |        |       |          |       |<-result-|           |          |       |        |
   |        |        |       |<-response-----------|      |           |          |       |        |
   |<-result-|       |       |          |       |        |          |          |       |        |
```

---

### 3.4 Tabla Resumida del Flujo

| Paso | Componente | Accion | Responsabilidad |
|---|---|---|---|
| 1 | Usuario | Accede al simulador via HTTPS | Inicio de la interaccion |
| 2 | DNS | Resuelve el dominio publico | Enrutamiento de red |
| 3 | Azure Front Door | Recibe trafico, balancea y optimiza | Entrada global y SSL offloading |
| 4 | Azure WAF | Inspecciona y filtra trafico malicioso | Seguridad perimetral |
| 5 | API Management | Autentica JWT, aplica rate limiting y policies | Gobierno de APIs |
| 6 | Azure Functions | Ejecuta la logica del simulador | Procesamiento del negocio |
| 7 | Azure Key Vault | Entrega secretos mediante Managed Identity | Proteccion de credenciales |
| 8 | Cosmos DB | Almacena simulacion y parametrizacion | Persistencia operacional |
| 9 | Azure Blob Storage | Guarda trazas, logs extendidos y exportaciones | Persistencia de archivos |
| 10 | Azure Monitor + App Insights | Captura telemetria, metricas y logs | Observabilidad end-to-end |
| 11 | Frontend | Recibe resultado y lo presenta al usuario | Experiencia de usuario |

---

### 3.5 Consideraciones No Funcionales del Flujo

| Atributo | Estrategia aplicada | Metrica objetivo |
|---|---|---|
| Seguridad | HTTPS obligatorio, JWT en cada request, WAF OWASP, Managed Identity, sin secretos en codigo | Cero credenciales expuestas — 100% requests autenticados |
| Escalabilidad | Azure Functions serverless con escalado automatico, Cosmos DB con throughput auto-scale | 20 o mas usuarios concurrentes sin degradacion |
| Disponibilidad | Front Door con health probes, deployment slots para zero-downtime | 99.9% o superior mensual en produccion |
| Trazabilidad | `operation_id` propagado en todos los componentes, logs estructurados | 100% requests correlacionados end-to-end |
| Latencia | Pre-warming en plan Premium, cache de parametrizacion en memoria | p95 inferior a 3,000 ms para simulacion completa |
| Recuperacion ante fallos | Retry con backoff exponencial, deployment slot swap reversible, PITR en Cosmos DB | RTO inferior a 4 horas, RPO inferior a 1 hora |

---

### 3.6 Servicios Azure Involucrados

| Servicio | Rol en la solucion |
|---|---|
| Azure DNS | Resolucion del dominio publico del simulador |
| Azure Front Door | Punto de entrada global, balanceo, SSL offloading |
| Azure WAF | Proteccion OWASP, filtrado de trafico malicioso |
| API Management (APIM) | Publicacion segura de APIs, autenticacion JWT, rate limiting |
| Azure Functions | Backend serverless con motor de calculo de precios |
| Azure Key Vault | Almacenamiento seguro de secretos, connection strings y claves |
| Cosmos DB (Core SQL) | Persistencia NoSQL de simulaciones y parametrizacion |
| Azure Blob Storage | Logs extendidos, trazas de ejecucion, archivos de exportacion |
| Azure Monitor | Metricas, dashboards operativos, alertas |
| Application Insights | Telemetria detallada, correlacion de dependencias, excepciones |

---

## 4. Componentes Frontend

### 4.1 Framework y Caracteristicas Tecnicas

El frontend esta construido con React 18 y Vite como build tool, con arquitectura SPA (Single Page Application). Las principales caracteristicas tecnicas son:

- Componentizacion reutilizable para formularios, tablas de resultados y graficos de P&G
- Manejo de estado mediante React Context y hooks para sesion de usuario, simulacion activa y resultados
- Configuracion por ambiente mediante variables de entorno (`.env.dev`, `.env.qa`, `.env.prod`)
- Autenticacion implementada con Microsoft MSAL (Microsoft Authentication Library)
- Cliente HTTP centralizado con interceptores para adjuntar JWT y manejar errores 401 y 403

### 4.2 Flujo de Navegacion

| Paso | Pantalla | Descripcion |
|---|---|---|
| 1 | Login | El usuario accede al portal — redirección transparente a Azure AD SSO |
| 2 | Autenticacion | Azure AD emite JWT, almacenado en sessionStorage sin cookies persistentes |
| 3 | Carga inicial | GET /api/catalogs obtiene catalogos de parametros vigentes |
| 4 | Simulacion | Formulario estructurado: Panel de Control, Cadena A, Cadena B, Cadena C |
| 5 | Procesamiento | POST /api/v1/simulation/calculate ejecuta el motor de calculo |
| 6 | Resultados | Pantalla con visiones: P&G, economics, tarifas por canal, Cost-to-Serve |
| 7 | Auditoria | El resultado queda almacenado en Cosmos DB y accesible desde el historial |

### 4.3 Pantallas Principales

| Pantalla | Descripcion |
|---|---|
| Login | Redireccion transparente a Azure AD SSO. Sin formulario de usuario ni contrasena en el simulador |
| Dashboard principal | Listado de simulaciones recientes, acceso rapido a nueva simulacion |
| Pantalla de simulacion | Formulario estructurado en 4 secciones: Panel de Control, Cadena A, Cadena B, Cadena C |
| Pantalla de resultados | Visualizacion tabular de P&G mensual, economics, tarifas y evaluacion de riesgo |
| Manejo de errores | Pantalla de error con codigo, mensaje amigable y opcion de reintento |
| Sesion expirada | Aviso de expiracion del token JWT con boton de re-autenticacion automatica |

---

## 5. Componentes Backend

### 5.1 Azure Functions

Las Azure Functions contienen la logica de negocio principal del simulador, implementadas en Python 3.12 con el framework FastAPI.

**Responsabilidades:**

| Responsabilidad | Descripcion |
|---|---|
| Procesamiento del simulador | Motor de calculo que genera todas las visiones del deal |
| Validaciones funcionales | Triple capa: Pydantic, InputValidator, ContextBuilder |
| Orquestacion | PricingEngine orquesta calculadoras en orden deterministico |
| Persistencia de resultados | Serializacion a Cosmos DB mediante PricingSerializer |
| Auditoria | Logs estructurados con correlation ID por simulacion |
| Manejo de errores | Excepciones tipadas con respuestas HTTP estandarizadas |

**Caracteristicas tecnicas:**

Arquitectura serverless en Azure Functions con HTTP trigger por endpoint. Escalamiento automatico desde cero instancias hasta N segun la demanda (plan Consumption o Premium). Managed Identity habilitada para acceso a Key Vault y Cosmos DB sin credenciales hardcodeadas. Application Insights SDK integrado con trazas por correlation ID. Configuracion desacoplada: todos los secretos en Key Vault, todos los parametros en `storage/parametrization/`.

### 5.2 API Management (APIM)

APIM expone las Azure Functions de manera segura con las siguientes responsabilidades:

| Capacidad | Descripcion |
|---|---|
| Autenticacion JWT | Validacion del token emitido por Azure AD en cada request |
| Rate limiting | Maximo de requests por usuario por minuto, configurable por ambiente |
| Politicas CORS | Lista blanca de dominios autorizados del simulador (dev/qa/prod) |
| Subscription Keys | Capa adicional de control de acceso por aplicacion cliente |
| Logging | Todos los requests y responses registrados en Application Insights |
| Versionamiento | Prefijo /api/v1/ — cambios breaking requieren nueva version major |

---

## 6. Integraciones y Servicios Azure

### 6.1 Mapa de Dependencias

| Servicio | Depende de | Proposito |
|---|---|---|
| Front Door | DNS, APIM, WAF | Entrada global, balanceo, SSL |
| APIM | Functions, Key Vault, Azure AD | Exposicion segura de APIs |
| Functions | Cosmos DB, Blob, Key Vault | Logica de negocio y motor de calculo |
| Cosmos DB | IAM, Networking | Persistencia de simulaciones |
| Key Vault | Managed Identity | Gestion centralizada de secretos |
| Application Insights | Azure Functions | Telemetria y trazabilidad |
| Blob Storage | Azure Functions | Logs extendidos y exportaciones |

### 6.2 Descripcion de Servicios

**Azure DNS.** Responsable de la resolucion del dominio publico del simulador. Apunta mediante registro CNAME al endpoint de Azure Front Door.

**Azure Front Door.** Punto de entrada global con baja latencia y alta disponibilidad. Gestiona balanceo de carga, SSL offloading y enrutamiento inteligente. Health probes activos hacia APIM con cache de respuestas estaticas del frontend.

**API Management.** Publicacion y gobierno de las APIs del simulador. Responsable de autenticacion JWT, rate limiting, CORS, logging y transformacion de respuestas. Politicas configuradas: `validate-jwt`, `rate-limit-by-key`, `cors`, `log-to-eventhub`.

**Azure Functions.** Computo serverless con la logica del motor de calculo. Runtime Python 3.12, FastAPI. Plan de hosting Consumption o Premium (a confirmar). Managed Identity habilitada para acceso sin credenciales explicitas.

**Azure Key Vault.** Almacenamiento seguro de secretos, certificados y claves. Un Key Vault por ambiente (dev-kv, qa-kv, prod-kv). Acceso exclusivo mediante Managed Identity. Secretos: `COSMOS_DB_CONNECTION_STRING`, `BLOB_STORAGE_KEY`, `APIM_SUBSCRIPTION_KEY`, `APP_INSIGHTS_KEY`.

**Cosmos DB (Core SQL API).** Base de datos NoSQL para persistencia de simulaciones. Particion por `result_id`. Colecciones: `simulations`, `pricingRules`, `auditLogs`, `configuration`. Consistencia: Session.

**Azure Monitor y Application Insights.** Observabilidad completa. Application Insights SDK integrado en Azure Functions con auto-instrumentacion. Correlacion end-to-end con `operation_id` propagado desde APIM hasta Functions.

**Azure Blob Storage.** Almacenamiento de archivos no estructurados. Contenedores: `simulation-traces`, `exports`, `temp-files`, `parametrization-backups`. Retención a confirmar. Accesos publicos deshabilitados en todos los contenedores.

---

## 7. Seguridad

### 7.1 HTTPS y TLS

Toda comunicacion entre el cliente y los servicios Azure se realiza mediante HTTPS con TLS 1.2 como minimo. TLS 1.0 y 1.1 estan deshabilitados en Azure Front Door y en APIM.

### 7.2 Autenticacion — SSO con Azure AD / Entra ID

```
Usuario --> Navegador --> Redirect a Azure AD (Entra ID)
            Azure AD valida credenciales corporativas (SSO)
            Azure AD emite Authorization Code
            Frontend intercambia code por Access Token (JWT)
            Frontend envia JWT en cada request (Authorization: Bearer <token>)
            APIM valida JWT (firma, expiracion, claims de rol)
            Azure Functions recibe request autenticado
```

El proveedor de identidad es Azure AD / Microsoft Entra ID (a confirmar: ADFS adicional). El flujo implementado es Authorization Code Flow con PKCE. No existe gestion de contrasenas dentro del simulador — toda autenticacion esta delegada al IDP corporativo.

**Roles de aplicacion definidos en el App Registration de Entra ID:**

| Rol | Permisos |
|---|---|
| NEXA_COMMERCIAL | Crear y consultar simulaciones propias |
| NEXA_OPERATIONS | Consultar simulaciones de todo el equipo |
| NEXA_ADMIN | Administrar parametrizacion y ver todas las simulaciones |
| NEXA_AUDITOR | Solo lectura — acceso completo con fines de auditoria |

### 7.3 Web Application Firewall (WAF)

Azure WAF protege la solucion contra inyeccion SQL, Cross-Site Scripting (XSS), ataques OWASP Top 10, DDoS mediante proteccion integrada con Front Door, y trafico malicioso con IPs en lista negra.

### 7.4 Gestion de Secretos con Key Vault

Todas las credenciales y secretos se almacenan en Azure Key Vault, uno por ambiente. No existen credenciales en el codigo fuente — verificado mediante la herramienta bandit en el pipeline de CI. Las Azure Functions acceden a Key Vault mediante Managed Identity. Los pipelines de Azure DevOps acceden mediante Variable Groups enlazados al vault correspondiente.

### 7.5 Roles y Accesos (RBAC en Azure)

| Recurso | Rol asignado a Azure Functions |
|---|---|
| Cosmos DB | Cosmos DB Built-in Data Contributor |
| Key Vault | Key Vault Secrets User (lectura unicamente) |
| Blob Storage | Storage Blob Data Contributor |
| Application Insights | Monitoring Metrics Publisher |

### 7.6 Restriccion de APIs

| Mecanismo | Descripcion |
|---|---|
| JWT | Token emitido por Azure AD, validado por APIM en cada request |
| Subscription Key | Clave adicional por aplicacion cliente |
| Policies APIM | Validacion de claims, transformacion de headers |
| Rate limiting | Maximo de requests por IP o usuario por ventana de tiempo |

### 7.7 Politicas CORS

Unicamente los dominios del simulador correspondientes a los ambientes DEV, QA y PROD estan en la lista blanca. Los requests de origen no autorizado son rechazados con HTTP 403.

---

## 8. Modelo de Datos

### 8.1 Cosmos DB — Colecciones

| Coleccion | Descripcion | Clave de particion |
|---|---|---|
| `simulations` | Resultados completos de simulaciones | `result_id` |
| `pricingRules` | Parametrizacion versionada por dominio | `domain` |
| `auditLogs` | Registro de acciones sobre simulaciones | `user_id` |
| `configuration` | Configuracion general del sistema por ambiente | `environment` |

### 8.2 Estructura de Entrada — entry_data

La entrada del simulador corresponde a cuatro archivos JSON que mapean directamente a las secciones del formulario de la interfaz.

**Archivo 1: panel_control.json — Panel de Control General**

Contiene datos operativos del deal, polizas y parametros de volumetria:

```json
{
  "datos_operativos": {
    "servicio":              "SAC",
    "cliente":               "Bancamia",
    "tipo_cliente":          "Cliente Nuevo",
    "fecha_inicio":          "2026-01-01",
    "duracion_meses":        24,
    "sede":                  "Toberin",
    "tarifa_diaria_capacitacion": 20000,
    "cufin":                 8422,
    "horas_formacion_mes":   8,
    "pct_ausentismo":        0.07,
    "pct_rotacion":          0.9,
    "cons_costo_de_financiacion": true,
    "ciudades_recurso":      [{ "ciudad": "Bogota", "proporcion": 1.0 }],
    "tasa_ica":              0.02,
    "tasa_gmf":              0.004
  },
  "polizas": [
    {
      "nombre":           "Poliza de Cumplimiento",
      "activa":           true,
      "pct_poliza":       0.0062,
      "pct_atribuible":   0.2,
      "aplica_extension": false,
      "meses_extension":  36
    }
  ]
}
```

**Archivo 2: cadena_a.json — Condiciones Cadena A (Equipo Operativo)**

Contiene los perfiles de agentes, roles operativos y parametros de conversion FTE-interacciones:

```json
{
  "condiciones_cadena_a": {
    "Calculo_conversion_fte_interacciones": {
      "tmo": 0.0145,
      "tmo_promedio_seg": 522.2,
      "horas": 3600
    },
    "perfiles": [
      {
        "nombre":                  "Inbound 10",
        "modalidad":               "Inbound",
        "canal":                   "WhatsApp",
        "fte":                     10,
        "salario_base":            1560000,
        "roles_operativos": [
          { "rol": "Director de cuentas", "ratio": "750 Agentes" }
        ]
      }
    ]
  }
}
```

**Archivo 3: cadena_b.json — Condiciones Cadena B (OPEX y Plataformas)**

Contiene items de gasto operativo: plataformas, licencias y tecnologia, clasificados por canal y tipo:

```json
{
  "condiciones_cadena_b": {
    "opex": {
      "items": [
        {
          "rubro":       "Plataformas y licencias",
          "canal":       "WhatsApp",
          "producto":    "Token IA",
          "tipo_cobro":  "Unitario",
          "valor":       3075,
          "cantidad":    10,
          "valor_total": 30750
        }
      ]
    }
  }
}
```

**Archivo 4: cadena_c.json — Condiciones Cadena C (CAPEX e Inversiones)**

Contiene tarifas de proveedor por canal e inversiones de capital diferidas por meses:

```json
{
  "condiciones_cadena_c": {
    "tarifa_proveedor_canal": {
      "items": [
        { "canal": "WhatsApp", "tipo_de_cobro": "Unitario", "valor": 3075 }
      ]
    },
    "inversiones_capex": [
      {
        "descripcion":     "Infraestructura y cloud",
        "tipo_de_gasto":   "Fijo",
        "valor":           7000,
        "meses_a_diferir": 24,
        "valor_mensual":   710.71
      }
    ]
  }
}
```

### 8.3 Estructura de Persistencia — Coleccion simulations

Cada simulacion almacenada en Cosmos DB conserva el input completo y el resultado con todas las visiones:

```json
{
  "result_id":      "uuid-v4",
  "user_id":        "azure-ad-object-id",
  "calculated_at":  "2026-05-22T10:05:23Z",
  "status":         "COMPLETED",
  "input": {
    "panel_control": {},
    "cadena_a":      {},
    "cadena_b":      {},
    "cadena_c":      {}
  },
  "output": {
    "kpis":              {},
    "pyg_por_mes":       [],
    "waterfall_promedio":{},
    "vision_tarifas":    {},
    "vision_pyg":        {},
    "cost_to_serve":     {},
    "evaluacion_riesgo": {},
    "reglas_negocio":    []
  },
  "parametrization_snapshot": {
    "hr": "2026-01",
    "gn": "2026-01",
    "op": "2026-01"
  }
}
```

### 8.4 Versionamiento de Parametrizacion

Los dominios `hr`, `gn` y `op` se versionan en `storage/parametrization/`. Cada dominio contiene un archivo `versions.json` que indica la version activa y un archivo de datos por version:

```
storage/parametrization/
    hr/
        versions.json       -->  { "active_version": "2026-01" }
        2026-01.json        -->  parametros de nomina y RRHH
    gn/
        versions.json
        2026-01.json        -->  parametros generales y metricas
    op/
        versions.json
        2026-01.json        -->  parametros operativos y financieros
```

El dominio `business_rules` (politicas comerciales y criterios de riesgo) permanece fijo en codigo y no se versiona. Cada simulacion almacena el `parametrization_snapshot` de los dominios versionados al momento de la ejecucion, garantizando la reproducibilidad. Toda activacion de nueva version queda registrada en la coleccion `auditLogs`.

### 8.5 Blob Storage — Archivos Almacenados

| Contenedor | Contenido | Retencion |
|---|---|---|
| `simulation-traces` | Logs detallados por simulacion (debug completo) | Confirmar |
| `exports` | Archivos exportados por usuarios (Excel, PDF) | Confirmar |
| `temp-files` | Archivos temporales de procesamiento | Confirmar |
| `parametrization` | Copias de respaldo de parametrizacion | Confirmar |

---

## 9. Interfaces de Programacion (APIs)

### 9.1 Arquitectura API

Las APIs son expuestas mediante Azure API Management y consumidas desde el frontend React. Todas siguen el patron REST con JSON como formato de intercambio.

Rutas base por ambiente:

| Ambiente | URL base |
|---|---|
| DEV | `https://apim-nexa-dev.azure-api.net/api/v1/` |
| QA | `https://apim-nexa-qa.azure-api.net/api/v1/` |
| PROD | `https://api.nexa.com.co/api/v1/` |

### 9.2 Endpoints Principales

| Endpoint | Metodo | Vision o Componente | Respuesta |
|---|---|---|---|
| `/simulation/calculate` | POST | Ejecuta motor — genera todas las visiones | `{ result_id, calculated_at }` |
| `/simulation/{id}/results/kpis` | GET | Economics del deal | `KPIsDeal` |
| `/simulation/{id}/results/pyg` | GET | Vision P&G mensual | `PyGMensual[]` (N meses) |
| `/simulation/{id}/results/cost-to-serve` | GET | Vision Cost-to-Serve | `ResultadoCostToServe` |
| `/simulation/{id}/results/vision-tarifas` | GET | Vision Tarifas por canal | `ResultadoVisionTarifas` |
| `/catalogs` | GET | Catalogos de parametrizacion vigentes | `Catalogos` |
| `/history` | GET | Historial de simulaciones del usuario | `SimulationSummary[]` |
| `/parametrization/{domain}/versions` | GET | Versiones activas (hr, gn, op) | `VersionIndex` |
| `/parametrization/{domain}/activate` | POST | Activar version de dominio | `{ activated }` |

### 9.3 Ejemplo de Request — POST /simulation/calculate

```json
{
  "panel_de_control": {
    "meses_contrato":          12,
    "cadena_a_activa":         true,
    "cadena_b_activa":         true,
    "cadena_c_activa":         false,
    "contingencia_operativa":  0.03,
    "contingencia_comercial":  0.02,
    "markup":                  0.08,
    "descuento":               0.0
  },
  "condiciones_cadena_a": [
    {
      "canal":           "WhatsApp",
      "fte":             10,
      "salario_base":    1800000,
      "volumen_mensual": 25000
    }
  ],
  "condiciones_cadena_b": {
    "opex": { "items": [] }
  }
}
```

### 9.4 Ejemplo de Response — GET /simulation/{id}/results/kpis

```json
{
  "result_id":   "sim-abc123-2026",
  "kpis": {
    "costo_mensual_promedio":          125000000,
    "ingreso_mensual":                 150000000,
    "ingreso_neto_total":              1800000000,
    "costo_total_contrato":            1500000000,
    "contribucion_total":              300000000,
    "utilidad_neta_total":             300000000,
    "pct_utilidad_neta_total":         0.1667,
    "valor_total_deal":                1800000000,
    "cumple_margen_minimo":            true
  },
  "generated_at":              "2026-05-22T10:05:23Z",
  "parametrization_snapshot":  { "hr": "2026-01", "gn": "2026-01", "op": "2026-01" }
}
```

### 9.5 Codigos de Respuesta HTTP

| Codigo | Descripcion | Cuando ocurre |
|---|---|---|
| 200 OK | Operacion exitosa | Simulacion completada, consulta exitosa |
| 201 Created | Recurso creado | Simulacion persistida |
| 400 Bad Request | Error de validacion | Datos de entrada incompletos o invalidos |
| 401 Unauthorized | No autenticado | JWT ausente o expirado |
| 403 Forbidden | Sin permisos | Rol insuficiente para la operacion |
| 404 Not Found | Recurso no encontrado | result_id no existe |
| 422 Unprocessable Entity | Datos invalidos semanticamente | Valores fuera de rango permitido |
| 429 Too Many Requests | Rate limit excedido | Politica APIM activa |
| 500 Internal Server Error | Error del servidor | Error no controlado en el motor de calculo |

### 9.6 Seguridad de APIs

Las APIs requieren JWT Bearer emitido por Azure AD, validado por APIM mediante la politica `validate-jwt`. HTTPS es obligatorio — el trafico HTTP es rechazado por Front Door. Los claims de rol del JWT se validan contra los permisos de cada endpoint. El token generado en DEV no es valido en PROD por diferencia de audiencia.

---

## 10. Observabilidad y Monitoreo

### 10.1 Niveles de Log

La solucion genera logs estructurados en Application Insights con los siguientes niveles:

| Nivel | Cuando se registra |
|---|---|
| INFO | Inicio y fin de simulacion, parametrizacion cargada, request recibido |
| WARNING | Fallback de parametrizacion, valores fuera del rango esperado |
| ERROR | Error de validacion, excepcion en el motor, fallo de persistencia |
| CRITICAL | Fallo de conexion a Cosmos DB o Key Vault no disponible |

Cada log incluye: `correlation_id`, `user_id`, `simulation_id`, `timestamp`, `duration_ms` y la capa del motor que genero el evento.

### 10.2 Metricas Monitoreadas

| Metrica | Descripcion | Umbral de alerta |
|---|---|---|
| Tiempo de respuesta p95 | Percentil 95 de latencia del endpoint `/calculate` | Superior a 3,000 ms |
| Tasa de error HTTP 5xx | Porcentaje de errores del servidor | Superior al 1% en 5 minutos |
| Consumo de Functions | Invocaciones por minuto | Segun umbral configurable |
| Disponibilidad | Health check cada 5 minutos | Inferior al 99.9% en 24 horas |
| Uso de Cosmos DB (RU/s) | Request Units consumidas | Superior al 80% del provisionado |

### 10.3 Alertas Configuradas

Las alertas se envian mediante Microsoft Teams (canal Operaciones) y correo corporativo ante los siguientes eventos: errores HTTP 500 en produccion, tasa de errores 5xx superior al 1% sostenido durante 5 minutos, tiempo de respuesta p95 superior a 3 segundos, fallo en health check dos veces consecutivas.

### 10.4 Capacidades de Application Insights

| Capacidad | Uso en la solucion |
|---|---|
| Telemetria | Cada invocacion de Function registrada con duracion y resultado |
| Dependencias | Llamadas a Cosmos DB y Key Vault trazadas automaticamente |
| Performance | Live Metrics Stream para monitoreo en tiempo real |
| Exceptions | Stack traces completos de errores no capturados |
| Custom Events | Eventos de negocio: `simulation_completed`, `parametrization_activated` |

---

## 11. Rendimiento y Escalabilidad

### 11.1 Estrategia

| Aspecto | Estrategia aplicada |
|---|---|
| Arquitectura serverless | Azure Functions escala horizontalmente sin gestion manual |
| Escalabilidad automatica | Plan Consumption: hasta 200 instancias paralelas por Function App |
| Control de concurrencia | Configuracion `maxConcurrentRequests` en `host.json` |
| Reduccion de cold start | Pre-warming disponible en plan Premium |
| Cache de parametrizacion | Parametrizacion cargada en memoria durante la vida de la instancia |

### 11.2 Tiempos de Respuesta Esperados

| Operacion | Tiempo esperado (p95) | Observacion |
|---|---|---|
| POST /simulate/calculate — 12 meses, 1 canal | Inferior a 1,500 ms | Motor de calculo completo |
| POST /simulate/calculate — 12 meses, 3 canales | Inferior a 2,500 ms | Mayor computo en nomina y CTS |
| GET /results/kpis | Inferior a 300 ms | Lectura directa de Cosmos DB |
| GET /results/pyg | Inferior a 500 ms | Array de objetos desde Cosmos DB |
| GET /catalogs | Inferior a 200 ms | Parametros cacheados en memoria |

---

## 12. DevOps y Despliegue

### 12.1 Repositorios

| Repositorio | Plataforma | Contenido |
|---|---|---|
| `nexa-backend` | Azure DevOps | Python / FastAPI — Motor de calculo y APIs |
| `nexa-frontend` | Azure DevOps | React / Vite — Aplicacion web |
| `nexa-iac` | Azure DevOps | Bicep o Terraform — Infraestructura como codigo |

### 12.2 Estrategia Git (GitFlow)

```
main          -----------------------------------------------  (produccion)
               ^-- merge + tag desde release
release/x.y   -----------
               ^-- merge desde develop
develop       ----o----o----o----  (integracion continua)
               ^      ^
feature/xxx    o      |
feature/yyy          -o
hotfix/zzz    (desde main --> merge a main + develop)
```

La rama `main` contiene el codigo en produccion y solo recibe merge desde `release/*` o `hotfix/*`. La rama `develop` es la rama de integracion y se despliega automaticamente a DEV. Las ramas `feature/*` se fusionan a `develop` mediante Pull Request con revision obligatoria.

### 12.3 Pipeline de Construccion (Build Pipeline)

```yaml
stages:
  - stage: Validate
    jobs:
      - job: Lint
        steps:
          - script: flake8 . && black --check . && isort --check .
      - job: SecurityScan
        steps:
          - script: bandit -r . && safety check

  - stage: Test
    jobs:
      - job: UnitTests
        steps:
          - script: pytest tests/unit/ --cov=. --cov-report=xml
      - job: IntegrationTests
        steps:
          - script: pytest tests/integration/

  - stage: Build
    jobs:
      - job: BuildArtifact
        steps:
          - script: zip -r backend.zip . -x "*.git*" "tests/*"
```

Cobertura minima requerida: 80%.

### 12.4 Pipeline de Despliegue (Release Pipeline)

```yaml
stages:
  - stage: DeployDev
    condition: branch == 'develop'
    jobs:
      - deployment:
          steps:
            - task: AzureFunctionApp@2
              inputs: { appName: 'func-nexa-dev', package: 'backend.zip' }

  - stage: DeployQA
    dependsOn: DeployDev
    condition: succeeded()
    jobs:
      - deployment:
          steps:
            - task: AzureFunctionApp@2
              inputs: { appName: 'func-nexa-qa' }

  - stage: DeployProd
    dependsOn: DeployQA
    condition: succeeded()
    approval: required   # Aprobacion doble: Lider Tecnico + Responsable NEXA
    jobs:
      - deployment:
          steps:
            - task: AzureFunctionApp@2
              inputs: { appName: 'func-nexa-prod', slotName: 'staging' }
            - task: AzureAppServiceManage@0
              inputs: { action: 'Swap Slots', sourceSlot: 'staging' }
```

### 12.5 Infraestructura como Codigo

La infraestructura se gestiona con Bicep (recomendado para Azure nativo) o Terraform (si el cliente requiere portabilidad multi-cloud). El aprovisionamiento de todos los servicios Azure es automatizado por ambiente. Los cambios de infraestructura pasan por el mismo proceso de Pull Request que el codigo de aplicacion.

### 12.6 Pipeline de Despliegue — Resumen

| Paso | Ambiente | Aprobacion requerida |
|---|---|---|
| 1. Commit y Pull Request | — | Revision de codigo (minimo 1 revisor) |
| 2. Build, Validate y Test | — | Automatico mediante pipeline |
| 3. Despliegue DEV | DEV | Automatico |
| 4. Despliegue QA | QA | Automatico (tras DEV exitoso) |
| 5. Despliegue Produccion | PROD | Aprobacion doble mas ventana de mantenimiento |

---

## 13. Supuestos y Restricciones

### 13.1 Supuestos Tecnicos

| Codigo | Supuesto | Impacto si no se cumple |
|---|---|---|
| S01 | El cliente usa Azure AD / Microsoft Entra ID como IDP corporativo | Se requiere ajustar la configuracion del App Registration y el flujo de autenticacion |
| S02 | El plan de Azure Functions sera Premium en Produccion | Con plan Consumption, el cold start puede afectar la latencia en requests esporadicos |
| S03 | Cosmos DB se usara con la API Core SQL | Si el cliente prefiere MongoDB API, se requiere ajustar el driver de acceso a datos |
| S04 | Los servicios Azure estaran en la region East US 2 o Brazil South | Cambiar de region implica ajustar latencia y seleccion de pares de region para failover |
| S05 | El frontend se despliega como Static Web App o en Azure Blob con CDN | Si el cliente usa otro servidor web, la configuracion CORS y las variables de entorno difieren |
| S06 | Azure DevOps es la plataforma oficial de CI/CD | Si el cliente usa GitHub Enterprise o GitLab, los pipelines YAML deben adaptarse |
| S07 | Los agentes de build son Microsoft-hosted (ubuntu-latest) | Si el cliente requiere self-hosted agents, se debe provisionar y mantener la VM del agente |

### 13.2 Restricciones del Cliente

| Codigo | Restriccion | Consideracion |
|---|---|---|
| R01 | Sin gestion de usuarios ni contrasenas dentro del simulador | Toda autenticacion delegada a Azure AD. No existe pantalla de registro ni recuperacion de contrasena |
| R02 | Sin integraciones con ERP o CRM en Fase 1 | El simulador opera de manera autonoma |
| R03 | Datos de simulaciones son confidenciales | Acceso a Cosmos DB restringido por Managed Identity y RBAC |
| R04 | Cumplimiento con Ley 1581 de datos personales (Colombia) | Los datos de simulacion no contienen datos personales de consumidores finales |

### 13.3 Consideraciones de Costos Azure

Los principales componentes con costo variable son Azure Functions (por ejecucion en Consumption o costo fijo en Premium), Cosmos DB (por RU/s provisionadas y almacenamiento), Azure Front Door (por transferencia de datos y reglas), APIM (por nivel de servicio y numero de llamadas) y Application Insights (por volumen de datos ingeridos). Se recomienda revisar la estimacion de costos con el responsable de infraestructura antes de aprovisionar en produccion.

---

## 14. Riesgos

### 14.1 Riesgos Tecnicos

| Codigo | Riesgo | Probabilidad | Impacto | Mitigacion |
|---|---|---|---|---|
| RT01 | Cold start en Azure Functions afecta latencia | Media | Medio | Usar plan Premium en produccion; implementar keep-alive |
| RT02 | Proveedor SSO no confirmado (AD vs ADFS) retrasa autenticacion | Media | Alto | Confirmar en reunion tecnica antes de iniciar desarrollo de frontend |
| RT03 | Throttling de Cosmos DB en picos de uso | Baja | Alto | Dimensionar RU/s correctamente; implementar retry con backoff exponencial |
| RT04 | Expiracion de secretos en Key Vault interrumpe servicio | Baja | Critico | Configurar alertas de expiracion 30 dias antes; automatizar rotacion |
| RT05 | Acceso a Key Vault bloqueado por Conditional Access del cliente | Media | Critico | Verificar politicas del tenant antes del despliegue |
| RT06 | Dependencia del Excel V2-4 como referencia de verdad | Media | Medio | Motor de calculo validado contra Excel con delta inferior a 0.0001% |

### 14.2 Riesgos Operativos

| Codigo | Riesgo | Mitigacion |
|---|---|---|
| RO01 | Interrupcion de servicio Azure (outage regional) | Front Door con failover multi-region; RTO inferior a 4 horas |
| RO02 | Perdida de datos en Cosmos DB | Backups automaticos con PITR habilitado |
| RO03 | Deploy fallido en produccion | Deployment slots con swap reversible en menos de 5 minutos |
| RO04 | Fuga de secretos en repositorio | bandit y git-secrets en pipeline; Key Vault para todos los secretos |

---

## 15. Criterios de Aceptacion

### 15.1 Criterios Funcionales

| Criterio | Descripcion | Validacion |
|---|---|---|
| Simulacion completa | El usuario ingresa datos, ejecuta simulacion y visualiza todas las visiones | Prueba end-to-end en QA |
| Reproducibilidad | Los mismos inputs producen exactamente el mismo resultado | Test automatizado de regresion |
| Persistencia | La simulacion queda guardada y accesible desde el historial | Verificacion en Cosmos DB post-ejecucion |
| Integracion frontend/backend | El frontend consume correctamente todos los endpoints | Tests de integracion en QA |
| Parametrizacion activa | Los resultados reflejan la version activa de parametrizacion | Test con versiones distintas |

### 15.2 Criterios Tecnicos

| Criterio | Valor esperado | Medicion |
|---|---|---|
| Disponibilidad | 99.9% o superior mensual en produccion | Azure Monitor Availability |
| Latencia p95 | Inferior a 3,000 ms para simulacion completa (12 meses, 3 canales) | Application Insights |
| Cobertura de tests | 80% o superior del codigo backend | pytest-cov en pipeline CI |
| Escalabilidad | Minimo 20 usuarios concurrentes sin degradacion | Azure Load Testing |
| Zero-downtime deploy | Despliegue a produccion sin interrupcion de servicio | Deployment slot swap |

### 15.3 Criterios de Seguridad

| Criterio | Descripcion |
|---|---|
| Autenticacion obligatoria | Ningun endpoint accesible sin JWT valido de Azure AD |
| Gestion de secretos | Cero credenciales en codigo fuente, verificado con bandit |
| HTTPS obligatorio | Todas las comunicaciones cifradas con TLS 1.2 o superior |
| RBAC por rol | Cada rol accede unicamente a las operaciones permitidas |

### 15.4 Criterios de Performance

| Criterio | Valor |
|---|---|
| Tiempo de respuesta promedio | Inferior a 1,500 ms para simulacion de 12 meses, 1 canal |
| Concurrencia soportada | Minimo 20 usuarios simultaneos sin degradacion |
| Tiempo de cold start | Inferior a 3,000 ms, mitigado con plan Premium o keep-alive |

---

## 16. Vision Imprimible

### 16.1 Proposito

La Vision Imprimible es la representacion consolidada del deal que concentra, en una unica vista, todos los resultados relevantes para la toma de decision comercial. Corresponde directamente a la hoja "Vision Imprimible" del Excel V2-4 de referencia y es la vista principal que el equipo comercial presenta al cliente.

Principio fundamental: el frontend solo renderiza. El backend solo calcula. Ningun valor de la Vision Imprimible es recalculado en el lado del cliente.

### 16.2 Composicion de la Vision Imprimible

| Seccion | Clave en JSON | Fuente de datos |
|---|---|---|
| Ficha del Deal | `ficha_deal` | `panel_control.datos_operativos` |
| Economics | `kpis` | `KPIsDeal` calculado por el motor |
| Vision P&G mensual | `pyg_por_mes` y `vision_pyg` | `PyGCalculator` y `VisionPyGBuilder` |
| Waterfall Promedio | `waterfall_promedio` | `WaterfallPromedio` (promedio de meses activos) |
| Configuracion Comercial | `configuracion_comercial` | Canal principal de `vision_tarifas` |
| Reglas de Negocio | `reglas_negocio` | `business_rules` fijo en codigo |
| Evaluacion de Riesgo | `evaluacion_riesgo` | `RiesgoCalculator` (10 criterios, 2 categorias) |
| Cost-to-Serve | `cost_to_serve` | `CostToServeCalculator` |
| Vision Tarifas | `vision_tarifas` | `VisionTarifasCalculator` |

### 16.3 Flujo de Generacion

```
POST /simulation/calculate
         |
         +-- Motor de calculo ejecuta todas las capas
         +-- PricingSerializer consolida en JSON unico
         |
         +-- Response contiene:
             |-- ficha_deal            datos del panel de control
             |-- kpis                  economics del deal
             |-- pyg_por_mes           P&G mensual (N objetos)
             |-- waterfall_promedio    desglose promedio de margenes
             |-- vision_pyg            P&G estructurado para tabla
             |-- vision_tarifas        tarifas por canal y perfil
             |-- cost_to_serve         CTS cadena A, B y ponderado
             |-- evaluacion_riesgo     score, clasificacion, 10 criterios
             |-- reglas_negocio        politicas comerciales aplicadas
             +-- configuracion_comercial canal principal del deal
```

### 16.4 Waterfall Promedio

El waterfall es el grafico central de la Vision Imprimible. Muestra el desglose de margenes usando promedios de los meses activos del contrato:

```
Ingreso Bruto
    - Nomina Cadena A       (payroll_a)
    - No Payroll Cadena A   (no_payroll_a)
    - Costo Cadena B        (costo_b)
    - Costo Cadena C        (costo_c)
    - Costos Financieros    (ica + gmf + polizas + financiacion)
    + Contingencias         (cont_operativa + cont_comercial)
    + Markup y Descuento    (markup - descuento)
    = Ingreso Neto
    = Contribucion / Utilidad
```

### 16.5 Exportacion

La Vision Imprimible puede exportarse como PDF o Excel desde el frontend. El backend provee todos los datos necesarios mediante el `result_id` persistido en Cosmos DB. El archivo es generado por el frontend usando los datos ya calculados, sin recalcular ningun valor.

### 16.6 Relacion con las Demas Visiones

La Vision Imprimible consolida y presenta el resultado de todas las demas visiones del sistema:

| Vision consumida | Proposito dentro de la Vision Imprimible |
|---|---|
| Vision P&G | Estado de resultados mensual del deal |
| Vision Tarifas | Tarifas por canal y perfil de agente |
| Cost-to-Serve | Costo unitario de atencion por cadena |
| Waterfall Promedio | Grafico de desglose de margenes |
| Evaluacion de Riesgo | Score y clasificacion del deal |

---

## 17. Motor de Datos

### 17.1 Proposito

El Motor de Datos es la capa responsable de ingestar, transformar, validar y persistir los datos del simulador. Conecta la entrada estructurada (`entry_data`) con la parametrizacion versionada y con las visiones de salida, definiendo las reglas de transformacion que garantizan la reproducibilidad de los calculos financieros.

### 17.2 Estructura del Motor

```
entry_data (4 archivos JSON)
    |
    +-- [1] Ingestion
    |       JsonLoader valida estructura y tipos (Pydantic)
    |       InputValidator aplica reglas de negocio
    |
    +-- [2] Transformacion
    |       ContextBuilder convierte JSON plano en PricingRequest
    |       Mapeo: cadena_a.perfiles[]       --> List[PerfilCadenaA]
    |       Mapeo: cadena_b.opex.items[]     --> List[ItemCadenaB]
    |       Mapeo: cadena_c.inversiones[]    --> List[InversionCapex]
    |       Mapeo: panel_control             --> PanelDeControl
    |
    +-- [3] Enriquecimiento con parametrizacion
    |       ParametrizationProvider carga versiones activas:
    |       hr/2026-01.json   --> factores de nomina cargada
    |       gn/2026-01.json   --> parametros generales
    |       op/2026-01.json   --> tasas ICA, GMF, financieras
    |       business_rules (fijo) --> politicas comerciales, criterios riesgo
    |
    +-- [4] Calculo (PricingEngine, deterministico)
    |       Nomina --> No-Payroll --> Cadena B --> Cadena C -->
    |       Costos Totales --> Costos Financieros (intermensual) -->
    |       P&G mensual --> Economics --> Visiones
    |
    +-- [5] Validacion de salida
    |       PricingSerializer verifica integridad del PricingResult
    |
    +-- [6] Persistencia
            Cosmos DB: input + output + parametrization_snapshot
            Blob Storage: trazas de ejecucion
            Application Insights: telemetria (duracion, errores)
```

### 17.3 Flujo de Ingestion

| Paso | Componente | Entrada | Salida |
|---|---|---|---|
| 1 | `JsonLoader` | 4 archivos JSON (raw) | Diccionario validado con Pydantic |
| 2 | `InputValidator` | Diccionario validado | Diccionario con reglas de negocio aplicadas |
| 3 | `ContextBuilder` | Diccionario validado | `PricingRequest` (domain objects) |
| 4 | `ParametrizationProvider` | Dominio y version activa | Parametros inyectados en calculadoras |
| 5 | `PricingEngine` | `PricingRequest` mas parametros | `PricingResult` con todas las visiones |
| 6 | `PricingSerializer` | `PricingResult` | JSON para Cosmos DB y respuesta API |

### 17.4 Relacion con Excel V2-4

El Excel V2-4 es la fuente de verdad matematica del simulador. Cada formula del motor fue validada celda a celda:

| Concepto en Excel | Implementacion backend | Estado de validacion |
|---|---|---|
| Hoja "Nomina Loaded" | `NominaCalculator` | Delta inferior a 0.0001% vs Excel |
| Hoja "PyG" | `PyGCalculator` | Delta inferior a 0.0001% vs Excel |
| Hoja "Vision Tarifas" | `VisionTarifasCalculator` | Validado contra Excel VCS |
| Hoja "Vision Imprimible" | `PricingSerializer` mas visiones | 7 de 7 secciones con match exacto |
| Factor de Margenes | `utils.calcular_factor_margenes` | Formula: (1-cont_op) x (1-cont_com) x (1+markup) x (1-desc) |

### 17.5 Relacion con Parametrizacion

```
ParametrizationProvider (Facade)
    |
    +-- HR domain     --> salario minimo base, factores de prestaciones,
    |                     indexacion IPC, factor de nomina cargada
    |
    +-- GN domain     --> porcentajes minimos de margen,
    |                     tasas de referencia generales
    |
    +-- OP domain     --> tasa ICA, tasa GMF,
    |                     tasas de financiacion por periodo
    |
    +-- business_rules (fijo en codigo)
                      --> rangos de politicas comerciales
                          criterios y pesos de evaluacion de riesgo
```

### 17.6 Relacion con las Visiones

```
PricingEngine (calcula)
    |
    +-- Vision P&G           PyGMensual[] + VisionPyG
    +-- Vision Tarifas       ResultadoVisionTarifas (canales[], tarifa por FTE)
    +-- Vision Cost-to-Serve ResultadoCostToServe (CTS cadena A, B, ponderado)
    +-- Waterfall Promedio   WaterfallPromedio (promedios del contrato)
    +-- Evaluacion de Riesgo EvaluacionRiesgo (score 0-100, 10 criterios)
    +-- Vision Imprimible    Consolidacion de todas las anteriores
```

---

## 18. Anexos

### 18.1 Matriz de Endpoints y Visiones

| Endpoint | Metodo | Vision o Componente | Response Schema | Auth |
|---|---|---|---|---|
| `/simulation/calculate` | POST | Ejecuta motor y genera todas las visiones | `{ result_id, calculated_at }` | JWT + Key |
| `/simulation/{id}/results/kpis` | GET | Economics del deal | `KPIsDeal` | JWT + Key |
| `/simulation/{id}/results/pyg` | GET | Vision P&G | `PyGMensual[]` | JWT + Key |
| `/simulation/{id}/results/cost-to-serve` | GET | Vision Cost-to-Serve | `ResultadoCostToServe` | JWT + Key |
| `/simulation/{id}/results/vision-tarifas` | GET | Vision Tarifas | `ResultadoVisionTarifas` | JWT + Key |
| `/catalogs` | GET | Catalogos de parametrizacion | `Catalogos` | JWT + Key |
| `/history` | GET | Historial de simulaciones | `SimulationSummary[]` | JWT + Key |
| `/parametrization/{domain}/versions` | GET | Versiones activas (hr, gn, op) | `VersionIndex` | JWT (ADMIN) |
| `/parametrization/{domain}/activate` | POST | Activar version de dominio | `{ activated }` | JWT (ADMIN) |

### 18.2 Glosario

| Termino | Definicion |
|---|---|
| BPO | Business Process Outsourcing — tercerizacion de procesos de negocio |
| FTE | Full-Time Equivalent — unidad de medida de capacidad de personal |
| P&G | Estado de resultados (Perdidas y Ganancias) por periodo |
| CTS | Cost-to-Serve — costo de atender una unidad de servicio por cadena |
| ICA | Impuesto de Industria y Comercio (Colombia) |
| GMF | Gravamen a Movimientos Financieros (Colombia, 4x1000) |
| SMMLV | Salario Minimo Mensual Legal Vigente (Colombia) |
| SSO | Single Sign-On — autenticacion unica corporativa |
| WAF | Web Application Firewall — firewall para aplicaciones web |
| APIM | Azure API Management — servicio de gestion de APIs en Azure |
| Managed Identity | Identidad administrada de Azure — acceso entre servicios sin credenciales explicitas |
| entry_data | Estructura de entrada del simulador (4 archivos JSON: panel_control, cadena_a, cadena_b, cadena_c) |
| PricingResult | Objeto de dominio con todas las visiones y resultados de la simulacion |
| Vision | Representacion estructurada de un conjunto de resultados, consumida directamente por el frontend |
| Vision Imprimible | Vista consolidada del deal equivalente a la hoja Excel homonima |
| Waterfall | Grafico de desglose de margenes: ingresos hacia costos hacia contribucion |
| Cadena A | Equipo operativo directo (agentes, nomina, roles de apoyo) |
| Cadena B | Costos operativos indirectos (plataformas, licencias, OPEX) |
| Cadena C | Inversiones de capital y recursos transversales (CAPEX, RH especializado) |

### 18.3 Documentacion Complementaria

| Documento | Estado | Ubicacion |
|---|---|---|
| Diagrama de arquitectura v1.01 | Disponible | Proporcionado por cliente |
| Lineamientos de seguridad NEXA | Incorporado | Proporcionado por cliente |
| Solicitud de requerimientos tecnicos | Respondida | `docs/RESPUESTA_SOLICITUD_REQUERIMIENTOS.md` |
| Documentacion de trazabilidad (Fase 10) | Completa | `docs/audit/10_traceability_complete.md` |
| Swagger / OpenAPI | Pendiente publicacion | Generado automaticamente por FastAPI en `/docs` |
| Mockups de pantallas | Pendiente cliente | A proveer por equipo de diseno |
| Estimacion de costos Azure | Pendiente | A calcular con responsable de infraestructura |

---

## 19. Conclusiones

La arquitectura propuesta para el Simulador de Precios Nexa esta construida sobre Azure como plataforma principal, con servicios desacoplados, almacenamiento centralizado, procesamiento escalable y separacion clara entre parametrizacion, entrada de datos y visiones de resultados.

### 19.1 Principios Arquitectonicos Aplicados

| Principio | Implementacion |
|---|---|
| Servicios desacoplados | Azure Functions, Cosmos DB, Key Vault, Blob Storage y APIM operan de forma independiente |
| Almacenamiento centralizado | Cosmos DB como unica fuente de verdad de simulaciones; `storage/parametrization/` para parametrizacion versionada |
| Procesamiento escalable | Azure Functions escala horizontalmente sin gestion manual; el motor de calculo es stateless y paralelizable |
| Separacion de responsabilidades | entry_data (entrada) — PricingEngine (calculo) — Visiones (presentacion) — Cosmos DB (persistencia) |
| Trazabilidad end-to-end | `operation_id` propagado desde APIM hasta App Insights; snapshot de parametrizacion almacenado por simulacion |
| Seguridad por diseno | Managed Identity, Key Vault, WAF OWASP, JWT Azure AD, sin credenciales en codigo |

### 19.2 Visiones Alineadas con Excel V2-4

| Vision | Correspondencia en Excel | Estado |
|---|---|---|
| Vision P&G | Hoja "PyG" | Implementada y validada |
| Vision Tarifas | Hoja "Vision Tarifas" | Implementada y validada |
| Vision Cost-to-Serve | Hoja "CTS" | Implementada y validada |
| Waterfall Promedio | Grafico waterfall de "Vision Imprimible" | Implementado |
| Evaluacion de Riesgo | Hoja "Control de Riesgo" | Implementada y validada |
| Vision Imprimible | Hoja "Vision Imprimible" completa | Contrato documentado — 7 de 7 secciones |

### 19.3 Proximos Pasos para Validacion

1. Revision y aprobacion de este documento por el equipo tecnico de NEXA.
2. Confirmacion de los supuestos tecnicos, en especial el proveedor SSO y el plan de Azure Functions.
3. Reunion de kickoff tecnico para resolver los items pendientes de la solicitud de requerimientos.
4. Aprovisionamiento de los ambientes DEV y QA.
5. Validacion funcional de las visiones con usuarios de negocio en el ambiente QA.

---

*El presente documento queda sujeto a validacion funcional y tecnica por parte del cliente.*

*Elaborado por: Equipo de Arquitectura — Accenture*
*Version 1.0.0 — 2026-05-22*
*Clasificacion: Confidencial — Uso interno NexaBPO*
