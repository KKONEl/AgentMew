import json
import secrets
import os
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, asdict

from AgentHarness.todo_manager import markers


@dataclass
class Task:
    id: str
    # 标题
    subject: str
    description: str
    status: str
    owner: str | None
    blockedBy: list[str]
    worktree: str | None = None


import re
import fcntl
from pathlib import Path

WORKDIR = Path.cwd()
TASKS_DIR = WORKDIR / ".tasks"
TASK_ID_PATTERN = re.compile(r"^task_[0-9a-f]{8}$")
_TASK_LOCK = threading.RLock()


@contextmanager
def task_store_lock():
    """Serialize task transitions across threads and local processes."""
    with _TASK_LOCK:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        with (TASKS_DIR / ".lock").open("a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


class TaskStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def _root(self, create: bool = False) -> Path:
        if create:
            self.directory.mkdir(parents=True, exist_ok=True)
        root = self.directory.resolve()
        if not root.is_relative_to(WORKDIR.resolve()):
            raise ValueError(f"Task store escapes the workspace")
        return root

    def _path(self, task_id: str, create_root: bool = False) -> Path:
        if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
            raise ValueError(f"Invalid task ID: {task_id!r}")
        root = self._root(create_root)
        path = (root / f"{task_id}.json").resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Invalid taskId:  {task_id}")
        return path

    def exists(self, task_id: str) -> bool:
        return self._path(task_id).is_file()

    def create(self, subject: str, description: str = "") -> Task:
        subject = subject.strip()
        if not subject:
            raise ValueError("Task subject cannot be empty")
        self._root(create=True)
        for _ in range(100):
            task = Task(
                id=f"task_{secrets.token_hex(4)}",
                subject=subject,
                description=description,
                status="pending",
                owner=None,
                blockedBy=[],
            )
            try:
                with self._path(task.id, create_root=True).open("x", encoding="utf-8") as handle:
                    json.dump(asdict(task), handle, indent=2)
                    return task
            except FileExistsError:
                continue
        raise RuntimeError(f"Could not allocate a unique task ID")

    def save(self, task: Task) -> None:
        path = self._path(task.id, create_root=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{task.id}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(asdict(task), handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load(self, task_id: str) -> Task:
        data = json.loads(self._path(task_id).read_text(encoding="utf-8"))
        task = Task(**data)
        if task.id != task_id:
            raise ValueError(f"Invalid taskId: Task file Id does not match {task_id}")
        if task.status not in markers:
            raise ValueError(f"Invalid taskStatus: {task.status}")
        return task

    def list_tasks(self) -> list[Task]:
        if not self.directory.exists():
            return []
        root = self._root()
        return [self.load(path.stem) for path in sorted(root.glob("task_*.json"))]

    def _depends_on(self, task_id: str, target_id: str) -> bool:
        """task_id transitively depends on target_id"""
        pending = [task_id]
        visited = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            if current == target_id:
                return True
            visited.add(current)
            pending.extend(self.load(current).blockedBy)
        return False

    def update_dependencies(self, task_id: str, add_blocked_by: list[str]) -> Task:
        if not isinstance(add_blocked_by, list):
            raise ValueError(f"add_blocked_by must be a list")
        task = self.load(task_id)
        if task.status != "pending" or task.owner is not None:
            raise ValueError(f"Invalid taskStatus: {task.status}")
        dependencies = list(dict.fromkeys(add_blocked_by))
        for dependency in dependencies:
            if dependency == task_id:
                raise ValueError(f"Invalid taskId: {task_id}")
            if not self.exists(dependency):
                raise ValueError(f"Invalid dependency: {dependency}")
            if dependency not in task.blockedBy and self._depends_on(dependency, task_id):
                raise ValueError(f"Invalid dependency: {dependency}")

        task.blockedBy.extend(dependency for dependency in dependencies if dependency not in task.blockedBy)
        self.save(task)
        return task


TASKS = TaskStore(TASKS_DIR)


def create_task(subject: str, description: str) -> Task:
    return TASKS.create(subject, description)


def update_task(task_id: str, addBlockedBy: list[str]) -> Task:
    with task_store_lock():
        return TASKS.update_dependencies(task_id, addBlockedBy)


def load_task(task_id: str) -> Task:
    return TASKS.load(task_id)


def list_tasks() -> list[Task]:
    return TASKS.list_tasks()


def get_task(task_id: str) -> str:
    return json.dumps(asdict(load_task(task_id)), indent=2)


def incomplete_dependencies(task: Task) -> list[str]:
    incomplete = []
    for dependency in task.blockedBy:
        try:
            if load_task(dependency).status != "completed":
                incomplete.append(dependency)
        except (FileNotFoundError, ValueError):
            incomplete.append(dependency)
    return incomplete


def can_start(task_id: str) -> bool:
    return not incomplete_dependencies(load_task(task_id))


def claim_task(task_id: str, owner: str = "agent") -> str:
    with task_store_lock():
        task = load_task(task_id)
        if task.status != "pending" or task.owner is not None:
            return f"Task {task_id} is no longer available"
        if any(t.status == "in_progress" and t.owner == owner for t in list_tasks()):
            return f"Owner {owner} already has an in-progress task"
        dependencies = incomplete_dependencies(task)
        if dependencies:
            return f"Task {task_id} depends on {', '.join(dependencies)} cannot be claimed"
        if task.worktree:
            directory = (WORKDIR / ".worktrees" / task.worktree).resolve()
            if not directory.is_relative_to((WORKDIR / ".worktrees").resolve()) \
                    or not directory.is_dir():
                return f"Task {task_id} worktree is unavailable"
        task.owner = owner
        task.status = "in_progress"
        TASKS.save(task)
        return f"Claimed {task.id} ({task.subject})"


def complete_task(task_id: str, owner: str = "agent") -> str:
    with task_store_lock():
        task = load_task(task_id)
        if task.status != "in_progress":
            return f"Task {task_id} is {task.status}, cannot complete"
        if task.owner != owner:
            return f"Task {task_id} is owned by {task.owner}, not {owner}"
        ready_before = {
            candidate.id for candidate in list_tasks()
            if candidate.status == "pending" and candidate.blockedBy and can_start(candidate.id)
        }
        task.status = "completed"
        TASKS.save(task)
        unblocked = [candidate.subject for candidate in list_tasks()
                     if candidate.status == "pending" and candidate.blockedBy
                     and candidate.id not in ready_before and can_start(candidate.id)]
        message = f"Completed {task.id} ({task.subject})"
        if unblocked:
            message += f"\nUnblocked: {', '.join(unblocked)}"
        return message
