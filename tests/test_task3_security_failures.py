
from dataclasses import replace

from src.contracts import ErrorStatus, ToolCall
from src.gateway import ToolGateway


def make_call(name="order_lookup", arguments=None, request_id="security-1"):
    if arguments is None:
        arguments = {"order_id": "ORD-1001"}

    return ToolCall(
        request_id=request_id,
        name=name,
        version="1.0",
        arguments=arguments,
    )


def test_unauthorized_update_does_not_change_order():
    gateway = ToolGateway()
    before = dict(gateway.provider.orders["ORD-1001"])

    result = gateway.dispatch(
        make_call(
            name="order_update",
            arguments={
                "order_id": "ORD-1001",
                "status": "shipped",
            },
        ),
        role="support",
    )

    assert result.status == ErrorStatus.DENIED
    assert gateway.provider.orders["ORD-1001"] == before
    assert gateway.provider.update_count == 0


def test_invalid_arguments_do_not_call_provider(monkeypatch):
    gateway = ToolGateway()

    def forbidden_call(arguments):
        raise AssertionError("Provider must not be called")

    monkeypatch.setattr(gateway.provider, "lookup_order", forbidden_call)

    result = gateway.dispatch(
        make_call(arguments={"order_id": "NOT-AN-ORDER"}),
        role="support",
    )

    assert result.status == ErrorStatus.INVALID


def test_unknown_tool_does_not_call_provider(monkeypatch):
    gateway = ToolGateway()

    def forbidden_call(arguments):
        raise AssertionError("Provider must not be called")

    monkeypatch.setattr(gateway.provider, "lookup_order", forbidden_call)

    result = gateway.dispatch(
        make_call(name="unregistered_tool"),
        role="support",
    )

    assert result.status == ErrorStatus.NOT_FOUND


def test_provider_error_details_are_not_returned():
    gateway = ToolGateway()
    spec = gateway.registry.get("order_lookup", "1.0")
    assert spec is not None

    def failing_handler(arguments):
        raise RuntimeError("password=super-secret-token")

    gateway.registry._tools["order_lookup:1.0"] = replace(
        spec,
        handler=failing_handler,
    )

    result = gateway.dispatch(make_call(), role="support")
    rendered = str(result.model_dump(mode="json"))

    assert result.status == ErrorStatus.FAILED
    assert "super-secret-token" not in rendered
    assert "password=" not in rendered


def test_unknown_role_cannot_update_order():
    gateway = ToolGateway()

    result = gateway.dispatch(
        make_call(
            name="order_update",
            arguments={
                "order_id": "ORD-1001",
                "status": "cancelled",
            },
        ),
        role="guest",
    )

    assert result.status == ErrorStatus.DENIED
    assert gateway.provider.update_count == 0


def test_admin_can_update_order():
    gateway = ToolGateway()

    result = gateway.dispatch(
        make_call(
            name="order_update",
            arguments={
                "order_id": "ORD-1001",
                "status": "shipped",
            },
        ),
        role="admin",
    )

    assert result.status == ErrorStatus.OK
    assert gateway.provider.orders["ORD-1001"]["status"] == "shipped"
    assert gateway.provider.update_count == 1
