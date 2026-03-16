from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class TaskContext(BaseModel):
    """Structured context passed around during processing."""

    user_id: str | None = None
    phone: str | None = None
    role: str | None = None
    raw_message: str | None = None
    intent: str | None = None
    confidence: float | None = None
    extracted: dict[str, Any] | None = None


class BaseAgent(ABC):
    def __init__(self, context: TaskContext):
        self.context = context

    @abstractmethod
    def process(self) -> TaskContext:
        """Perform agent-specific processing and update context."""
        ...
