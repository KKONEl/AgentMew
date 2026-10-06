import json
import logging
import os

from openai import OpenAI

from AgentHarness.background_manager import BACKGROUND
from AgentHarness.compaction import Compactor
from AgentHarness.configs.config import (
    MAX_REACTIVE_RETRIES,
    api_key,
    base_url,
    model,
)
from AgentHarness.cron_scheduler import consume_cron_queue, restore_cron_jobs, acknowledge_cron_jobs
from AgentHarness.hooks import trigger_hooks
from AgentHarness.memory import consolidate_memories, extract_memories
from AgentHarness.mcp_runtime import assemble_tool_pool
from AgentHarness.goal_runtime import GOAL
from AgentHarness.subagent import TASK_TOOL, run_subagent
from AgentHarness.team_runtime import TEAM, TEAM_HANDLERS, TEAM_TOOLS
from AgentHarness.tools import TOOLS, TOOL_HANDLERS
from AgentHarness.workflow_runtime import WORKFLOW_TOOL, run_workflow

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

PARENT_TOOLS = [*TOOLS, TASK_TOOL, COMPACT_TOOL, *TEAM_TOOLS, WORKFLOW_TOOL]

PARENT_HANDLERS = {
    **TOOL_HANDLERS,
    "task": run_subagent,
    **TEAM_HANDLERS,
    "Workflow": run_workflow,
}


def inject_background_results(messages: list) -> int:
    """Add completed background work as standalone user notifications."""
    completed = BACKGROUND.collect()
    for task in completed:
        messages.append({
            "role": "user",
            "content": (
                "<task_notification>\n"
                f"  <task_id>{task['id']}</task_id>\n"
                f"  <status>{task['status']}</status>\n"
                f"  <command>{task['command']}</command>\n"
                f"  <exit_code>{task['exit_code']}</exit_code>\n"
                f"  <summary>{task['result'][:500]}</summary>\n"
                "</task_notification>"
            ),
        })
    return len(completed)


def inject_team_events(messages: list) -> int:
    events = TEAM.consume_lead_events()
    if events:
        messages.append({"role": "user", "content": "[Team events]\n" +
                         "\n".join(json.dumps(event, ensure_ascii=False) for event in events)})
    return len(events)


def agent_loop(
        messages: list,
        available_tools: list = PARENT_TOOLS,
        handlers: dict = PARENT_HANDLERS,
        active_request: str | None = None,
):
    fired = consume_cron_queue()
    scheduled_messages = []
    for job in fired:
        scheduled_message = {
            "role": "user",
            "content": f"[Scheduled] {job.prompt}",
        }
        messages.append(scheduled_message)
        scheduled_messages.append(scheduled_message)
    waiting_for_ack = list(fired)
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
    total_rounds = 0
    max_turns = int(os.getenv("MAX_TURNS", "30"))
    while True:
        if total_rounds >= max_turns:
            logger.warning("Agent turn limit reached; goal remains active if set")
            return
        # The original tool call is already closed; completed work is a new event.
        inject_background_results(messages)
        inject_team_events(messages)
        # 每次请求都先执行同一条压缩管线。
        messages[:] = COMPACTOR.prepare(messages, active_request)
        try:
            current_tools, current_handlers = assemble_tool_pool(available_tools, handlers)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=current_tools,
                max_tokens=128000,
            )
            total_rounds += 1
            reactive_retries = 0
        except Exception as error:
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

            if waiting_for_ack:
                messages[:] = [
                    message
                    for message in messages
                    if not any(message is scheduled for scheduled in scheduled_messages)
                ]
                restore_cron_jobs(waiting_for_ack)
                waiting_for_ack.clear()
            raise
        message = response.choices[0].message
        if waiting_for_ack:
            try:
                acknowledge_cron_jobs(waiting_for_ack)
            except Exception as error:
                logger.error("Cron acknowledgement failed: %s", error)
            finally:
                waiting_for_ack.clear()
        messages.append(message.model_dump(exclude_none=True))

        tool_calls = message.tool_calls or []
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": str(force)})
                continue
            action, reason = GOAL.after_turn(messages, background_pending=BACKGROUND.has_running())
            if action == "block":
                messages.append({"role": "user", "content":
                                 f"[Goal not yet met] {reason}. Continue working and verify the result."})
                continue
            if action in {"defer", "limit", "error", "impossible"}:
                logger.info("Goal stopped or deferred: %s: %s", action, reason)
                return
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
            try:
                args = json.loads(tool.function.arguments)
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be an object")
            except (json.JSONDecodeError, ValueError) as error:
                results.append({"role": "tool", "content": f"Error: {error}",
                                "tool_call_id": tool.id})
                continue
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
            handler = current_handlers.get(tool.function.name)
            try:
                output = handler(**args) if handler else f"Unknown: {tool.function.name}"
            except Exception as error:
                output = f"Error: {type(error).__name__}: {error}"

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
