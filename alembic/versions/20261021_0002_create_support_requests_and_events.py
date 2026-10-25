"""create support requests and review events

Revision ID: 20261021_0002
Revises: 20260318_0001
Create Date: 2026-10-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_0002"
down_revision: Union[str, Sequence[str], None] = "20260318_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REVIEW_STATUS_VALUES = ("pending_review", "approved", "rejected")
REVIEW_EVENT_ACTION_VALUES = ("created", "edited", "approved", "rejected")

review_status_enum = postgresql.ENUM(
    *REVIEW_STATUS_VALUES,
    name="review_status",
    create_type=False,
)
review_event_action_enum = postgresql.ENUM(
    *REVIEW_EVENT_ACTION_VALUES,
    name="review_event_action",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(*REVIEW_STATUS_VALUES, name="review_status").create(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(*REVIEW_EVENT_ACTION_VALUES, name="review_event_action").create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "support_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("idempotency_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=True),
        sa.Column("classification_intent", sa.String(length=64), nullable=False),
        sa.Column("classification_order_id", sa.String(length=64), nullable=True),
        sa.Column("classification_requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("draft_original", sa.Text(), nullable=False),
        sa.Column("draft_current", sa.Text(), nullable=False),
        sa.Column(
            "sources_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("review_status", review_status_enum, nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("reviewed_text", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_support_requests_idempotency_key"),
    )
    op.create_index(
        "ix_support_requests_review_status",
        "support_requests",
        ["review_status"],
    )
    op.create_index(
        "ix_support_requests_created_at",
        "support_requests",
        ["created_at"],
    )

    op.create_table(
        "support_review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", review_event_action_enum, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["support_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_review_events_request_id",
        "support_review_events",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_review_events_request_id", table_name="support_review_events")
    op.drop_table("support_review_events")
    op.drop_index("ix_support_requests_created_at", table_name="support_requests")
    op.drop_index("ix_support_requests_review_status", table_name="support_requests")
    op.drop_table("support_requests")
    postgresql.ENUM(name="review_event_action").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="review_status").drop(op.get_bind(), checkfirst=True)
