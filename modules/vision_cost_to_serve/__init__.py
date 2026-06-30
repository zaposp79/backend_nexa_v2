"""
Public/read-only layer — Cost To Serve presentation.

Ownership boundary (Block 20C-D):
  calculator_motor:  formulas, CostToServeCalculator, CostToServeFacts
  vision_cost_to_serve:  API route, DTOs, helpers (service catalog)

NO formula implementation lives here.
Re-export wrappers in models/ and services/ provide backward compat.
"""
