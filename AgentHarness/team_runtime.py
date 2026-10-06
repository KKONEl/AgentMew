"""Persistent teammate coordination on top of the shared task graph (s13)."""

import json
import re
import subprocess
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from AgentHarness.configs.config import model
from AgentHarness.task_manager import (
    TASKS, WORKDIR, can_start, claim_task, complete_task, list_tasks,
    load_task, task_store_lock,
)
from AgentHarness.permission import check_deny_list, contains_destructive_command

TEAM_DIR = WORKDIR / ".team"
MAILBOX_DIR = TEAM_DIR / "mailboxes"
WORKTREE_DIR = WORKDIR / ".worktrees"
_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class MessageBus:
    def __init__(self, directory: Path = MAILBOX_DIR):
        self.directory = directory
        self.changed = threading.Condition(threading.RLock())

    def _path(self, agent: str) -> Path:
        if not _NAME.fullmatch(agent):
            raise ValueError("Invalid agent name")
        return self.directory / f"{agent}.jsonl"

    def send(self, sender: str, recipient: str, content: str,
             kind: str = "message", metadata: dict | None = None) -> dict:
        item = {"id": uuid.uuid4().hex, "from": sender, "to": recipient,
                "type": kind, "content": content, "metadata": metadata or {}}
        with self.changed:
            path = self._path(recipient)
            self.directory.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            self.changed.notify_all()
        return item

    def drain(self, agent: str) -> list[dict]:
        with self.changed:
            path = self._path(agent)
            if not path.exists():
                return []
            data = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            path.unlink()
            return data

    def wait(self, agent: str, timeout: float = 1.0) -> list[dict]:
        with self.changed:
            if not self._path(agent).exists():
                self.changed.wait(timeout)
            return self.drain(agent)


