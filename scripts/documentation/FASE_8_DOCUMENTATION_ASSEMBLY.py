#!/usr/bin/env python3
"""
FASE 8: Architecture Documentation Assembly
Creates comprehensive markdown document that can be converted to PDF/Word.
"""

import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path("/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa")
DOCS_DIR = PROJECT_ROOT / "docs"
DIAGRAMS_DIR = PROJECT_ROOT / "FASE7_DIAGRAMS"
OUTPUT_DIR = PROJECT_ROOT / "deliverables"
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_MARKDOWN = OUTPUT_DIR / "NEXA_Architecture_Complete.md"

def read_markdown_file(filepath: Path) -> str:
    """Read markdown file content."""
    if not filepath.exists():
        return f"\n[File not found: {filepath.name}]\n"

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def generate_front_matter() -> str:
    """Generate front matter."""
    return f"""# NEXA — Simulador de Precios BPO

## Documentación Arquitectónica Integral

**Version:** 3.0
**Date:** 2026-05-31
**Classification:** Confidential
**Audience:** Arquitectos, Desarrolladores, Auditores, DevOps, Administración

---

## Resumen Ejecutivo

**Propósito:** NEXA es un motor de simulación de costos y precios determinístico para operaciones de TI/BPO, con capacidad de parity Excel y auditoría completa. Implementa Clean Architecture + Domain-Driven Design con versionado inmutable y modos certificados para cumplimiento regulatorio.

**Capacidades Principales:**
- 10-layer deterministic pipeline
- 4 visions: Cost To Serve, Tarifas, P&G, Imprimible
- Excel V2-7 parity certified (100%)
- Parametrization versioning (HR, GN, OP modules)
- Azure-ready serverless architecture
- Lineage & audit trail (immutable)
- Risk scoring + contingency modeling

**Stack Técnico:**
- Python 3.9+ | Decimal precision | Clean Architecture | DDD
- Azure: APIM, Functions, Cosmos DB, Storage, Key Vault
- CI/CD: GitHub Actions | Observability: Application Insights

**Flujo Entrada → Salida:**
- **ENTRADA:** Excel V2-7 panels + Panel selection + Cadenas A/B/C + Escenarios comerciales
- **PROCESAMIENTO:** 10-layer pipeline (deterministic, parallelizable)
- **SALIDA:** Cost To Serve | Tarifas | P&G (60-month) | Imprimible | KPIs | Risk Assessment

**Timeline & Producción:**
- En producción desde 2024
- Version 3.0: Refactor nomenclatural + cargo_tipo + versionado
- Azure migration: Q3 2026 (4-phase roadmap)
- Estimated cost: $600–1,100/mes en Azure

---

## Tabla de Contenidos

### Capítulos Principales
1. Visión General del Sistema
2. Arquitectura de Software
3. Modelo de Datos
4. API Reference
5. Motor de Cálculo (10-Layer Pipeline)
6. Reglas de Negocio Completas
7. Visions (CTS, Tarifas, P&G, Imprimible)
8. Matriz de Trazabilidad
9. Versionado y Modos Certificados
10. Arquitectura Azure Objetivo

### Apéndices
- Apéndice A: FORMULAS REFERENCE
- Apéndice B: BUSINESS RULES CATALOG
- Apéndice C: COMPLETE TRACEABILITY MATRIX
- Apéndice D: DATA DICTIONARY
- Apéndice E: API CONTRACTS
- Apéndice F: BUSINESS GLOSSARY
- Apéndice G: DIAGRAMAS (12 diagramas)
- Apéndice H: MAINTENANCE GUIDE

---

"""

