# Respuesta — Solicitud de Requerimientos Técnicos e Infraestructura
## Proyecto NEXA Pricing Simulator

---

| Campo | Detalle |
|---|---|
| **Proyecto** | NEXA Pricing Simulator |
| **Cliente** | NexaBPO |
| **Documento origen** | Solicitud de Requerimientos Técnicos e Infraestructura |
| **Fecha de respuesta** | 2026-05-22 |
| **Estado** | Borrador — Pendiente validación en reunión técnica |
| **Elaborado por** | Equipo de Desarrollo Accenture |
| **Revisores** | Arquitecto NEXA · Responsable Infraestructura · Responsable Seguridad |

---

### Leyenda de estados

| Ícono | Estado | Descripción |
|---|---|---|
| ✅ | **Confirmado** | Definido y confirmado. No requiere acción adicional. |
| 🟡 | **Propuesto** | El equipo de desarrollo propone esta opción. Requiere validación del cliente en reunión técnica. |
| 🔴 | **Pendiente** | Requiere respuesta o acción del cliente. Bloqueante si no se resuelve antes del inicio. |
| ⚪ | **No aplica** | Fuera del alcance de este proyecto o fase. |

---

## 1. Microsoft Office 365

### 1.1 Cuentas y Acceso

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 1.1.1 | Cuentas corporativas para todos los integrantes del equipo | 🔴 **Pendiente** | El cliente debe proveer cuentas `@nexa.com.co` (o el dominio corporativo) para cada integrante. Indicar cuántos perfiles se requieren y proceso de solicitud. |
| 1.1.2 | Acceso a correo corporativo (Outlook) | 🔴 **Pendiente** | Incluido en la solicitud de cuentas (ítem anterior). |
| 1.1.3 | Microsoft Teams con audio, video y canales | 🔴 **Pendiente** | Solicitar habilitación de Teams con licencia mínima M365 Business Basic. Canales requeridos: **Desarrollo**, **Calidad**, **Operaciones**. |
| 1.1.4 | SharePoint con sitio del proyecto y permisos de escritura | 🔴 **Pendiente** | Sitio sugerido: `nexa-pricing-simulator`. El equipo requiere permisos de **Miembro** (lectura + escritura). |
| 1.1.5 | OneDrive corporativo | 🔴 **Pendiente** | Incluido con la cuenta M365. Confirmar si existe política de almacenamiento máximo por usuario. |
| 1.1.6 | Calendarios compartidos | 🔴 **Pendiente** | Solicitar calendario compartido del proyecto para hitos, sprints y ceremonias. |
| 1.1.7 | Grupos de trabajo por área (Desarrollo, Calidad, Operaciones) | 🔴 **Pendiente** | Crear grupos M365: `nexa-dev@`, `nexa-qa@`, `nexa-ops@` (o equivalentes en el dominio del cliente). |
| 1.1.8 | Microsoft Word, Excel y PowerPoint | 🔴 **Pendiente** | Confirmar que la licencia M365 asignada incluye aplicaciones de escritorio (Plan Business Standard o superior). |

### 1.2 Seguridad y Políticas

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 1.2.1 | VPN corporativa para acceder a recursos de NEXA | 🔴 **Pendiente** | Confirmar si los servicios Azure del proyecto están expuestos públicamente (vía APIM + Front Door) o requieren VPN para acceso interno. |
| 1.2.2 | Verificación en dos pasos (MFA) — método requerido | 🟡 **Propuesto** | Se propone **Microsoft Authenticator** (TOTP). Si el cliente requiere otro método (SMS, llave física), indicarlo. |
| 1.2.3 | Políticas de acceso condicional | 🔴 **Pendiente** | Confirmar si existen políticas de Conditional Access en el tenant que puedan bloquear cuentas de terceros (Accenture). Solicitar excepción si aplica. |
| 1.2.4 | Confirmación del directorio de identidades (Azure AD u otro) | 🟡 **Propuesto** | Se propone **Azure AD / Microsoft Entra ID** como directorio corporativo. Ver sección 4.4 (SSO). Confirmar en reunión técnica. |
| 1.2.5 | Proceso para solicitar accesos adicionales durante el proyecto | 🔴 **Pendiente** | Indicar: canal de solicitud (ticket ServiceNow / formulario / correo), responsable de aprobación y tiempo estimado de respuesta. |

