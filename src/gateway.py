
from dataclasses import asdict
from time import sleep
from typing import Any

from pydantic import ValidationError

from src.contracts import ErrorStatus, NextAction, ToolCall, ToolResult
from src.observability import EventLogger
from src.providers import (
    FakeOrderProvider,
    ProviderTimeout,
    ProviderUnavailable,
)
from src.reliability import IdempotencyStore, RateLimiter
from src.registry import ToolRegistry
from src.tool_setup import build_registry


class ToolGateway:
    """Validate, authorize, and reliably execute registered tools."""

    def __init__(
        self,
        provider: FakeOrderProvider | None = None,
        registry: ToolRegistry | None = None,
        rate_limit: int = 5,
        max_retries: int = 2,
        retry_delay: float = 0.01,
    ) -> None:
        self.provider = provider or FakeOrderProvider()
        self.registry = registry or build_registry(self.provider)
        self.rate_limiter = RateLimiter(limit=rate_limit, window_seconds=60)
        self.idempotency = IdempotencyStore()
        self.logger = EventLogger()
        self.max_retries = max(0, max_retries)
        self.retry_delay = max(0.0, retry_delay)

    def _result(
        self,
        call: ToolCall,
        result: ToolResult,
    ) -> ToolResult:
        self.logger.emit(
            event="tool.completed",
            request_id=call.request_id,
            status=result.status.value,
            tool_name=call.name,
        )
        result.events = [self.logger.events[-1]]
        return result

    def dispatch(
        self,
        request: ToolCall | dict[str, Any],
        role: str,
    ) -> ToolResult:
        try:
            call = (
                request
                if isinstance(request, ToolCall)
                else ToolCall.model_validate(request)
            )
        except ValidationError:
            return ToolResult(
                status=ErrorStatus.INVALID,
                next_action=NextAction.CORRECT_ARGUMENTS,
            )

        cached = self.idempotency.get(call.request_id)
        if cached is not None:
            return ToolResult.model_validate(cached)

        spec = self.registry.get(call.name, call.version)
        if spec is None:
            return self._result(
                call,
                ToolResult(
                    status=ErrorStatus.NOT_FOUND,
                    next_action=NextAction.CHOOSE_REGISTERED_TOOL,
                ),
            )

        if role not in spec.allowed_roles:
            return self._result(
                call,
                ToolResult(
                    status=ErrorStatus.DENIED,
                    next_action=NextAction.REQUEST_AUTHORIZATION,
                ),
            )

        if not self.rate_limiter.allow(f"{role}:{call.name}"):
            return self._result(
                call,
                ToolResult(
                    status=ErrorStatus.RATE_LIMITED,
                    next_action=NextAction.RETRY,
                ),
            )

        try:
            validated = spec.input_model.model_validate(call.arguments)
        except ValidationError:
            return self._result(
                call,
                ToolResult(
                    status=ErrorStatus.INVALID,
                    next_action=NextAction.CORRECT_ARGUMENTS,
                ),
            )

        arguments = validated.model_dump()
        attempts = 0

        while True:
            try:
                data = spec.handler(arguments)
                break
            except ProviderTimeout:
                if attempts >= self.max_retries:
                    return self._result(
                        call,
                        ToolResult(
                            status=ErrorStatus.TIMEOUT,
                            next_action=NextAction.RETRY,
                        ),
                    )

                attempts += 1
                if self.retry_delay:
                    sleep(self.retry_delay)
            except ProviderUnavailable:
                if attempts >= self.max_retries:
                    return self._result(
                        call,
                        ToolResult(
                            status=ErrorStatus.RETRY_EXHAUSTED,
                            next_action=NextAction.REVIEW,
                        ),
                    )

                attempts += 1
                if self.retry_delay:
                    sleep(self.retry_delay)
            except Exception:
                return self._result(
                    call,
                    ToolResult(
                        status=ErrorStatus.FAILED,
                        next_action=NextAction.REVIEW,
                    ),
                )

        if data.get("found") is False or data.get("updated") is False:
            result = ToolResult(
                status=ErrorStatus.NOT_FOUND,
                data=data,
                next_action=NextAction.CHECK_STATUS,
            )
        else:
            result = ToolResult(
                status=ErrorStatus.OK,
                data=data,
                next_action=NextAction.NONE,
            )

        result = self._result(call, result)
        self.idempotency.put(call.request_id, result.model_dump(mode="json"))
        return result
