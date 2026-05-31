from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type

from pydantic import BaseModel
from sqlalchemy.orm import Session


@dataclass
class ToolRuntime:
    db: Session
    organization_id: str


class Tool(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel] | None = None

    @abstractmethod
    def execute(self, runtime: ToolRuntime, payload: BaseModel) -> dict[str, Any]:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def all(self) -> list[Tool]:
        return list(self._tools.values())

