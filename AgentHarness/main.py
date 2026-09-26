import logging

from AgentHarness.agent_loop import agent_loop
from AgentHarness.configs.logging_config import setup_logging
from AgentHarness.hooks import (
    register_hook,
    trigger_hooks,
    log_hook,
    permission_hook,
    context_inject_hook,
    large_output_hook,
    summary_hook,
)
from AgentHarness.prompts import SYSTEM

setup_logging()
logger = logging.getLogger(__name__)

register_hook("PreToolUse", log_hook)
register_hook("PreToolUse", permission_hook)
register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)


if __name__ == '__main__':
    logger.info('CodeMew Start')

    history = [{"role":"system","content":SYSTEM}]
    while True:
        try:
            query = input("You Say :")

        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() == '':
            continue
        if query.strip().lower() in ("q", "exit"):
            break

        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        logger.info("into agent loop")
        agent_loop(history)
        response_content = history[-1]["content"]
        print("=^..^=:  " +  response_content)
        print()

