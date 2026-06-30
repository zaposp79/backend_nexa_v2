# ANÁLISIS DE COMPLEJIDADES Y SU IMPACTO — V2-7

---

## 1. Dimensiones de Complejidad en el Modelo

El modelo V2-7 no tiene un "nivel de complejidad" explícito como variable. La complejidad se expresa a través de:

1. **Mark up operativo** (`Panel!C69`): rango 0%–8%, sugerido por nivel
2. **Contingencias** (operativa + comercial): adicionales al mark up
3. **Puntaje de Riesgo** (hoja Riesgo): cualitativo, no automático

---

## 2. Mark Up por Complejidad

### Valores del rango definidos en Panel (D69:E69)

| Rango | Valor Mínimo | Valor Máximo |
|-------|-------------|-------------|
| Mark up complejidad/horarios | 2% | 8% |

### Impacto del Mark Up en Pricing

```python
# Fórmula de pricing con markup:
ingreso = costo / ((1-margen) × (1-cont_op) × (1-cont_com) × (1-markup) × (1+descuento))

# Ejemplo con margen=18%, markup=0% vs 5% vs 8%:
costo = 100
margen = 0.18
cont_op = cont_com = descuento = 0

sin_markup    = 100 / (0.82 × 1.0 × 1.0 × 1.0 × 1.0) = 121.95
con_5_markup  = 100 / (0.82 × 1.0 × 1.0 × 0.95 × 1.0) = 128.37
con_8_markup  = 100 / (0.82 × 1.0 × 1.0 × 0.92 × 1.0) = 132.55

# Diferencia 0% vs 8%: +8.7% en el precio final
```

---

## 3. Factores de Complejidad en la Hoja Riesgo

### Preguntas y Opciones de Riesgo

| ID | Factor | Categoría | Opciones |
|----|--------|-----------|---------|
| 1 | Clasificación de oportunidad | Cliente | Negocio >1000 SMLV o >200M/mes |
| 2 | Tipo de cliente | Cliente | Fuera del Grupo Aval, sin referido |
| 3 | Período de pago | Cliente | Pago >60 días |
| 4 | Experiencia con cliente | Cliente | Sin historial previo |
| 5 | Presupuesto de imprevistos | Cliente | Sí (>$0) |
| 6 | Alertas activadas | Operativo | 3 alertas |
| 7 | Complejidad | Operativo | Alta complejidad multicanal ≥10 |
| 8 | Capacitaciones | Operativo | Capacitación >20 días |
| 9 | Rotación | Operativo | Rotación alta >10% |
| 10 | Dependencia de terceros | Operativo | Alta dependencia >50% |

### Ponderación

```python
puntaje_operativo = promedio(respuestas_operativas) × 0.60
puntaje_cliente   = promedio(respuestas_cliente) × 0.40
riesgo_total = puntaje_operativo + puntaje_cliente
```

### Nota: El riesgo es **informativo** en V2-7, no modifica automáticamente el precio.

El comercial debe interpretar el puntaje y ajustar manualmente el mark up, contingencias o imprevistos.

---

## 4. Complejidad de Canales (Multicanal)

El modelo no penaliza explícitamente la complejidad multicanal en los costos, pero:

1. **Más canales activos** → más FTE en Condiciones Cadena A → mayor costo base
2. **Canales digitales (Cadena B)** → costos adicionales de plataforma por sesión/transacción
3. **Cadena C activa** → costo adicional del proveedor

### Impacto en Minutos Improductivos (Canal Voz vs Digital)

Para Canal Voz:
```
Tiempo improductivo = breaks(30min) + capacitación + deslogueos(5min) + coaching(5min) + pausa(5min)
Tiempo logueado = Tiempo programado × (1 - factor_improductivo) × (1 - ausentismo)
```

Para canales digitales (WhatsApp, WebChat, Mensajes):
- Los mismos factores aplican (mismo agente puede manejar múltiples canales)
- La tarifa por transacción absorbe la diferencia de productividad

---

## 5. Complejidad en Staffing

El ratio de staffing cambia según la complejidad del equipo configurado:

```python
# Cargos de Staff opcionales (Condiciones Cadena A):
# Alta complejidad: incluye Director de Cuentas + Director de Performance
# Media: solo coordinadores y QA
# Baja: mínimo staff de soporte

# Ratio de Director de Cuentas (C25=TRUE habilitado):
ratio = FTE_agentes / FTE_director  # ej: 40/1 = 1 director por cada 40 agentes
```

Cuantos más cargos de staff se habiliten en `Condiciones Cadena A`, mayor el costo per FTE operativo.

---

## 6. Sensibilidad al % Ausentismo y Rotación

### Impacto del Ausentismo

```python
# Horas logueadas (para tarifa por tiempo):
horas_log = horas_prog × (1 - ausentismo) × factor_tiempo_improductivo

# Con ausentismo=6.5% vs 12%:
# 6.5%: factor = 0.935 → menor denominador → mayor tarifa por hora
# 12%:  factor = 0.88  → aún menor → tarifa aún más alta

# El costo de la operación NO baja con ausentismo (hay que pagar igual los FTE)
# pero las horas entregadas bajan → la tarifa por hora sube
```

### Impacto de la Rotación

```python
# Costo de capacitación por rotación (Nomina Loaded):
costo_cap_rotacion_mes = dias_capacitacion × tarifa_dia × (FTE × pct_rotacion)

# Con rotación=8.5% vs 15%:
# 8.5%:  costo_rotacion = dias × tarifa × FTE × 0.085
# 15%:   costo_rotacion = dias × tarifa × FTE × 0.15 → +76% más caro

# También afecta exámenes médicos y estudios de seguridad
```

---

## 7. Complejidad Contractual (Período de Pago)

El período de pago activa el costo de financiación:

```python
# Solo si Panel!C21 = "Sí" (costo financiación habilitado)
costo_fin = costo_mensual × tasa_mensual × meses_financiados
meses_financiados = (periodo_pago_dias - 30) / 30

# Período 30 días: costo_fin = 0 (no hay financiación)
# Período 60 días: 1 mes de financiación
# Período 90 días: 2 meses de financiación
# Tasa mensual = 1.53% (Panel!L10)
```

El costo de financiación se suma a los costos de cada canal y se incluye en la tarifa.

---

## 8. Complejidad en Cadena C (Proveedor)

Cadena C añade complejidad de integración:

```python
# Sub-componentes de costo de integración:
costo_integracion = opex_fijo_c + inversiones_c + equipo_integracion

# Equipo de integración: recursos de proyecto (no operativos)
# Se cobra durante los primeros N meses (de configuración)

# HITL (Human-in-the-Loop): cuando el bot no puede resolver, escala a agente
costo_hitl = volumen_escalamientos × costo_por_escalamiento
```