def generate_chapter_1() -> str:
    """Generate Chapter 1: Vision General."""
    return """# CAPÍTULO 1: Visión General del Sistema

## 1.1 Contexto BPO

NEXA nace de la necesidad de simular costos y precios determinísticos para operaciones de BPO complejas, donde múltiples cadenas de servicio (A/B/C) pueden activarse según escenarios comerciales, y donde la trazabilidad completa (Excel → Backend → API) es crítica para auditoría financiera.

Las operaciones de servicios compartidos requieren:
- **Determinismo:** Mismo input siempre produce mismo output
- **Trazabilidad:** Auditoría completa de cada valor calculado
- **Versionado:** Control de versiones de parametrización
- **Escalabilidad:** Cálculos rápidos para 1,000+ contratos
- **Conformidad:** Cumplimiento regulatorio (SOC2, GDPR, auditoría financiera)

## 1.2 Componentes Principales

| Componente | Responsabilidad |
|------------|-----------------|
| **Motor de Cálculo** | 10-layer pipeline determinístico que procesa entrada y produce visions |
| **Versionado** | Parametrization inmutable con historial completo de cambios |
| **Visions** | 4 perspectivas (CTS, Tarifas, P&G, Imprimible) del mismo cálculo |
| **Auditoría** | Lineage graph que traza cada valor desde origen hasta salida |

## 1.3 Cadenas A/B/C

NEXA soporta 3 cadenas de costo/ingreso:

| Cadena | Descripción | Ejemplos |
|--------|-------------|----------|
| **A** | Base operational (nomina, no-payroll fijo) | Salarios, beneficios fijos |
| **B** | Variable según volumen (escalados, comisiones variables) | Bonos, comisiones, escalados |
| **C** | Riesgos y contingencias (seguros, provisiones) | Seguros, provisiones, contingencias |

Cada cadena:
- Se activa condicionalmente según reglas de negocio
- Se proyecta en P&G por 60 meses
- Se desglosa en CTS por componente
- Aparece en Tarifas como línea separada

## 1.4 Escenarios Comerciales

Un simulación puede ejecutarse con múltiples escenarios simultáneamente, permitiendo análisis de sensibilidad (optimista, base, pesimista) en una sola ejecución.

Ejemplo:
```
EscenarioComercial("Base"): escalado = 1.0, margen = 15%
EscenarioComercial("Optimista"): escalado = 1.1, margen = 18%
EscenarioComercial("Pesimista"): escalado = 0.9, margen = 12%
```

Cada escenario produce:
- Tarifas independientes
- P&G independiente
- KPIs independientes
- Risk scores independientes

## 1.5 Casos de Uso

1. **Precificación de nuevos contratos** (pricing engine)
2. **Análisis de rentabilidad** con diferentes cadenas
3. **Proyección financiera** (P&G 60-month)
4. **Evaluación de riesgo** (scoring + contingencies)
5. **Auditoría post-firmado** (verificación de parity)
6. **Reporting ejecutivo** (Imprimible vision)
7. **Benchmarking** (comparar con contratos anteriores)

---

"""

