"""Fictional synthetic seed records (example.com emails, fictional couriers)."""

from datetime import date, datetime, timezone

from app.models.order import OrderStatus

# All emails use the reserved example.com domain. Couriers are fictional.
SEED_CUSTOMERS = [
    {
        "email": "alex.rivera@example.com",
        "full_name": "Alex Rivera (Synthetic)",
    },
    {
        "email": "blair.chen@example.com",
        "full_name": "Blair Chen (Synthetic)",
    },
    {
        "email": "casey.nguyen@example.com",
        "full_name": "Casey Nguyen (Synthetic)",
    },
    {
        "email": "devon.okafor@example.com",
        "full_name": "Devon Okafor (Synthetic)",
    },
    {
        "email": "ellis.patel@example.com",
        "full_name": "Ellis Patel (Synthetic)",
    },
]


def _ts(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# Ten orders covering every synthetic status at least once.
SEED_ORDERS = [
    {
        "order_id": "SF-1001",
        "customer_email": "alex.rivera@example.com",
        "status": OrderStatus.PROCESSING,
        "courier": None,
        "estimated_delivery": date(2026, 4, 2),
        "last_update": _ts(2026, 3, 20, 9, 15),
        "notes": "Synthetic — awaiting warehouse pick.",
    },
    {
        "order_id": "SF-1002",
        "customer_email": "blair.chen@example.com",
        "status": OrderStatus.SHIPPED,
        "courier": "ParcelSprite Express (Fictional)",
        "estimated_delivery": date(2026, 3, 28),
        "last_update": _ts(2026, 3, 21, 16, 40),
        "notes": "Synthetic — handed to fictional courier.",
    },
    {
        "order_id": "SF-1003",
        "customer_email": "casey.nguyen@example.com",
        "status": OrderStatus.IN_TRANSIT,
        "courier": "Northern Nimbus Logistics (Fictional)",
        "estimated_delivery": date(2026, 3, 27),
        "last_update": _ts(2026, 3, 22, 8, 5),
        "notes": "Synthetic — in transit between hubs.",
    },
    {
        "order_id": "SF-1004",
        "customer_email": "devon.okafor@example.com",
        "status": OrderStatus.DELAYED,
        "courier": "Riverbend Relay Co. (Fictional)",
        "estimated_delivery": date(2026, 4, 5),
        "last_update": _ts(2026, 3, 22, 11, 20),
        "notes": "Synthetic — weather delay at fictional hub.",
    },
    {
        "order_id": "SF-1005",
        "customer_email": "ellis.patel@example.com",
        "status": OrderStatus.DELIVERED,
        "courier": "Maple Mile Couriers (Fictional)",
        "estimated_delivery": date(2026, 3, 18),
        "last_update": _ts(2026, 3, 18, 17, 55),
        "notes": "Synthetic — marked delivered.",
    },
    {
        "order_id": "SF-1006",
        "customer_email": "alex.rivera@example.com",
        "status": OrderStatus.CANCELLED,
        "courier": None,
        "estimated_delivery": None,
        "last_update": _ts(2026, 3, 10, 13, 0),
        "notes": "Synthetic — cancelled before ship.",
    },
    {
        "order_id": "SF-1007",
        "customer_email": "blair.chen@example.com",
        "status": OrderStatus.PROCESSING,
        "courier": None,
        "estimated_delivery": date(2026, 4, 8),
        "last_update": _ts(2026, 3, 23, 7, 30),
        "notes": "Synthetic — payment captured, packing.",
    },
    {
        "order_id": "SF-1008",
        "customer_email": "casey.nguyen@example.com",
        "status": OrderStatus.SHIPPED,
        "courier": "Coastal Cartographers Post (Fictional)",
        "estimated_delivery": date(2026, 3, 30),
        "last_update": _ts(2026, 3, 22, 19, 10),
        "notes": "Synthetic — label created.",
    },
    {
        "order_id": "SF-1009",
        "customer_email": "devon.okafor@example.com",
        "status": OrderStatus.IN_TRANSIT,
        "courier": "Summit Sprite Shipping (Fictional)",
        "estimated_delivery": date(2026, 3, 29),
        "last_update": _ts(2026, 3, 23, 6, 45),
        "notes": "Synthetic — out for sortation.",
    },
    {
        "order_id": "SF-1010",
        "customer_email": "ellis.patel@example.com",
        "status": OrderStatus.DELIVERED,
        "courier": "Harbor Halo Delivery (Fictional)",
        "estimated_delivery": date(2026, 3, 15),
        "last_update": _ts(2026, 3, 15, 12, 0),
        "notes": "Synthetic — delivered to fictional address.",
    },
]
