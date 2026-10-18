#!/usr/bin/env python3
"""Small stdlib-only helpers for learning-coach Markdown state."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path


CONCEPT_COLUMNS = [
    "id", "topic", "status", "confidence", "first_seen", "last_review",
    "review_count", "success_streak", "interval_days", "next_review",
    "related_project", "common_mistakes", "notes",
]
QUEUE_COLUMNS = [
    "due_date", "priority", "type", "item_id", "topic", "source", "reason",
]
MISTAKE_FIELDS = [
    "topic", "question", "incorrect_model", "correct_model", "minimal_example",
    "cause", "repeat_count", "first_seen", "last_seen", "last_review",
    "next_review", "priority", "status", "related_concept", "related_project",
]


def project_root(explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / "learning").is_dir():
            raise ValueError(f"learning/ not found under {root}")
        return root
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists() and (candidate / "learning").is_dir():
                return candidate
    raise ValueError("Could not locate a project root containing .git and learning/")


def split_row(line: str) -> list[str]:
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>").strip()


def read_table(path: Path, expected: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = -1
    for index, line in enumerate(lines):
        if line.lstrip().startswith("|") and split_row(line) == expected:
            header_index = index
            break
    if header_index < 0:
        raise ValueError(f"Missing expected table header in {path}")
    rows: list[dict[str, str]] = []
    index = header_index + 2
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        cells = split_row(lines[index])
        if len(cells) != len(expected):
            raise ValueError(f"Malformed table row at {path}:{index + 1}; expected {len(expected)} cells, got {len(cells)}")
        if any(cells):
            rows.append(dict(zip(expected, cells)))
        index += 1
    return rows, lines


def replace_table(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    _, lines = read_table(path, columns)
    header_index = next(i for i, line in enumerate(lines) if line.lstrip().startswith("|") and split_row(line) == columns)
    end = header_index + 2
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    rendered = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    rendered.extend("| " + " | ".join(escape_cell(row.get(column, "")) for column in columns) + " |" for row in rows)
    path.write_text("\n".join(lines[:header_index] + rendered + lines[end:]).rstrip() + "\n", encoding="utf-8")


def read_mistakes(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    # Templates live in HTML comments and are documentation, not state records.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    blocks = re.split(r"(?m)^## (?!使用说明)(.+?)\s*$", text)
    records: list[dict[str, str]] = []
    for index in range(1, len(blocks), 2):
        record = {"id": blocks[index].strip(), "_body": blocks[index + 1].strip()}
        for field in MISTAKE_FIELDS:
            match = re.search(rf"(?m)^- \*\*{re.escape(field)}\*\*:[ \t]*(.*)$", record["_body"])
            record[field] = match.group(1).strip() if match else ""
        records.append(record)
    return records


def parse_date(value: str) -> date | None:
    value = value.strip()
    if not value or value in {"-", "never"}:
        return None
    return date.fromisoformat(value)


def priority_rank(value: str) -> int:
    return {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(value, 2)