---

## 2. Plataforma DevOps

> **Plataforma confirmada**: ✅ **Azure DevOps**

### 2.1 Repositorios

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 2.1.1 | Acceso al repositorio con permisos de lectura y escritura | 🔴 **Pendiente** | Solicitar acceso al proyecto Azure DevOps de NEXA. El equipo necesita rol **Contributor** en el repo del backend y frontend. |
| 2.1.2 | Estrategia de ramas | 🟡 **Propuesto** | Se propone **GitFlow adaptado**: `main` (producción), `develop` (integración), `feature/*`, `hotfix/*`, `release/*`. Confirmar con el cliente si ya existe una estrategia definida. |
| 2.1.3 | Políticas de Pull Request | 🟡 **Propuesto** | Se propone: mínimo **1 revisor**, build verde obligatorio, resolución de comentarios requerida. Confirmar política corporativa si existe. |
| 2.1.4 | Protección de ramas principales (`main`, `develop`, `release`) | 🟡 **Propuesto** | Habilitar Branch Policies en Azure DevOps: push directo bloqueado, PR obligatorio, firma de commits recomendada. |

### 2.2 Gestión de Trabajo

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 2.2.1 | Acceso al tablero de trabajo (Boards) | 🔴 **Pendiente** | Solicitar acceso a Azure Boards con rol **Contributor**. Confirmar si el proyecto ya tiene épicas o backlog inicializado. |
| 2.2.2 | Permiso para crear/editar/cerrar tareas, historias y errores | 🔴 **Pendiente** | Incluido con rol Contributor en Boards. Confirmar que el proceso de cierre de ítems en producción requiere aprobación del PO. |
| 2.2.3 | Acceso al backlog y épicas definidas | 🔴 **Pendiente** | Solicitar que el cliente comparta las épicas ya creadas (si las hay) o confirmar que el equipo puede crearlas. |

### 2.3 Integración y Entrega Continua (CI/CD)

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 2.3.1 | Acceso para crear/modificar pipelines | 🔴 **Pendiente** | Solicitar rol **Build Administrator** o equivalente en Azure Pipelines. |
| 2.3.2 | Acceso a variables y secretos en pipelines | 🟡 **Propuesto** | Los secretos deben estar en **Azure Key Vault** (uno por ambiente). Los pipelines los consumen vía Variable Groups enlazados a Key Vault. Confirmar que el cliente provee acceso al Key Vault de cada ambiente. |
| 2.3.3 | Conexiones de servicio con infraestructura Azure | 🔴 **Pendiente** | Crear **Service Connections** en Azure DevOps hacia las suscripciones de Dev, QA, UAT y Prod. Requiere rol **Contributor** en cada suscripción o Resource Group. |
| 2.3.4 | Agentes de construcción | 🟡 **Propuesto** | Se propone usar **Microsoft-hosted agents** (ubuntu-latest). Si el cliente requiere self-hosted agents por políticas de red, indicarlo. |
| 2.3.5 | Pipeline de liberación con aprobaciones por ambiente | 🟡 **Propuesto** | Diseñado: `Dev` (auto) → `QA` (auto) → `UAT` (aprobación manual) → `Prod` (aprobación doble + ventana de mantenimiento). Confirmar responsables de aprobación. |

### 2.4 Artefactos

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 2.4.1 | Repositorio de artefactos | 🟡 **Propuesto** | Se propone **Azure Artifacts** (feed privado dentro de Azure DevOps). Confirmar si el cliente prefiere otro repositorio (Nexus, Artifactory). |
| 2.4.2 | Registro de contenedores Docker | ⚪ **No aplica** | El backend se despliega como **Azure Functions con paquete ZIP** (no contenedores). No se requiere container registry en esta fase. |
| 2.4.3 | Política de versionado | 🟡 **Propuesto** | Se propone **SemVer** (`MAJOR.MINOR.PATCH`). Los artefactos de producción se etiquetan con el número de versión y el commit SHA. |

