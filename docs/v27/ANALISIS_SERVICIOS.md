# ANÁLISIS POR SERVICIO / CANAL / MODALIDAD — V2-7

---

## 1. Servicios Soportados

| Servicio | Código Panel | Ramp-up | Margen obj. A | Ausentismo histórico | Rotación histórica |
|----------|-------------|---------|--------------|---------------------|-------------------|
| Cobranzas | "Cobranzas" | 85%→92%→100% | 18% | 7.35%–9.72% prom ~8.6% | 9.31%–15.77% prom ~11.5% |
| SAC | "SAC" | 85%→92%→100% | 18% | 7.58%–8.65% prom ~8.2% | 6.09%–9.31% prom ~7.7% |
| Ventas Multicanal | "Ventas Multicanal" | 85%→92%→100% | 18% | 9.63%–13.14% prom ~10.1% | 8.0%–10.53% prom ~9.5% |
| SACO | "SACO" | 85%→92%→100% | 10.5% | 5.68%–9.52% prom ~8.0% | 7.79%–11.06% prom ~9.6% |
| Plataformas | "Plataformas" | No aplica (factor=0) | 15% | 0% | 0% |
| Captura de Datos | "Captura de Datos" | No aplica | 32.92% | 0% | 0% |

### Diferenciación por servicio en el modelo:

1. **Margen Objetivo (Cadena A)**: varía por servicio (Panel!C63 ← lookup en Rot,Ausent!C28:C34)
2. **Ausentismo**: se propone como default según servicio (usuario puede sobreescribir en Panel!C19)
3. **Rotación**: ídem (Panel!C20)
4. **Ramp-up**: tabla Rot,Ausent!B38:BI43 — todos los servicios operativos tienen la misma curva (85/92/100)
5. **SACO/Ventas**: activan módulo especial de comisiones por ventas (Panel rows 118–170)

---

## 2. Canales Soportados

### Inbound
| Canal | Código | FTE/Vol | Unidad pricing típica |
|-------|--------|---------|----------------------|
| Voz | "Voz" | FTE | FTE/mes o min logueado |
| IVR | "IVR" | FTE | FTE/mes |
| WebChat | "WebChat" | FTE | FTE/mes o transacción |
| Mensajes | "Mensajes" | FTE | FTE/mes o transacción |
| WhatsApp | "WhatsApp" | FTE | FTE/mes o sesión |
| Correo | "Correo" | FTE | FTE/mes o correo |
| Otros | "Otros" | FTE | FTE/mes |

### Outbound
| Canal | Código | FTE/Vol | Notas |
|-------|--------|---------|-------|
| Voz | "Voz" | FTE | igual que Inbound |
| IVR | "IVR" | FTE | — |
| WebChat | "WebChat" | FTE | — |
| Mensajes | "Mensajes" | FTE | — |
| WhatsApp | "WhatsApp" | FTE | — |
| Correo | "Correo" | FTE | — |
| Otros | "Otros" | FTE | — |
| Fuerza de ventas | "Fuerza de ventas" | FTE | especial SACO/Ventas |

---

## 3. Configuración de Volumetría por Canal

### Panel de Control General — Tabla de Volumetría Inbound (K18:R25)

```
Columnas: FTE (Cadena A) | Volumen (Cadena B) | Volumen (Cadena C)
Filas   : Voz | IVR | WebChat | Mensajes | WhatsApp | Correo | Otros
```

Ejemplo Bancamia:
```
Voz:      FTE=25,  Vol_B=1000,  Vol_C=10000
WhatsApp: FTE=15,  Vol_B=15000, Vol_C=0
```

**Fórmulas de totales:**
```excel
L26 = SUM(L19:L25)   # FTE total Inbound
M26 = IF(M17=TRUE, IF(O9<>"", SUM(M19:M25)*O9, SUM(M19:M25)), 0)
#    Cadena A activa → si hay TMO, ajusta FTE por TMO
N26 = IF(N17=TRUE, SUM(N19:N25), 0)   # Cadena B activa → volumen total
O26 = IF(O17=TRUE, SUM(O19:O25), 0)   # Cadena C activa → volumen total
```

### Participación por cadena (Panel!M52:O53)

```excel
M52 = SUM(M44:M51)   # FTE/Vol Cadena A por canal
N52 = SUM(N44:N51)   # FTE/Vol Cadena B por canal
O52 = SUM(O44:O51)   # FTE/Vol Cadena C por canal
L52 = SUM(M52:O52)   # Total

M53 = M52/$L$52      # Participación Cadena A
N53 = N52/$L$52      # Participación Cadena B
O53 = O52/$L$52      # Participación Cadena C
```

