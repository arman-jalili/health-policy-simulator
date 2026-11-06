PYTHON ?= .venv/bin/python

.PHONY: demo-seed demo-walkthrough

# Idempotent local-demo bootstrap; refused outside ENV=local.
demo-seed:
	@$(PYTHON) -m shared.demo_seed

# Full HTTP walkthrough against a migrated database; starts and stops the API.
demo-walkthrough:
	bash scripts/demo_walkthrough.sh