---

## 3. Plataforma Cloud e Infraestructura

> **Plataforma confirmada**: ✅ **Microsoft Azure**  
> **Arquitectura de referencia**: Azure Front Door + WAF → APIM → Azure Functions → Cosmos DB + Blob Storage + Key Vault + Monitor + App Insights

### 3.1 Ambientes

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 3.1.1 | Ambiente de desarrollo | ✅ **Confirmado** | Ambiente `dev` definido en la arquitectura. Requiere aprovisionamiento de todos los servicios Azure del diagrama. |
| 3.1.2 | Ambiente de pruebas funcionales y automáticas | ✅ **Confirmado** | Ambiente `qa` definido. Los tests automatizados del CI apuntan a este ambiente. |
| 3.1.3 | Ambiente de pruebas con usuarios finales (UAT) | ✅ **Confirmado** | Ambiente `uat` definido. Acceso controlado para validación con usuarios de negocio NEXA. |
| 3.1.4 | Ambiente de producción | ✅ **Confirmado** | Ambiente `prod` con **deployment slots** (staging → swap) para zero-downtime. Acceso restringido a despliegues aprobados. |
| 3.1.5 | Especificaciones de capacidad por ambiente | 🔴 **Pendiente** | Confirmar plan de Azure Functions: **Consumption** (escala automática, pago por uso) vs **Premium** (latencia fija, VNet). El equipo recomienda Premium para producción. |

### 3.2 Accesos y Red

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 3.2.1 | Credenciales de administración para despliegues en Dev y QA | 🔴 **Pendiente** | Proveer Service Principal o Managed Identity con rol **Contributor** en los Resource Groups de dev y qa. |
| 3.2.2 | Configuración de redes (VNets, subredes, NSGs) | 🔴 **Pendiente** | Confirmar si se usa integración VNet en Azure Functions (requerido si Cosmos DB tiene Private Endpoints). Solicitar diagrama de red actual si existe. |
| 3.2.3 | Reglas de firewall entre servicios y ambientes | 🔴 **Pendiente** | Confirmar si los servicios (Cosmos DB, Key Vault, Blob) estarán detrás de Private Endpoints o accesibles públicamente con restricciones de IP. |
| 3.2.4 | URLs y endpoints de APIs/servicios internos | 🔴 **Pendiente** | Proveer las URLs de APIM por ambiente (ej. `api-dev.nexa.com`, `api.nexa.com`). Si no están asignadas, confirmar el proceso de asignación de DNS. |
| 3.2.5 | Certificados SSL/TLS para dominios del proyecto | 🔴 **Pendiente** | Confirmar si Azure Front Door gestiona los certificados automáticamente (recomendado) o si el cliente aporta certificados propios. |
| 3.2.6 | Configuración DNS interno | 🔴 **Pendiente** | Indicar si el proyecto usa dominios corporativos internos (ej. `nexa.internal`) o solo dominios públicos. |

### 3.3 Secretos y Configuración

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 3.3.1 | Acceso al administrador de secretos (Key Vault) | ✅ **Confirmado (arquitectura)** | Se usa **Azure Key Vault** (uno por ambiente). El equipo requiere rol **Key Vault Secrets Officer** en Dev/QA y **Key Vault Secrets User** en UAT/Prod. |
| 3.3.2 | Variables de entorno por ambiente | 🔴 **Pendiente** | El cliente debe crear los Key Vaults y pre-cargar los secretos base (connection strings de Cosmos DB, Blob, APIM subscription keys). El equipo puede agregar secretos propios del código. |
| 3.3.3 | Política de renovación de credenciales | 🔴 **Pendiente** | Confirmar frecuencia de rotación (sugerido: 90 días para secrets, 365 días para certificados). Azure Key Vault soporta rotación automática. |

