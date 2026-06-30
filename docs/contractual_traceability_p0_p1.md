# Trazabilidad contractual P0/P1

## Alcance implementado

Esta intervención conecta el contrato `entry_data` con el pipeline:

`JSON -> UserInputLoader -> UserInput -> PricingRequest -> Calculators -> Visions -> Serializer -> Endpoint`

## Reglas contractuales cerradas

### Polizas por cadena

- `polizas[].cadenas.cadena_a` se mapea a `PolizaContractual.aplica_a`.
- `polizas[].cadenas.cadena_b` se mapea a `PolizaContractual.aplica_b`.
- `polizas[].cadenas.cadena_c` se mapea a `PolizaContractual.aplica_c`.
- `CostosFinancierosCalculator.calcular()` separa `polizas_a`, `polizas_b` y `polizas_c`.
- La serializacion expone `polizas.cadena_a`, `polizas.cadena_b`, `polizas.cadena_c`.
- Vision P&G incluye filas separadas por cadena.

### Diferencia entre null y []

- `polizas: null` o ausencia de `polizas` usa parametrizacion.
- `polizas: []` significa cero polizas y no consulta parametrizacion.
- `polizas: [...]` usa exclusivamente las polizas contractuales.

### Cadenas opcionales

- `VolumeResolutionService` consolida activacion global desde `volumetria.inbound/outbound.cadenas_activas`.
- `PanelDeControl.cadenas_activas` y `PricingRequest.cadenas_activas` transportan el estado contractual.
- La validacion de visiones solo exige payroll/tarifas cuando `cadena_a` esta activa.
- Cadena B y Cadena C pueden recibir volumen oficial sin depender de Cadena A.

### Volumetria oficial

- La resolucion oficial es `(modalidad, canal, cadena) -> volumen`.
- Si una cadena esta desactivada, su volumen resuelto es `0.0` aunque el JSON contenga valor.
- Cadena A, B y C reciben volumen desde el servicio antes de construir dominio.

### Validacion estricta

- `ValidationMode.CONTRACT_STRICT` queda disponible.
- `ContractValidator` valida campos criticos de `datos_operativos`, `reglas_negocio`, `volumetria.indexacion`, cadenas activas, polizas y escenarios.
- `/simulation/calculate` ejecuta `ContractValidator` para payloads `entry_data` y devuelve `422` ante errores contractuales.
- `/simulation/calculate/validate` entiende payload legacy y payload `entry_data`.

### Indexacion e imprevistos

- `indexacion.mes_aplicacion` se mapea desde JSON hacia panel, nomina y parametros de Cadena B/C cuando existe.
- `reglas_negocio.imprevistos` se mapea hacia panel y P&G.

### Auditoria obligatoria

- `audit_trace`, `datasets_vision`, trazabilidad y snapshots dejan de ser opcionales silenciosos.
- `AuditIntegrityError` aborta si no se puede construir o persistir auditoria obligatoria.

### Traceability endpoint

- `GET /simulation/{simulation_id}/traceability` retorna:
  - `unused_fields`
  - `partial_fields`
  - `financially_connected_fields`
  - `dead_fields`

## Pruebas ejecutadas

- `tests/unit/test_contractual_p0.py`: 7 passed.
- `tests/unit/test_costos_financieros.py`: 13 passed.
- `tests/integration/test_traceability_polizas_source.py`: 2 passed.
- `tests/unit/test_fase2_input_normalizer.py tests/unit/test_fase3_single_source.py`: 52 passed, 1 skipped, 5 failed.

## Bloqueo externo detectado

Las 5 fallas de `TestProvenanceIntegracion` no llegan a validar esta capa contractual porque el builder falla cargando parametrizacion:

`OP-Config key 'factor_alto_salario_smmlv' not found. Available keys: []`

Origen observado:

- `repositories/financial_parametrization_repository.py:get_op_config`
- `repositories/parametrization_provider.py:get_nomina_laboral_params`
- `domain/services/nomina_cargada.py:desde_parametrizacion`
- `input/context_builder.py:construir`

## Riesgos restantes

- El endpoint de trazabilidad implementa una clasificacion inicial; no es todavia un registry exhaustivo campo por campo para todo el contrato.
- Los escenarios comerciales se parsean y gobiernan la configuracion de tarifas existente, pero no se creo un `PricingResult` independiente por escenario.
- La suite de integracion completa depende de parametrizacion OP valida.
