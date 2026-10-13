
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    allowed_roles: frozenset[str]
    access: str  # "read" or "write"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    @staticmethod
    def _key(name: str, version: str) -> str:
        return f"{name}:{version}"

    def register(self, spec: ToolSpec) -> None:
        if spec.access not in {"read", "write"}:
            raise ValueError("Tool access must be 'read' or 'write'")

        if not spec.name.strip() or not spec.version.strip():
            raise ValueError("Tool name and version are required")

        key = self._key(spec.name, spec.version)
        if key in self._tools:
            raise ValueError(f"Tool already registered: {key}")

        self._tools[key] = spec

    def get(self, name: str, version: str) -> ToolSpec | None:
        return self._tools.get(self._key(name, version))

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "version": spec.version,
                "description": spec.description,
                "allowed_roles": sorted(spec.allowed_roles),
                "access": spec.access,
                "input_schema": spec.input_model.model_json_schema(),
            }
            for spec in sorted(
                self._tools.values(),
                key=lambda item: (item.name, item.version),
            )
        ]
