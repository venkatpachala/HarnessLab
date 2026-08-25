"""Named initial worlds. Tasks point at a fixture, never invent ad-hoc JSON inline."""

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
            "pay_100": {
                "id": "pay_100",
                "order_id": "o_100",
                "amount": 18.0,
                "status": "captured",
            },
            "pay_101": {
                "id": "pay_101",
                "order_id": "o_101",
                "amount": 32.0,
                "status": "captured",
            },
            "pay_200": {
                "id": "pay_200",
                "order_id": "o_200",
                "amount": 24.0,
                "status": "captured",
            },
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
                "text": "Gold-tier customers may receive one courtesy refund on a delivered order even after minor policy ambiguity. Never refund processing orders.",
            },
        },
        "messages": [],
        "meta": {"now": "2026-08-24", "store": "demo"},
    }


def _hard() -> dict[str, Any]:
    """Same schema as baseline; more traps (lookalike name, cancelled, already refunded)."""
    s = _base()
    s["customers"]["c_alicia"] = {
        "id": "c_alicia",
        "name": "Alicia Cheng",
        "email": "alicia@example.com",
        "tier": "standard",
    }
    s["orders"]["o_102"] = {
        "id": "o_102",
        "customer_id": "c_alice",
        "items": [{"product_id": "p_cable", "qty": 1, "price": 12.0}],
        "amount": 12.0,
        "status": "cancelled",
        "created_at": "2026-08-10",
    }
    s["orders"]["o_103"] = {
        "id": "o_103",
        "customer_id": "c_alice",
        "items": [{"product_id": "p_mug", "qty": 2, "price": 18.0}],
        "amount": 36.0,
        "status": "refunded",
        "created_at": "2026-07-20",
    }
    s["orders"]["o_300"] = {
        "id": "o_300",
        "customer_id": "c_alicia",
        "items": [{"product_id": "p_shirt", "qty": 1, "price": 32.0}],
        "amount": 32.0,
        "status": "delivered",
        "created_at": "2026-08-20",
    }
    s["payments"]["pay_102"] = {
        "id": "pay_102",
        "order_id": "o_102",
        "amount": 12.0,
        "status": "voided",
    }
    s["payments"]["pay_103"] = {
        "id": "pay_103",
        "order_id": "o_103",
        "amount": 36.0,
        "status": "refunded",
    }
    s["payments"]["pay_300"] = {
        "id": "pay_300",
        "order_id": "o_300",
        "amount": 32.0,
        "status": "captured",
    }
    s["tickets"]["t_2"] = {
        "id": "t_2",
        "customer_id": "c_bob",
        "order_id": "o_200",
        "status": "open",
        "subject": "Where is my cable order",
    }
    s["refunds"]["r_o_103"] = {
        "id": "r_o_103",
        "order_id": "o_103",
        "payment_id": "pay_103",
        "amount": 36.0,
        "status": "completed",
    }
    return s


FIXTURES: dict[str, dict[str, Any]] = {
    "baseline_001": _base(),
    "hard_001": _hard(),
}


def get_fixture(name: str) -> dict[str, Any]:
    if name not in FIXTURES:
        raise KeyError(f"Unknown fixture: {name}. Have {list(FIXTURES)}")
    return deepcopy(FIXTURES[name])