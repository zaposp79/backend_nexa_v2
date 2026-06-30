# Registro Priorizado de Gaps — Paridad Excel V2-7 ↔ Backend

> Consolidación F-final (entregables 7 + 10). Reúne todos los gaps descubiertos en las
> auditorías por hoja y por cadena. **Insumo de decisión** — sin propuestas de implementación.
> Evidencia detallada en los documentos referenciados (no se duplica aquí).
>
> **Tipo**: `cálculo` (qué número da) · `modelo` (decisión de negocio sobre qué se calcula) ·
> `presentación` (formato/enlace) · `contrato` (falta en JSON) · `mecanismo` (vía distinta, valor coincide) ·
> `verificación` (paridad de valor no comprobada) · `limpieza` (deuda técnica).
> **Estado**: Abierto · Resuelto · Cerrado (equivalente) · Bloqueado (oracle) · No-gap.
>
> Docs fuente: `VISION_IMPRIMIBLE_AUDIT_V2-7.md`, `VISION_TRACEABILITY_MATRIX.md`,
> auditorías P&G / Tarifas / CTS / Cadena A (Fases 1-4, en historial de sesión).

## 🔴 CRÍTICA — bloquea certificación de paridad / decisiones

| GAP | Tipo | Descripción (evidencia) | Impacto medido | Estado | Dependencias |
|-----|------|--------------------------|----------------|--------|--------------|
| **GAP-TAR-08** | cálculo | Cadena C: Tarifas lee `Costo Cadena C` filas **67-85** (28,2 B); P&G lee filas **95-457** (15,2 B). Bases disjuntas, factor 1,88×. Propaga a `C72`/`ingreso` headline. | **−45,66%** en C72 vs base P&G (backend usa base P&G ≈20,98 B; Excel C72=38,61 B) | Abierto | Requiere decisión de negocio (base autoritativa) + auditar fórmulas fuente filas 67-85 |
| **GAP-PYG-01** | cálculo | `P&G!BK30` (costo total acumulado) **incluye** Componente Financiero (BK65); backend acumulado lo **excluye**. | **+97,5%** sobreestimación de contribución/utilidad acumulada (Δ = BK65 = 2,02 B); **−10,46%** en costo total | Abierto | Decisión: ¿acumulado P&G incluye financiero? Afecta VI!H19 (`=BK30/E6`) |

## 🟠 ALTA — material, requiere decisión

| GAP | Tipo | Descripción | Impacto | Estado | Dependencias |
|-----|------|-------------|---------|--------|--------------|
| **GAP-IMP-04** | modelo | Aprobación: backend = 1 bool con `1000·SMMLV` (≈1,42 B); Excel = 3 niveles (Ger.Financiera ≥100M/mes, Ger.General ≥200M/mes, Alta Dir. ≥**1,0 B fijo**). | Umbral diverge **+42%**; backend puede sub-reportar aprobación | Abierto (TODO en `riesgo.py:213`) | Decisión de negocio sobre umbrales + facturación mensual |
| **GAP-IMP-01 / TAR-05** | contrato | `comparativo_escenarios` no incluye tarifa fija/variable por escenario (`Tarifas!C20:G21`) ni estado ★SELECCIONADO; además no se serializa (ver IMP-11). | Tabla VI filas 74-78 no reconstruible | Abierto | El builder produce `escenarios_detalle`; falta exponer + enriquecer |
| **GAP-IMP-11** | contrato | `comparativo_escenarios` (builder lo crea) **no se serializa** en el composite. | Sección 05 VI ausente del JSON | Abierto | `_vision_ejecutiva_sections` no lee `vi.comparativo_escenarios` |
| **GAP-CADENA-A-FASE4** | modelo | Margen ingreso A usa `panel.margen` (input); Excel deriva de tabla servicio (Rot!B29:B34 → 0,21). Storage tiene el valor correcto (`get_margen_minimo`, expuesto en `kpis.margen_minimo_requerido`) pero no se cablea al ingreso. | **+9,63%** en `ingreso_cadena_a` si se conmuta | Abierto (warning instrumentado, no destructivo) | Decisión de negocio: ¿fuente del margen? |

