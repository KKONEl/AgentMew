import json
import logging

from AgentHarness.configs.config import (
    MAX_REACTIVE_RETRIES,
    api_key,
    base_url,
    model,
)
from openai import OpenAI

from AgentHarness.hooks import trigger_hooks
from AgentHarness.tools import TOOLS, TOOL_HANDLERS
from AgentHarness.subagent import TASK_TOOL, run_subagent
from AgentHarness.compaction import Compactor
from AgentHarness.memory import consolidate_memories, extract_memories

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)
COMPACTOR = Compactor()
COMPACTOR.client = client
COMPACTOR.model = model
logger = logging.getLogger(__name__)

COMPACT_TOOL = {
    "type": "function",
    "function": {
        "name": "compact",
        "description": "Summarize earlier conversation after this tool batch completes.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

PARENT_TOOLS = [*TOOLS, TASK_TOOL, COMPACT_TOOL]

PARENT_HANDLERS = {
    **TOOL_HANDLERS,
    "task": run_subagent,
}

def agent_loop(
    messages: list,
    available_tools: list = PARENT_TOOLS,
    handlers: dict = PARENT_HANDLERS,
    active_request: str | None = None,
):
    # 保存本轮原始 query，避免之后的历史摘要覆盖用户当前请求。
    if active_request is None:
        active_request = next(
            (
                message.get("content", "")
                for message in reversed(messages)
                if message.get("role") == "user"
                and isinstance(message.get("content"), str)
            ),
            "",
        )

    rounds_since_todo = 0
    reactive_retries = 0
    while True:
        # 每次请求都先执行同一条压缩管线。
        messages[:] = COMPACTOR.prepare(messages, active_request)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=available_tools,
                max_tokens=128000,
            )
            reactive_retries = 0
        except Exception as error:
            # 字符数只是 token 的估算；API 拒绝后进行一次补救压缩并重试。
            if (
                COMPACTOR.is_context_length_error(error)
                and reactive_retries < MAX_REACTIVE_RETRIES
            ):
                messages[:] = COMPACTOR.reactive_compact(
                    messages,
                    active_request,
                )
                reactive_retries += 1
                continue
            raise
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        tool_calls = message.tool_calls or []
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": str(force)})
                continue
            if extract_memories(messages, client, model):
                consolidate_memories(client, model)
            return

        results = []
        used_todo = False
        compact_requested = False
        for tool in tool_calls:
            if tool.function.name == "compact":
                # 先完成同一响应里的所有工具，再执行模型主动压缩。
                compact_requested = True
                results.append({
                    "role": "tool",
                    "content": "Compaction will run after this tool batch completes.",
                    "tool_call_id": tool.id,
                })
                continue

            if tool.function.name == "todo_write":
                used_todo = True
            args = json.loads(tool.function.arguments)
            logger.info("Mew start run tool called : {} ".format(tool.function.name))
            logger.info("Mew start run tool args : {} ".format(args))
            blocked = trigger_hooks("PreToolUse", tool.function.name, args)
            if blocked:
                results.append({
                    "role": "tool",
                    "content": str(blocked),
                    "tool_call_id": tool.id
                })
                continue
            handler = handlers.get(tool.function.name)
            output = handler(**args) if handler else f"Unknown: {tool.function.name}"

            trigger_hooks("PostToolUse", tool.function.name, args, output)
            output = str(output)
            logger.info("Mew start run tool output : {} ".format(output[:200]))
            results.append({
                "role": "tool",
                "content": output,
                "tool_call_id": tool.id
            })
        # 先把每个工具结果都追加，保证 tool_calls 批次完整闭合。
        messages.extend(results)
        if compact_requested:
            messages[:] = COMPACTOR.compact_history(
                messages,
                active_request,
                label="Manual compact",
            )
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0
