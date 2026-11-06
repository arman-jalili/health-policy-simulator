"""Frozen error contract of the EvidenceCorpus bounded context.

Canonical: .pi/architecture/modules/evidence-corpus.md

Each error is a stable machine code plus an HTTP status, so the API envelope never depends on
message wording (ADR-004). Codes are uppercase snake case and must stay unique per context.
"""

from __future__ import annotations

from shared.errors import ConflictError, NotFoundError, ValidationFailedError


class AlreadyExtracted(ConflictError):
    """A document may be extracted exactly once (invariant 2)."""

    code = "ALREADY_EXTRACTED"

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document {document_id} has already been extracted")


class AuthorityAlreadyAssigned(ConflictError):
    """Authority tier is assigned once and immutable thereafter (invariant 2)."""

    code = "AUTHORITY_ALREADY_ASSIGNED"

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document {document_id} already has an authority tier")


class DocumentNotCitable(ConflictError):
    """A quarantined or unclassified document may not produce citable passages."""

    code = "DOCUMENT_NOT_CITABLE"

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document {document_id} is not citable")


class OffsetsOutOfBounds(ValidationFailedError):
    """Passage offsets must lie inside the parent article body (invariant 3)."""

    code = "OFFSETS_OUT_OF_BOUNDS"

    def __init__(self, *, article_id: str, start: int, end: int, article_length: int) -> None:
        super().__init__(
            f"offsets [{start}, {end}) outside article {article_id} of length {article_length}"
        )


class OverlappingPassages(ConflictError):
    """Sibling passages may not overlap (invariant 3)."""

    code = "PASSAGE_OVERLAP"

    def __init__(self, *, article_id: str, first: str, second: str) -> None:
        super().__init__(f"passages {first} and {second} overlap in article {article_id}")


class SourceTypeUnknown(ValidationFailedError):
    """An unknown source type cannot be promoted to an authoritative tier (invariant 7)."""

    code = "SOURCE_TYPE_UNKNOWN"

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document {document_id} has no classifiable source type")


class ExtractionFailed(ValidationFailedError):
    """Extraction could not complete; the document is excluded from citation."""

    code = "EXTRACTION_FAILED"

    def __init__(self, source_uri: str, reason: str) -> None:
        super().__init__(f"extraction failed for {source_uri}: {reason}")


class DocumentTooLarge(ValidationFailedError):
    """A source document exceeds the configured page budget; refused before extraction."""

    code = "DOCUMENT_TOO_LARGE"


class RunAlreadyClosed(ConflictError):
    """An ingestion run is closed once; late outcomes are refused."""

    code = "RUN_ALREADY_CLOSED"

    def __init__(self, run_id: str) -> None:
        super().__init__(f"ingestion run {run_id} is already closed")


class RunNotFound(NotFoundError):
    code = "RUN_NOT_FOUND"

    def __init__(self, run_id: str) -> None:
        super().__init__(f"ingestion run {run_id} not found")


class DocumentNotFound(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document {document_id} not found")


class ArticleNotFound(NotFoundError):
    code = "ARTICLE_NOT_FOUND"

    def __init__(self, article_id: str) -> None:
        super().__init__(f"article {article_id} not found")


class PassageNotFound(NotFoundError):
    code = "PASSAGE_NOT_FOUND"

    def __init__(self, passage_id: str) -> None:
        super().__init__(f"passage {passage_id} not found")


class SnapshotNotFound(NotFoundError):
    code = "SNAPSHOT_NOT_FOUND"

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"corpus snapshot {snapshot_id} not found")
