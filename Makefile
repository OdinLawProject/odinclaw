# OdinClaw Makefile
# Works on Windows (bash/Git Bash) and Linux/macOS.
# Activate via: source .venv/Scripts/activate  (Windows)
#              source .venv/bin/activate       (Linux/macOS)

PYTHON := python
# Auto-detect venv activation script path (Windows vs Unix)
ifeq ($(OS),Windows_NT)
    VENV_ACTIVATE := .venv/Scripts/activate
else
    VENV_ACTIVATE := .venv/bin/activate
endif

.PHONY: venv install dev test clean status

## Create the virtual environment
venv:
	$(PYTHON) -m venv .venv
	@echo "Virtual environment created."
	@echo "Activate with: source $(VENV_ACTIVATE)"

## Install OdinClaw in editable mode (runtime only, no test deps)
install:
	. $(VENV_ACTIVATE) && pip install -e .

## Install with dev/test dependencies
dev:
	. $(VENV_ACTIVATE) && pip install -e ".[dev]"

## Run the full test suite
test:
	. $(VENV_ACTIVATE) && pytest -q

## Run tests with coverage
coverage:
	. $(VENV_ACTIVATE) && pytest -q --cov=odinclaw --cov-report=term-missing

## Show extension state (requires install)
status:
	. $(VENV_ACTIVATE) && odinclaw status

## Remove build artifacts and venv
clean:
	rm -rf .venv build dist *.egg-info __pycache__

## Full setup from scratch: create venv + install dev deps + run tests
setup: venv dev test
	@echo ""
	@echo "OdinClaw is ready. Run 'odinclaw start' to open a session."
