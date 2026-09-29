import json
import logging

from openai import OpenAI

from AgentHarness.configs.config import subagent_loop, model, api_key, base_url
from AgentHarness.hooks import trigger_hooks
from AgentHarness.prompts import SUB_SYSTEM, build_system_prompt
from AgentHarness.tools import BASE_HANDLERS, BASE_TOOLS

logger = logging.getLogger(__name__)
SUB_TOOLS = list(BASE_TOOLS)

SUB_HANDLERS = dict(BASE_HANDLERS)


client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

TASK_TOOL = {
    "type": "function",
    "function": {
        "name": "task",
        "description": "Run a subagent with fresh conversation context and return its final text.",
        "parameters": {
            "type": "object",
            "properties": {"prompt": {"type": "string", "minLength": 1}},
            "required": ["prompt"],
        }
    },
}

def run_subagent(prompt: str) -> str:
    logger.info("Subagent started")
    messages = [{"role": "system", "content": build_system_prompt(SUB_SYSTEM)}, {"role": "user", "content": prompt}]

    for _ in range(subagent_loop):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=SUB_TOOLS,
            max_tokens=128000
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        tool_calls = message.tool_calls or []
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": str(force)})
                continue
            logger.info("Subagent done")
            return message  .content or "(no summary)"

        results = []
        for tool in tool_calls:
            args = json.loads(tool.function.arguments)
            blocked = trigger_hooks("PreToolUse", tool.function.name, args)
            if blocked:
                output = str(blocked)
            else:
                handler = SUB_HANDLERS.get(tool.function.name)
                output = handler(**args) if handler else (
                    f"Unknown: {tool.function.name}"
                )
                trigger_hooks("PostToolUse", tool.function.name, args, output)

            results.append({
                "role": "tool",
                "content": str(output),
                "tool_call_id": tool.id,
            })
        messages.extend(results)
    logger.info("Subagent stopped")
    return f"Subagent stopped after {subagent_loop} turns without a final answer."

