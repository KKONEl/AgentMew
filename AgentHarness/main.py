import logging
import threading
from datetime import datetime

from AgentHarness.agent_loop import (
    PARENT_HANDLERS,
    PARENT_TOOLS,
    agent_loop,
    client,
)
from AgentHarness.background_manager import BACKGROUND
from AgentHarness.goal_runtime import GOAL
from AgentHarness.team_runtime import TEAM
from AgentHarness.configs.config import SKILLS_DIR, model
from AgentHarness.configs.logging_config import setup_logging
from AgentHarness.cron_scheduler import (
    has_cron_queue,
    load_durable_jobs,
    poll_due_jobs,
)
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
from AgentHarness.mcp_runtime import approve_mcp_tool

setup_logging()
logger = logging.getLogger(__name__)
SKILL_LOADER = SkillLoader(SKILLS_DIR)
SKILL_LOADER.scan()
agent_lock = threading.Lock()


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


def print_latest_assistant_text(session_history):
    for message in session_history:
        if message["role"] != "assistant":
            continue
        response_content = message["content"]
        if isinstance(response_content, str) and response_content:
            print("=^..^=:  " + response_content)
        print()


def run_agent_turn_locked(user_query: str | None = None):
    turn_start = len(history)
    if user_query is not None:
        trigger_hooks("UserPromptSubmit", user_query)
        history.append({"role": "user", "content": user_query})
        recalled = load_memories(history, client, model)
        history[0]["content"] = build_system_prompt(
            SYSTEM, SKILL_LOADER.catalog(), recalled
        )
        logger.info("into agent loop")
    agent_loop(
        history,
        available_tools=MAIN_TOOLS,
        handlers=MAIN_HANDLERS,
        active_request=user_query,
    )
    print_latest_assistant_text(history[turn_start:])
    print()

def cron_scheduler_loop(stop_event: threading.Event) -> None:
    """Poll local time and enqueue due cron jobs without touching history."""
    while not stop_event.wait(1.0):
        poll_due_jobs(datetime.now())


def queue_processor_loop(stop_event: threading.Event) -> None:
    """Deliver due jobs only when no user Agent turn owns the session lock."""
    while not stop_event.wait(0.2):
        if not (has_cron_queue() or TEAM.has_lead_events() or BACKGROUND.has_ready()) \
                or not agent_lock.acquire(blocking=False):
            continue
        try:
            if has_cron_queue() or TEAM.has_lead_events() or BACKGROUND.has_ready():
                run_agent_turn_locked()
        finally:
            agent_lock.release()

if __name__ == '__main__':
    logger.info('CodeMew Start')
    history = [{"role": "system", "content": build_system_prompt(SYSTEM, SKILL_LOADER.catalog())}]
    runtime_stop = threading.Event()
    load_durable_jobs()
    runtime_threads = [
        threading.Thread(
            target=cron_scheduler_loop,
            args=(runtime_stop,),
            name="cron-scheduler",
            daemon=True,
        ),
        threading.Thread(
            target=queue_processor_loop,
            args=(runtime_stop,),
            name="cron-queue-processor",
            daemon=True,
        ),
    ]
    for thread in runtime_threads:
        thread.start()
    try:
        while True:
            try:
                query = input("You Say :")
            except (EOFError, KeyboardInterrupt):
                break
            if query.strip().lower() == '':
                continue
            if query.strip().lower() in ("q", "exit"):
                break
            if query.strip().startswith("/mcp approve "):
                parts = query.strip().split()
                if len(parts) != 4:
                    print("Usage: /mcp approve SERVER TOOL")
                else:
                    approve_mcp_tool(parts[2], parts[3])
                    print(f"Approved MCP tool {parts[2]}/{parts[3]} for this session")
                continue
            if query.strip().startswith("/goal"):
                criterion = query.strip()[5:].strip()
                if not criterion:
                    print(GOAL.status())
                    continue
                if criterion.lower() in {"clear", "stop", "off", "reset", "none", "cancel"}:
                    print(GOAL.clear())
                    continue
                print(GOAL.set(criterion))
                query = criterion
            with agent_lock:
                run_agent_turn_locked(query)
    finally:
        runtime_stop.set()
        for thread in runtime_threads:
            thread.join(timeout=1)
