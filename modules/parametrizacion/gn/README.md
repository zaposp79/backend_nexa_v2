# Parametrización GN

## Propósito

`modules/parametrizacion/gn` administra parametrización general de negocio:
catálogos, reglas de referencia y valores transversales que alimentan el motor.

## Responsabilidades

- Cargar versiones GN desde archivos aceptados por la API.
- Validar estructura y contenido antes de persistir.
- Mapear entradas a documentos GN.
- Consultar y activar versiones GN.
- Exponer repositorios tipados para consumo del provider.

## Qué no hace este módulo

- No calcula resultados de simulación.
- No construye visiones de pantalla.
- No administra datos HR u OP.
- No lee Excel desde los endpoints de visión.

## Estructura interna

```text
gn/
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
| POST | `/api/v1/parametrization/gn/upload` | Carga una versión GN. |
| GET | `/api/v1/parametrization/gn/versions` | Lista versiones GN. |
| PATCH | `/api/v1/parametrization/gn/{id}/activate` | Activa una versión GN. |
| DELETE | `/api/v1/parametrization/gn/{id}` | Elimina una versión GN. |

## Entradas y salidas principales

- Entrada: archivo de parametrización GN.
- Salida: documento GN versionado y versión activa.

## Dependencias relevantes

- Infraestructura `DocumentStore`.
- Contratos compartidos de parametrización.
- Validadores y mappers propios de GN.

## Contratos públicos

La API GN debe conservar rutas y envelopes estables. El cálculo consume GN por
provider o repositorio tipado.

## Reglas de negocio y fuentes de cálculo

GN aporta valores de negocio y catálogos. La aplicación de esos valores ocurre
en el motor o en servicios propietarios.

## Pruebas relacionadas

- Pruebas de API de parametrización.
- Pruebas de validadores, mappers y repositorios GN.

## Consideraciones de mantenimiento

- No duplicar catálogos GN en módulos consumidores.
- Mantener trazabilidad de versión activa.
