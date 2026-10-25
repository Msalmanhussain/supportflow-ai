"""create synthetic customers and orders

Revision ID: 20260318_0001
Revises:
Create Date: 2026-03-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260318_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORDER_STATUS_VALUES = (
    "processing",
    "shipped",
    "in_transit",
    "delayed",
    "delivered",
    "cancelled",
)

# create_type=False prevents CREATE TYPE during create_table / drop_table.
order_status_enum = postgresql.ENUM(
    *ORDER_STATUS_VALUES,
    name="order_status",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )

    postgresql.ENUM(*ORDER_STATUS_VALUES, name="order_status").create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("status", order_status_enum, nullable=False),
        sa.Column("courier", sa.String(length=120), nullable=True),
        sa.Column("estimated_delivery", sa.Date(), nullable=True),
        sa.Column("last_update", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_orders_order_id"),
    )


def downgrade() -> None:
    op.drop_table("orders")
    postgresql.ENUM(*ORDER_STATUS_VALUES, name="order_status").drop(
        op.get_bind(),
        checkfirst=True,
    )
    op.drop_table("customers")