## 🟡 MEDIA — afecta valor o contrato, no bloqueante

| GAP | Tipo | Descripción | Estado | Dependencias |
|-----|------|-------------|--------|--------------|
| **GAP-TAR-01** | cálculo | `C72` backend = `C47+C67` (excluye Cadena B `C57`); Excel = `C47+C57+C67`. | Abierto (nulo si B inactiva; material si activa) | Requiere caso Cadena B activa |
| **GAP-TAR-02** | mecanismo | Backend acopla `VisionTarifas` a `pyg_por_mes`; Excel Tarifas es independiente (0 refs a P&G). | Abierto (efecto vía pyg) | Arquitectónico; ligado a GAP-TAR-08 |
| **GAP-TAR-03** | presentación | VI tarifa fija = `Tarifas!G47` (=0 para FTE); la real es `G45` (90 M). | Abierto | Enlace de campo; dato correcto existe (G45) |
| **GAP-IMP-02** | cálculo | CTS mensual VI!H19 = `P&G!BK30/E6`; backend usa `cost_to_serve.cts_ponderado`. | Abierto | Sub-caso de GAP-PYG-01 |
| **GAP-IMP-03** | contrato/present. | `estado_margen` (VI!N20) + banner aprobación (VI!S7) no expuestos como string. | Abierto | Composición de strings en builder |
| **GAP-IMP-06** | modelo | Volumen base VI!N38 = `Panel!L52`; backend = `cost_to_serve.vol_cadena_b`. | Abierto | Fuente distinta |
| **GAP-IMP-10** | contrato | `economics` (builder lo crea) no se serializa (`cts_mensual`, `escenario_referencia` sin hogar JSON). | Abierto | `_vision_ejecutiva_sections` no lee `vi.economics` |
| **GAP-IMP-12** | contrato | `evolucion_mensual` no serializado (derivable de `pyg_por_mes`); `N20` ausente. | Abierto (parcial: data derivable) | — |
| **GAP-PYG-04** | cálculo | Comisión Administración: Excel `C68`=SUMPRODUCT 3 bloques Pólizas; backend = `(base+fin)/fm × tasa`. | Abierto (equiv. condicional A-only) | Verificar paridad valor |
| **GAP-CTS-01** | contrato | `C200` (valor total) no en `ResultadoCostToServe`; expuesto vía `kpis.valor_total_deal`. | Abierto | Verificar `kpis.valor_total_deal == C186×(1+margen)` |

## 🟢 BAJA — deuda técnica / presentación menor

| GAP | Tipo | Descripción | Estado |
|-----|------|-------------|--------|
| GAP-IMP-05 | presentación | Componente fijo/variable sin label compuesto (`"FTE (70%)"`); falta `tipo`. | Abierto |
| GAP-IMP-07 | contrato | Sección 08 firmas (5 campos) no existe. | Abierto |
| GAP-IMP-09 | limpieza | `FichaDelDeal` dataclass muerto (serializer usa Panel directo). | Abierto |
| GAP-PYG-03 | cálculo | `+C71` (término ingreso bruto) ausente; hoy =0 (placeholder). | Abierto |
| GAP-PYG-06 | contrato | `tipo_servicio` (Call Center/Fuerza Ventas, P&G!G6) no expuesto. | Abierto |
| GAP-CTS-04 | mecanismo | Canal único Excel (C90 hardcoded "WhatsApp") vs lista backend (superset). | Abierto (intencional) |
| GAP-CTS-05 | modelo | Gate `canal_view` (IF servicio="SAC"). | Abierto (intencional) |
| F5-nuevo-1 | mecanismo | 3 bases de "costo total" coexisten (reglas_negocio.monto=Σpyg, cts.costo_total_acumulado=nativo, vision_tarifas.costo_total_scenario). | Registrar |
| F5-nuevo-2 | limpieza | `panel` duplica ~15 campos de `ficha_deal` (doble fuente de verdad). | Registrar |
| ICA storage | cálculo menor | ICA Bogota storage 0,00966 vs Panel display 0,01 (~3,4% del rate). | Abierto (inmaterial) |
| Crucero | cálculo menor | `Panel!C17 = 8000×1,051` (8408) vs input backend (8422), ~0,17%. | Abierto (inmaterial) |
| G35 mágico | cálculo | `HME!G35 = 752.815013404826` (volumetría 1 FTE), sin equivalente backend. | Abierto |

