from __future__ import annotations

import pytest
from harnesslab.environment.commerce.world import CommerceWorld


def test_commerce_world_reset():
    env = CommerceWorld()
    state1 = env.get_state()
    env.call_tool("refund_payment", {"order_id": "o_101"})
    assert env.get_state()["orders"]["o_101"]["status"] == "refunded"
    state2 = env.reset()
    assert state2 == state1
    assert env.get_state()["orders"]["o_101"]["status"] == "delivered"


def test_commerce_world_snapshot_restore():
    env = CommerceWorld()
    snap = env.snapshot()
    res = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert res.ok is True
    assert env.get_state()["orders"]["o_101"]["status"] == "refunded"
    env.restore(snap)
    assert env.get_state()["orders"]["o_101"]["status"] == "delivered"


def test_commerce_world_stateful_refund():
    env = CommerceWorld()
    check = env.call_tool("check_refund_eligibility", {"order_id": "o_101"})
    assert check.ok is True
    assert check.data["eligible"] is True

    res = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert res.ok is True
    assert res.data["status"] == "completed"

    pay = env.call_tool("get_payment", {"order_id": "o_101"})
    assert pay.ok is True
    assert pay.data["status"] == "refunded"
    assert env.get_state()["orders"]["o_101"]["status"] == "refunded"


def test_commerce_world_refuse_processing():
    env = CommerceWorld()
    check = env.call_tool("check_refund_eligibility", {"order_id": "o_200"})
    assert check.ok is True
    assert check.data["eligible"] is False
    assert check.data["reason"] == "not_delivered"

    res = env.call_tool("refund_payment", {"order_id": "o_200"})
    assert res.ok is False
    assert res.code == "ineligible"
    assert env.get_state()["orders"]["o_200"]["status"] == "processing"


def test_commerce_world_diff():
    env = CommerceWorld()
    before = env.snapshot()
    env.call_tool("refund_payment", {"order_id": "o_101"})
    diff = env.diff(before)
    assert "orders.o_101.status" in diff
    assert diff["orders.o_101.status"] == {"from": "delivered", "to": "refunded"}
    assert "payments.pay_101.status" in diff
    assert diff["payments.pay_101.status"] == {"from": "captured", "to": "refunded"}


def test_commerce_world_permissions():
    env = CommerceWorld(permissions={"refund": False})
    res = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert res.ok is False
    assert res.code == "permission_denied"


def test_commerce_world_faults():
    env = CommerceWorld(faults=[{"tool": "get_order", "type": "timeout", "probability": 1.0}])
    res = env.call_tool("get_order", {"order_id": "o_101"})
    assert res.ok is False
    assert res.code == "timeout"
    assert res.error == "Tool timed out"
