
import pytest
from pydantic import ValidationError

from src.contracts import ErrorStatus, NextAction, ToolCall
from src.gateway import ToolGateway
from src.providers import ProviderTimeout, ProviderUnavailable


def make_call(
    name="order_lookup",
    arguments=None,
    request_id="test-1",
    version="1.0",
):
    if arguments is None:
        arguments = {"order_id": "ORD-1001"}

    return ToolCall(
        request_id=request_id,
        name=name,
        version=version,
        arguments=arguments,
    )


def test_successful_lookup():
    gateway = ToolGateway()
    result = gateway.dispatch(make_call(), role="support")

    assert result.status == ErrorStatus.OK
    assert result.data["found"] is True


def test_unknown_order_returns_not_found():
    gateway = ToolGateway()
    result = gateway.dispatch(
        make_call(arguments={"order_id": "ORD-9999"}),
        role="support",
    )

    assert result.status == ErrorStatus.NOT_FOUND
    assert result.next_action == NextAction.CHECK_STATUS


def test_unknown_tool_returns_not_found():
    gateway = ToolGateway()
    result = gateway.dispatch(
        make_call(name="unknown_tool"),
        role="admin",
    )

    assert result.status == ErrorStatus.NOT_FOUND
    assert result.next_action == NextAction.CHOOSE_REGISTERED_TOOL


def test_unknown_version_returns_not_found():
    gateway = ToolGateway()
    result = gateway.dispatch(
        make_call(version="99.0"),
        role="support",
    )

    assert result.status == ErrorStatus.NOT_FOUND


def test_unauthorized_write_is_denied():
    gateway = ToolGateway()
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
    assert result.next_action == NextAction.REQUEST_AUTHORIZATION
    assert gateway.provider.update_count == 0


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"order_id": "bad-id"},
        {"order_id": "ORD-1001", "unexpected": "value"},
    ],
)
def test_invalid_tool_arguments_are_rejected(arguments):
    gateway = ToolGateway()
    result = gateway.dispatch(
        make_call(arguments=arguments),
        role="support",
    )

    assert result.status == ErrorStatus.INVALID
    assert result.next_action == NextAction.CORRECT_ARGUMENTS


def test_provider_timeout_maps_to_timeout():
    gateway = ToolGateway()
    gateway.provider.failure_mode = "timeout"

    result = gateway.dispatch(make_call(), role="support")

    assert result.status == ErrorStatus.TIMEOUT
    assert result.next_action == NextAction.RETRY


def test_provider_unavailable_maps_to_retry_exhausted():
    gateway = ToolGateway()
    gateway.provider.failure_mode = "unavailable"

    result = gateway.dispatch(make_call(), role="support")

    assert result.status == ErrorStatus.RETRY_EXHAUSTED
    assert result.next_action == NextAction.REVIEW


def test_unexpected_provider_exception_is_redacted():
    gateway = ToolGateway()
    spec = gateway.registry.get("order_lookup", "1.0")
    assert spec is not None

    def broken_handler(arguments):
        raise RuntimeError("secret internal detail")

    # Replace the handler in this test only.
    from dataclasses import replace

    gateway.registry._tools["order_lookup:1.0"] = replace(
        spec,
        handler=broken_handler,
    )

    result = gateway.dispatch(make_call(), role="support")

    assert result.status == ErrorStatus.FAILED
    assert "secret internal detail" not in str(result.model_dump())


def test_invalid_outer_contract_is_rejected():
    gateway = ToolGateway()

    result = gateway.dispatch(
        {
            "request_id": "bad",
            "name": "order_lookup",
            "version": "1.0",
            "arguments": {},
            "unexpected": True,
        },
        role="support",
    )

    assert result.status == ErrorStatus.INVALID


def test_outer_validation_exception_is_not_exposed():
    gateway = ToolGateway()

    with pytest.raises(ValidationError):
        ToolCall(
            request_id="",
            name="order_lookup",
            version="1.0",
        )
