# Parametrización

## Propósito

`modules/parametrizacion` administra las parametrizaciones activas,
versionadas y certificadas que alimentan el motor de simulación. Es el dueño de
la carga, validación, almacenamiento y consulta de datos HR, GN y OP.

## Responsabilidades

- Exponer endpoints de carga, listado, consulta, activación y eliminación de
  versiones de parametrización.
- Validar archivos de entrada antes de persistirlos.
- Mapear documentos HR, GN y OP hacia modelos internos.
- Proveer acceso tipado a parametrización mediante provider, resolver y
  repositorios.
- Mantener snapshots certificados para reproducibilidad.

## Qué no hace este módulo

- No calcula precios ni rentabilidad.
- No construye contratos de pantalla.
- No genera fixtures dorados.
- No interpreta `request/request.json`.
- No debe ser consumido por visiones mediante rutas físicas de storage.

## Estructura interna

```text
parametrizacion/
├── api/
│   └── router.py
├── gn/
├── hr/
├── op/
├── mixins/
├── repositories/
├── services/
└── shared/
```

## Endpoints expuestos

Los endpoints se publican bajo `/api/v1`:

| Familia | Método | Ruta | Propósito |
|---|---|---|---|
| HR | POST | `/api/v1/parametrization/hr/upload` | Carga una versión HR. |
| HR | GET | `/api/v1/parametrization/hr/versions` | Lista versiones HR. |
| HR | GET | `/api/v1/parametrization/hr/active` | Consulta la versión HR activa. |
| HR | GET | `/api/v1/parametrization/hr/{version_id}/activate` | Activa una versión HR. |
| HR | DELETE | `/api/v1/parametrization/hr/{version_id}` | Elimina una versión HR. |
| GN | POST | `/api/v1/parametrization/gn/upload` | Carga una versión GN. |
| GN | GET | `/api/v1/parametrization/gn/versions` | Lista versiones GN. |
| GN | GET | `/api/v1/parametrization/gn/active` | Consulta la versión GN activa. |
| GN | GET | `/api/v1/parametrization/gn/{version_id}/activate` | Activa una versión GN. |
| GN | DELETE | `/api/v1/parametrization/gn/{version_id}` | Elimina una versión GN. |
| OP | POST | `/api/v1/parametrization/op/upload` | Carga una versión OP. |
| OP | GET | `/api/v1/parametrization/op/versions` | Lista versiones OP. |
| OP | GET | `/api/v1/parametrization/op/active` | Consulta la versión OP activa. |
| OP | GET | `/api/v1/parametrization/op/{version_id}/activate` | Activa una versión OP. |
| OP | DELETE | `/api/v1/parametrization/op/{version_id}` | Elimina una versión OP. |

## Entradas y salidas principales

- Entrada principal: archivos de parametrización y metadatos de versión.
- Salida principal: documentos versionados, versión activa y datos tipados para
  cálculo.
- Consumo interno: provider y resolver usados por el motor y servicios de
  aplicación.

## Dependencias relevantes

- `db` para `DocumentStore` y proveedores de persistencia.
- `modules/shared/ports/parametrization_provider.py` para el contrato de
  provider.
- Helpers compartidos de lectura segura, normalización y validación de uploads.

## Contratos públicos

- Las rutas HR, GN y OP deben conservar envelopes públicos estables.
- El provider debe ser la puerta de acceso para consumidores de cálculo.
- La parametrización activa debe consultarse por repositorio/provider, no por
  rutas físicas.

## Reglas de negocio y fuentes de cálculo

La parametrización es fuente de datos para el cálculo, pero no ejecuta las
fórmulas. El motor decide cómo aplicar esos valores.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de repositorios, servicios y validadores de parametrización.

## Consideraciones de mantenimiento

- Mantener HR, GN y OP como familias separadas.
- No duplicar constantes de negocio fuera de la fuente canónica.
- Cualquier migración de backend de persistencia debe preservar el contrato de
  `DocumentStore`.
