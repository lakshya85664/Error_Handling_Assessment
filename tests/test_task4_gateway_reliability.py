
from src.contracts import ErrorStatus, ToolCall
from src.gateway import ToolGateway


def make_call(request_id, name="order_lookup", arguments=None):
    if arguments is None:
        arguments = {"order_id": "ORD-1001"}

    return ToolCall(
        request_id=request_id,
        name=name,
        version="1.0",
        arguments=arguments,
    )


def test_gateway_emits_structured_event():
    gateway = ToolGateway()
    result = gateway.dispatch(make_call("event-1"), role="support")

    assert result.status == ErrorStatus.OK
    assert len(result.events) == 1
    assert result.events[0]["event"] == "tool.completed"
    assert result.events[0]["request_id"] == "event-1"


def test_gateway_caches_completed_request():
    gateway = ToolGateway()

    first = gateway.dispatch(make_call("cache-1"), role="support")
    second = gateway.dispatch(make_call("cache-1"), role="support")

    assert first.status == ErrorStatus.OK
    assert second.status == ErrorStatus.OK
    assert gateway.provider.update_count == 0


def test_gateway_rate_limits_excess_requests():
    gateway = ToolGateway(rate_limit=2)

    assert gateway.dispatch(make_call("rate-1"), "support").status == ErrorStatus.OK
    assert gateway.dispatch(make_call("rate-2"), "support").status == ErrorStatus.OK

    third = gateway.dispatch(make_call("rate-3"), "support")
    assert third.status == ErrorStatus.RATE_LIMITED


def test_gateway_retries_timeout_within_bound():
    gateway = ToolGateway(max_retries=2, retry_delay=0)
    gateway.provider.failure_mode = "timeout"

    result = gateway.dispatch(make_call("timeout-1"), "support")

    assert result.status == ErrorStatus.TIMEOUT


def test_gateway_records_failed_outcomes():
    gateway = ToolGateway()
    result = gateway.dispatch(
        make_call(
            "denied-1",
            name="order_update",
            arguments={"order_id": "ORD-1001", "status": "shipped"},
        ),
        role="support",
    )

    assert result.status == ErrorStatus.DENIED
    assert result.events[0]["status"] == "denied"



def test_gateway_retries_exactly_max_retries_plus_one(monkeypatch):
    from dataclasses import replace
    from src.providers import ProviderTimeout

    gateway = ToolGateway(max_retries=2, retry_delay=0)
    spec = gateway.registry.get("order_lookup", "1.0")
    assert spec is not None

    attempts = {"count": 0}

    def always_timeout(arguments):
        attempts["count"] += 1
        raise ProviderTimeout("simulated timeout")

    # The registry holds the original handler reference, so replace
    # the registered ToolSpec rather than patching the provider method.
    gateway.registry._tools["order_lookup:1.0"] = replace(
        spec,
        handler=always_timeout,
    )

    result = gateway.dispatch(make_call("retry-count-1"), "support")

    assert result.status == ErrorStatus.TIMEOUT
    assert attempts["count"] == 3

