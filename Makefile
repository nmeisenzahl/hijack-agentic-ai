.PHONY: install-dev test test-01 test-02 test-03 test-04

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

test: test-01 test-02 test-03 test-04

test-01:
	$(PYTEST) tests/test_demo01_poisoned_advisory.py -v

test-02:
	$(PYTEST) tests/test_demo02_sleeper_mcp.py -v

test-03:
	$(PYTEST) tests/test_demo03_sleeper_cell.py -v

test-04:
	$(PYTEST) tests/test_demo04_runbook_drift.py -v
