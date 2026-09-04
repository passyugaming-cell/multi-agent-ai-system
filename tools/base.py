"""Tools architecture base abstractions and models.

Defines typed interfaces and execution models for agent tools.
Enforces security guardrails preventing arbitrary shell or code execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from core.exceptions import ToolExecutionError


class ToolInput(BaseModel):
    """Base schema for structured tool inputs."""

    model_config = {"extra": "forbid"}


class ToolOutput(BaseModel):
    """Base schema for structured tool execution outputs."""

    success: bool = Field(description="Indicates if the tool execution was successful.")
    result: Any = Field(default=None, description="The output payload resulting from tool execution.")
    error: str | None = Field(default=None, description="Error message if tool execution failed.")


InputT = TypeVar("InputT", bound=ToolInput)
OutputT = TypeVar("OutputT", bound=ToolOutput)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all agent tools.

    Security Policy:
    Tools must be explicitly defined and allowlisted. Arbitrary shell or code
    execution is strictly prohibited.
    """

    name: str
    description: str

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, tool_input: InputT) -> OutputT:
        """Executes the tool synchronously with the provided validated input.

        Args:
            tool_input: Validated input schema for the tool.

        Returns:
            ToolOutput containing execution result or error.

        Raises:
            ToolExecutionError: If execution fails or violates security policy.
        """
        pass
