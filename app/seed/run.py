"""Idempotent development/test seeder for synthetic customers and orders."""

from __future__ import annotations

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Customer, Order
from app.seed.data import SEED_CUSTOMERS, SEED_ORDERS


class SeedRefusedError(RuntimeError):
    """Raised when seeding is attempted outside development/test."""


def seed_database(db: Session) -> dict[str, int]:
    """Insert missing synthetic rows. Never duplicates existing order_id/email.

    Refuses unless APP_ENV is development or test.
    """
    settings = get_settings()
    if not settings.allows_seeding:
        raise SeedRefusedError(
            f"Seeding refused: APP_ENV={settings.app_env!r}. "
            "Only development and test modes may seed synthetic data."
        )

    customers_created = 0
    orders_created = 0

    email_to_customer: dict[str, Customer] = {}
    for row in SEED_CUSTOMERS:
        email = row["email"].lower()
        existing = db.execute(
            select(Customer).where(Customer.email == email)
        ).scalar_one_or_none()
        if existing is None:
            customer = Customer(email=email, full_name=row["full_name"])
            db.add(customer)
            db.flush()
            customers_created += 1
            email_to_customer[email] = customer
        else:
            email_to_customer[email] = existing

    for row in SEED_ORDERS:
        existing_order = db.execute(
            select(Order).where(Order.order_id == row["order_id"])
        ).scalar_one_or_none()
        if existing_order is not None:
            continue
        customer = email_to_customer[row["customer_email"].lower()]
        db.add(
            Order(
                order_id=row["order_id"],
                customer_id=customer.id,
                status=row["status"],
                courier=row["courier"],
                estimated_delivery=row["estimated_delivery"],
                last_update=row["last_update"],
                notes=row["notes"],
            )
        )
        orders_created += 1

    db.commit()
    return {
        "customers_created": customers_created,
        "orders_created": orders_created,
        "customers_total_seed_defs": len(SEED_CUSTOMERS),
        "orders_total_seed_defs": len(SEED_ORDERS),
    }


def main() -> int:
    settings = get_settings()
    if not settings.allows_seeding:
        print(
            f"ERROR: Seeding refused for APP_ENV={settings.app_env!r}.",
            file=sys.stderr,
        )
        return 2

    db = SessionLocal()
    try:
        result = seed_database(db)
    except SeedRefusedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()

    print(
        "Seed complete "
        f"(customers_created={result['customers_created']}, "
        f"orders_created={result['orders_created']}, "
        f"order_defs={result['orders_total_seed_defs']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
