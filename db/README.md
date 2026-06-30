# DB

## Propósito

`db` concentra el wiring de persistencia de la aplicación. Define cómo se
construyen repositorios, providers y stores usados por los módulos funcionales.

## Responsabilidades

- Construir el contenedor de dependencias de FastAPI.
- Exponer dependencias reutilizables para routers y servicios.
- Seleccionar el provider de documentos configurado.
- Mantener puertos e implementaciones de persistencia.
- Aislar detalles de JSON o Cosmos detrás de contratos de infraestructura.

## Qué no hace este módulo

- No implementa fórmulas de negocio.
- No construye contratos de pantalla.
- No decide reglas comerciales.
- No orquesta casos de uso funcionales.

## Estructura interna

```text
db/
├── container.py
├── dependencies.py
├── factory.py
├── providers/
└── ports/
```

## Endpoints expuestos

`db` no expone endpoints. Sus componentes se consumen por inyección de
dependencias.

## Entradas y salidas principales

- Entrada: configuración de entorno y settings de aplicación.
- Salida: repositorios, stores y providers listos para ser usados por módulos.

## Dependencias relevantes

- Configuración compartida de la aplicación.
- Implementaciones de `DocumentStore`.
- Repositorios de módulos consumidores.

## Contratos públicos

El contrato importante de este paquete es de infraestructura: los módulos deben
depender de puertos y factories, no de detalles físicos del backend de
persistencia.

## Reglas de negocio y fuentes de cálculo

Este paquete no contiene reglas de negocio. Solo entrega infraestructura para
que otros módulos consulten o persistan sus datos.

## Pruebas relacionadas

- Pruebas de integración de API.
- Pruebas de repositorios y providers cuando existan.

## Consideraciones de mantenimiento

- Mantener `db` como composición técnica, no como módulo de dominio.
- Al cambiar backend de persistencia, conservar los contratos usados por los
  módulos funcionales.
