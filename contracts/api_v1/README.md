# API v1

## Propósito

`contracts/api_v1` define la primera versión pública congelada de la API de
simulación NEXA.

## Responsabilidades

- Declarar DTOs de request y response de API v1.
- Mantener modelos estrictos e inmutables.
- Generar schemas verificables.
- Documentar ejemplos públicos de request y response.

## Qué no hace este módulo

- No ejecuta el motor.
- No valida reglas de negocio dinámicas.
- No consulta storage.
- No construye contratos de pantalla de visiones nuevas.

## Estructura interna

```text
api_v1/
├── request/
├── response/
├── schema/
├── examples/
├── adapter.py
└── __init__.py
```

## Endpoints expuestos

No expone endpoints. Los routers usan estos contratos para validar la forma de
entrada y salida.

## Entradas y salidas principales

### Request

| DTO | Archivo | Propósito |
|---|---|---|
| `EntryDataV1` | `request/entry_data.py` | Envelope raíz de simulación. |
| `PanelDeControlRequestV1` | `request/panel.py` | Panel de control. |
| `CadenaARequestV1` | `request/cadena_a.py` | Perfiles y nómina de Cadena A. |
| `CadenaBRequestV1` | `request/cadena_b.py` | Canales y componentes de Cadena B. |
| `CadenaCRequestV1` | `request/cadena_c.py` | Integraciones y equipo transversal. |
| `EscenarioComercialV1` | `request/escenarios.py` | Escenarios comerciales. |
| `ContractMetadataV1` | `request/entry_data.py` | Metadata opcional. |

### Response

| DTO | Archivo | Propósito |
|---|---|---|
| `SimulationResultV1` | `response/simulation_result.py` | Envelope estable de resultado. |
| `VisionsBundleV1` | `response/visions.py` | Bundle de visiones de respuesta. |
| `KpisV1` | `response/kpis.py` | KPIs del deal. |
| `PricingV1` | `response/pricing.py` | Resumen de pricing reservado. |

## Dependencias relevantes

- Pydantic v2.
- Generadores de schemas y OpenAPI.
- Pruebas de contratos.

## Contratos públicos

- `extra="forbid"` para rechazar campos desconocidos.
- `frozen=True` para evitar mutación accidental.
- Rangos numéricos explícitos en porcentajes, meses y valores monetarios.
- Validadores cruzados para cadenas activas y referencias de escenarios.

## Reglas de negocio y fuentes de cálculo

Los contratos validan forma y rangos. Las reglas de cálculo se aplican en los
módulos propietarios.

## Pruebas relacionadas

- `tests/contracts/test_contract_schema_stable.py`
- Pruebas de API que usan `EntryDataV1`.

## Consideraciones de mantenimiento

- Cambios aditivos opcionales son aceptables con regeneración intencional.
- Cambios incompatibles deben ir a una versión nueva.
- Mantener `adapter.py` como puente acotado mientras el flujo de cálculo lo
  requiera.
