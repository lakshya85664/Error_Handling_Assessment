
from src.providers import FakeOrderProvider
from src.registry import ToolRegistry, ToolSpec
from src.schemas import OrderLookupInput, OrderUpdateInput


def build_registry(
    provider: FakeOrderProvider,
) -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            name="order_lookup",
            version="1.0",
            description="Look up an order by its identifier.",
            input_model=OrderLookupInput,
            handler=provider.lookup_order,
            allowed_roles=frozenset({"support", "admin"}),
            access="read",
        )
    )

    registry.register(
        ToolSpec(
            name="order_update",
            version="1.0",
            description="Update the status of an existing order.",
            input_model=OrderUpdateInput,
            handler=provider.update_order,
            allowed_roles=frozenset({"admin"}),
            access="write",
        )
    )

    return registry
