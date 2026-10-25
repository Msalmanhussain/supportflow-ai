"""Synthetic order model."""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class OrderStatus(str, Enum):
    """Synthetic fulfilment statuses used in demos."""

    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    @property
    def display_label(self) -> str:
        labels = {
            OrderStatus.PROCESSING: "Processing",
            OrderStatus.SHIPPED: "Shipped",
            OrderStatus.IN_TRANSIT: "In transit",
            OrderStatus.DELAYED: "Delayed",
            OrderStatus.DELIVERED: "Delivered",
            OrderStatus.CANCELLED: "Cancelled",
        }
        return labels[self]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            name="order_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        nullable=False,
    )
    courier: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    estimated_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="orders")
