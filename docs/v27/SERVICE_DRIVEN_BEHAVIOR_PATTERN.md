# Service-Driven Behavior Pattern — Architecture Note

## Pattern Overview

The `servicio` (Panel!C5 / `panel.linea_negocio`) is a **functional driver** in Excel V2-7.
This pattern documents how to integrate service-driven behavior without hardcoded strings.

## Single Source of Truth

**File**: `domain/services/servicio_catalogo.py`

**Catalog source**: `Listas Desplegables!A4:A9` (authoritative Excel dropdown).

```python
SERVICIOS_V27 = (
    "Cobranzas", "SAC", "Ventas multicanal",
    "SACO", "Plataformas", "Captura de Datos",
)
```

## ServicioBehavior Dataclass

```python
@dataclass(frozen=True)
class ServicioBehavior:
    nombre: str
    es_servicio_conocido: bool
    canal_detail_habilitado: bool          # CTS!C58/C87 — SAC only
    seccion_saco_ventas_habilitada: bool   # Panel!C120 — SACO or Ventas multicanal
    seccion_cobranzas_habilitada: bool     # Panel!C152 — Cobranzas only
    seccion_captura_datos_habilitada: bool  # Panel!C184 — Captura de Datos only
    vt_billing_mode: VTBillingMode         # VT!C77/C133 — SACO | Cobranzas | default
```

Each field is traceable to a specific workbook cell. No fabricated mappings.

## Usage Pattern

```python
# In any calculator or serializer:
from nexa_engine.domain.services.servicio_catalogo import servicio_behavior

behavior = servicio_behavior(panel.linea_negocio)
cost_to_serve.canal_view_habilitado = behavior.canal_detail_habilitado
# No hardcoded service strings; all logic via the catalog
```

## Currently Wired

| Consumer | Field | Source cell |
|----------|-------|-------------|
| `CostToServeCalculator` | `canal_view_habilitado` | CTS!C58/C87 |
| Serializer / frontend | `seccion_*_habilitada` flags | Panel!C120/C152/C184 |
| (Future) VT billing rows | `vt_billing_mode` | VT!C77/C133 |

## Non-Service Dimensions (Do Not Add)

The following are **NOT** service-driven and must not be added to `ServicioBehavior`:

| Dimension | True driver |
|-----------|-------------|
| Active chains A/B/C | `cadenas_activas` input (Panel!M17/M30) |
| Active channels | volume > 0 per channel (volumetria input) |
| Billing model (FTE/Tiempo/etc.) | `EscenarioComercial.modelo_cobro` |
| Client name display | `tipo_cliente` input (Panel!C7) |

Adding these to `ServicioBehavior` would fabricate a mapping the workbook doesn't have.

## Guidelines for Future Views

1. **Before adding a service conditional**: scan the workbook for the IF formula to confirm the literal used.
2. **Add to `servicio_catalogo.py`** with a cell citation in the docstring.
3. **Never compare `servicio` strings directly** in calculator code — route through `servicio_behavior()`.
4. **Unknown services default to False** — no invented behavior for unlisted services.
5. **Test per catalog**: parametrize over `SERVICIOS_V27` to catch regressions.

## Migration Map

| Old pattern | New pattern |
|-------------|-------------|
| `if linea_negocio == "SAC": ...` | `servicio_behavior(linea_negocio).canal_detail_habilitado` |
| `if servicio.upper() == "SAC": ...` | same — catalog handles case-sensitivity |
| New VT billing rows (SACO/Cobranzas) | `behavior.vt_billing_mode in ("SACO", "Cobranzas")` |

## Future Extensions

- **VT billing rows SACO/Cobranzas**: when `vt_billing_mode != "default"`, emit extra VT rows from Panel!C143/C182. Requires input contract for SACO/Cobranzas billing parameters.
- **Panel section visibility**: expose `seccion_*_habilitada` in API response so frontend can show/hide sections without hardcoding service names.
