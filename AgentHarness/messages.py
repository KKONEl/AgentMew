from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    arguments: dict[str, Any]


class BaseMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str | None = None


class SystemMessage(BaseMessage):
    role: Literal["system"] = "system"
    content: str


class HumanMessage(BaseMessage):
    role: Literal["user"] = "user"
    content: str


class AIMessage(BaseMessage):
    role: Literal["assistant"] = "assistant"
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolMessage(BaseMessage):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str


Message: TypeAlias = Annotated[
    SystemMessage
    | HumanMessage
    | AIMessage
    | ToolMessage,
    Field(discriminator="role"),
]