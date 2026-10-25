import logging
import subprocess
from pathlib import Path

from AgentHarness.knowledge_tool import KNOWLEDGE_TOOL, search_knowledge
from AgentHarness.background_manager import BACKGROUND
from AgentHarness.configs.config import todo_len
from AgentHarness.cron_scheduler import cancel_job, list_jobs, schedule_job
from AgentHarness.task_manager import (
    claim_task,
    complete_task,
    create_task,
    get_task,
    list_tasks,
    update_task,
)
from AgentHarness.todo_manager import TODO, markers

# -- Tool definition: just bash --
logger = logging.getLogger(__name__)

WORKDIR = Path.cwd()
BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "run_in_background":{"type":"boolean"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in a file once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"}
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files matching a glob pattern; ** matches recursively.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    },
]

TODO_TOOL = {
    "type": "function",
    "function": {
        "name": "todo_write",
        "description": "Create and manage a task list for your current coding session.",
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "maxItems": todo_len,
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "minLength": 1},
                            "status": {
                                "type": "string",
                                "enum": list(markers)}},
                        "required": ["content", "status"]
                    },
                },
            },
            "required": ["todos"]
        },
    }
}

LOAD_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": (
            "Load the full instructions for an available skill by name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
            },
            "required": ["name"],
        },
    },
}

TASK_ID_SCHEMA = {"type": "string", "pattern": "^task_[0-9a-f]{8}$"}

TASK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a persistent task and return its generated ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                },
                "required": ["subject"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Add dependency task IDs to a pending, unclaimed task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": TASK_ID_SCHEMA,
                    "addBlockedBy": {
                        "type": "array",
                        "items": TASK_ID_SCHEMA,
                        "minItems": 1,
                    },
                },
                "required": ["task_id", "addBlockedBy"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List tasks with statuses, owners, and dependencies.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "Get one task's complete persistent record.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": TASK_ID_SCHEMA},
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "claim_task",
            "description": "Claim a pending task after all dependencies are completed.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": TASK_ID_SCHEMA},
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Complete the task currently claimed by this agent.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": TASK_ID_SCHEMA},
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
]

CRON_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "schedule_cron",
            "description": "Schedule a prompt with a five-field cron expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cron": {"type": "string"},
                    "prompt": {"type": "string"},
                    "recurring": {"type": "boolean", "default": True},
                    "durable": {"type": "boolean", "default": True},
                },
                "required": ["cron", "prompt"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_crons",
            "description": "List registered cron jobs and their delivery state.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_cron",
            "description": "Cancel a cron job by its ID.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
                "additionalProperties": False,
            },
        },
    },
]

TOOLS = [*BASE_TOOLS, TODO_TOOL, *TASK_TOOLS, *CRON_TOOLS, KNOWLEDGE_TOOL]

def run_bash(command: str, run_in_background: bool = False) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    if run_in_background is True:
        try:
            task_id = BACKGROUND.start(command)
            return (
                f"[Background task {task_id} started] "
                "The result will be collected on a later turn."
            )
        except ValueError as error:
            return f"Error: {error}"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, errors="replace",
                           timeout=120)
        out = (r.stdout + r.stderr).strip()
        return f"exit_code={r.returncode}\n" + (out[:50000] if out else "(no output)")
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text(encoding="utf-8")
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str) -> str:
    import glob as g
    try:
        matches = sorted({
            match for match in g.glob(
                pattern, root_dir=WORKDIR, recursive=True)
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR)
        })
        shown = matches[:200]
        if len(matches) > 200:
            shown.append("... (more matches omitted; narrow the pattern)")
        return "\n".join(shown) if shown else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


def run_todo_write(todos: list | str) -> str:
    try:
        return TODO.update(todos)
    except ValueError as e:
        return f"Error: {e}"


def run_create_task(subject: str, description: str = "") -> str:
    try:
        task = create_task(subject, description)
        return f"Created {task.id}: {task.subject}"
    except ValueError as error:
        return f"Error: {error}"


def run_update_task(task_id: str, addBlockedBy: list[str]) -> str:
    try:
        task = update_task(task_id, addBlockedBy)
        dependencies = ", ".join(task.blockedBy) or "(none)"
        return f"Updated {task.id} blockedBy: {dependencies}"
    except (FileNotFoundError, ValueError) as error:
        return f"Error: {error}"


def run_list_tasks() -> str:
    tasks = list_tasks()
    if not tasks:
        return "No tasks. Use create_task to add some."
    lines = []
    for task in tasks:
        marker = markers.get(task.status, "[?]")
        owner = f" [{task.owner}]" if task.owner else ""
        dependencies = f" (blockedBy: {', '.join(task.blockedBy)})" if task.blockedBy else ""
        lines.append(f"{marker} {task.id}: {task.subject} [{task.status}]{owner}{dependencies}")
    return "\n".join(lines)


def run_get_task(task_id: str) -> str:
    try:
        return get_task(task_id)
    except (FileNotFoundError, ValueError) as error:
        return f"Error: {error}"


def run_claim_task(task_id: str) -> str:
    try:
        return claim_task(task_id, owner="agent")
    except (FileNotFoundError, ValueError) as error:
        return f"Error: {error}"


def run_complete_task(task_id: str) -> str:
    try:
        return complete_task(task_id, owner="agent")
    except (FileNotFoundError, ValueError) as error:
        return f"Error: {error}"


def run_schedule_cron(
    cron: str,
    prompt: str,
    recurring: bool = True,
    durable: bool = True,
) -> str:
    try:
        result = schedule_job(cron, prompt, recurring, durable)
    except Exception as error:
        return f"Error: {error}"
    if isinstance(result, str):
        return f"Error: {result}"
    return f"Scheduled {result.id}: {result.cron} -> {result.prompt}"


def run_list_crons() -> str:
    jobs = list_jobs()
    if not jobs:
        return "No cron jobs."
    lines = []
    for job in jobs:
        frequency = "recurring" if job.recurring else "one-shot"
        storage = "durable" if job.durable else "session"
        delivery = "pending delivery" if job.pending_delivery else "waiting"
        lines.append(
            f"{job.id}: {job.cron} -> {job.prompt[:60]} "
            f"[{frequency}, {storage}, {delivery}]"
        )
    return "\n".join(lines)


def run_cancel_cron(job_id: str) -> str:
    try:
        return cancel_job(job_id)
    except Exception as error:
        return f"Error: {error}"



BASE_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob,
}
TOOL_HANDLERS = {**BASE_HANDLERS,
                 "search_knowledge": search_knowledge,
                 "todo_write": run_todo_write,
                 "create_task": run_create_task,
                 "update_task": run_update_task,
                 "list_tasks": run_list_tasks,
                 "get_task": run_get_task,
                 "claim_task": run_claim_task,
                 "complete_task": run_complete_task,
                 "schedule_cron": run_schedule_cron,
                 "list_crons": run_list_crons,
                 "cancel_cron": run_cancel_cron, }
