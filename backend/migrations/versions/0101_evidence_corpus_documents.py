"""evidence corpus documents

Document persistence owned by the context (roadmap Phase 1, migration ``0101``):

- ``evidence_corpus_document`` — aggregate root, extraction state and frozen authority tier
- ``evidence_corpus_publication`` — 1:1 owned publication value
- ``evidence_corpus_article`` — segmented editorial unit (with the normalised body digest)
- ``evidence_corpus_passage`` — smallest citable span

The identifier says ``0101`` but the revision is chained after ``0102`` because the index tables
were created first in the original history. The ordering that matters is the dependency chain, not
the lexicographic name.

Revision ID: 0101_evidence_corpus_documents
Revises: 0102_evidence_corpus_index
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0101_evidence_corpus_documents"
down_revision: str | None = "0102_evidence_corpus_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_corpus_document",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("tier", sa.String(length=40), nullable=True),
        sa.Column("quality_method", sa.String(length=16), nullable=True),
        sa.Column("quality_confidence", sa.Float(), nullable=True),
        sa.Column("quality_missing_glyph_rate", sa.Float(), nullable=True),
        sa.Column("quality_page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_evidence_corpus_document"),
    )
    op.create_index(
        "ix_evidence_corpus_document_content_hash",
        "evidence_corpus_document",
        ["content_hash"],
        unique=True,
    )

    op.create_table(
        "evidence_corpus_publication",
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("outlet", sa.String(length=200), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("medium", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("document_id", name="pk_evidence_corpus_publication"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["evidence_corpus_document.id"],
            name="fk_evidence_corpus_publication_document",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "evidence_corpus_article",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_from", sa.Integer(), nullable=False),
        sa.Column("page_to", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("is_canonical", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_corpus_article"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["evidence_corpus_document.id"],
            name="fk_evidence_corpus_article_document",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_evidence_corpus_article_document_id",
        "evidence_corpus_article",
        ["document_id"],
    )
    op.create_index(
        "ix_evidence_corpus_article_content_hash",
        "evidence_corpus_article",
        ["content_hash"],
    )

    op.create_table(
        "evidence_corpus_passage",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.String(length=64), nullable=False),
        sa.Column("ord", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("offset_start", sa.Integer(), nullable=False),
        sa.Column("offset_end", sa.Integer(), nullable=False),
        sa.Column("speaker_kind", sa.String(length=16), nullable=False),
        sa.Column("citable", sa.Boolean(), nullable=False),
        sa.Column("section", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_corpus_passage"),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["evidence_corpus_article.id"],
            name="fk_evidence_corpus_passage_article",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_evidence_corpus_passage_article_id",
        "evidence_corpus_passage",
        ["article_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_corpus_passage_article_id", table_name="evidence_corpus_passage")
    op.drop_table("evidence_corpus_passage")
    op.drop_index("ix_evidence_corpus_article_content_hash", table_name="evidence_corpus_article")
    op.drop_index("ix_evidence_corpus_article_document_id", table_name="evidence_corpus_article")
    op.drop_table("evidence_corpus_article")
    op.drop_table("evidence_corpus_publication")
    op.drop_index("ix_evidence_corpus_document_content_hash", table_name="evidence_corpus_document")
    op.drop_table("evidence_corpus_document")
