"""Ingest a local PDF corpus into the evidence corpus, offline and resumable.

Canonical: ``.pi/architecture/modules/evidence-corpus.md``, ``docs/corpus-ingestion.md``

Why this script exists: the HTTP API stops after extraction. ``POST /corpus/documents`` extracts
text and saves the document, but segmentation, passage assembly and indexing have no route
(issue #424), and ``POST /corpus/ingestion-runs`` only records a row. A document ingested over
HTTP therefore never becomes searchable. This script drives the same use cases
``src/shared/demo_seed.py`` drives, in a separate process, so a multi-gigabyte corpus does not block
the API event loop.

Properties
- resumable: documents are content-addressed (sha256 of the file bytes), so a re-run skips existing
- per-document commit: one document per transaction, so a crash loses at most one document
- paragraph-aware chunking: passages are exact substrings of the article body, half-open offsets
- honest logging: progress to stderr, the final JSON result to stdout (see issue #419)
- nothing silent: scans without a text layer and oversized files are named and skipped

Usage
    python scripts/ingest_corpus.py "material/**/*.pdf" --snapshot-label full-corpus-2026
    python scripts/ingest_corpus.py material/ --snapshot-label corpus --limit 20 --dry-run
    python scripts/ingest_corpus.py material/ --snapshot-label corpus --reindex

Then assemble packs against the printed snapshot id (``POST /evidence/packs``) or point
``/settings -> Demo-Bootstrap`` at a seed file that contains it.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from evidence_corpus.application.commands import (
    IndexIngestedPassagesRequest,
    IngestDocumentRequest,
    PinCorpusSnapshotRequest,
    PublicationInput,
    SegmentArticleRequest,
)
from evidence_corpus.domain.errors import ExtractionFailed
from evidence_corpus.domain.values import Offsets, SourceType, SpeakerKind
from shared.app import create_app
from shared.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from evidence_corpus.domain.entities import Document

DEFAULT_CHUNK_CHARS = 1200
DEFAULT_MIN_CHUNK_CHARS = 200
DEFAULT_MAX_MB = 200
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


@dataclass(slots=True)
class Totals:
    """Running counters, printed to stderr after every document."""

    documents: int = 0
    skipped: int = 0
    failed: int = 0
    passages: int = 0
    characters: int = 0
    elapsed_s: float = 0.0


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _content_hash(path: Path) -> str:
    """Same material as ``evidence_corpus.application.ingestion_handlers._content_hash``."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _paragraph_spans(body: str) -> list[tuple[int, int]]:
    """Half-open spans of non-empty paragraphs, whitespace-trimmed, non-overlapping."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    boundaries = [match.span() for match in _PARAGRAPH_BREAK.finditer(body)]
    boundaries.append((len(body), len(body)))
    for start, end in boundaries:
        chunk = body[cursor:start]
        if chunk.strip():
            leading = len(chunk) - len(chunk.lstrip())
            trailing = len(chunk) - len(chunk.rstrip())
            spans.append((cursor + leading, cursor + len(chunk) - trailing))
        cursor = end
    return spans


def _chunk_spans(body: str, *, chunk_chars: int, min_chunk_chars: int) -> list[tuple[int, int]]:
    """Pack paragraphs into windows of at most ``chunk_chars`` characters."""
    chunks: list[tuple[int, int]] = []
    pending: tuple[int, int] | None = None
    for start, end in _paragraph_spans(body):
        if pending is None:
            pending = (start, end)
            continue
        if end - pending[0] <= chunk_chars:
            pending = (pending[0], end)
            continue
        if pending[1] - pending[0] >= min_chunk_chars:
            chunks.append(pending)
        pending = (start, end)
    if pending is not None and pending[1] - pending[0] >= min_chunk_chars:
        chunks.append(pending)
    return chunks


def _add_passages(document: Document, *, chunk_chars: int, min_chunk_chars: int) -> int:
    """Publish chunked passages for every article that has none yet; return how many were added."""
    added = 0
    for article in document.articles:
        if article.passages:
            continue
        for start, end in _chunk_spans(
            article.body, chunk_chars=chunk_chars, min_chunk_chars=min_chunk_chars
        ):
            article.add_passage(
                text=article.body[start:end],
                offsets=Offsets(start, end),
                speaker_kind=SpeakerKind.INSTITUTION,
            )
            added += 1
    return added


async def _ingest_one(
    corpus: Any,
    path: Path,
    *,
    outlet: str,
    published_on: date,
    source_type: SourceType,
    chunk_chars: int,
    min_chunk_chars: int,
    reindex: bool,
) -> tuple[str, int, int]:
    """Return ``(document_id, passages_added, characters)`` for one file."""
    digest = _content_hash(path)
    document = await corpus.documents.get_by_hash(digest)
    if document is None:
        ingested = await corpus.ingest_document.execute(
            IngestDocumentRequest(
                source_uri=str(path),
                publication=PublicationInput(
                    outlet=outlet, published_on=published_on, medium="print"
                ),
                source_type=source_type,
            )
        )
        document = await corpus.documents.get(ingested.document_id)
    if document is None:  # pragma: no cover - defensive
        raise RuntimeError(f"document for {path} disappeared after ingestion")
    if not document.articles:
        await corpus.segment_article.execute(SegmentArticleRequest(document_id=document.id))
        document = await corpus.documents.get(document.id)
    if document is None:  # pragma: no cover - defensive
        raise RuntimeError(f"document for {path} disappeared after segmentation")

    added = _add_passages(document, chunk_chars=chunk_chars, min_chunk_chars=min_chunk_chars)
    if added:
        await corpus.documents.save(document)
        document = await corpus.documents.get(document.id)
    if document is None:  # pragma: no cover - defensive
        raise RuntimeError(f"document for {path} disappeared after passage assembly")

    if added or reindex:
        await corpus.index_ingested_passages.execute(
            IndexIngestedPassagesRequest(document_id=document.id)
        )
    characters = sum(len(article.body) for article in document.articles)
    return document.id, added, characters


async def run(args: argparse.Namespace) -> dict[str, object]:
    """Ingest every matching file, then pin the snapshot unless disabled."""
    paths = _expand(args.paths)
    if not paths:
        raise SystemExit(f"no PDFs matched: {args.paths}")
    if args.limit:
        paths = paths[: args.limit]

    app = create_app(get_settings(), log_stream=sys.stderr)
    corpus = app.state.corpus
    source_type = SourceType(args.source_type)
    if source_type is SourceType.UNKNOWN:
        raise SystemExit("--source-type unknown is refused: declare what the corpus is")
    published_on = date.fromisoformat(args.published_on)
    totals = Totals()
    started = time.perf_counter()
    document_ids: list[str] = []
    failures: list[dict[str, str]] = []

    _log(f"{len(paths)} file(s), snapshot label {args.snapshot_label!r}, dry run {args.dry_run}")
    try:
        for index, path in enumerate(paths, start=1):
            size_mb = path.stat().st_size / (1 << 20)
            prefix = f"[{index}/{len(paths)}] {path.name} ({size_mb:.1f} MB)"
            if size_mb > args.max_mb and not args.allow_large:
                totals.skipped += 1
                failures.append({"path": str(path), "reason": "above --max-mb"})
                _log(f"{prefix}: skipped, above --max-mb {args.max_mb} (use --allow-large)")
                continue
            if args.dry_run:
                _log(f"{prefix}: would ingest")
                continue
            began = time.perf_counter()
            try:
                document_id, added, characters = await _ingest_one(
                    corpus,
                    path,
                    outlet=args.outlet,
                    published_on=published_on,
                    source_type=source_type,
                    chunk_chars=args.chunk_chars,
                    min_chunk_chars=args.min_chunk_chars,
                    reindex=args.reindex,
                )
            except ExtractionFailed as error:
                totals.failed += 1
                failures.append({"path": str(path), "reason": str(error)})
                _log(
                    f"{prefix}: extraction failed ({error}); scanned PDF? OCR is a separate adapter"
                )
                continue
            document_ids.append(document_id)
            totals.documents += 1
            totals.passages += added
            totals.characters += characters
            totals.elapsed_s = time.perf_counter() - started
            took = time.perf_counter() - began
            _log(
                f"{prefix}: doc {document_id} +{added} passages, {characters / 1000:.0f}k chars, "
                f"{took:.1f}s | total {totals.documents} docs, {totals.passages} passages"
            )

        snapshot_id: str | None = None
        if not args.dry_run and not args.no_pin and document_ids:
            pinned = await corpus.pin_corpus_snapshot.execute(
                PinCorpusSnapshotRequest(label=args.snapshot_label, document_ids=document_ids)
            )
            snapshot_id = pinned.snapshot_id
            _log(f"pinned snapshot {snapshot_id} over {len(document_ids)} documents")
    finally:
        await app.state.db.dispose()

    return {
        "snapshot_id": snapshot_id,
        "snapshot_label": None if args.dry_run else args.snapshot_label,
        "documents": totals.documents,
        "skipped": totals.skipped,
        "failed": totals.failed,
        "passages": totals.passages,
        "characters": totals.characters,
        "elapsed_s": round(totals.elapsed_s, 1),
        "failures": failures,
    }


def _expand(patterns: list[str]) -> list[Path]:
    """Expand globs and directories into a sorted, de-duplicated list of PDF paths."""
    found: dict[str, Path] = {}
    for pattern in patterns:
        candidate = Path(pattern)
        matches = sorted(Path(p) for p in glob.glob(pattern, recursive=True))
        if candidate.is_dir():
            matches = sorted(candidate.rglob("*.pdf"))
        for path in matches:
            if path.is_file() and path.suffix.lower() == ".pdf":
                found[str(path.resolve())] = path
    return [found[key] for key in sorted(found)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("paths", nargs="+", help="glob(s) or directories containing PDFs")
    parser.add_argument("--snapshot-label", required=True, help="label of the pinned snapshot")
    parser.add_argument("--outlet", default="Operator Corpus", help="publication outlet")
    parser.add_argument(
        "--published-on",
        default=date.today().isoformat(),
        help="ISO date recorded as the publication date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--source-type",
        default=SourceType.OFFICIAL_STATISTICS.value,
        choices=[value.value for value in SourceType if value is not SourceType.UNKNOWN],
        help="declared source type; drives the authority tier",
    )
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--min-chunk-chars", type=int, default=DEFAULT_MIN_CHUNK_CHARS)
    parser.add_argument("--limit", type=int, default=0, help="ingest only the first N files")
    parser.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB)
    parser.add_argument(
        "--allow-large", action="store_true", help="do not skip files above --max-mb"
    )
    parser.add_argument(
        "--reindex", action="store_true", help="re-index documents that already exist"
    )
    parser.add_argument("--no-pin", action="store_true", help="do not pin a snapshot afterwards")
    parser.add_argument("--dry-run", action="store_true", help="list what would be ingested")
    return parser


def main() -> None:
    """Operator entry point: JSON on stdout, progress on stderr."""
    result = asyncio.run(run(_parser().parse_args()))
    sys.stdout.write(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":  # pragma: no cover - operator entry
    main()
