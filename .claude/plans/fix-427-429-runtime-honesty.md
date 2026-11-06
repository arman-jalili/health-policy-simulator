# Plan — #427, #428, #429

## #427 — batch ingestion must explain itself
1. `IngestionRun.record(outcome, path, reason)` keeps one `IngestionOutcomeRecord` per file and a
   first failure reason; migration `0105` persists the records as JSON.
2. `GET /corpus/ingestion-runs/{id}` returns `outcomes[]` and `failure_reason`.
3. OCR only for a missing text layer; sparse/damaged text stays native. `TesseractOcrExtractor.available()`
   checks the system binary; missing OCR raises `OCR_UNAVAILABLE` and a batch that needs it fails fast.
4. Re-running a shard reuses immutable extraction and does not duplicate articles/passages.

## #428 — proofing must gate a merge
1. `ci.yml` loops over every `check_*_contracts.sh` / `check_*_contract.py`; judgment is the only explicit skip.
2. `check_contract_proofing_gate.py` fails if a module doc lacks a script or the workflow stops looping.
3. The gate also runs in `check_architecture_conformance.sh` for local parity.

## #429 — scripted runs must be explainable
1. `NegotiationTurnBriefing` carries institution code, interests/weights, constraints, red lines, vetoes.
2. `_decision()` rejects prompt echoes; the scripted path derives a stance from the priority interest,
   veto right and constraints, and writes a labelled `[synthetic] … Begründung: …` argument.
3. A real provider with unusable output raises `LLM_OUTPUT_UNPARSEABLE`; no hash fallback remains.
4. `GET /runs/{id}/usage` exposes `model` and `provider`.
