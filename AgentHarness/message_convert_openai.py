import json
from typing import Any

from AgentHarness.messages import Message, AIMessage, ToolMessage, ToolCall


def message_to_openai(message: Message) -> dict[str, Any]:
    if isinstance(message, AIMessage):
        result: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
        }

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(
                            call.arguments,
                            ensure_ascii=False,
                        ),
                    },
                }
                for call in message.tool_calls
            ]

        return result

    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
        }

    return {
        "role": message.role,
        "content": message.content,
    }

def from_openai_message(message) -> AIMessage:
    raw_tool_calls = getattr(message, "tool_calls", None) or []

    return AIMessage(
        content=message.content,
        tool_calls=[
            ToolCall(
                id=tool.id,
                name=tool.function.name,
                arguments=json.loads(tool.function.arguments or "{}"),
            )
            for tool in raw_tool_calls
        ],
    )