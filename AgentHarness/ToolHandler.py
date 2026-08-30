#  tool 对应调用的方法
from AgentHarness.Tools import run_bash, run_read, run_write, run_edit, run_glob
from AgentHarness.todo_manager import run_todo_write

TOOL_HANDLERS = {
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
    "todo_write":run_todo_write,
}
