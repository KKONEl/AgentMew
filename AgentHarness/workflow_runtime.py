"""Saved, resumable workflow orchestration (s16)."""

import asyncio
import fcntl
import hashlib
import json
import os
import re
import secrets
from contextlib import contextmanager
from pathlib import Path

from AgentHarness.configs.config import model
from AgentHarness.task_manager import WORKDIR

RUNTIME_DIR = WORKDIR / ".workflow"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class WorkflowError(Exception):
    pass


def _write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _valid(value, schema: dict) -> bool:
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return False
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(
                key not in schema.get("properties", {}) for key in value):
            return False
        return all(_valid(item, schema.get("properties", {}).get(key, {}))
                   for key, item in value.items())
    if kind == "array":
        return isinstance(value, list) and all(_valid(item, schema.get("items", {})) for item in value)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return type(value) is int
    return True


class OpenAIAgentRunner:
    def __init__(self, client=None):
        self.client = client

    def run(self, prompt: str, schema: dict | None, label: str):
        if self.client is None:
            from AgentHarness.agent_loop import client
            self.client = client
        instruction = "Return only a JSON object matching this schema: " + json.dumps(schema) if schema else "Answer concisely."
        response = self.client.chat.completions.create(
            model=model, messages=[{"role": "system", "content": instruction},
                                   {"role": "user", "content": prompt}])
        text = response.choices[0].message.content or ""
        if schema is None:
            return text
        try:
            return json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError as error:
            raise WorkflowError(f"{label} returned invalid JSON: {error}") from error


class Execution:
    def __init__(self, run_id: str, journal: Path, runner, depth: int = 0):
        self.run_id = run_id
        self.journal = journal
        self.runner = runner
        self.depth = depth
        self.cache = {}
        self.events = []
        self.agent_calls = 0
        if journal.exists():
            for line in journal.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                self.cache[item["key"]] = item["value"]

    def phase(self, name: str):
        self.events.append({"type": "task_progress", "phase": name})

    def log(self, text: str):
        self.events.append({"type": "task_progress", "message": text})

    async def agent(self, prompt: str, *, schema: dict | None = None,
                    label: str = "agent", phase: str = ""):
        basis = json.dumps([label, prompt, schema], ensure_ascii=False, sort_keys=True)
        key = hashlib.sha256(basis.encode()).hexdigest()
        if key in self.cache:
            self.events.append({"type": "workflow_agent", "label": label, "status": "cached"})
            return self.cache[key]
        self.phase(phase or label)
        for attempt in range(2):
            try:
                value = await asyncio.to_thread(self.runner.run, prompt, schema, label)
                valid = schema is None or _valid(value, schema)
            except WorkflowError:
                valid = False
            if valid:
                break
            if attempt == 1:
                raise WorkflowError(f"{label} returned data outside schema")
            prompt += "\nReturn valid JSON matching the required schema."
        with self.journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.cache[key] = value
        self.agent_calls += 1
        self.events.append({"type": "workflow_agent", "label": label, "status": "completed"})
        return value

    async def parallel(self, calls):
        return await asyncio.gather(*(call() for call in calls))

    async def pipeline(self, items, *stages):
        async def one(item, index):
            value = item
            for stage in stages:
                value = await stage(value, item, index)
            return value
        return await asyncio.gather(*(one(item, index) for index, item in enumerate(items)))

    async def workflow(self, name: str, args: dict):
        if self.depth >= 1:
            raise WorkflowError("Nested workflows are limited to one level")
        record = WORKFLOWS.get(name)
        if record is None:
            raise WorkflowError(f"Unknown nested workflow: {name}")
        _validate_meta(record["meta"])
        nested = Execution(self.run_id, self.journal, self.runner, self.depth + 1)
        result = await record["script"](nested, args)
        self.agent_calls += nested.agent_calls
        self.events.extend(nested.events)
        self.cache.update(nested.cache)
        return result


FINDINGS = {"type": "object", "properties": {"findings": {"type": "array", "items": {
    "type": "object", "properties": {"title": {"type": "string"},
                                      "detail": {"type": "string"}},
    "required": ["title", "detail"]}}}, "required": ["findings"]}
VERDICT = {"type": "object", "properties": {"isReal": {"type": "boolean"},
                                               "reason": {"type": "string"}},
           "required": ["isReal", "reason"]}


