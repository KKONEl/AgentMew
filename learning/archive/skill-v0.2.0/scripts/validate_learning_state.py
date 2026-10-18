#!/usr/bin/env python3
"""Validate learning-coach files without changing them."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from state_lib import CONCEPT_COLUMNS, QUEUE_COLUMNS, parse_date, project_root, read_mistakes, read_table


SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def integer(value: str, field: str, item_id: str, errors: list[str], minimum: int = 0, maximum: int | None = None) -> None:
    try:
        number = int(value)
    except ValueError:
        errors.append(f"{item_id}: {field} must be an integer")
        return
    if number < minimum or (maximum is not None and number > maximum):
        errors.append(f"{item_id}: {field} outside {minimum}..{maximum if maximum is not None else '∞'}")


def checked_date(value: str, field: str, item_id: str, errors: list[str]) -> None:
    try:
        parse_date(value)
    except ValueError:
        errors.append(f"{item_id}: {field} must be YYYY-MM-DD or blank")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", help="Project root; auto-detected by default")
    args = parser.parse_args()
    root = project_root(args.root)
    learning = root / "learning"
    required = ["profile.md", "progress.md", "concepts.md", "mistakes.md", "review_queue.md", "skill_feedback.md"]
    errors: list[str] = []
    for name in required:
        if not (learning / name).is_file():
            errors.append(f"missing learning/{name}")
    if errors:
        print("INVALID\n- " + "\n- ".join(errors))
        return 1

    concepts, _ = read_table(learning / "concepts.md", CONCEPT_COLUMNS)
    seen: set[str] = set()
    valid_status = {"new", "learning", "weak", "understood", "mastered"}
    for item in concepts:
        item_id = item["id"]
        if not SLUG.fullmatch(item_id):
            errors.append(f"concept id is not kebab-case: {item_id!r}")
        if item_id in seen:
            errors.append(f"duplicate concept id: {item_id}")
        seen.add(item_id)
        if item["status"] not in valid_status:
            errors.append(f"{item_id}: invalid status {item['status']!r}")
        integer(item["confidence"], "confidence", item_id, errors, 0, 5)
        integer(item["review_count"], "review_count", item_id, errors)
        integer(item["success_streak"], "success_streak", item_id, errors)
        integer(item["interval_days"], "interval_days", item_id, errors)
        for field in ("first_seen", "last_review", "next_review"):
            checked_date(item[field], field, item_id, errors)

    mistake_ids: set[str] = set()
    for item in read_mistakes(learning / "mistakes.md"):
        item_id = item["id"]
        if not SLUG.fullmatch(item_id):
            errors.append(f"mistake id is not kebab-case: {item_id!r}")
        if item_id in mistake_ids:
            errors.append(f"duplicate mistake id: {item_id}")
        mistake_ids.add(item_id)
        missing = [field for field in ("topic", "question", "incorrect_model", "correct_model", "cause", "repeat_count", "first_seen", "last_seen", "priority", "status") if not item[field]]
        if missing:
            errors.append(f"{item_id}: missing fields {', '.join(missing)}")
        if item["priority"] and item["priority"] not in {"low", "normal", "high", "critical"}:
            errors.append(f"{item_id}: invalid priority {item['priority']!r}")
        if item["status"] and item["status"] not in {"open", "monitoring", "resolved"}:
            errors.append(f"{item_id}: invalid status {item['status']!r}")
        if item["repeat_count"]:
            integer(item["repeat_count"], "repeat_count", item_id, errors, 1)
        for field in ("first_seen", "last_seen", "last_review", "next_review"):
            checked_date(item[field], field, item_id, errors)

    queue, _ = read_table(learning / "review_queue.md", QUEUE_COLUMNS)
    for item in queue:
        checked_date(item["due_date"], "due_date", item["item_id"], errors)
        if item["priority"] not in {"low", "normal", "high", "critical"}:
            errors.append(f"queue {item['item_id']}: invalid priority")
        if item["type"] not in {"concept", "mistake"}:
            errors.append(f"queue {item['item_id']}: invalid type")
        valid_ids = seen if item["type"] == "concept" else mistake_ids
        if item["item_id"] not in valid_ids:
            errors.append(f"queue points to missing {item['type']}: {item['item_id']}")

    skill = root / ".agents" / "skills" / "learning-coach" / "SKILL.md"
    if not skill.is_file():
        errors.append("missing project skill SKILL.md")
    else:
        front = skill.read_text(encoding="utf-8").split("---", 2)
        if len(front) < 3 or "name: learning-coach" not in front[1] or "description:" not in front[1]:
            errors.append("SKILL.md frontmatter is incomplete")

    if errors:
        print("INVALID\n- " + "\n- ".join(errors))
        return 1
    print(f"VALID: {len(concepts)} concept(s), {len(mistake_ids)} mistake(s), {len(queue)} queued review(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

