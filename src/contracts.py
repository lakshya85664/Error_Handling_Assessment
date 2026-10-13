
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorStatus(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    DENIED = "denied"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    RETRY_EXHAUSTED = "retry_exhausted"
    RATE_LIMITED = "rate_limited"
    CONFLICT = "conflict"
    FAILED = "failed"


class NextAction(str, Enum):
    NONE = "none"
    CORRECT_ARGUMENTS = "correct_arguments"
    CHOOSE_REGISTERED_TOOL = "choose_registered_tool"
    REQUEST_AUTHORIZATION = "request_authorization"
    RETRY = "retry"
    REVIEW = "review"
    CHECK_STATUS = "check_status"


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=30)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ErrorStatus
    data: dict[str, Any] = Field(default_factory=dict)
    next_action: NextAction = NextAction.NONE
    events: list[dict[str, Any]] = Field(default_factory=list)
