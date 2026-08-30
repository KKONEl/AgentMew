import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from AgentHarness.ToolHandler import TOOL_HANDLERS
from AgentHarness.Tools import TOOLS
from AgentHarness.hooks import trigger_hooks

load_dotenv(override=True)

MODEL_KEY = os.getenv("api_key")
BASE_URL = os.getenv("base_url")
MODEL = os.getenv("model")
WORKDIR = Path.cwd()
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go."
)
client = OpenAI(
    api_key=MODEL_KEY,
    base_url=BASE_URL
)

def agent_loop(messages: list):
    rounds_since_todo = 0
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM}, *messages],
            tools=TOOLS,
            max_tokens=8000,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        used_todo = False
        for tool_call in message.tool_calls:
            blocked = trigger_hooks("PreToolUse", tool_call)
            if blocked:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(blocked),
                })
                continue
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            handler = TOOL_HANDLERS.get(name)
            try:
                output = handler(**args) if handler else f"Unknown: {name}"
            except Exception as e:
                output = f"Error: {e}"
            trigger_hooks("PostToolUse", tool_call, output)
            if name == "todo_write":
                used_todo = True
            print(str(output)[:200])
            messages.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content":str(output),
            })

        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            messages.append({
                "role": "user",
                "content": "<reminder>Update your todos.</reminder>",
            })
            rounds_since_todo = 0


if __name__ == "__main__":
    print(" > 3 <")
    print("Enter a question, press Enter to send. Type q to quit.\n")
    history = []
    while True:
        try:
            query = input("\033[36m>^._.^<  \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1].content
        print(response_content)
        print()
