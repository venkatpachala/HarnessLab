from harnesslab.environment.commerce.world import CommerceWorld


def test_refund_is_stateful():
    env = CommerceWorld()
    before = env.get_state()
    elig = env.call_tool("check_refund_eligibility", {"order_id": "o_101"})
    assert elig.ok and elig.data["eligible"] is True
    ref = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert ref.ok
    pay = env.call_tool("get_payment", {"order_id": "o_101"})
    assert pay.data["status"] == "refunded"
    order = env.call_tool("get_order", {"order_id": "o_101"})
    assert order.data["status"] == "refunded"
    diff = env.diff(before)
    assert "orders.o_101.status" in diff


def test_cannot_refund_processing():
    env = CommerceWorld()
    elig = env.call_tool("check_refund_eligibility", {"order_id": "o_200"})
    assert elig.data["eligible"] is False
    ref = env.call_tool("refund_payment", {"order_id": "o_200"})
    assert not ref.ok
    assert env.get_state()["orders"]["o_200"]["status"] == "processing"


def test_permission_denied():
    env = CommerceWorld(permissions={"refund": False})
    ref = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert ref.code == "permission_denied"


def test_fail_times_then_succeeds():
    env = CommerceWorld(
        faults=[{"tool": "refund_payment", "type": "timeout", "fail_times": 2}]
    )
    a = env.call_tool("refund_payment", {"order_id": "o_101"})
    b = env.call_tool("refund_payment", {"order_id": "o_101"})
    c = env.call_tool("refund_payment", {"order_id": "o_101"})
    assert a.code == "timeout" and not a.ok
    assert b.code == "timeout" and not b.ok
    assert c.ok
    assert env.get_state()["orders"]["o_101"]["status"] == "refunded"


def test_snapshot_restore():
    env = CommerceWorld()
    snap = env.snapshot()
    env.call_tool("refund_payment", {"order_id": "o_101"})
    env.restore(snap)
    assert env.get_state()["orders"]["o_101"]["status"] == "delivered"


def test_fault_injection_always():
    env = CommerceWorld(faults=[{"tool": "get_order", "type": "timeout", "probability": 1.0}])
    r = env.call_tool("get_order", {"order_id": "o_101"})
    assert r.code == "timeout"