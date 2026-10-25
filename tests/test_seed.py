"""Seed idempotency and environment guard tests."""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.config import clear_settings_cache
from app.models import Customer, Order
from app.seed.data import SEED_ORDERS
from app.seed.run import SeedRefusedError, seed_database


def test_repeated_seeding_does_not_duplicate(db_session) -> None:
    first = seed_database(db_session)
    second = seed_database(db_session)
    assert first["orders_created"] == 0  # already seeded in session fixture
    assert second["orders_created"] == 0
    assert second["customers_created"] == 0

    order_count = db_session.execute(select(func.count()).select_from(Order)).scalar_one()
    customer_count = db_session.execute(
        select(func.count()).select_from(Customer)
    ).scalar_one()
    assert order_count == len(SEED_ORDERS)
    assert customer_count == 5


def test_seed_refused_outside_development_and_test(db_session) -> None:
    # Keep INFERENCE_FIXTURE off: true + production fails Settings startup.
    with patch.dict(
        os.environ,
        {"APP_ENV": "production", "INFERENCE_FIXTURE": "false"},
        clear=False,
    ):
        clear_settings_cache()
        with pytest.raises(SeedRefusedError):
            seed_database(db_session)
        clear_settings_cache()
