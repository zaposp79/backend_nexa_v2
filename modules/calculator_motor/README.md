# Calculator Motor

## Propósito

`modules/calculator_motor` es el dueño del cálculo de pricing. Convierte una
solicitud normalizada y parametrización aprobada en resultados calculados y
serializables.

## Responsabilidades

- Orquestar el pipeline principal de simulación.
- Mantener fórmulas de negocio bajo `formulas/`.
- Construir contexto de simulación.
- Validar y normalizar entradas antes del cálculo.
- Serializar resultados preservando el contrato persistido.

## Qué no hace este módulo

- No expone rutas HTTP.
- No construye contratos de pantalla de visiones.
- No lee parametrización por rutas físicas dentro de fórmulas.
- No administra uploads de parametrización.
- No actualiza fixtures dorados.

## Estructura interna

```text
calculator_motor/
├── adapters/
├── constants/
├── dto/
├── formulas/
├── helpers/
├── mixins/
├── models/
├── serializers/
├── use_cases/
└── validation/
```

## Endpoints expuestos

No expone endpoints. Se consume desde `modules/calculator` y otros servicios
de aplicación.

## Entradas y salidas principales

- Entrada: solicitud de simulación validada y parametrización resuelta.
- Salida: resultado calculado, snapshots y estructuras persistibles.

## Dependencias relevantes

- Provider de parametrización aprobado.
- Modelos y DTOs internos del motor.
- Helpers de precisión compartidos.
- Serializadores de resultado.

## Contratos públicos

Los entrypoints relevantes son:

- `engine.py`
- `context_builder.py`
- `adapters/user_input_loader.py`
- `serializers/`
- `validation/`

Los consumidores deben usar estas superficies en lugar de importar fórmulas
internas directamente.

## Reglas de negocio y fuentes de cálculo

- Las fórmulas pertenecen a `formulas/`.
- Los valores de negocio deben llegar por provider o entrada normalizada.
- Las visiones consumen salidas del motor, pero no son dueñas de fórmulas.
- Los cambios de fórmulas deben validarse contra API, paridad y baselines
  cuando aplique.

## Pruebas relacionadas

- `tests/api/`
- `tests/golden/`
- Pruebas focalizadas del área de fórmula tocada.

## Consideraciones de mantenimiento

- Mover fórmulas de forma mecánica y con pruebas.
- Evitar dependencias del motor hacia routers o mappers de visión.
- No introducir defaults silenciosos de negocio.
