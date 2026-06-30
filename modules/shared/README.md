# Shared

## Propósito

`modules/shared` concentra contratos, puertos y utilidades transversales usados
por varios módulos del backend.

## Responsabilidades

- Definir excepciones de dominio compartidas.
- Proveer `ApiResponse` y errores estándar.
- Mantener helpers de precisión y redondeo.
- Alojar contratos públicos de API v1.
- Definir puertos como `IParametrizationProvider`, `ILogger` y
  `ITraceEmitter`.
- Mantener infraestructura común de FastAPI, logging y middleware.

## Qué no hace este módulo

- No implementa fórmulas.
- No orquesta el motor.
- No construye visiones de pantalla.
- No administra parametrización activa.
- No lee fixtures ni resultados persistidos como owner funcional.

## Estructura interna

```text
shared/
├── config/
├── contracts/
├── infrastructure/
├── middleware/
├── models/
├── ports/
├── versioning/
├── exceptions.py
├── precision.py
└── responses.py
```

## Endpoints expuestos

No expone endpoints. Sus componentes son usados por routers, servicios y
módulos de dominio.

## Entradas y salidas principales

- Entrada: datos de aplicación que necesitan contratos o utilidades comunes.
- Salida: envelopes, excepciones, puertos, helpers y configuración compartida.

## Dependencias relevantes

- FastAPI para infraestructura y middleware.
- Configuración de aplicación.
- Contratos de API v1.

## Contratos públicos

Pueden vivir aquí únicamente contratos transversales:

- DTOs públicos de API.
- Puertos usados por más de un módulo.
- Excepciones compartidas.
- Utilidades puras usadas por varios módulos.
- Re-exports de compatibilidad documentados y acotados.

## Reglas de negocio y fuentes de cálculo

Las reglas de negocio canónicas compartidas se cargan desde
`modules/shared/config/business_rules/`. Las fórmulas que aplican esas reglas
pertenecen al módulo propietario correspondiente.

## Pruebas relacionadas

- `tests/api/`
- Pruebas de contratos y utilidades compartidas.

## Consideraciones de mantenimiento

- Evitar agregar abstracciones sin consumidor real.
- Preferir exports explícitos.
- Mantener `shared` libre de dependencias hacia visiones, cadenas o fórmulas.
