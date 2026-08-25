from __future__ import annotations

import copy
import random
from typing import Any, Callable

from harnesslab.environment.base import Environment, ToolError, ToolResult, ToolSpec
from harnesslab.environment.commerce.fixtures import get_fixture

DEFAULT_PERMISSIONS = {
    "customer_read": True,
    "order_read": True,
    "payment_read": True,
    "refund": True,
    "ticket_write": True,
    "message_send": True,
    "policy_read": True,
    "customer_delete": False,
}


class CommerceWorld(Environment):
    name = "commerce_world"
    version = "0.1"

    def __init__(
        self,
        fixture: str = "baseline_001",
        permissions: dict[str, bool] | None = None,
        faults: list[dict[str, Any]] | None = None,
        rng_seed: int = 0,
    ):
        self._fixture_name = fixture
        self.permissions = {**DEFAULT_PERMISSIONS, **(permissions or {})}
        self.faults = list(faults or [])
        self._rng = random.Random(rng_seed)
        self._state: dict[str, Any] = {}
        self._handlers: dict[str, Callable[..., Any]] = {
            "get_customer": self._get_customer,
            "search_customers": self._search_customers,
            "get_order": self._get_order,
            "list_orders": self._list_orders,
            "search_orders": self._search_orders,
            "get_payment": self._get_payment,
            "check_refund_eligibility": self._check_refund_eligibility,
            "refund_payment": self._refund_payment,
            "get_ticket": self._get_ticket,
            "create_ticket": self._create_ticket,
            "update_ticket": self._update_ticket,
            "send_message": self._send_message,
            "search_policy": self._search_policy,
        }
        self.reset(fixture)

    def reset(self, fixture: str | None = None) -> dict[str, Any]:
        name = fixture or self._fixture_name
        self._fixture_name = name
        self._state = get_fixture(name)
        return self.get_state()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def restore(self, snap: dict[str, Any]) -> None:
        self._state = copy.deepcopy(snap)

    def get_state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="get_customer",
                description="Get a customer by id.",
                parameters={"customer_id": {"type": "string"}},
                permission="customer_read",
            ),
            ToolSpec(
                name="search_customers",
                description="Search customers by name or email substring.",
                parameters={"query": {"type": "string"}},
                permission="customer_read",
            ),
            ToolSpec(
                name="get_order",
                description="Get an order by id.",
                parameters={"order_id": {"type": "string"}},
                permission="order_read",
            ),
            ToolSpec(
                name="list_orders",
                description="List orders for a customer_id, newest first.",
                parameters={"customer_id": {"type": "string"}},
                permission="order_read",
            ),
            ToolSpec(
                name="search_orders",
                description="Search orders by customer_id and optional status.",
                parameters={
                    "customer_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                permission="order_read",
            ),
            ToolSpec(
                name="get_payment",
                description="Get a payment by id or by order_id.",
                parameters={
                    "payment_id": {"type": "string"},
                    "order_id": {"type": "string"},
                },
                permission="payment_read",
            ),
            ToolSpec(
                name="check_refund_eligibility",
                description="Return whether an order can be refunded and why.",
                parameters={"order_id": {"type": "string"}},
                permission="payment_read",
            ),
            ToolSpec(
                name="refund_payment",
                description="Refund the captured payment for an order if eligible.",
                parameters={"order_id": {"type": "string"}},
                permission="refund",
            ),
            ToolSpec(
                name="get_ticket",
                description="Get a support ticket by id.",
                parameters={"ticket_id": {"type": "string"}},
                permission="ticket_write",
            ),
            ToolSpec(
                name="create_ticket",
                description="Create a support ticket.",
                parameters={
                    "customer_id": {"type": "string"},
                    "subject": {"type": "string"},
                    "order_id": {"type": "string"},
                },
                permission="ticket_write",
            ),
            ToolSpec(
                name="update_ticket",
                description="Update ticket status or note.",
                parameters={
                    "ticket_id": {"type": "string"},
                    "status": {"type": "string"},
                    "note": {"type": "string"},
                },
                permission="ticket_write",
            ),
            ToolSpec(
                name="send_message",
                description="Send a message to a customer.",
                parameters={
                    "customer_id": {"type": "string"},
                    "body": {"type": "string"},
                },
                permission="message_send",
            ),
            ToolSpec(
                name="search_policy",
                description="Search policy documents.",
                parameters={"query": {"type": "string"}},
                permission="policy_read",
            ),
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        spec = next((t for t in self.list_tools() if t.name == name), None)
        if spec is None:
            return ToolResult(ok=False, code="unknown_tool", error=f"Unknown tool: {name}")

        if spec.permission and not self.permissions.get(spec.permission, False):
            return ToolResult(
                ok=False,
                code="permission_denied",
                error=f"Permission denied: {spec.permission}",
            )

        fault = self._maybe_fault(name)
        if fault is not None:
            return fault

        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(ok=False, code="unknown_tool", error=f"Unknown tool: {name}")
        try:
            data = handler(**{k: v for k, v in arguments.items() if v is not None})
            return ToolResult(ok=True, data=copy.deepcopy(data))
        except TypeError as e:
            return ToolResult(ok=False, code="bad_arguments", error=str(e))
        except ToolError as e:
            res = e.to_result()
            res.data = copy.deepcopy(res.data)
            return res

    def inject_event(self, kind: str, payload: dict[str, Any]) -> None:
        """Non-stationary world hook (used later)."""
        if kind == "order_status":
            oid = payload["order_id"]
            if oid in self._state["orders"]:
                self._state["orders"][oid]["status"] = payload["status"]
        elif kind == "customer_message":
            self._state["messages"].append(
                {
                    "id": f"m_{len(self._state['messages'])+1}",
                    "customer_id": payload["customer_id"],
                    "direction": "inbound",
                    "body": payload.get("body", ""),
                }
            )
        else:
            raise ValueError(f"Unknown event kind: {kind}")

    # --- faults ---
    def _maybe_fault(self, tool: str) -> ToolResult | None:
        for f in self.faults:
            if f.get("tool") not in (None, "*", tool):
                continue
            p = float(f.get("probability", 1.0))
            if self._rng.random() > p:
                continue
            kind = f.get("type", "server_error")
            mapping = {
                "timeout": ("timeout", "Tool timed out"),
                "rate_limit": ("rate_limit", "429 rate limited"),
                "server_error": ("server_error", "500 server error"),
                "permission_denied": ("permission_denied", "403 forbidden"),
                "malformed_response": ("malformed_response", "Malformed payload"),
                "missing_resource": ("missing_resource", "Resource not found"),
            }
            code, msg = mapping.get(kind, ("server_error", kind))
            return ToolResult(ok=False, code=code, error=msg)
        return None

    # --- domain rules ---
    def _eligibility(self, order: dict[str, Any]) -> tuple[bool, str]:
        if order["status"] == "refunded":
            return False, "already_refunded"
        if order["status"] != "delivered":
            return False, "not_delivered"
        return True, "delivered_within_policy"

    def _payment_for_order(self, order_id: str) -> dict[str, Any] | None:
        for p in self._state["payments"].values():
            if p["order_id"] == order_id:
                return p
        return None

    def _req(self, collection: str, key: str, ident: str) -> dict[str, Any]:
        obj = self._state[collection].get(ident)
        if obj is None:
            raise ToolError("not_found", f"{key} not found: {ident}")
        return obj

    def _get_customer(self, customer_id: str) -> dict[str, Any]:
        return self._req("customers", "customer", customer_id)

    def _search_customers(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            c
            for c in self._state["customers"].values()
            if q in c["name"].lower() or q in c["email"].lower()
        ]

    def _get_order(self, order_id: str) -> dict[str, Any]:
        return self._req("orders", "order", order_id)

    def _list_orders(self, customer_id: str) -> list[dict[str, Any]]:
        self._req("customers", "customer", customer_id)
        orders = [o for o in self._state["orders"].values() if o["customer_id"] == customer_id]
        return sorted(orders, key=lambda o: o["created_at"], reverse=True)

    def _search_orders(self, customer_id: str, status: str | None = None) -> list[dict[str, Any]]:
        orders = self._list_orders(customer_id)
        if status:
            orders = [o for o in orders if o["status"] == status]
        return orders

    def _get_payment(self, payment_id: str | None = None, order_id: str | None = None) -> dict[str, Any]:
        if payment_id:
            return self._req("payments", "payment", payment_id)
        if order_id:
            pay = self._payment_for_order(order_id)
            if not pay:
                raise ToolError("not_found", f"No payment for order {order_id}")
            return pay
        raise ToolError("bad_arguments", "Provide payment_id or order_id")

    def _check_refund_eligibility(self, order_id: str) -> dict[str, Any]:
        order = self._req("orders", "order", order_id)
        ok, reason = self._eligibility(order)
        return {
            "order_id": order_id,
            "eligible": ok,
            "reason": reason,
            "amount": order["amount"],
        }

    def _refund_payment(self, order_id: str) -> dict[str, Any]:
        order = self._req("orders", "order", order_id)
        ok, reason = self._eligibility(order)
        if not ok:
            raise ToolError("ineligible", f"Refund refused: {reason}", {"reason": reason})
        pay = self._payment_for_order(order_id)
        if not pay:
            raise ToolError("not_found", f"No payment for order {order_id}")
        if pay["status"] == "refunded":
            raise ToolError("ineligible", "Payment already refunded", {"reason": "already_refunded"})
        pay["status"] = "refunded"
        order["status"] = "refunded"
        rid = f"r_{order_id}"
        refund = {
            "id": rid,
            "order_id": order_id,
            "payment_id": pay["id"],
            "amount": pay["amount"],
            "status": "completed",
        }
        self._state["refunds"][rid] = refund
        return refund

    def _get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return self._req("tickets", "ticket", ticket_id)

    def _create_ticket(
        self, customer_id: str, subject: str, order_id: str | None = None
    ) -> dict[str, Any]:
        self._req("customers", "customer", customer_id)
        tid = f"t_{len(self._state['tickets']) + 1}"
        ticket = {
            "id": tid,
            "customer_id": customer_id,
            "order_id": order_id,
            "status": "open",
            "subject": subject,
        }
        self._state["tickets"][tid] = ticket
        return ticket

    def _update_ticket(
        self, ticket_id: str, status: str | None = None, note: str | None = None
    ) -> dict[str, Any]:
        ticket = self._req("tickets", "ticket", ticket_id)
        if status:
            ticket["status"] = status
        if note:
            ticket["note"] = note
        return ticket

    def _send_message(self, customer_id: str, body: str) -> dict[str, Any]:
        self._req("customers", "customer", customer_id)
        msg = {
            "id": f"m_{len(self._state['messages']) + 1}",
            "customer_id": customer_id,
            "direction": "outbound",
            "body": body,
        }
        self._state["messages"].append(msg)
        return msg

    def _search_policy(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            p
            for p in self._state["policies"].values()
            if q in p["title"].lower() or q in p["text"].lower() or q in p["id"].lower()
        ]