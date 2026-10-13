
from typing import Any


class ProviderError(Exception):
    """Base exception for simulated provider failures."""


class ProviderTimeout(ProviderError):
    """Simulated provider timeout."""


class ProviderUnavailable(ProviderError):
    """Simulated upstream service failure."""


class FakeOrderProvider:
    """Deterministic in-memory provider; never contacts a real service."""

    def __init__(self) -> None:
        self.orders: dict[str, dict[str, Any]] = {
            "ORD-1001": {
                "order_id": "ORD-1001",
                "status": "processing",
            },
            "ORD-1002": {
                "order_id": "ORD-1002",
                "status": "shipped",
            },
            "ORD-1003": {
                "order_id": "ORD-1003",
                "status": "cancelled",
            },
        }
        self.update_count = 0
        self.failure_mode: str | None = None

    def _check_failure(self) -> None:
        if self.failure_mode == "timeout":
            raise ProviderTimeout("Simulated provider timeout")

        if self.failure_mode == "unavailable":
            raise ProviderUnavailable("Simulated upstream failure")

    def lookup_order(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._check_failure()

        order_id = arguments["order_id"]
        order = self.orders.get(order_id)

        if order is None:
            return {"found": False, "order_id": order_id}

        return {"found": True, "order": dict(order)}

    def update_order(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._check_failure()

        order_id = arguments["order_id"]
        order = self.orders.get(order_id)

        if order is None:
            return {"updated": False, "order_id": order_id}

        order["status"] = arguments["status"]
        self.update_count += 1

        return {"updated": True, "order": dict(order)}
