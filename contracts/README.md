# Contratos NEXA

## Propósito

`contracts/` conserva los contratos públicos congelados de la API de
simulación. Cada contrato combina modelos Pydantic, JSON Schema, ejemplos y
extractos OpenAPI.

## Responsabilidades

- Guardar la forma pública versionada de requests y responses.
- Permitir validación automática de drift de schema.
- Separar cambios compatibles de cambios que requieren una nueva versión.
- Documentar ejemplos certificados de payloads públicos.

## Qué no hace este módulo

- No ejecuta simulaciones.
- No persiste resultados.
- No contiene fórmulas.
- No reemplaza los routers de FastAPI.

## Estructura interna

```text
contracts/
├── api_v1/
│   ├── request/
│   ├── response/
│   ├── schema/
│   └── examples/
└── openapi/
```

## Endpoints expuestos

No expone endpoints. Define la forma esperada de los endpoints públicos.

## Entradas y salidas principales

- Entrada: modelos Pydantic versionados.
- Salida: schemas JSON, ejemplos y especificaciones OpenAPI generadas.

## Dependencias relevantes

- `scripts/contracts/generate_schemas.py`.
- `scripts/contracts/generate_openapi.py`.
- `tests/contracts/`.

## Contratos públicos

| Versión | Estado | Ubicación | Política |
|---|---|---|---|
| `api-v1` | Congelado | `contracts/api_v1/` | Solo cambios aditivos opcionales. |
| `api-v2` | Futuro | `contracts/api_v2/` | Para cambios incompatibles. |

Un cambio incompatible incluye renombrar o eliminar campos, endurecer tipos,
agregar campos requeridos o cambiar la semántica de unidades, signos o
redondeos.

## Reglas de negocio y fuentes de cálculo

Este directorio no define reglas de cálculo. Solo documenta el contrato de
transporte.

## Pruebas relacionadas

```bash
python scripts/contracts/generate_schemas.py
python scripts/contracts/generate_openapi.py
python -m pytest tests/contracts --tb=short -v
```

## Consideraciones de mantenimiento

- No modificar schemas congelados sin intención explícita.
- Si cambia el contrato de forma incompatible, crear una nueva versión.
- Mantener ejemplos alineados con payloads certificados.
