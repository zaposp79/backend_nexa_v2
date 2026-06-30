# Calculator

## Propósito

`modules/calculator` es la capa HTTP y de aplicación que inicia una
simulación, consulta resultados persistidos y expone trazabilidad básica del
cálculo. Actúa como shell alrededor del motor de cálculo y del repositorio de
resultados.

## Responsabilidades

- Recibir solicitudes públicas de simulación.
- Orquestar handlers normales y certificados.
- Persistir y consultar resultados de simulación.
- Exponer el resultado imprimible general y la trazabilidad por simulación.
- Conectar la API con `calculator_motor` sin duplicar fórmulas.

## Qué no hace este módulo

- No implementa fórmulas de negocio.
- No construye contratos de pantalla de las visiones especializadas.
- No administra parametrización activa.
- No lee Excel en runtime.
- No decide estructura pública de PYG, CTS, tarifas o imprimible especializado.

## Estructura interna

```text
calculator/
├── api/
│   ├── calculate_router.py
│   ├── results_router.py
│   ├── calculate_normal_handler.py
│   └── calculate_certified_handler.py
├── application/
├── repositories/
└── services/
```

## Endpoints expuestos

| Método | Ruta | Propósito | Tag OpenAPI |
|---|---|---|---|
| POST | `/api/v1/simulation/calculate` | Ejecuta y persiste una simulación. | Simulations |
| GET | `/api/v1/simulation/{simulation_id}/results` | Devuelve el resultado imprimible general. | Simulations |
| GET | `/api/v1/simulation/{simulation_id}/traceability` | Devuelve trazabilidad asociada a la simulación. | Simulations |

## Entradas y salidas principales

- Entrada principal: contrato público de simulación v1.
- Salida principal: identificador de simulación, resultado persistido y
  metadatos de ejecución.
- Fuente de lectura: `ResultsRepository` y repositorios asociados al cálculo.

## Dependencias relevantes

- `modules/calculator_motor` para ejecución y ensamblaje de resultados.
- `modules/shared/responses.py` para el envelope público.
- `db` para wiring de repositorios.

## Contratos públicos

- Las respuestas deben usar `ApiResponse`.
- Los errores deben expresarse con el formato compartido.
- Las rutas de visiones screen-ready pertenecen a sus módulos propietarios, no
  a `calculator`.

## Reglas de negocio y fuentes de cálculo

Las reglas y fórmulas viven en `calculator_motor`. Este módulo solo coordina
la ejecución y la persistencia del resultado.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de cálculo y persistencia asociadas al flujo de simulación.

## Consideraciones de mantenimiento

- Si se agrega una ruta de resultado visual, ubicarla en el módulo de visión
  correspondiente.
- Mantener handlers pequeños y enfocados en orquestación.
- Evitar dependencias directas a archivos de parametrización o Excel.