---

## 4. Modalidades (Inbound / Outbound)

### Inbound
- Activado por: `Panel!M17 = TRUE` (Cadena A Inbound) / `Panel!N17` (B) / `Panel!O17` (C)
- Perfiles en `Condiciones Cadena A!E14`: `"Inbound"`
- Costos en Nomina Loaded filtrados por fila `"Inbound"`

### Outbound
- Activado por: `Panel!M30 = TRUE` (Cadena A Outbound) / `Panel!N30` (B) / `Panel!O30` (C)
- Perfiles en `Condiciones Cadena A!E14`: `"Outbound"`
- Costos en Nomina Loaded filtrados por fila `"Outbound"`

---

## 5. Comportamiento del TMO (Tiempo Medio de Operación)

El TMO es crítico para el canal Voz y para calcular FTE a partir de volumen:

```excel
# Condiciones Cadena A!E8:
TMO_segundos = 522.2  # hardcode (promedio de Voz)

# Conversión TMO → horas:
TMO_horas = TMO_seg / 3600 = 0.145 horas/interacción

# FTE desde volumen (si se usa):
FTE_requerido = (volumen_interacciones × TMO_horas) / (horas_productivas_por_FTE)
```

La columna `O9` en Panel contiene el FTE calculado desde TMO para Cadena A si el usuario prefiere usar volumen en lugar de FTE directo.

---

## 6. Módulo SACO/Ventas (Componente de Resultados)

Activo cuando: `Panel!C5 IN ["SACO", "Ventas Multicanal"]`

### Estructura de Comisiones (Panel rows 118–170)

```
Niveles de productividad: 1, 2, 3, 4, 5
│
├── Cantidad de Asesores: [15, 15, 15, 15, 15]
├── Ventas TC por Asesor: [12, 21, 40, 41, 41]
├── Ventas Seguro P1:     [2.88, 5.04, 9.6, 9.84, 9.84]
├── Ventas Seguro P2:     [1.44, 2.52, 4.8, 4.92, 4.92]
├── Ventas Seguro P3:     [0.48, 0.84, 1.6, 1.64, 1.64]
│
├── Comisión TC:    [21500, 23660, 30789, 35573, 35573] COP/venta
├── Comisión Seg1:  [13000, 13000, 13000, 13000, 13000] COP/venta
├── Comisión Seg2:  [15000, 15000, 15000, 15000, 15000] COP/venta
└── Comisión Seg3:  [21000, 21000, 21000, 21000, 21000] COP/venta
```

### Fórmulas:

```python
# Ingreso Variable por Asesor (Panel!C137):
ingreso_var_asesor = (
    ventas_tc × comision_tc
    + ventas_seg1 × comision_seg1
    + ventas_seg2 × comision_seg2
    + ventas_seg3 × comision_seg3
)

# Valor Total por Asesor (Panel!C141):
carga_prestacional = 0.42  # hardcode
valor_total = ingreso_var_asesor × (1 + carga_prestacional)

# Facturación Variable Total (Panel!C143):
aiu_niveles = [0.098, 0.113, 0.15, 0.18, 0.18]  # AIU por nivel
facturacion_variable = valor_total × (1 + aiu) × cantidad_asesores
```

---

## 7. Complejidades y su Impacto

### Variables de Complejidad (Panel!C69 — Mark up)

| Nivel de Complejidad | Mark up sugerido | Rango definido |
|---------------------|-----------------|----------------|
| Baja | 0% – 2% | 0%–8% (Panel!D69:E69) |
| Media | 2% – 5% | — |
| Alta multicanal ≥10 | 5% – 8% | — |

### Impacto del Markup en Tarifa:

```python
# Cada punto de markup sube el precio final:
precio_sin_markup = costo / (1 - margen)
precio_con_markup = costo / ((1 - margen) × (1 - markup))

# Ejemplo: margen=18%, markup=5%:
# Sin markup: precio = costo/0.82 = +22%
# Con markup: precio = costo/(0.82×0.95) = +28.5%
```

### Factor de Riesgo (Hoja Riesgo)

La hoja Riesgo calcula un puntaje ponderado:
```python
puntaje_operativo = promedio(respuestas_operativas) × 0.60
puntaje_cliente   = promedio(respuestas_cliente) × 0.40
riesgo_total = puntaje_operativo + puntaje_cliente
```

Este puntaje **no alimenta directamente** ningún cálculo automático en V2-7. Es un indicador cualitativo para el comercial.
