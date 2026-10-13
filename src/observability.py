
import json
from datetime import datetime, timezone
from typing import Any


class EventLogger:
    """Collect structured events without logging request arguments."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def emit(
        self,
        event: str,
        request_id: str,
        status: str,
        tool_name: str,
    ) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "request_id": request_id,
            "status": status,
            "tool_name": tool_name,
        }

        # Validate that the event is JSON serializable.
        json.dumps(record)
        self.events.append(record)
        return record

    def to_json(self) -> str:
        return json.dumps(self.events, indent=2)
