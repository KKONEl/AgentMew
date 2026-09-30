import logging

from AgentHarness.agent_loop import (
    PARENT_HANDLERS,
    PARENT_TOOLS,
    agent_loop,
    client,
)
from AgentHarness.configs.config import SKILLS_DIR, model
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
from AgentHarness.prompts import SYSTEM, build_system_prompt
from AgentHarness.skill_loader import SkillLoader
from AgentHarness.tools import LOAD_SKILL_TOOL
from AgentHarness.memory import load_memories

setup_logging()
logger = logging.getLogger(__name__)
SKILL_LOADER = SkillLoader(SKILLS_DIR)
SKILL_LOADER.scan()


def run_load_skill(name: str) -> str:
    return SKILL_LOADER.load(name)


MAIN_TOOLS = [*PARENT_TOOLS, LOAD_SKILL_TOOL]

MAIN_HANDLERS = {
    **PARENT_HANDLERS,
    "load_skill": run_load_skill,
}

register_hook("PreToolUse", log_hook)
register_hook("PreToolUse", permission_hook)
register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)

if __name__ == '__main__':
    logger.info('CodeMew Start')
    history = [{"role": "system", "content": build_system_prompt(SYSTEM, SKILL_LOADER.catalog())}]
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
        recalled = load_memories(history, client, model)
        history[0]["content"] = build_system_prompt(
            SYSTEM, SKILL_LOADER.catalog(), recalled
        )
        logger.info("into agent loop")
        agent_loop(
            history,
            available_tools=MAIN_TOOLS,
            handlers=MAIN_HANDLERS,
            active_request=query,
        )
        response_content = history[-1]["content"]
        print("=^..^=:  " + response_content)
        print()