### 3.4 Monitoreo y Registros

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 3.4.1 | Plataforma de monitoreo corporativa | ✅ **Confirmado** | **Azure Monitor** como plataforma principal. Incluido en el diagrama de arquitectura. |
| 3.4.2 | Acceso a dashboards de métricas | 🔴 **Pendiente** | Solicitar rol **Monitoring Reader** en los Resource Groups. El equipo creará dashboards personalizados en Azure Monitor para cada ambiente. |
| 3.4.3 | Plataforma de registros centralizada | ✅ **Confirmado** | **Azure Application Insights** (integrado con Azure Monitor). Los logs del motor de cálculo y endpoints se envían a App Insights automáticamente. |
| 3.4.4 | Configuración de alertas y notificaciones | 🟡 **Propuesto** | Se propone alertas vía **Microsoft Teams** (canal Operaciones) y correo corporativo para errores críticos (HTTP 5xx > umbral, latencia p95 > 3s). Confirmar umbrales con el cliente. |

---

## 4. Herramientas y Sistemas Corporativos

### 4.1 Calidad y Seguridad de Código

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.1.1 | SonarQube / SonarCloud o equivalente | 🔴 **Pendiente** | Confirmar herramienta corporativa. El equipo propone **SonarCloud** (SaaS, integra con Azure DevOps sin instalación). Si el cliente tiene SonarQube Enterprise, proveer URL y token de acceso. |
| 4.1.2 | Herramientas de estilo de código (linters) | ✅ **Definido** | Ya integrado en el pipeline CI: **flake8** (estilo PEP 8), **black** (formateo), **isort** (imports). Configuración en `pyproject.toml`. |
| 4.1.3 | Herramienta de análisis de seguridad de código | ✅ **Definido** | Ya integrado en el pipeline CI: **bandit** (SAST para Python) + **safety** (vulnerabilidades en dependencias). |

### 4.2 Pruebas y Aseguramiento de Calidad

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.2.1 | Herramienta de gestión de casos de prueba | 🔴 **Pendiente** | Confirmar si el cliente usa **Azure Test Plans** (ya incluido en Azure DevOps) u otra herramienta (TestRail, Xray). Si no hay preferencia, se propone Azure Test Plans. |
| 4.2.2 | Framework de automatización de pruebas | ✅ **Definido** | **pytest** con cobertura mínima del 80%. 140+ tests unitarios y de integración ya existentes. Los resultados se publican en Azure Pipelines como JUnit XML. |
| 4.2.3 | Ambientes/herramientas para pruebas de carga | 🟡 **Propuesto** | Se propone **Azure Load Testing** (servicio nativo, integra con pipelines). Confirmar si el cliente requiere herramienta específica (JMeter, k6, Locust). |
| 4.2.4 | Acceso a datos de prueba anónimos | 🔴 **Pendiente** | El simulador usa datos de entrada estructurados (perfiles de agentes, parámetros de contratos). No maneja datos personales. Sin embargo, se requiere que el cliente confirme si los datos de cotizaciones reales pueden usarse en ambientes no-productivos. |

### 4.3 Documentación

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.3.1 | Plataforma de documentación técnica | 🔴 **Pendiente** | Confirmar plataforma corporativa: **Confluence**, **SharePoint Wiki** u otra. El equipo tiene documentación técnica lista para publicar (`docs/` en el repositorio). |
| 4.3.2 | Espacio del proyecto con permisos de escritura | 🔴 **Pendiente** | Solicitar espacio/sección del proyecto en la plataforma definida con permisos de escritura para el equipo. |
| 4.3.3 | Plantillas corporativas para documentación técnica | 🔴 **Pendiente** | Proveer plantillas si el cliente tiene estándares de documentación corporativa (portadas, fuentes, estructuras). El equipo las adoptará. |

