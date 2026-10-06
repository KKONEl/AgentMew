import asyncio
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from AgentHarness import task_manager as tasks
from AgentHarness.goal_runtime import GoalController
from AgentHarness.mcp_runtime import (
    _CONNECTED, _APPROVED, approve_mcp_tool, assemble_tool_pool, connect_mcp,
)
from AgentHarness.team_runtime import MessageBus, TeamRuntime
from AgentHarness import workflow_runtime as workflow


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, prompt, schema, label):
        self.calls.append(label)
        if label.startswith("audit:"):
            return {"findings": [{"title": label, "detail": "Potential issue"}]}
        return {"isReal": True, "reason": "Confirmed"}


class FakeEvaluator:
    def __init__(self):
        self.results = iter([
            {"ok": False, "impossible": False, "reason": "Run tests"},
            {"ok": True, "impossible": False, "reason": "Tests passed"},
        ])

    def evaluate(self, criterion, messages):
        return next(self.results)


class FakeMessage:
    def __init__(self, content="done", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        value = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            value["tool_calls"] = [
                {"id": call.id, "type": "function", "function": {
                    "name": call.function.name, "arguments": call.function.arguments}}
                for call in self.tool_calls]
        return value


class FakeClient:
    def __init__(self, messages):
        self.responses = iter(messages)
        self.tool_names = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.tool_names.append([item["function"]["name"] for item in kwargs.get("tools", [])])
        return SimpleNamespace(choices=[SimpleNamespace(message=next(self.responses))])


def fake_call(name, args, ident):
    return SimpleNamespace(id=ident, function=SimpleNamespace(
        name=name, arguments=json.dumps(args)))


class RuntimeTests(unittest.TestCase):
    def test_atomic_claim_and_mailbox(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            store = tasks.TaskStore(root / "tasks")
            with patch.object(tasks, "TASKS_DIR", root / "tasks"), patch.object(tasks, "TASKS", store):
                task = tasks.create_task("example", "")
                answers = []
                threads = [threading.Thread(target=lambda owner=owner:
                           answers.append(tasks.claim_task(task.id, owner)))
                           for owner in ("alice", "bob")]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                self.assertEqual(sum(answer.startswith("Claimed ") for answer in answers), 1)
                self.assertIn(tasks.load_task(task.id).owner, {"alice", "bob"})
            bus = MessageBus(root / "mailboxes")
            bus.send("alice", "lead", "done", "result")
            self.assertEqual(bus.drain("lead")[0]["content"], "done")
            self.assertEqual(bus.drain("lead"), [])

    def test_mcp_discovery_policy_and_collision(self):
        _CONNECTED.clear()
        _APPROVED.clear()
        self.assertIn("Connected docs", connect_mcp("docs"))
        self.assertIn("Connected deploy", connect_mcp("deploy"))
        tools, handlers = assemble_tool_pool([], {})
        names = [item["function"]["name"] for item in tools]
        self.assertIn("mcp__docs__search", names)
        self.assertIn("mcp__deploy__trigger", names)
        self.assertIn("host approval required", handlers["mcp__deploy__trigger"](environment="test"))
        approve_mcp_tool("deploy", "trigger")
        self.assertIn("triggered", handlers["mcp__deploy__trigger"](environment="test"))
        _CONNECTED.clear()
        _APPROVED.clear()

    def test_workflow_resume_uses_journal(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            runner = FakeRunner()
            with patch.object(workflow, "RUNTIME_DIR", Path(directory)):
                first = asyncio.run(workflow.execute_workflow(
                    "review-changes", {"changes": "+ insecure code"}, runner=runner))
                self.assertEqual(first["task"]["agents"], 6)
                self.assertEqual(len(first["result"]["confirmed"]), 3)
                again = asyncio.run(workflow.execute_workflow(
                    "review-changes", resume_from_run_id=first["run_id"], runner=runner))
                self.assertEqual(again["task"]["agents"], 0)
                self.assertEqual(len(runner.calls), 6)

    def test_goal_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            goal = GoalController(FakeEvaluator(), Path(directory) / "goal.json")
            goal.set("tests pass")
            self.assertEqual(goal.after_turn([])[0], "block")
            self.assertEqual(goal.after_turn([])[0], "allow")
            self.assertIsNone(goal.criterion)

    def test_team_worker_result_and_shutdown(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            store = tasks.TaskStore(root / "tasks")
            with patch.object(tasks, "TASKS_DIR", root / "tasks"), patch.object(tasks, "TASKS", store):
                task = tasks.create_task("example", "")
                team = TeamRuntime(MessageBus(root / "mailboxes"), FakeClient([FakeMessage()]))
                self.assertIn("Spawned", team.spawn("alice", "worker", "do work", task.id))
                events = team.bus.wait("lead", 2)
                self.assertTrue(any(event["type"] == "result" for event in events))
                self.assertIn("Shutdown requested", team.request_shutdown("alice"))
                thread = team.threads["alice"]
                thread.join(2)
                self.assertFalse(thread.is_alive())

    def test_agent_loop_reassembles_mcp_pool(self):
        from AgentHarness import agent_loop
        _CONNECTED.clear()
        client = FakeClient([
            FakeMessage("", [fake_call("connect_mcp", {"name": "docs"}, "a")]),
            FakeMessage("", [fake_call("mcp__docs__search", {"query": "hooks"}, "b")]),
            FakeMessage("finished"),
        ])
        history = [{"role": "system", "content": "test"},
                   {"role": "user", "content": "search docs"}]
        with patch.object(agent_loop, "client", client), \
                patch.object(agent_loop.COMPACTOR, "prepare", side_effect=lambda m, _: m), \
                patch.object(agent_loop, "extract_memories", return_value=False), \
                patch.object(agent_loop, "trigger_hooks", return_value=None):
            agent_loop.agent_loop(history, available_tools=[], handlers={})
        self.assertNotIn("mcp__docs__search", client.tool_names[0])
        self.assertIn("mcp__docs__search", client.tool_names[1])
        self.assertEqual([m["tool_call_id"] for m in history if m["role"] == "tool"], ["a", "b"])
        _CONNECTED.clear()


if __name__ == "__main__":
    unittest.main()