## ✅ RESUELTOS en esta sesión

| GAP | Resolución | Verificación |
|-----|------------|--------------|
| **GAP-A-02** (×12 hardcode `vision_tarifas`) | `×12` → `× n` (n=meses_contrato); A/B en misma base que C. | Escala 6/12/24m; **0 regresión** (48==48) |
| **GAP-A-01** (overwrite `engine.py:314-320`) | Eliminado; kpis/cts nativos; cifra escenario en `vision_tarifas.costo_total_scenario` (@property). Oracle repuntado a VT (A+). | B19/H19 parity verde; **0 regresión** |
| **Problema 3** (base split kpis) | Resuelto por P2; kpis monobase, reconcilia (`valor−costo=utilidad`). | Exacto |
| **GAP-PYG-05** (periodo pago I5) | Cerrado equivalente (Pólizas!D364=30 == Panel!C9=30). | — |
| **GAP-CTS-02** | No-gap: mecanismo coincide (`costo_total_acumulado == sum(m.costo_total)`). | — |
| SMMLV `riesgo.py` | Ya externalizado a storage; TODO(GAP-IMP-04) añadido. | — |

## ⛔ BLOQUEADO — oracle no ejecutable

| ID | Descripción | Causa | Desbloqueo |
|----|-------------|-------|-----------|
| GAP-PYG-08 / GAP-IMP-08 / TAR-04/06/07 | Paridad de **valor** celda-a-celda contra Excel real; "primer punto de divergencia" | No existe fixture que reproduzca el deal cacheado V2-7 (AMERICAS/Captura de Datos); esquema de fixtures derivado | Reconstruir el deal completo (Panel+Nómina+Cadena A/B/C+volumetría) en formato NUEVO, o disponer de outputs intermedios cacheados del Excel |

## Orden de ataque recomendado (por severidad × desbloqueo)

1. **Decisión de negocio (no requiere código):** GAP-TAR-08 (base Cadena C autoritativa), GAP-PYG-01 (financiero en acumulado), GAP-IMP-04 (umbrales aprobación), GAP-CADENA-A-FASE4 (fuente margen). Son las 4 que **bloquean paridad** y son decisiones, no bugs.
2. **Desbloquear oracle (habilitador):** reconstruir deal AMERICAS → permite cuantificar y certificar todo lo demás.
3. **Contrato (mecánico, bajo riesgo):** exponer comparativo_escenarios (IMP-11/01), economics (IMP-10), evolucion_mensual (IMP-12), estado_margen/banner (IMP-03) — el builder ya los produce.
4. **Presentación/limpieza:** GAP-TAR-03 (G45 vs G47), IMP-05/07/09, PYG-03/06, dedup panel/ficha.

## Criterio de éxito — estado

- *"¿De dónde salió este número?"* (Excel→fórmula→deps→parámetro→regla→builder→API): **alcanzado** para Visión Imprimible y Cadena A (docs F1-F7 + esta matriz).
- *"Backend == Excel certificado"*: **NO alcanzable** sin desbloquear el oracle (reconstrucción del deal). Hoy se tiene paridad de **fórmula/estructura** y **sensibilidad medida**, no paridad de **valor** contra el Excel real.
