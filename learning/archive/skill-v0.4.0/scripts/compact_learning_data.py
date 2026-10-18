#!/usr/bin/env python3
"""Report conservative archive candidates; apply only when explicitly requested."""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from state_lib import CONCEPT_COLUMNS, parse_date, project_root, read_mistakes, read_table


def main() -> int:
    parser = argparse.ArgumentParser(description="Find old, inactive learning records safe to consider for archive")
    parser.add_argument("--root", help="Project root; auto-detected by default")
    parser.add_argument("--inactive-days", type=int, default=180)
    args = parser.parse_args()
    root = project_root(args.root)
    learning = root / "learning"
    cutoff = date.today() - timedelta(days=args.inactive_days)
    concepts, _ = read_table(learning / "concepts.md", CONCEPT_COLUMNS)
    mistakes = read_mistakes(learning / "mistakes.md")
    concept_candidates = [item["id"] for item in concepts if item["status"] == "mastered" and not parse_date(item["next_review"]) and parse_date(item["last_review"]) and parse_date(item["last_review"]) <= cutoff]
    mistake_candidates = [item["id"] for item in mistakes if item["status"] == "resolved" and not parse_date(item["next_review"]) and parse_date(item["last_seen"]) and parse_date(item["last_seen"]) <= cutoff]
    sizes = {path.name: path.stat().st_size for path in learning.glob("*.md")}
    print(f"Cutoff: {cutoff.isoformat()} ({args.inactive_days} inactive days)")
    print("Concept archive candidates:", ", ".join(concept_candidates) or "none")
    print("Mistake archive candidates:", ", ".join(mistake_candidates) or "none")
    print("File sizes:", ", ".join(f"{name}={size}B" for name, size in sorted(sizes.items())))
    print("This command is report-only. Archive reviewed candidates manually so no learning data is silently lost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
