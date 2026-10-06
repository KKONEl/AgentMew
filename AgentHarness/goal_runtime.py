"""Session scoped goal gate with an independent completion evaluator (s17)."""

import json
import os
import time
from pathlib import Path

from AgentHarness.configs.config import model
from AgentHarness.task_manager import WORKDIR


class PromptGoalEvaluator:
    def __init__(self, client=None, evaluator_model: str | None = None):
        self.client = client
        self.model = evaluator_model or os.getenv("GOAL_EVALUATOR_MODEL_ID") or model

    def evaluate(self, criterion: str, messages: list[dict]) -> dict:
        if self.client is None:
            from AgentHarness.agent_loop import client
            self.client = client
        transcript = []
        for item in messages[-40:]:
            role = item.get("role", "")
            content = item.get("content") or ""
            if isinstance(content, str):
                transcript.append(f"{role}: {content[:4000]}")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content":
                       "You independently judge whether the goal is complete. "
                       "Use concrete tool results in the transcript; an unsupported assistant claim "
                       "is not proof. Return only JSON with boolean ok, boolean impossible, and "
                       "short string reason. Do not call tools."},
                      {"role": "user", "content":
                       f"Goal: {criterion}\n\nTranscript:\n" + "\n".join(transcript)[-30000:]}],
        )
        raw = response.choices[0].message.content or ""
        value = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(value.get("ok"), bool) or not isinstance(value.get("impossible"), bool) \
                or not isinstance(value.get("reason"), str):
            raise ValueError("Goal evaluator returned invalid decision")
        return value


class GoalController:
    def __init__(self, evaluator=None, status_file: Path | None = None):
        self.evaluator = evaluator or PromptGoalEvaluator()
        self.status_file = status_file or (WORKDIR / ".goal_status.json")
        self.criterion: str | None = None
        self.started_at = 0.0
        self.evaluations = 0
        self.blocks = 0
        self.last_reason = ""
        self.restore()

    def _save(self):
        self.status_file.write_text(json.dumps({
            "criterion": self.criterion, "started_at": self.started_at,
            "evaluations": self.evaluations, "blocks": self.blocks,
            "last_reason": self.last_reason}, ensure_ascii=False), encoding="utf-8")

    def restore(self):
        if not self.status_file.exists():
            return
        try:
            data = json.loads(self.status_file.read_text(encoding="utf-8"))
            if isinstance(data.get("criterion"), str) and data["criterion"]:
                self.criterion = data["criterion"]
                self.started_at = time.time()
                self.last_reason = data.get("last_reason", "")
        except (OSError, ValueError, TypeError):
            pass

    def set(self, criterion: str) -> str:
        if not criterion.strip():
            raise ValueError("Goal criterion cannot be empty")
        self.criterion = criterion.strip()
        self.started_at = time.time()
        self.evaluations = 0
        self.blocks = 0
        self.last_reason = ""
        self._save()
        return f"Goal set: {self.criterion}"

    def clear(self) -> str:
        self.criterion = None
        self._save()
        return "Goal cleared"

    def status(self) -> str:
        if self.criterion is None:
            return "No active goal"
        elapsed = int(time.time() - self.started_at)
        return (f"Goal: {self.criterion}\nEvaluations: {self.evaluations}\n"
                f"Elapsed: {elapsed}s\nLast reason: {self.last_reason or '(none)'}")

    def after_turn(self, messages: list[dict], *, background_pending: bool = False,
                   max_blocks: int = 5) -> tuple[str, str]:
        if self.criterion is None:
            return "allow", ""
        if background_pending:
            return "defer", "Waiting for background work to finish"
        if self.blocks >= max_blocks:
            return "limit", "Goal remains active; automatic continuation limit reached"
        try:
            decision = self.evaluator.evaluate(self.criterion, messages)
        except Exception as error:
            self.last_reason = f"Goal evaluation failed: {error}"
            self._save()
            return "error", self.last_reason
        self.evaluations += 1
        self.last_reason = decision["reason"]
        if decision["ok"]:
            self.clear()
            return "allow", self.last_reason
        if decision["impossible"]:
            self._save()
            return "impossible", self.last_reason
        self.blocks += 1
        self._save()
        return "block", self.last_reason


GOAL = GoalController()