### 4.4 Seguridad y Accesos

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.4.1 | SSO corporativo — confirmar proveedor | 🟡 **Propuesto** | Se propone **Azure AD / Microsoft Entra ID** con flujo OAuth 2.0 Authorization Code + PKCE. Si el cliente usa **ADFS**, confirmar en reunión técnica para ajustar la configuración del App Registration. **No se gestionarán usuarios/contraseñas dentro del simulador** — toda autenticación es delegada al IDP corporativo. |
| 4.4.2 | Proceso formal para dar de alta usuarios en sistemas NEXA | 🔴 **Pendiente** | Indicar: ¿quién aprueba el alta? ¿hay formulario/ticket? ¿cuánto tiempo toma? Este proceso aplica tanto para el equipo de desarrollo como para los usuarios finales del simulador. |
| 4.4.3 | Proceso formal para dar de baja usuarios al cierre del proyecto | 🔴 **Pendiente** | Confirmar proceso de offboarding: revocación de cuentas M365, eliminación de accesos en Azure DevOps, remoción de roles en Azure RBAC. |

### 4.5 Gestión de Servicios

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.5.1 | Herramienta de gestión de servicios TI (ServiceNow u otra) | 🔴 **Pendiente** | Confirmar si el cliente usa ServiceNow u otra herramienta ITSM. Si es así, indicar si el equipo de desarrollo debe usarla para gestionar incidentes o cambios. |
| 4.5.2 | Proceso de gestión de cambios para despliegues en UAT y Prod | 🟡 **Propuesto** | Se propone: Change Request formal en Azure Boards → revisión técnica → aprobación del PO → despliegue en ventana definida. Confirmar si el cliente requiere CAB (Change Advisory Board). |
| 4.5.3 | Ventanas de mantenimiento/despliegue | 🔴 **Pendiente** | Indicar ventanas disponibles para despliegues en UAT y producción (ej. martes y jueves 8pm–10pm COT). Requerido para planificar el pipeline de release. |

### 4.6 Integraciones

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 4.6.1 | Listado de APIs internas de NEXA a consumir o publicar | ⚪ **Fuera de alcance — Fase 1** | En esta fase, el simulador es un sistema autónomo. No consume APIs internas de NEXA ni publica integraciones con sistemas ERP/CRM. Confirmar si hay integraciones previstas en fases futuras. |
| 4.6.2 | Documentación de contratos de API (Swagger, Postman) | ⚪ **Fuera de alcance — Fase 1** | El equipo publicará la documentación OpenAPI del simulador (`/docs` endpoint en FastAPI). Si el cliente requiere publicarla en APIM o Postman, se puede gestionar. |
| 4.6.3 | Acceso a entornos sandbox de sistemas integrados | ⚪ **Fuera de alcance — Fase 1** | Sin integraciones externas en esta fase. |
| 4.6.4 | Infraestructura de mensajería (Kafka, Service Bus, etc.) | ⚪ **Fuera de alcance — Fase 1** | El simulador usa arquitectura REST síncrona. No requiere messaging en esta fase. |

---

## 5. Coordinación Técnica

### 5.1 Contactos Clave

| # | Rol | Estado | Acción requerida |
|---|---|---|---|
| 5.1.1 | Arquitecto / referente técnico principal (NEXA) | 🔴 **Pendiente** | Indicar nombre, cargo, correo y disponibilidad para reuniones técnicas semanales. |
| 5.1.2 | Responsable de infraestructura y operaciones | 🔴 **Pendiente** | Indicar nombre y correo. Es el contacto para aprovisionamiento de ambientes, Service Connections y redes. |
| 5.1.3 | Responsable de seguridad de la información | 🔴 **Pendiente** | Indicar nombre y correo. Es el contacto para políticas MFA, Conditional Access, App Registration en Entra ID. |
| 5.1.4 | Contacto para gestión de identidades y creación de cuentas | 🔴 **Pendiente** | Indicar nombre y correo. Es quien procesa las solicitudes de altas/bajas de usuarios. |
| 5.1.5 | Contacto de soporte de primera línea | 🔴 **Pendiente** | Indicar canal de soporte (Teams, correo, ticket) y horario de atención para bloqueos críticos del equipo. |

