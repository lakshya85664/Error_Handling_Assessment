
import pytest
from pydantic import ValidationError

from src.contracts import ErrorStatus, ToolCall, ToolResult
from src.providers import FakeOrderProvider, ProviderTimeout
from src.schemas import OrderLookupInput, OrderUpdateInput
from src.tool_setup import build_registry


def test_tool_call_contract():
    call = ToolCall(
        request_id="req-1",
        name="order_lookup",
        version="1.0",
        arguments={"order_id": "ORD-1001"},
    )
    assert call.name == "order_lookup"
    assert call.request_id == "req-1"


def test_tool_call_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ToolCall(
            request_id="req-1",
            name="order_lookup",
            version="1.0",
            unexpected="value",
        )


def test_tool_result_serializes_status():
    result = ToolResult(status=ErrorStatus.OK)
    assert result.model_dump(mode="json")["status"] == "ok"


def test_order_lookup_schema_accepts_valid_id():
    assert OrderLookupInput(order_id="ORD-1001").order_id == "ORD-1001"


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"order_id": ""},
        {"order_id": "INVALID"},
        {"order_id": "ORD-1001", "extra": "blocked"},
    ],
)
def test_order_lookup_schema_rejects_invalid_input(arguments):
    with pytest.raises(ValidationError):
        OrderLookupInput.model_validate(arguments)


def test_order_update_schema_accepts_allowed_status():
    result = OrderUpdateInput(
        order_id="ORD-1001",
        status="shipped",
    )
    assert result.status == "shipped"


def test_order_update_schema_rejects_invalid_status():
    with pytest.raises(ValidationError):
        OrderUpdateInput(
            order_id="ORD-1001",
            status="teleported",
        )


def test_registry_contains_expected_tools():
    provider = FakeOrderProvider()
    registry = build_registry(provider)

    assert registry.get("order_lookup", "1.0") is not None
    assert registry.get("order_update", "1.0") is not None
    assert len(registry.list_tools()) == 2


def test_registry_returns_none_for_unknown_tool():
    registry = build_registry(FakeOrderProvider())
    assert registry.get("unknown_tool", "1.0") is None


def test_update_tool_is_admin_only():
    registry = build_registry(FakeOrderProvider())
    spec = registry.get("order_update", "1.0")

    assert spec is not None
    assert spec.allowed_roles == frozenset({"admin"})
    assert spec.access == "write"


def test_lookup_tool_allows_support_and_admin():
    registry = build_registry(FakeOrderProvider())
    spec = registry.get("order_lookup", "1.0")

    assert spec is not None
    assert spec.allowed_roles == frozenset({"support", "admin"})
    assert spec.access == "read"


def test_provider_returns_existing_order():
    provider = FakeOrderProvider()
    result = provider.lookup_order({"order_id": "ORD-1001"})

    assert result["found"] is True
    assert result["order"]["status"] == "processing"


def test_provider_reports_unknown_order():
    provider = FakeOrderProvider()
    result = provider.lookup_order({"order_id": "ORD-9999"})

    assert result["found"] is False


def test_provider_update_changes_status():
    provider = FakeOrderProvider()
    result = provider.update_order(
        {"order_id": "ORD-1001", "status": "shipped"}
    )

    assert result["updated"] is True
    assert result["order"]["status"] == "shipped"
    assert provider.update_count == 1


def test_provider_timeout_injection():
    provider = FakeOrderProvider()
    provider.failure_mode = "timeout"

    with pytest.raises(ProviderTimeout):
        provider.lookup_order({"order_id": "ORD-1001"})
