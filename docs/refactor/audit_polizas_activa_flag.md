# Auditoría — Campo `activa` en pólizas

> **Fecha:** 2026-06-11  
> **Tarea:** PASO-B-POLIZAS-FLAGS — verificar consumo de `polizas[*].activa`

---

## Evidencia

| Componente | Archivo | Línea | Consume `activa` | Evidencia |
|------------|---------|-------|------------------|-----------|
| UserInputLoader | `modules/calculator_motor/adapters/user_input_loader.py` | 250 | **sí** | `activa = bool(p.get("activa", False))` — lectura directa del dict de entrada |
| PolizaInput (model) | `modules/panel/models/panel.py` | 386 | **sí** | `return self.porcentaje_poliza * self.porcentaje_atribuible if self.activa else 0.0` — `tasa_efectiva` retorna 0 si inactiva |
| PolizaContractual (model) | `modules/panel/models/panel.py` | 417 | **sí** | Mismo patrón: `return self.pct_poliza * self.pct_atribuible if self.activa else 0.0` |
| NexaPricingEngine | `modules/calculator_motor/engine.py` | 306 | **sí** | `and p.activa` — filtro en iteración de pólizas del pipeline |
| CostosFinancierosCalculator | `modules/calculator_motor/formulas/costos_financieros/calculator.py` | 144 | **sí** | `(p for p in polizas_vigentes if p.is_comision_administracion and p.activa)` |
| VisionTarifasReglas | `modules/vision_tarifas/reglas.py` | 297, 467 | **sí** | `and p.activa` en filtros de pólizas para visión de tarifas |
| VisionImprimibleBuilder | `modules/vision_imprimible/builders/vision_datasets_builder.py` | 151 | **sí** | `if not pol.activa: continue` — excluye pólizas inactivas de la visión |
| AuditWriter | `modules/audit/writer.py` | 87 | **sí** | `activas = [poliza for poliza in polizas_usuario if poliza.activa]` — audit trail filtra por activa |
| SimulationContextBuilder | `modules/calculator_motor/context_builder.py` | 144 | **sí** | `activa = p.activa` — propaga el campo al model de dominio |

---

## Veredicto

**CONSUMED**

El campo `activa` es leído por `UserInputLoader` desde `request.json`, propagado a través de `SimulationContextBuilder` hasta `PolizaContractual`, y consumido activamente en:
- Cálculo de `tasa_efectiva` (gating numérico: 0.0 si inactiva)  
- Filtros en motor de costos financieros  
- Filtros en visión de tarifas  
- Audit trail  

Una póliza con `activa=False` **no contribuye** a costos de pólizas ni a `tasa_efectiva`.

---

## Acción aplicada

Los 6 flags VALUE_UPDATE de `v28_input_mapping.md §2` aplicados en `request/request.json`:

| Nombre póliza | Antes | Después | Evidencia V2-8 |
|---------------|:-----:|:-------:|----------------|
| Póliza de Seriedad | `true` | `false` | Panel fila 38, V2-8=False |
| Poliza de rc cruzada | `true` | `false` | Panel fila 42, V2-8=False |
| poliza de IRF | `true` | `false` | Panel fila 43, V2-8=False |
| Póliza de Responsabilidad | `true` | `false` | Panel fila 44, V2-8=False |
| Otros impuestos | `true` | `false` | Panel fila 46, V2-8=False |
| Responsabilidad Civil Protección de Datos | `true` | `false` | Panel fila 50, V2-8=False |

Pólizas sin cambio (MATCH o fuera de scope): Cumplimiento (MATCH), Salarios (MATCH), Calidad (MATCH), Comisión Administración (MATCH).

---

## Impacto en goldens

Los golden tests (`tests/golden/`) usan fixtures propias (`vt_v27_real_request.json`, etc.) — no leen `request/request.json`. Las 42 fallas observadas son GOLDEN-001 pre-existente (SMMLV productiva 2026 vs frozen v2-7). Sin regresión nueva atribuible a este cambio.