def generate_chapter_11() -> str:
    """Generate Chapter 11: Maintenance Guide."""
    return """# CAPÍTULO 11: Guía de Mantenimiento y Evolución

## 11.1 Agregar Nueva Calculator al Pipeline

El pipeline de 10 capas es extensible. Para agregar una nueva calculator:

1. **Crear clase** que hereda de `BaseCalculator`
2. **Implementar método** `execute(context)` que devuelve contexto enriquecido
3. **Registrar en** `PricingPipeline.layers` en el orden correcto
4. **Escribir tests unitarios** (mocking de dependencias)
5. **Validar que no rompe** parity Excel

Ejemplo:
```python
class MiNuevaCalculator(BaseCalculator):
    def execute(self, context: PricingContext) -> PricingContext:
        # Calcular algo nuevo
        context.mi_resultado = calcular_mi_logica(context)
        return context
```

## 11.2 Agregar Campo a Vision

Si necesitas agregar un campo nuevo a una vision (ej: CostToServe):

1. Agregar field a dataclass (ej: `ResultadoCTS`)
2. Implementar lógica de cálculo en vision builder correspondiente
3. Agregar a schema OpenAPI (`contracts/api_v1/schema/*.schema.json`)
4. Escribir tests de integración (request → vision with new field)
5. Documentar en `CAP_7_Visions.md`

## 11.3 Cambiar Fórmula sin Romper Parity

Cuando detectas un bug en una fórmula pero necesitas mantener parity Excel temporalmente:

1. Implementar nueva fórmula en nuevo método (ej: `calculate_ica_gross_up_v2`)
2. Crear feature flag en `VersionRegistry` para activar condicional
3. Ejecutar tests de parity comparando v1 vs v2 resultados
4. Una vez validado, switchear flag y deprecate v1
5. Aguardar 2 releases antes de remover v1 (backward compatibility)

## 11.4 Versionar Cambios en Parametrización

Los datos de parametrización (ratios HR, escalados GN, etc.) son versionados automáticamente:

1. Modificar archivo Excel o actualizar `storage/parametrization/`
2. Sistema captura cambio automáticamente (SHA-256)
3. `VersionRegistry.register_parametrization_update()` crea snapshot
4. Cada simulación incluye `@parametrization_version_id`
5. Para rewind: `VersionRegistry.load_version(version_id)` recarga snapshot

## 11.5 Agregar Nueva Cadena/Servicio

Si necesitas agregar una nueva cadena de costo (ej: Cadena D - 'Servicios Especializados'):

1. Definir `CadenaD` dataclass con campos específicos
2. Extender `ModeladorCadenas` para calcular `CadenaD`
3. Agregar `CadenaD` a cada vision (CTS, Tarifas, P&G, Imprimible)
4. Actualizar business rules (ej: condiciones de activación, rampup)
5. Migrar parametrización Excel (agregar columnas)
6. Ejecutar parity tests (Excel vs backend para todas las cadenas)

## 11.6 Estrategia de Rollback

En caso de bug crítico en producción:

1. Revert último commit que afecta cálculo (`git revert hash`)
2. Ejecutar baseline validation contra últimos 10 simulations
3. Si parity OK: deploy versión anterior
4. Si parity falla: investigar en branch feature, no cambiar main
5. Documentar en `CHANGES_SUMMARY.md`

## 11.7 Estrategia de Testing

Testing se organiza en 3 niveles:

### UNIT TESTS
Cada calculator tiene tests unitarios. Mock todas las dependencias. Target: >85% code coverage.

### INTEGRATION TESTS
Prueba flujo completo (request → pipeline → vision) con datos reales. Casos: Bancamia, WhatsApp, Contract Z. Validar outputs contra Excel.

### PARITY TESTS
Compara backend vs Excel V2-7 para 100+ campos en 50+ contracts. Target: 100% parity en valores críticos (CTS, Tarifas).

## 11.8 Disaster Recovery Runbooks

### SCENARIO: Cosmos DB corrupted

1. Alert: Inconsistent query results
2. Failover a secondary region (RTO < 5 min)
3. Restore from backup (RPO < 1 min, ~90 min de datos)
4. Verify simulation results match pre-corruption
5. Failback when primary repaired

### SCENARIO: Function cold start spike

1. Monitor: AppInsights alerts on P95 latency > 5s
2. Scale: Auto-scale Functions to 10 instances
3. Cache: Pre-warm parametrization in memory
4. Investigate: Check code for large imports/initializations
5. Optimize: Move initialization outside handler

### SCENARIO: Data drift detected

1. Alert: VersionRegistry detects parametrization change
2. Isolate: Mark affected versions as 'drifted'
3. Investigate: Compare before/after parametrization snapshot
4. Decide: Revert parametrization or accept drift
5. Communicate: Notify audit team of decision

---

"""

