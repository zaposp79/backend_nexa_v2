"""
tests/certification/
====================
Triple-Layer Financial Certification Harness.

Arquitectura:
  Layer 1 — Determinism        (test_layer1_determinism.py)
  Layer 2 — Cross-Consistency  (test_layer2_consistency.py)
  Layer 3 — Economic Oracle    (test_layer3_oracle.py)

La simulación solo es válida si TODOS los layers pasan.

Diferencia clave vs tests unitarios:
  - tests/unit/  → valida comportamiento aislado de componentes
  - tests/certification/ → valida que el sistema completo sea:
      L1: reproducible (determinístico)
      L2: internamente consistente (sin drift entre visiones)
      L3: económicamente veraz (contra oráculo externo)

Ver: README en este directorio para guía de certificación completa.
"""