async def review_changes(ctx: Execution, args: dict):
    changes = args.get("changes")
    if not isinstance(changes, str) or not changes.strip():
        raise WorkflowError("review-changes requires nonempty args.changes")
    dimensions = ["correctness", "security", "maintainability"]

    async def audit(_value, dimension, _index):
        out = await ctx.agent(f"Find concrete {dimension} issues in this diff:\n{changes}",
                              schema=FINDINGS, label=f"audit:{dimension}", phase="Review")
        return {"dimension": dimension, "findings": out["findings"]}

    async def verify(audited, dimension, _index):
        verdicts = await ctx.parallel([
            (lambda finding=finding: ctx.agent(
                f"Verify this finding against the diff. Diff:\n{changes}\nFinding: {finding}",
                schema=VERDICT, label=f"verify:{dimension}:{finding['title']}", phase="Verify"))
            for finding in audited["findings"]])
        return {"dimension": dimension, "confirmed": [
            finding for finding, verdict in zip(audited["findings"], verdicts)
            if verdict["isReal"]]}

    results = await ctx.pipeline(dimensions, audit, verify)
    confirmed = [dict(dimension=item["dimension"], **finding)
                 for item in results for finding in item["confirmed"]]
    ctx.log(f"Confirmed {len(confirmed)} findings")
    return {"confirmed": confirmed}


WORKFLOWS = {"review-changes": {
    "meta": {"name": "review-changes", "description": "Review changes across three dimensions",
             "phases": ["Review", "Verify"]}, "script": review_changes}}


@contextmanager
def _run_lock(run_id: str):
    path = RUNTIME_DIR / f"{run_id}.lock"
    with path.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WorkflowError("run is already active") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _validate_meta(meta: dict):
    if not isinstance(meta, dict) or not isinstance(meta.get("name"), str) \
            or not NAME_RE.fullmatch(meta["name"]) or not meta.get("description"):
        raise WorkflowError("Invalid registered workflow metadata")
    if not all(isinstance(p, str) and p for p in meta.get("phases", [])):
        raise WorkflowError("Invalid workflow phases")


async def execute_workflow(name: str, args: dict | None = None,
                           resume_from_run_id: str | None = None, runner=None) -> dict:
    record = WORKFLOWS.get(name)
    if record is None:
        raise WorkflowError(f"Unknown workflow: {name}")
    _validate_meta(record["meta"])
    if args is not None and not isinstance(args, dict):
        raise WorkflowError("args must be an object")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if resume_from_run_id:
        if not re.fullmatch(r"run_[0-9a-f]{16}", resume_from_run_id):
            raise WorkflowError("Invalid run ID")
        run_id = resume_from_run_id
    else:
        run_id = f"run_{secrets.token_hex(8)}"
        reservation = RUNTIME_DIR / f"{run_id}.reserve"
        with reservation.open("x"):
            pass
    with _run_lock(run_id):
        snapshot = RUNTIME_DIR / f"{run_id}.json"
        if resume_from_run_id:
            if not snapshot.exists():
                raise WorkflowError("Run snapshot not found")
            saved = json.loads(snapshot.read_text(encoding="utf-8"))
            if saved["name"] != name or (args is not None and saved["args"] != args):
                raise WorkflowError("Resume name or args mismatch")
            args = saved["args"]
        else:
            args = args or {}
        _write_json(snapshot, {"name": name, "args": args, "status": "running"})
        execution = Execution(run_id, RUNTIME_DIR / f"{run_id}.journal.jsonl",
                              runner or OpenAIAgentRunner())
        execution.events.append({"type": "task_started", "run_id": run_id})
        try:
            result = await record["script"](execution, args)
        except Exception as error:
            _write_json(snapshot, {"name": name, "args": args, "status": "failed",
                                   "error": str(error)})
            raise
        _write_json(RUNTIME_DIR / f"{run_id}.output.json", result)
        _write_json(snapshot, {"name": name, "args": args, "status": "completed"})
        execution.events.append({"type": "task_notification", "status": "completed",
                                 "run_id": run_id, "agents": execution.agent_calls})
        return {"launched": True, "run_id": run_id, "result": result,
                "task": {"status": "completed", "agents": execution.agent_calls,
                         "events": execution.events}}


def run_workflow(name: str, args: dict | None = None,
                 resume_from_run_id: str | None = None) -> str:
    try:
        return json.dumps(asyncio.run(execute_workflow(name, args, resume_from_run_id)),
                          ensure_ascii=False)
    except Exception as error:
        return f"Workflow error: {error}"


WORKFLOW_TOOL = {"type": "function", "function": {
    "name": "Workflow", "description": "Run or resume a saved workflow.",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string"}, "args": {"type": "object"},
        "resume_from_run_id": {"type": "string"}}, "required": ["name"],
        "additionalProperties": False}}}
