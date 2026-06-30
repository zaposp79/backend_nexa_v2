# PYG

## Propósito

`modules/pyg` compone estructuras internas de Profit & Loss usadas por el
pipeline de cálculo. La visión pública actual de PYG vive en
`modules/vision_pyg`.

## Responsabilidades

- Orquestar servicios internos relacionados con PYG.
- Construir modelos de PYG mensual y KPIs del deal.
- Transformar datos calculados en estructuras internas consumidas por otros
  componentes.
- Delegar fórmulas al motor de cálculo.

## Qué no hace este módulo

- No expone el contrato público screen-ready de PYG.
- No debe implementar fórmulas de negocio propias.
- No debe leer parametrización por rutas físicas.
- No debe recalcular dentro de builders de presentación.

## Estructura interna

```text
pyg/
├── api/
├── builders/
├── dto/
└── services/
```

## Endpoints expuestos

Este módulo conserva componentes históricos de PYG. La ruta pública actual
screen-ready se documenta y mantiene en `modules/vision_pyg`.

## Entradas y salidas principales

- Entrada: datos calculados por el motor y parámetros entregados por provider.
- Salida: modelos internos de PYG, KPIs y estructuras auxiliares.

## Dependencias relevantes

- `modules/calculator_motor/formulas/` para fórmulas.
- `IParametrizationProvider` para datos de parametrización.
- DTOs internos de PYG.

## Contratos públicos

El contrato público frontend de PYG no pertenece a este módulo. Debe exponerse
desde `modules/vision_pyg` con respuesta screen-ready.

## Reglas de negocio y fuentes de cálculo

Las fórmulas viven en `calculator_motor`. Este módulo puede componer resultados
pero no convertirse en dueño de cálculos.

## Pruebas relacionadas

- Pruebas de servicios PYG.
- `tests/vision_pyg/` para el contrato público de pantalla.
- `tests/api/test_vision_pyg_endpoint.py`.

## Consideraciones de mantenimiento

- Mantener una frontera clara entre composición interna y contrato público.
- Si se mueve lógica a `vision_pyg`, validar que no se arrastren fórmulas.
- Si se mueve lógica al motor, preservar valores y contratos persistidos.
