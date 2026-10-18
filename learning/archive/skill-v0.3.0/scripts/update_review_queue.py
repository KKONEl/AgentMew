#!/usr/bin/env python3
"""Regenerate learning/review_queue.md from concepts and mistakes."""

from __future__ import annotations

import argparse
from datetime import date

from state_lib import CONCEPT_COLUMNS, QUEUE_COLUMNS, parse_date, priority_rank, project_root, read_mistakes, read_table, replace_table


def concept_priority(status: str, due, today: date) -> str:
    overdue = (today - due).days if due else 0
    if status == "weak" and overdue >= 3:
        return "critical"
    if status == "weak" or overdue >= 7:
        return "high"
    if status == "mastered" and overdue <= 0:
        return "low"
    return "normal"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", help="Project root; auto-detected by default")
    parser.add_argument("--today", help="Override today as YYYY-MM-DD for testing")
    args = parser.parse_args()
    root = project_root(args.root)
    today = date.fromisoformat(args.today) if args.today else date.today()
    learning = root / "learning"
    concepts, _ = read_table(learning / "concepts.md", CONCEPT_COLUMNS)
    mistakes = read_mistakes(learning / "mistakes.md")
    queue: list[dict[str, str]] = []

    for item in concepts:
        due = parse_date(item["next_review"])
        if not due:
            continue
        priority = concept_priority(item["status"], due, today)
        reason = "overdue" if due < today else ("due today" if due == today else "scheduled review")
        if item["status"] == "weak":
            reason += "; weak concept"
        queue.append({
            "due_date": due.isoformat(), "priority": priority, "type": "concept",
            "item_id": item["id"], "topic": item["topic"], "source": "concepts.md",
            "reason": reason,
        })

    for item in mistakes:
        if item["status"] == "resolved" and not item["next_review"]:
            continue
        due = parse_date(item["next_review"])
        if not due:
            continue
        priority = item["priority"] or "normal"
        reason = "overdue mistake" if due < today else ("mistake due today" if due == today else "scheduled mistake review")
        if int(item["repeat_count"] or "0") > 1:
            reason += "; repeated"
        queue.append({
            "due_date": due.isoformat(), "priority": priority, "type": "mistake",
            "item_id": item["id"], "topic": item["topic"], "source": "mistakes.md",
            "reason": reason,
        })

    queue.sort(key=lambda row: (row["due_date"], priority_rank(row["priority"]), row["type"], row["item_id"]))
    replace_table(learning / "review_queue.md", QUEUE_COLUMNS, queue)
    print(f"Updated review queue: {len(queue)} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

