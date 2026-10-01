import logging
import subprocess
from pathlib import Path

from AgentHarness.configs.config import todo_len
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
                    "command": {"type": "string"}
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

TOOLS = [*BASE_TOOLS, TODO_TOOL, *TASK_TOOLS]

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, errors="replace",
                           timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
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



BASE_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "write_file": run_write,
    "edit_file": run_edit, "glob": run_glob,
}
TOOL_HANDLERS = {**BASE_HANDLERS,
                 "todo_write": run_todo_write,
                 "create_task": run_create_task,
                 "update_task": run_update_task,
                 "list_tasks": run_list_tasks,
                 "get_task": run_get_task,
                 "claim_task": run_claim_task,
                 "complete_task": run_complete_task, }
