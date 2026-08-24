from __future__ import annotations

from copy import deepcopy
from typing import Any


def _base() -> dict[str, Any]:
    return {
        "customers": {
            "c_alice": {
                "id": "c_alice",
                "name": "Alice Chen",
                "email": "alice@example.com",
                "tier": "gold",
            },
            "c_bob": {
                "id": "c_bob",
                "name": "Bob Singh",
                "email": "bob@example.com",
                "tier": "standard",
            },
        },
        "products": {
            "p_mug": {"id": "p_mug", "name": "Ceramic Mug", "price": 18.0},
            "p_shirt": {"id": "p_shirt", "name": "Black Shirt", "price": 32.0},
            "p_cable": {"id": "p_cable", "name": "USB-C Cable", "price": 12.0},
        },
        "orders": {
            "o_100": {
                "id": "o_100",
                "customer_id": "c_alice",
                "items": [{"product_id": "p_mug", "qty": 1, "price": 18.0}],
                "amount": 18.0,
                "status": "delivered",
                "created_at": "2026-08-01",
            },
            "o_101": {
                "id": "o_101",
                "customer_id": "c_alice",
                "items": [{"product_id": "p_shirt", "qty": 1, "price": 32.0}],
                "amount": 32.0,
                "status": "delivered",
                "created_at": "2026-08-15",
            },
            "o_200": {
                "id": "o_200",
                "customer_id": "c_bob",
                "items": [{"product_id": "p_cable", "qty": 2, "price": 12.0}],
                "amount": 24.0,
                "status": "processing",
                "created_at": "2026-08-18",
            },
        },
        "payments": {
            "pay_100": {"id": "pay_100", "order_id": "o_100", "amount": 18.0, "status": "captured"},
            "pay_101": {"id": "pay_101", "order_id": "o_101", "amount": 32.0, "status": "captured"},
            "pay_200": {"id": "pay_200", "order_id": "o_200", "amount": 24.0, "status": "captured"},
        },
        "refunds": {},
        "tickets": {
            "t_1": {
                "id": "t_1",
                "customer_id": "c_alice",
                "order_id": "o_101",
                "status": "open",
                "subject": "Want a refund on latest order",
            }
        },
        "policies": {
            "refund_window": {
                "id": "refund_window",
                "title": "Refund window",
                "text": "Delivered orders may be refunded within 30 days. Processing orders are not refundable until delivered or cancelled.",
            },
            "gold_courtesy": {
                "id": "gold_courtesy",
                "title": "Gold courtesy refund",
                "text": "Gold-tier customers may receive one courtesy refund on a delivered order. Never refund processing orders.",
            },
        },
        "messages": [],
        "meta": {"now": "2026-08-24", "store": "demo"},
    }


FIXTURES: dict[str, dict[str, Any]] = {
    "baseline_001": _base(),
}


def get_fixture(name: str) -> dict[str, Any]:
    if name not in FIXTURES:
        raise KeyError(f"Unknown fixture: {name}. Have {list(FIXTURES)}")
    return deepcopy(FIXTURES[name])