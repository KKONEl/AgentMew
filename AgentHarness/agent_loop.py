import json
import logging

from AgentHarness.configs.config import model, api_key, base_url
from openai import OpenAI

from AgentHarness.hooks import trigger_hooks
from AgentHarness.tools import TOOLS, TOOL_HANDLERS

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)
logger = logging.getLogger(__name__)


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
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
        for tool in tool_calls:
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
            handler = TOOL_HANDLERS.get(tool.function.name)
            output = handler(**args) if handler else f"Unknown: {tool.function.name}"

            trigger_hooks("PostToolUse", tool.function.name, args, output)
            logger.info("Mew start run tool output : {} ".format(output[:200]))
            results.append({
                "role": "tool",
                "content": output,
                "tool_call_id": tool.id
            })
        messages.extend(results)