def generate_conclusion() -> str:
    """Generate conclusion."""
    return """# CONCLUSIÓN

## Estado Actual

NEXA está en producción desde 2024, version 3.0 a fecha 2026-05-31. La arquitectura ha alcanzado madurez con:

- 100% parity con Excel V2-7
- 10-layer pipeline determinístico y parallelizable
- Versionado inmutable de parametrización
- 4 visions con trazabilidad completa
- Lineage & audit trail certified
- Azure-ready serverless architecture

## Roadmap

| Timeline | Iniciativas |
|----------|-------------|
| **Q3 2026** | Migración a Azure (4 fases) • Implementación APIM + Functions • Cosmos DB global replication |
| **Q4 2026** | Advanced analytics • ML-based risk prediction • Dynamic pricing optimization |
| **2027** | Managed agents • Automated parametrization updates • API GraphQL opcional |

## Soporte

- **Propietario arquitectónico:** NEXA Architecture Team
- **GitHub:** [NEXA Repository]
- **Slack:** #nexa-architecture
- **Email:** CloudArchitect@company.com

---

## Historial de Cambios

### Version 3.0 (2026-05-31)
- Refactoring nomenclatural completo
- Fix cargo_tipo para escenarios múltiples
- Arquitectura Azure objetivo detallada
- 12 diagramas Mermaid embebidos
- Matriz de trazabilidad 65+ entradas
- Guía de mantenimiento exhaustiva

### Version 2.7 (2025-12-15)
- ICA gross-up finalizado
- Pólizas per-cadena implementadas
- Vision Imprimible agregada

### Version 2.5 (2025-10-01)
- Lanzamiento inicial a producción
- 100% parity Excel V2-5

---

"""

