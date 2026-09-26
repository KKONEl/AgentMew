import os

WORKDIR = os.getcwd()
HOOKS = {
    "PreToolUse": [],
    "PostToolUse": [],
    "UserPromptSubmit": [],
    "Stop": [],
}


def register_hook(event: str, callback) -> None:
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None


from AgentHarness.permission import check_permission


def log_hook(tool_name: str, args: dict):
    print(f"[HOOK] 准备调用：{tool_name}({args})")
    return None


def permission_hook(tool_name: str, args: dict):
    allowed = check_permission(tool_name, args)

    if not allowed:
        return "Permission denied"

    return None


def large_output_hook(tool_name: str, args: dict, output):
    """PostToolUse: warn on large output."""
    if len(str(output)) > 100000:
        print(f"[HOOK] Large output from {tool_name}: {len(str(output))} chars")
    return None


# UserPromptSubmit hook: log user input before it reaches the LLM
def context_inject_hook(query: str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None


# Stop hook: print summary when loop is about to exit
def summary_hook(messages: list):
    tool_count = sum(
        1 for message in messages
        if message.get("role") == "tool"
    )
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None