class TeamRuntime:
    def __init__(self, bus: MessageBus | None = None, client=None):
        self.bus = bus or MessageBus()
        self.client = client
        self.lock = threading.RLock()
        self.threads: dict[str, threading.Thread] = {}
        self.states: dict[str, dict] = {}
        self.requests: dict[str, dict] = {}

    def _client(self):
        if self.client is None:
            from AgentHarness.agent_loop import client
            self.client = client
        return self.client

    def _assigned_task(self, name: str):
        return next((t for t in list_tasks()
                     if t.owner == name and t.status == "in_progress"), None)

    def _cwd(self, name: str) -> Path:
        task = self._assigned_task(name)
        if task is None:
            raise ValueError("Claim a task before using workspace tools")
        if task.worktree:
            path = (WORKTREE_DIR / task.worktree).resolve()
            if not path.is_relative_to(WORKTREE_DIR.resolve()) or not path.is_dir():
                raise ValueError("Assigned worktree is unavailable")
            return path
        return WORKDIR

    def _path(self, name: str, relative: str) -> Path:
        cwd = self._cwd(name).resolve()
        path = (cwd / relative).resolve()
        if not path.is_relative_to(cwd):
            raise ValueError("Path escapes assigned workspace")
        return path

    def _workspace_tool(self, name: str, tool: str, args: dict) -> str:
        if tool == "bash":
            command = args["command"]
            if check_deny_list(command) or contains_destructive_command(command):
                return "Error: command requires lead and user approval"
            result = subprocess.run(command, shell=True, cwd=self._cwd(name),
                                    capture_output=True, text=True, timeout=120)
            return f"exit_code={result.returncode}\n{(result.stdout + result.stderr)[:50000]}"
        if tool == "glob":
            cwd = self._cwd(name)
            return "\n".join(str(p.relative_to(cwd)) for p in cwd.glob(args["pattern"])
                             if p.resolve().is_relative_to(cwd.resolve()))[:50000]
        path = self._path(name, args["path"])
        if tool == "read_file":
            return "\n".join(path.read_text(encoding="utf-8").splitlines()[:args.get("limit", 10000)])
        if tool == "write_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"], encoding="utf-8")
            return f"Wrote {path}"
        if tool == "edit_file":
            old = path.read_text(encoding="utf-8")
            if args["old_text"] not in old:
                return "Error: old_text not found"
            path.write_text(old.replace(args["old_text"], args["new_text"], 1), encoding="utf-8")
            return f"Edited {path}"
        return f"Unknown tool: {tool}"

    def _team_tool(self, name: str, tool: str, args: dict) -> str:
        if tool == "claim_task":
            return claim_task(args["task_id"], name)
        if tool == "complete_task":
            return complete_task(args["task_id"], name)
        if tool == "list_tasks":
            return json.dumps([asdict(t) for t in list_tasks()])
        if tool == "send_message":
            self.bus.send(name, args["to"], args["content"])
            return "Message sent"
        if tool == "submit_plan":
            request_id = uuid.uuid4().hex
            with self.lock:
                state = self.states[name]
                state["gate"] = "pending"
                self.requests[request_id] = {"type": "plan", "name": name,
                                             "task_id": state.get("task_id"),
                                             "status": "pending"}
            self.bus.send(name, "lead", args["plan"], "plan_approval_request",
                          {"request_id": request_id, "task_id": state.get("task_id")})
            return f"Plan submitted: {request_id}"
        return self._workspace_tool(name, tool, args)

    def _tool_pool(self):
        from AgentHarness.tools import BASE_TOOLS, TASK_TOOLS
        wanted = {"bash", "read_file", "write_file", "edit_file", "glob",
                  "claim_task", "complete_task", "list_tasks"}
        tools = [t for t in [*BASE_TOOLS, *TASK_TOOLS] if t["function"]["name"] in wanted]
        tools.extend([
            _tool("send_message", "Send a message to lead or a teammate.",
                  {"to": {"type": "string"}, "content": {"type": "string"}}, ["to", "content"]),
            _tool("submit_plan", "Submit a plan to lead for approval.",
                  {"plan": {"type": "string"}}, ["plan"]),
        ])
        return tools

    def _claim_next(self, name: str):
        for task in list_tasks():
            if task.status == "pending" and task.owner is None and can_start(task.id):
                result = claim_task(task.id, name)
                if result.startswith("Claimed "):
                    return load_task(task.id)
        return None

    def _handle_control(self, name: str, message: dict) -> bool:
        kind = message["type"]
        request_id = message.get("metadata", {}).get("request_id")
        with self.lock:
            if kind == "plan_request":
                self.states[name]["gate"] = "required"
                return False
            if kind == "plan_approval_response":
                request = self.requests.get(request_id)
                if (request and request["type"] == "plan" and request["name"] == name
                        and request["status"] == "pending"
                        and request["task_id"] == self.states[name].get("task_id")):
                    approved = bool(message.get("metadata", {}).get("approve"))
                    request["status"] = "approved" if approved else "rejected"
                    self.states[name]["gate"] = request["status"]
                return False
            if kind == "shutdown_request":
                self.bus.send(name, "lead", "Shutdown accepted", "shutdown_response",
                              {"request_id": request_id, "approve": True})
                self.states[name]["status"] = "stopped"
                return True
        return False

    def _worker(self, name: str, role: str, prompt: str):
        messages = [{"role": "system", "content":
                     f"You are teammate {name}, role {role}. Work only on claimed tasks. "
                     "Use complete_task when finished. Send concise results to lead. "
                     "When a plan is required, submit it and wait for approval before mutations."},
                    {"role": "user", "content": prompt}]
        while True:
            with self.lock:
                if self.states[name]["status"] == "stopped":
                    return
                self.states[name]["status"] = "working"
                task = self._assigned_task(name)
                self.states[name]["task_id"] = task.id if task else None
            try:
                for _ in range(30):
                    response = self._client().chat.completions.create(
                        model=model, messages=messages, tools=self._tool_pool())
                    message = response.choices[0].message
                    messages.append(message.model_dump(exclude_none=True))
                    calls = message.tool_calls or []
                    if not calls:
                        content = message.content or ""
                        self.bus.send(name, "lead", content, "result",
                                      {"task_id": self.states[name].get("task_id")})
                        break
                    for call in calls:
                        try:
                            args = json.loads(call.function.arguments)
                            tool = call.function.name
                            gate = self.states[name]["gate"]
                            if gate not in {"not_required", "approved"} and tool in {
                                "bash", "write_file", "edit_file"}:
                                output = f"Blocked: plan status is {gate}"
                            else:
                                output = self._team_tool(name, tool, args)
                        except Exception as error:
                            output = f"Error: {type(error).__name__}: {error}"
                        messages.append({"role": "tool", "tool_call_id": call.id,
                                         "content": str(output)})
                else:
                    self.bus.send(name, "lead", "Teammate turn limit reached", "result")
            except Exception as error:
                self.bus.send(name, "lead", f"Teammate error: {error}", "result")
            with self.lock:
                self.states[name]["status"] = "idle"
                self.states[name]["task_id"] = None
            self.bus.send(name, "lead", "Waiting for work", "idle_notification")
            while True:
                incoming = self.bus.wait(name, 1.0)
                if any(self._handle_control(name, item) for item in incoming):
                    return
                if any(item["type"] in {"plan_request", "plan_approval_response"}
                       for item in incoming):
                    messages.append({"role": "user", "content": "\n".join(
                        f"[{item['type']}] {item['content']}" for item in incoming)})
                    break
                ordinary = [item for item in incoming if item["type"] == "message"]
                if ordinary:
                    messages.append({"role": "user", "content": "\n".join(
                        item["content"] for item in ordinary)})
                    break
                task = self._claim_next(name)
                if task:
                    with self.lock:
                        self.states[name]["gate"] = "not_required"
                    messages.append({"role": "user", "content":
                                     f"[Auto-claimed {task.id}] {task.subject}\n{task.description}"})
                    break

    def spawn(self, name: str, role: str, prompt: str,
              task_id: str | None = None, require_plan: bool = False) -> str:
        if not _NAME.fullmatch(name) or name in {"lead", "agent"}:
            return "Error: invalid teammate name"
        with self.lock:
            if name in self.threads:
                return "Error: teammate already exists"
            if task_id:
                result = claim_task(task_id, name)
                if not result.startswith("Claimed "):
                    return f"Error: {result}"
            self.states[name] = {"status": "starting", "gate": "required" if require_plan
                                 else "not_required", "task_id": task_id}
            thread = threading.Thread(target=self._worker, args=(name, role, prompt),
                                      name=f"teammate-{name}", daemon=True)
            self.threads[name] = thread
            thread.start()
        return f"Spawned {name}" + (f" for {task_id}" if task_id else "")

    def list_teammates(self) -> str:
        with self.lock:
            return json.dumps(self.states, ensure_ascii=False)

    def send(self, to: str, content: str) -> str:
        if to not in self.threads:
            return "Error: unknown teammate"
        self.bus.send("lead", to, content)
        return "Message sent"

    def request_shutdown(self, teammate: str) -> str:
        if teammate not in self.threads:
            return "Error: unknown teammate"
        request_id = uuid.uuid4().hex
        with self.lock:
            self.requests[request_id] = {"type": "shutdown", "name": teammate,
                                         "status": "pending"}
        self.bus.send("lead", teammate, "Please shut down", "shutdown_request",
                      {"request_id": request_id})
        return f"Shutdown requested: {request_id}"

    def request_plan(self, teammate: str, task: str) -> str:
        if teammate not in self.threads:
            return "Error: unknown teammate"
        with self.lock:
            self.states[teammate]["gate"] = "required"
        self.bus.send("lead", teammate, task, "plan_request")
        return "Plan requested"

    def review_plan(self, request_id: str, approve: bool, feedback: str = "") -> str:
        with self.lock:
            request = self.requests.get(request_id)
            if not request or request["type"] != "plan" or request["status"] != "pending":
                return "Error: stale or unknown plan request"
            name = request["name"]
        self.bus.send("lead", name, feedback, "plan_approval_response",
                      {"request_id": request_id, "approve": approve})
        return "Plan response sent"

    def consume_lead_events(self) -> list[dict]:
        events = self.bus.drain("lead")
        with self.lock:
            for event in events:
                if event["type"] == "shutdown_response":
                    request = self.requests.get(event["metadata"].get("request_id"))
                    if request and request["type"] == "shutdown" and request["status"] == "pending":
                        request["status"] = "approved" if event["metadata"].get("approve") else "rejected"
        return events

    def has_lead_events(self) -> bool:
        with self.bus.changed:
            return self.bus._path("lead").exists()

    def create_worktree(self, name: str, task_id: str) -> str:
        if not _NAME.fullmatch(name):
            return "Error: invalid worktree name"
        path = WORKTREE_DIR / name
        with task_store_lock():
            task = load_task(task_id)
            if task.status != "pending" or task.owner or task.worktree:
                return "Error: task must be pending, unclaimed, and unbound"
            if path.exists():
                return "Error: worktree path already exists"
            WORKTREE_DIR.mkdir(exist_ok=True)
            result = subprocess.run(["git", "worktree", "add", "-b", f"wt/{name}",
                                     str(path)], cwd=WORKDIR, capture_output=True, text=True)
            if result.returncode:
                return f"Error: git worktree failed; check partial operation: {result.stderr.strip()}"
            task.worktree = name
            TASKS.save(task)
        return f"Created worktree {name} for {task_id}"

    def remove_worktree(self, name: str, discard_changes: bool = False) -> str:
        """Host-only cleanup. Never exposed as a model tool; wt/<name> branch remains."""
        if not _NAME.fullmatch(name):
            return "Error: invalid worktree name"
        path = WORKTREE_DIR / name
        with task_store_lock():
            bound = [task for task in list_tasks() if task.worktree == name]
            if not bound or any(task.status != "completed" for task in bound):
                return "Error: bound tasks must be completed before removal"
            if any(self._assigned_task(agent) and self._assigned_task(agent).worktree == name
                   for agent in self.states):
                return "Error: worktree is still assigned"
            if not path.is_dir():
                return "Error: worktree directory is missing"
            status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all",
                                     "--ignored"], cwd=path, capture_output=True, text=True)
            if status.returncode:
                return f"Error: cannot inspect worktree: {status.stderr.strip()}"
            if status.stdout.strip() and not discard_changes:
                return "Error: worktree has changes; host must explicitly choose discard_changes"
            command = ["git", "worktree", "remove"]
            if discard_changes:
                command.append("--force")
            command.append(str(path))
            result = subprocess.run(command, cwd=WORKDIR, capture_output=True, text=True)
            if result.returncode:
                return f"Error: {result.stderr.strip()}"
            for task in bound:
                task.worktree = None
                TASKS.save(task)
        return f"Removed worktree {name}; branch wt/{name} retained"


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": required, "additionalProperties": False}}}


