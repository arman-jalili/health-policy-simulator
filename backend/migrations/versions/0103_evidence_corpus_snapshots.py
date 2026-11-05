"""evidence corpus snapshots and ingestion runs

Roadmap Phase 1, migration ``0103``:

- ``evidence_corpus_snapshot`` — pinned manifest (documents + index version)
- ``evidence_corpus_snapshot_document`` — immutable membership of the pinned document set
- ``evidence_corpus_ingestion_run`` — auditable batch with outcome counts

Snapshot membership has no foreign key to the document table on purpose: deleting a source file
later must not rewrite a manifest that a published citation already quotes.

Revision ID: 0103_evidence_corpus_snapshots
Revises: 0101_evidence_corpus_documents
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0103_evidence_corpus_snapshots"
down_revision: str | None = "0101_evidence_corpus_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_corpus_snapshot",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("index_version", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("searchable_since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("passage_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_corpus_snapshot"),
    )

    op.create_table(
        "evidence_corpus_snapshot_document",
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint(
            "snapshot_id",
            "document_id",
            name="pk_evidence_corpus_snapshot_document",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["evidence_corpus_snapshot.id"],
            name="fk_evidence_corpus_snapshot_document_snapshot",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "evidence_corpus_ingestion_run",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("shard_label", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempted", sa.Integer(), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False),
        sa.Column("quarantined", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_corpus_ingestion_run"),
    )


def downgrade() -> None:
    op.drop_table("evidence_corpus_ingestion_run")
    op.drop_table("evidence_corpus_snapshot_document")
    op.drop_table("evidence_corpus_snapshot")
