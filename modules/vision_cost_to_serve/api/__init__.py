"""
Read-only HTTP layer — serves stored CTS results via ResultsRepository.

Ownership: vision_cost_to_serve · public/read-only.
calculator_motor owns the formula logic (CostToServeCalculator).

No calculation logic here — only wire protocol (GET endpoint).
"""