TEAM_TOOLS = [
    _tool("spawn_teammate", "Start a persistent teammate after user confirms the team plan.",
          {"name": {"type": "string"}, "role": {"type": "string"},
           "prompt": {"type": "string"}, "task_id": {"type": "string"},
           "require_plan": {"type": "boolean"}}, ["name", "role", "prompt"]),
    _tool("list_teammates", "List teammate states.", {}, []),
    _tool("send_message", "Message a teammate.",
          {"to": {"type": "string"}, "content": {"type": "string"}}, ["to", "content"]),
    _tool("request_shutdown", "Ask a teammate to shut down.",
          {"teammate": {"type": "string"}}, ["teammate"]),
    _tool("request_plan", "Require a teammate plan before mutations.",
          {"teammate": {"type": "string"}, "task": {"type": "string"}}, ["teammate", "task"]),
    _tool("review_plan", "Approve or reject a submitted teammate plan.",
          {"request_id": {"type": "string"}, "approve": {"type": "boolean"},
           "feedback": {"type": "string"}}, ["request_id", "approve"]),
    _tool("create_worktree", "Bind a pending task to a separate Git worktree.",
          {"name": {"type": "string"}, "task_id": {"type": "string"}}, ["name", "task_id"]),
]

TEAM = TeamRuntime()
TEAM_HANDLERS = {
    "spawn_teammate": TEAM.spawn, "list_teammates": TEAM.list_teammates,
    "send_message": TEAM.send, "request_shutdown": TEAM.request_shutdown,
    "request_plan": TEAM.request_plan, "review_plan": TEAM.review_plan,
    "create_worktree": TEAM.create_worktree,
}
