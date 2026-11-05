"""simulation orchestration persistence

Jobs, invocation envelopes, ordered progress events and prompt versions.

Revision ID: 0302_simulation_orchestration
Revises: 0301_claim_validation
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0302_simulation_orchestration"
down_revision: str | None = "0301_claim_validation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulation_orchestration_job",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("budget_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("budget", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("claimed_by", sa.String(length=128), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_simulation_orchestration_job"),
    )
    op.create_index(
        "ix_simulation_orchestration_job_run_id",
        "simulation_orchestration_job",
        ["run_id"],
    )
    op.create_index(
        "ix_simulation_orchestration_job_status",
        "simulation_orchestration_job",
        ["status"],
    )

    op.create_table(
        "simulation_orchestration_invocation",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("stakeholder", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_pack_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_estimate", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_simulation_orchestration_invocation"),
    )
    op.create_index(
        "ix_simulation_orchestration_invocation_run_id",
        "simulation_orchestration_invocation",
        ["run_id"],
    )

    op.create_table(
        "simulation_orchestration_progress",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_simulation_orchestration_progress"),
        sa.UniqueConstraint(
            "run_id",
            "sequence",
            name="uq_simulation_orchestration_progress_seq",
        ),
    )
    op.create_index(
        "ix_simulation_orchestration_progress_run_id",
        "simulation_orchestration_progress",
        ["run_id"],
    )

    op.create_table(
        "simulation_orchestration_prompt",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_simulation_orchestration_prompt"),
        sa.UniqueConstraint(
            "name",
            "version",
            name="uq_simulation_orchestration_prompt_version",
        ),
    )
    op.create_index(
        "ix_simulation_orchestration_prompt_name",
        "simulation_orchestration_prompt",
        ["name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_simulation_orchestration_prompt_name", table_name="simulation_orchestration_prompt"
    )
    op.drop_table("simulation_orchestration_prompt")
    op.drop_index(
        "ix_simulation_orchestration_progress_run_id",
        table_name="simulation_orchestration_progress",
    )
    op.drop_table("simulation_orchestration_progress")
    op.drop_index(
        "ix_simulation_orchestration_invocation_run_id",
        table_name="simulation_orchestration_invocation",
    )
    op.drop_table("simulation_orchestration_invocation")
    op.drop_index(
        "ix_simulation_orchestration_job_status", table_name="simulation_orchestration_job"
    )
    op.drop_index(
        "ix_simulation_orchestration_job_run_id", table_name="simulation_orchestration_job"
    )
    op.drop_table("simulation_orchestration_job")
