.PHONY: setup check test lint lint-all doctor

UV ?= uv

setup:
	$(UV) sync --frozen

check: lint test

test:
	$(UV) run --frozen python -m unittest discover -s tests -v

# Existing source has style debt under ALL; gate syntax and definite errors.
lint:
	$(UV) run --frozen ruff check --select E9,F63,F7,F82 src tests scripts

lint-all:
	$(UV) run --frozen ruff check src

doctor:
	$(UV) run --frozen python scripts/doctor.py
