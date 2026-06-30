"""WAVE 4 — Parity test suite between Excel V2-7 and backend_nexa engine.

Two oracle strategies coexist:

1. **Formula oracle** (`tolerance.assert_close`): we compute the expected value
   *symbolically* from the inputs using the documented WAVE 3 formula
   (`ingreso = costo / ((1-m)·(1-op_cont)·(1-com_cont)·(1-markup)·(1+descuento))`)
   and assert the engine outputs match within 1e-4 relative tolerance.

2. **Excel value oracle** (`excel_oracle.read_cell`): we read the actual numeric
   value from a designated cell in the V2-7 workbook (`data_only=True`).
   The Excel V2-7 canonical case in the workbook is currently "Captura de Datos"
   with ramp-up=0, so most P&G cells are 0 by design — we fall back to formula
   oracle for non-trivial assertions.
"""
