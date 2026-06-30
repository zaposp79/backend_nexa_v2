# Makefile — Validación y endurecimiento del motor NEXA
#
# Targets principales:
#   make baseline       — Regenera baseline oficial congelado
#   make validate-excel — Compara backend vs Excel V2-4 (genera diff report)
#   make verify         — Verifica que el output actual matchea el baseline
#   make test           — Corre el test suite determinístico
#   make audit          — Ejecuta engine con tracing y exporta JSON+CSV
#   make all            — Pipeline completo de validación

VENV    := $(shell [ -d venv ] && echo venv/bin/ || echo "")
PYTHON  := $(VENV)python3
PYPATH  := PYTHONPATH=$(shell cd .. && pwd)
SCRIPTS := scripts

.PHONY: help baseline validate-excel verify test audit all clean test-known-debt

help:
	@echo "NEXA — Validation Pipeline"
	@echo ""
	@echo "Targets:"
	@echo "  make baseline       — Generate frozen baseline (reports/baseline_oficial.json)"
	@echo "  make validate-excel — Compare backend vs Excel V2-4 (reports/excel_backend_diff.{json,md})"
	@echo "  make verify         — Verify current outputs match frozen baseline"
	@echo "  make test           — Run deterministic test suite (pytest)"
	@echo "  make audit          — Run engine with audit trace (reports/audit/trace_*.json)"
	@echo "  make all            — Full validation pipeline (test + verify + validate-excel)"
	@echo "  make clean          — Remove generated reports (preserves baseline)"

baseline:
	$(PYPATH) $(PYTHON) $(SCRIPTS)/generate_baseline.py

validate-excel:
	$(PYPATH) $(PYTHON) $(SCRIPTS)/validate_excel.py --fail-on-delta 0.5

verify:
	$(PYPATH) $(PYTHON) $(SCRIPTS)/generate_baseline.py --verify

test:
	$(PYPATH) $(PYTHON) -m pytest tests/integration/ -v --tb=short

audit:
	$(PYPATH) $(PYTHON) $(SCRIPTS)/run_audit.py

all: test verify validate-excel
	@echo ""
	@echo "✅ All validations passed."

clean:
	rm -f reports/excel_backend_diff.{json,md}
	rm -rf reports/audit/
	@echo "Cleaned. Baseline preserved."

validate-excel-v28:
	$(PYPATH) $(PYTHON) $(SCRIPTS)/validate_excel_v28.py

test-known-debt:
	$(PYPATH) $(PYTHON) -m pytest tests/integration/test_tipos_carga.py -m known_debt -v --tb=short
