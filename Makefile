# Convenience entrypoints. The demo stack lives in compose.yaml (see README.md).
.PHONY: demo-seed demo-reset demo-walkthrough stack-up stack-down stack-logs stack-seed stack-ingest stack-live stack-check

demo-seed:
	$(MAKE) -C backend demo-seed

demo-reset:
	$(MAKE) -C backend demo-reset

demo-walkthrough:
	$(MAKE) -C backend demo-walkthrough

# ── Full demo stack (PostgreSQL + backend + frontend) ────────────────────────────────────────────
stack-up:
	docker compose up --build -d
	@echo "waiting for the stack ..."
	@until curl -fsS http://127.0.0.1:3000/api/hps/_platform/readyz >/dev/null 2>&1; do sleep 2; done
	@curl -s http://127.0.0.1:3000/api/hps/_platform/readyz | python3 -c "import json,sys; d=json.load(sys.stdin); c=d['checks']; print('ready:', d['status'], '| llm:', c.get('llm'), '| pricing:', c.get('simulation_pricing'), '| ocr:', c.get('ocr'))"
	@echo "open http://127.0.0.1:3000"

stack-down:
	docker compose down

stack-logs:
	docker compose logs -f backend frontend

stack-seed:
	docker compose exec backend python -m shared.demo_seed

# Ingest the mounted corpus: make stack-ingest [LIMIT=10] [LABEL=corpus-2026]
LIMIT ?= 0
LABEL ?= corpus-2026
stack-ingest:
	docker compose exec backend python scripts/ingest_corpus.py /corpus --snapshot-label $(LABEL) --limit $(LIMIT)

# Enable the real model: requires demo.env.local (cp demo.env.example demo.env.local)
stack-live:
	@test -f demo.env.local || (echo "create demo.env.local first: cp demo.env.example demo.env.local" >&2; exit 1)
	docker compose up -d --force-recreate backend
	@sleep 5
	@curl -s http://127.0.0.1:3000/api/hps/_platform/readyz | python3 -c "import json,sys; c=json.load(sys.stdin)['checks']; print('llm:', c.get('llm'), '| model:', c.get('llm_model'), '| pricing:', c.get('simulation_pricing'))"

stack-check:
	docker compose ps
	curl -s http://127.0.0.1:3000/api/hps/_platform/readyz | python3 -m json.tool | head -40
