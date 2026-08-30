import json
from pathlib import Path

from AgentHarness.Fence import DENY_LIST, contains_destructive_command
from AgentHarness.Tools import approve_path_once

WORKDIR = Path.cwd()
HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
}


def register_hook(event: str, callback):
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    for hook in HOOKS[event]:
        result = hook(*args)
        if result is not None:
            return result
    return None


def context_inject_hook(query: str) -> str | None:
    print(f"[HOOK] UserPromptSubmit: working in {WORKDIR}")
    return None

register_hook("UserPromptSubmit", context_inject_hook)

def permission_hook(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    if name == "bash":
        command = args.get("command", "")
        for pattern in DENY_LIST:
            if pattern in command:
                print(f"\n\033[31m[blocked] '{pattern}'\033[0m")
                return "Permission denied by deny list"

        if contains_destructive_command(command) or any(
            keyword in command for keyword in ["rm ", "> /etc/", "chmod 777"]
        ):
            print("\n\033[33m[permission] Potentially destructive command\033[0m")
            print(f"   Tool: {name}({args})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"

    if name in ("read_file", "write_file", "edit_file"):
        if not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR):
            print("\n\033[33m[permission] Access outside workspace\033[0m")
            print(f"   Tool: {name}({args})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
            approve_path_once(args.get("path", ""))
    return None


def log_hook(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    args_preview = str(list(args.values())[:2])[:60]
    print(f"[HOOK] {name}({args_preview})")
    return None


def large_output_hook(tool_call, output):
    name = tool_call.function.name
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] Large output from {name}: {len(str(output))} chars\033[0m")
    return None


register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)


def summary_hook(messages: list) -> str | None:
    """Print a summary when the loop is about to stop."""
    tool_count = sum(
        1
        for message in messages
        if isinstance(message, dict) and message.get("role") == "tool"
    )
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

register_hook("Stop", summary_hook)
