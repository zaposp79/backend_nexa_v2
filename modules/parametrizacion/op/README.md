# Parametrización OP

## Propósito

`modules/parametrizacion/op` administra parametrización operacional y
financiera usada por el motor de simulación.

## Responsabilidades

- Cargar versiones OP desde archivos aceptados por la API.
- Validar estructura y contenido antes de persistir.
- Mapear entradas a documentos OP.
- Consultar y activar versiones OP.
- Exponer repositorios tipados para consumo del provider.

## Qué no hace este módulo

- No calcula tarifas, márgenes ni PYG.
- No construye contratos de pantalla.
- No administra datos HR o GN.
- No persiste resultados de simulación.

## Estructura interna

```text
op/
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
| POST | `/api/v1/parametrization/op/upload` | Carga una versión OP. |
| GET | `/api/v1/parametrization/op/versions` | Lista versiones OP. |
| PATCH | `/api/v1/parametrization/op/{id}/activate` | Activa una versión OP. |
| DELETE | `/api/v1/parametrization/op/{id}` | Elimina una versión OP. |

## Entradas y salidas principales

- Entrada: archivo de parametrización OP.
- Salida: documento OP versionado y versión activa.

## Dependencias relevantes

- Infraestructura `DocumentStore`.
- Contratos compartidos de parametrización.
- Validadores y mappers propios de OP.

## Contratos públicos

La API OP debe conservar rutas y envelopes estables. El cálculo consume OP por
provider o repositorio tipado.

## Reglas de negocio y fuentes de cálculo

OP aporta datos operacionales y financieros. Las fórmulas que aplican esos
valores viven en el motor.

## Pruebas relacionadas

- Pruebas de API de parametrización.
- Pruebas de validadores, mappers y repositorios OP.

## Consideraciones de mantenimiento

- No duplicar valores OP en módulos consumidores.
- Mantener separación entre datos operacionales y fórmulas.
