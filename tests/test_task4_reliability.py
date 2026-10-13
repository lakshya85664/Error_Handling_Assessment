
import json

from src.observability import EventLogger
from src.reliability import IdempotencyStore, RateLimiter


def test_rate_limiter_allows_requests_within_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("support-user")
    assert limiter.allow("support-user")


def test_rate_limiter_rejects_request_over_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("support-user")
    assert limiter.allow("support-user")
    assert not limiter.allow("support-user")


def test_rate_limiter_tracks_keys_separately():
    limiter = RateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("user-a")
    assert limiter.allow("user-b")
    assert not limiter.allow("user-a")


def test_idempotency_store_returns_cached_result():
    store = IdempotencyStore()
    result = {"status": "ok", "data": {"updated": True}}

    store.put("request-1", result)

    assert store.get("request-1") == result


def test_idempotency_store_returns_none_for_unknown_key():
    store = IdempotencyStore()

    assert store.get("missing-request") is None


def test_idempotency_store_does_not_return_mutable_internal_dict():
    store = IdempotencyStore()
    store.put("request-1", {"status": "ok"})

    cached = store.get("request-1")
    assert cached is not None
    cached["status"] = "changed"

    assert store.get("request-1") == {"status": "ok"}


def test_event_logger_emits_json_without_arguments():
    logger = EventLogger()
    logger.emit(
        event="tool.completed",
        request_id="request-1",
        status="ok",
        tool_name="order_lookup",
    )

    events = json.loads(logger.to_json())

    assert len(events) == 1
    assert events[0]["status"] == "ok"
    assert "arguments" not in events[0]