### 5.2 Tiempos y Procesos

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 5.2.1 | Tiempo estimado para crear cuentas de Office 365 | 🔴 **Pendiente** | Solicitar SLA de provisión de cuentas. El equipo de desarrollo no puede iniciar trabajo colaborativo hasta tener cuentas activas. |
| 5.2.2 | Tiempo estimado para preparar ambientes Dev y QA | 🔴 **Pendiente** | El equipo requiere ambientes listos (Azure Functions + Cosmos DB + Key Vault + APIM) en Dev como mínimo para iniciar integración. Solicitar fecha estimada. |
| 5.2.3 | Proceso formal para solicitar accesos | 🔴 **Pendiente** | Indicar: ¿número de ticket? ¿formulario web? ¿correo a quién? ¿tiempo de respuesta? |
| 5.2.4 | Ventanas de despliegue para UAT y Producción | 🔴 **Pendiente** | Requerido para configurar el pipeline de release. Indicar días/horas disponibles. |
| 5.2.5 | Proceso para escalar bloqueos críticos de infraestructura | 🔴 **Pendiente** | Indicar canal de escalamiento (jefe de proyecto, canal Teams urgente, etc.) y tiempo de respuesta esperado ante un bloqueo crítico. |

### 5.3 Dependencias Externas

| # | Ítem solicitado | Estado | Respuesta / Observación |
|---|---|---|---|
| 5.3.1 | Listado de dependencias externas críticas | ✅ **Definido (lado equipo)** | Las dependencias técnicas del simulador son: Python 3.12, FastAPI, Azure Functions Core Tools, Cosmos DB SDK, Azure SDK para Python. Todas son librerías públicas sin costos de licencia adicionales. El cliente debe confirmar si existe restricción sobre paquetes de código abierto. |
| 5.3.2 | Restricciones regulatorias o de cumplimiento | 🔴 **Pendiente** | Confirmar si aplica alguna norma específica: Ley 1581 (datos personales Colombia), normas de la Superfinanciera, certificaciones ISO 27001, SOC 2, etc. El equipo ajustará prácticas de seguridad según lo que el cliente indique. |
| 5.3.3 | Estándares tecnológicos de uso obligatorio en NEXA | 🔴 **Pendiente** | Confirmar si existen estándares corporativos obligatorios: versiones específicas de lenguajes, herramientas de code review aprobadas, convenciones de nomenclatura de recursos Azure, políticas de tagging de recursos, etc. |

---

## Resumen de Estado

| Categoría | ✅ Confirmado | 🟡 Propuesto | 🔴 Pendiente cliente | ⚪ No aplica |
|---|---|---|---|---|
| 1. Microsoft 365 | 0 | 1 | 12 | 0 |
| 2. Plataforma DevOps | 1 | 8 | 5 | 1 |
| 3. Cloud e Infraestructura | 6 | 2 | 10 | 0 |
| 4. Herramientas y Sistemas | 4 | 4 | 9 | 4 |
| 5. Coordinación Técnica | 1 | 1 | 13 | 0 |
| **TOTAL** | **12** | **16** | **49** | **5** |

---

## Próximos Pasos Recomendados

1. **Reunión técnica de kickoff** con el cliente (máx. 2 horas): recorrer juntos este documento y responder los ítems 🔴.
2. **Ítems bloqueantes prioritarios** (sin estos no se puede iniciar el desarrollo):
   - Cuentas Microsoft 365 para el equipo
   - Acceso a Azure DevOps (repositorio + Boards + Pipelines)
   - Ambiente Dev aprovisionado (Azure Functions + Cosmos DB + Key Vault)
   - Confirmación del proveedor SSO (Azure AD / Entra ID / ADFS)
   - Contactos técnicos clave (infraestructura + seguridad)
3. **Ítems diferibles** (pueden resolverse en las primeras 2 semanas del sprint): documentación platform, test management tool, load testing tool.

---

*Documento elaborado por Equipo de Desarrollo Accenture — Versión 1.0.0 — 2026-05-22*  
*Para uso en reunión de kickoff técnico con NEXA. Clasificación: Interno.*