def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("FASE 8: Generating Complete Architecture Documentation")
    print("="*80)

    # Start building document
    content = []

    print("\n1. Adding front matter...")
    content.append(generate_front_matter())

    # Chapter 1
    print("2. Adding Chapter 1...")
    content.append(generate_chapter_1())

    # Chapters 2-10
    chapter_files = {
        2: "CHAPTER_2_ARQUITECTURA_SOFTWARE.md",
        3: "CAP_3_Modelo_de_Datos.md",
        4: "API_REFERENCE.md",
        5: "CAP_5_Motor_de_Calculo.md",
        6: "CAP_6_Reglas_de_Negocio.md",
        7: "CAP_7_Visions.md",
        8: "CAP_8_Matriz_de_Trazabilidad.md",
        9: "CHAPTER_9_VERSIONADO_MODOS_CERTIFICADOS.md",
        10: "CHAPTER_10_ARQUITECTURA_AZURE_OBJETIVO.md",
    }

    for ch_num, filename in chapter_files.items():
        filepath = DOCS_DIR / filename
        if filepath.exists():
            print(f"3. Adding Chapter {ch_num}...")
            ch_content = read_markdown_file(filepath)
            # Prepend chapter number if not already there
            if not ch_content.startswith(f"# CAPÍTULO {ch_num}"):
                ch_content = f"# CAPÍTULO {ch_num}\n\n" + ch_content
            content.append(ch_content)
        else:
            print(f"   WARNING: Chapter {ch_num} file not found: {filename}")

    # Chapter 11
    print("4. Adding Chapter 11...")
    content.append(generate_chapter_11())

    # Appendices
    appendix_map = {
        "A": ("FORMULAS REFERENCE", "FORMULAS.md"),
        "B": ("BUSINESS RULES CATALOG", "BUSINESS_RULES.md"),
        "C": ("COMPLETE TRACEABILITY MATRIX", "TRACEABILITY_MATRIX.md"),
        "D": ("DATA DICTIONARY", "DATA_MODEL.md"),
        "E": ("API CONTRACTS", "API_REFERENCE.md"),
        "F": ("BUSINESS GLOSSARY", "refactor/BUSINESS_GLOSSARY.md"),
    }

    for app_key, (app_title, filename) in appendix_map.items():
        filepath = DOCS_DIR / filename
        if filepath.exists():
            print(f"5. Adding Appendix {app_key}...")
            app_content = read_markdown_file(filepath)
            header = f"\n\n# APÉNDICE {app_key}: {app_title}\n\n"
            content.append(header + app_content)
        else:
            print(f"   WARNING: Appendix {app_key} file not found: {filename}")

    # Diagrams
    print("6. Adding Diagrams section...")
    diagrams_header = "\n\n# APÉNDICE G: DIAGRAMAS\n\n"
    content.append(diagrams_header)

    diagrams = [
        ("1", "Request Flow End-to-End", "DIAGRAM_01_Request_Flow_EndToEnd.md"),
        ("2", "10-Layer Pipeline Dependency", "DIAGRAM_02_Pipeline_Dependency_Graph.md"),
        ("3", "Vision Composition Hierarchy", "DIAGRAM_03_Vision_Composition_Hierarchy.md"),
        ("4", "Lineage: Ingreso Neto Example", "DIAGRAM_04_Lineage_Ingreso_Neto.md"),
        ("5", "Versioning & Certified Mode", "DIAGRAM_05_Versioning_CertifiedMode.md"),
        ("6", "Azure Architecture Overview", "DIAGRAM_06_Azure_Architecture.md"),
        ("7", "Domain Model ER", "DIAGRAM_07_Domain_Model_ER.md"),
        ("8", "Module Dependencies Graph", "DIAGRAM_08_Module_Dependencies.md"),
        ("9", "Cadenas Relationships", "DIAGRAM_09_Cadenas_Relationships.md"),
        ("10", "FTE Volumetric Calculation", "DIAGRAM_10_FTE_Volumetric.md"),
        ("11", "Margin Factor Breakdown", "DIAGRAM_11_Margin_Factor_Breakdown.md"),
        ("12", "Vision Activation Decision Tree", "DIAGRAM_12_Vision_Activation_DecisionTree.md"),
    ]

    for diag_num, diag_title, diag_file in diagrams:
        diag_path = DIAGRAMS_DIR / diag_file
        if diag_path.exists():
            print(f"   ✓ Diagram {diag_num}")
            diag_content = read_markdown_file(diag_path)
            diagram_section = f"\n## Diagrama {diag_num}: {diag_title}\n\n{diag_content}\n"
            content.append(diagram_section)

    # Conclusion
    print("7. Adding conclusion...")
    content.append(generate_conclusion())

    # Write output file
    full_content = "".join(content)
    with open(OUTPUT_MARKDOWN, 'w', encoding='utf-8') as f:
        f.write(full_content)

    # Calculate metrics
    lines = full_content.split('\n')
    words = sum(len(line.split()) for line in lines)

    print("\n" + "="*80)
    print("FASE 8 COMPLETE")
    print("="*80)
    print(f"\nPrimary Deliverable:")
    print(f"  ✓ NEXA_Architecture_Complete.md")
    print(f"\nDocument Metrics:")
    print(f"  Lines: {len(lines):,}")
    print(f"  Words: {words:,}")
    print(f"  File size: {OUTPUT_MARKDOWN.stat().st_size / (1024*1024):.1f} MB")
    print(f"\nMetadata:")
    print(f"  Title: NEXA — Simulador de Precios BPO")
    print(f"  Version: 3.0")
    print(f"  Date: 2026-05-31")
    print(f"  Classification: Confidential")
    print(f"\nNext Steps:")
    print(f"  1. Convert MD → PDF using 'pandoc' or 'grip':")
    print(f"     pandoc -f markdown -t pdf -o NEXA_Architecture_Updated.pdf NEXA_Architecture_Complete.md")
    print(f"  2. Convert MD → Word using 'pandoc':")
    print(f"     pandoc -f markdown -t docx -o NEXA_Architecture_Updated.docx NEXA_Architecture_Complete.md")
    print(f"\nOutput: {OUTPUT_MARKDOWN}")

if __name__ == "__main__":
    main()
