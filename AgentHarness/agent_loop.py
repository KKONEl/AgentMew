import json
import logging

from AgentHarness.configs.config import model, api_key, base_url
from openai import OpenAI

from AgentHarness.hooks import trigger_hooks
from AgentHarness.tools import TOOLS, TOOL_HANDLERS
from AgentHarness.subagent import TASK_TOOL, run_subagent

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)
logger = logging.getLogger(__name__)

PARENT_TOOLS = [*TOOLS, TASK_TOOL]

PARENT_HANDLERS = {
    **TOOL_HANDLERS,
    "task": run_subagent,
}

def agent_loop(
    messages: list,
    available_tools: list = PARENT_TOOLS,
    handlers: dict = PARENT_HANDLERS,
):
    rounds_since_todo = 0
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=available_tools,
            max_tokens=8000
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        tool_calls = message.tool_calls or []
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": str(force)})
                continue
            return

        results = []
        used_todo = False
        for tool in tool_calls:
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
            logger.info("Mew start run tool output : {} ".format(output[:200]))
            results.append({
                "role": "tool",
                "content": output,
                "tool_call_id": tool.id
            })
        messages.extend(results)
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0
