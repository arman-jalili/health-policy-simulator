"""evidence corpus index

Searchable passage rows (generated German `tsvector` + GIN) and the published index manifest.

Document/article persistence (roadmap 0101) is still served by the in-memory adapters, so this
revision only owns what the index actually needs.

Revision ID: 0102_evidence_corpus_index
Revises: 0000_bootstrap
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0102_evidence_corpus_index"
down_revision: str | None = "0000_bootstrap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_corpus_indexed_passage",
        sa.Column("passage_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker_kind", sa.String(length=16), nullable=False),
        sa.Column("citable", sa.Boolean(), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=False),
        sa.Column("page_to", sa.Integer(), nullable=False),
        sa.Column("offset_start", sa.Integer(), nullable=False),
        sa.Column("offset_end", sa.Integer(), nullable=False),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('german', text)", persisted=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("passage_id", name="pk_evidence_corpus_indexed_passage"),
    )
    op.create_index(
        "ix_evidence_corpus_indexed_passage_tsv",
        "evidence_corpus_indexed_passage",
        ["tsv"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_evidence_corpus_indexed_passage_document_id",
        "evidence_corpus_indexed_passage",
        ["document_id"],
    )

    op.create_table(
        "evidence_corpus_index_manifest",
        sa.Column("index_version", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("searchable_since", sa.DateTime(timezone=True), nullable=False),
        sa.Column("passage_count", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("index_version", name="pk_evidence_corpus_index_manifest"),
    )


def downgrade() -> None:
    op.drop_table("evidence_corpus_index_manifest")
    op.drop_index(
        "ix_evidence_corpus_indexed_passage_document_id",
        table_name="evidence_corpus_indexed_passage",
    )
    op.drop_index(
        "ix_evidence_corpus_indexed_passage_tsv",
        table_name="evidence_corpus_indexed_passage",
    )
    op.drop_table("evidence_corpus_indexed_passage")
