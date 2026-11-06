# Ingesting a large PDF corpus

Canonical: `.pi/architecture/modules/evidence-corpus.md` (pipeline), `docs/demo-walkthrough.md` (small path).

> **Status: not started (deferred as D-010, `.pi/architecture/DEFERRED.md`).**
> The operator has a ~3 GB corpus to ingest *after* the frontend is built. Nothing depends on it today: the
> demo runs on the one-document `demo-corpus-v1` snapshot. When the work is done, record the snapshot label in
> D-010 and remove the entry.
>
> Before running anything: **finish the backend test suite first** — `pytest -m integration` runs
> `alembic downgrade base` on `DATABASE_URL` and wipes the database (issue #421). Ingest is the last step
> before a demo.

## The short version

Ingest **offline, in a separate process, per document**, with `scripts/ingest_corpus.py`:

```bash
cd backend && source .venv/bin/activate
export ENV=local AUTH_MODE=demo PERSISTENCE=postgres
export DATABASE_URL="postgresql+asyncpg://hps:hps@localhost:5433/health_policy"

# 1. See how big the job is (no writes)
python scripts/ingest_corpus.py material/ --snapshot-label corpus-2026 --dry-run

# 2. Ingest a first slice and measure the rate
python scripts/ingest_corpus.py material/ --snapshot-label corpus-2026 --limit 10

# 3. Ingest everything, resumable; progress on stderr, JSON result on stdout
nohup python scripts/ingest_corpus.py material/ --snapshot-label corpus-2026 \
  > /tmp/ingest.json 2> /tmp/ingest.log &
tail -f /tmp/ingest.log
```

Then assemble packs against the printed `snapshot_id` and point `/settings → Demo-Bootstrap`
at a seed file that contains it.

## Why not the HTTP API

`POST /api/v1/corpus/documents` extracts text and saves the document, but the remaining pipeline steps —
segmentation and passage indexing — have **no route** (issue #424), and `POST /api/v1/corpus/ingestion-runs`
only records a row. A document ingested over HTTP never becomes searchable.

Two more reasons to stay offline for large files:

- The route executes extraction **inline on the event loop** (PyMuPDF work inside `async def`), so the API is
  unresponsive for the whole file.
- Extraction joins every page's text into one string, so peak memory is several times the text size.

## Sizing

Run the script with `--limit 1` on the largest file and read the per-document line:

```
[1/240] report-2026.pdf (48.3 MB): doc doc_… +3120 passages, 1840k chars, 41.2s | total 1 docs, 3120 passages
```

Rules of thumb measured on the sample corpus:

| Quantity | Observation |
|---|---|
| Passages | one per ~500–700 characters with `--chunk-chars 1200` (paragraph-packed) |
| Database | passages row + persisted generated `tsvector` ≈ 2–3× the text bytes |
| Throughput | extraction is fast (PyMuPDF); the cost is per-passage insert + `tsvector` generation |
| Transaction | one document per commit; a crash loses at most one document |

For a 3 GB *text* corpus expect millions of passages and a database in the tens of GB — check disk before
starting, and prefer a curated subset for the demo (see below).

## Scanned documents

`PyMuPdfExtractor` refuses a PDF without a text layer (`ExtractionFailed: no text layer found; route to OCR`),
and a **sparse** text layer is routed to OCR too (a one-line cover page is enough). The OCR adapter
(`TesseractOcrExtractor`) needs the Python packages `pytesseract` + `Pillow` **and the `tesseract` system
binary**; it runs at ~300 dpi, i.e. seconds per page. Without the binary every OCR-routed file fails — through
`POST /corpus/ingestion-runs` that failure is reported as a bare `failed` count with no reason (#427).

```bash
# is the OCR stack usable? (the script will not tell you — see #427)
python -c "import pytesseract; print(pytesseract.get_tesseract_version())" || echo "OCR unavailable"
```

Check the text layer before planning:

```bash
python - <<'PY'
import pathlib, pymupdf
for p in sorted(pathlib.Path("material").glob("**/*.pdf")):
    d = pymupdf.open(p)
    chars = sum(len(page.get_text()) for page in d)
    print(f"{p.name}: {d.page_count:5d} pages, {chars/1000:8.0f}k chars")
PY
```

Files with ~0 chars per page are scans: OCR them separately, or exclude them from the demo corpus.

## Split monoliths

One PDF becomes one document, one article, one aggregate, and one transaction. A 3 GB single file is a bad
unit; split it first:

```bash
qpdf --split-pages=200 big.pdf part-%03d.pdf     # or: mutool split, pdfseparate
```

Aim for 20–80 MB / 100–500 pages per file.

## Curate the demo snapshot

Search is scoped to a **pinned snapshot**, so the full corpus and the demo corpus can coexist:

```bash
# full ingest, one snapshot
python scripts/ingest_corpus.py material/ --snapshot-label corpus-2026
# a curated demo set, another snapshot
python scripts/ingest_corpus.py material/demo/ --snapshot-label demo-corpus-v2
```

Packs are assembled per `snapshot_id` (`POST /api/v1/evidence/packs`). `make demo-seed` pins
`demo-corpus-v1` and its packs reference that snapshot, so after switching corpora re-run the seed or assemble
new packs and update the seed JSON the frontend imports.

## Order of operations (matters)

1. Finish running the backend suite **before** a large ingest: `pytest -m integration` runs
   `alembic downgrade base` against `DATABASE_URL` and wipes the database (issue #421).
2. Ingest (§ above), verify with a pack against the new snapshot.
3. Re-seed the demo artefacts (`make demo-seed`) or update the seed JSON for the frontend.
4. Only then start the demo run.
