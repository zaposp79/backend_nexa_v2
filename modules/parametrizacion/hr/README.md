# Parametrización HR

## Propósito

`modules/parametrizacion/hr` administra parametrización de recursos humanos:
nómina, staffing, rotación, ausentismo y datos relacionados con personal.

## Responsabilidades

- Cargar versiones HR desde archivos aceptados por la API.
- Validar estructura y contenido antes de persistir.
- Mapear filas de entrada a documentos HR.
- Consultar y activar versiones HR.
- Exponer repositorios tipados para consumo del provider.

## Qué no hace este módulo

- No calcula precios.
- No calcula PYG, CTS ni tarifas.
- No construye contratos de pantalla.
- No lee resultados de simulación.

## Estructura interna

```text
hr/
├── api/
├── dto/
├── mappers/
├── models/
├── repositories/
├── services/
└── validators/
```

## Endpoints expuestos

| Método | Ruta | Propósito |
|---|---|---|
| POST | `/api/v1/parametrization/hr/upload` | Carga una versión HR. |
| GET | `/api/v1/parametrization/hr/versions` | Lista versiones HR. |
| PATCH | `/api/v1/parametrization/hr/{id}/activate` | Activa una versión HR. |
| DELETE | `/api/v1/parametrization/hr/{id}` | Elimina una versión HR. |

## Entradas y salidas principales

- Entrada: archivo de parametrización HR.
- Salida: documento HR versionado y versión activa.

## Dependencias relevantes

- Infraestructura `DocumentStore`.
- Contratos compartidos de parametrización.
- Validadores y mappers propios de HR.

## Contratos públicos

Los endpoints deben mantener respuestas versionadas y trazables. Los
consumidores de cálculo deben acceder por provider o repositorio, no por
archivos.

## Reglas de negocio y fuentes de cálculo

HR aporta datos de personal para el motor. Las fórmulas que usan esos datos no
viven en este submódulo.

## Pruebas relacionadas

- Pruebas de API de parametrización.
- Pruebas de validadores, mappers y repositorios HR.

## Consideraciones de mantenimiento

- Evitar mezclar campos HR con GN u OP.
- Validar cambios de estructura contra los contratos de upload.
