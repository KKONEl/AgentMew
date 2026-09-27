import os
SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    "Before starting any multi-step task, use todo_write to plan your steps. "
    "Update status as you go. "
    "Use task for focused exploration or a self-contained subtask. "
)
SUB_SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    "Complete the given task, then return a concise final answer."
)