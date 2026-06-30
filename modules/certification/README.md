# Certification

## Propósito

`modules/certification` administra certificados de ejecución y flujos de
verificación asociados a resultados calculados.

## Responsabilidades

- Modelar certificados de ejecución.
- Persistir y consultar certificados.
- Exponer rutas de verificación.
- Validar evidencia de certificación sin alterar resultados.

## Qué no hace este módulo

- No ejecuta fórmulas.
- No construye visiones de pantalla.
- No administra el motor de persistencia.
- No cambia fixtures o baselines.

## Estructura interna

```text
certification/
├── api/
├── certificate_repository.py
└── models.py
```

## Endpoints expuestos

Las rutas de certificación viven en `api/certification_router.py` y se montan
desde la composición de API v1 cuando aplica.

## Entradas y salidas principales

- Entrada: identificadores de ejecución, certificados o evidencia.
- Salida: certificados y resultados de verificación.

## Dependencias relevantes

- Repositorio de certificados.
- Modelos de certificación.
- Contratos compartidos de respuesta.

## Contratos públicos

La certificación debe ser verificable y reproducible. Sus respuestas no deben
contener payloads técnicos innecesarios.

## Reglas de negocio y fuentes de cálculo

Este módulo verifica ejecuciones. No produce valores de cálculo.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de certificación cuando existan.

## Consideraciones de mantenimiento

- Mantener certificados como evidencia, no como fuente de cálculo.
- No mezclar certificación con visiones de frontend.
