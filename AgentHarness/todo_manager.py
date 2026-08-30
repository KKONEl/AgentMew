import ast
import json


class TodoManager:
    def __init__(self):
        self.items: list[dict] = []

    def update(self, todos: list | str) -> str:
        if isinstance(todos, str):
            try:
                todos = json.loads(todos)
            except json.JSONDecodeError:
                try:
                    todos = ast.literal_eval(todos)
                except (SyntaxError, ValueError) as e:
                    raise ValueError("todos must be a list or JSON array string") from e

        if not isinstance(todos, list):
            raise ValueError("todos must be a list")
        if len(todos) > 20:
            raise ValueError("Max 20 todos allowed")

        validated = []
        in_progress_count = 0
        for index, todo in enumerate(todos):
            if not isinstance(todo, dict):
                raise ValueError(f"todos[{index}] must be an object")

            content = str(todo.get("content", "")).strip()
            status = str(todo.get("status", "pending")).lower()
            if not content:
                raise ValueError(f"todos[{index}] requires content")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"todos[{index}] has invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"content": content, "status": status})

        if in_progress_count > 1:
            raise ValueError("Only one todo can be in_progress at a time")

        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."

        lines = []
        for todo in self.items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[x]",
            }[todo["status"]]
            lines.append(f"{marker} {todo['content']}")

        done = sum(todo["status"] == "completed" for todo in self.items)
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


def run_todo_write(todos: list | str) -> str:
    try:
        output = TODO.update(todos)
    except ValueError as e:
        return f"Error: {e}"
    print(f"\n\033[33m## Current Tasks\033[0m\n{output}")
    return output


TODO_LIST = [
    {"content": "查看当前项目结构", "status": "completed"},
    {"content": "分析清单（ANALYSIS.md）", "status": "completed"},
    {"content": "漏洞列表文档（VULNERABILITIES.md）", "status": "completed"},
    {"content": "优化建议（部分需在ANALYSIS.md中补充）", "status": "pending"},
    {"content": "更新 todo_manager.py 以包含完成状态", "status": "pending"},
    {"content": "创建 README.md 文档", "status": "pending"},
    {"content": "实施安全修复建议（命令注入、权限检查等）", "status": "pending"},
    {"content": "优化全局状态管理（_APPROVED_EXTERNAL_PATHS）", "status": "pending"},
    {"content": "添加超时机制到 agent_loop", "status": "pending"},
    {"content": "实现日志系统", "status": "pending"},
]