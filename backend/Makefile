PYTHON ?= .venv/bin/python

.PHONY: demo-seed demo-reset demo-walkthrough

# Idempotent local-demo bootstrap; refused outside ENV=local.
demo-seed:
	@$(PYTHON) -m shared.demo_seed

# Recover the demo database after an accidental destructive run.
demo-reset:
	$(PYTHON) -m alembic upgrade head
	$(MAKE) demo-seed

# Full HTTP walkthrough against a migrated database; starts and stops the API.
demo-walkthrough:
	bash scripts/demo_walkthrough.sh
