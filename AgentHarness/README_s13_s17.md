# s13–s17 in agentDemo

This project uses the existing OpenAI compatible client in `configs/config.py`. The
features follow the contracts in [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code),
while keeping this project's existing s01–s12 modules.

| Chapter | Entry point | Behavior |
| --- | --- | --- |
| s13 Agent Teams | `team_runtime.py` | Persistent teammate threads, independent histories, file mailboxes, atomic shared task claims, result and idle events, plan approval, shutdown handshake, optional task worktrees. |
| s14 MCP Tools | `mcp_runtime.py` | Connect mock `docs` and `deploy` servers, discover namespaced tools, rebuild the tool pool on each model call, enforce host policy. |
| s15 Integrated Harness | `agent_loop.py`, `main.py` | Team, MCP, task, cron, background, memory, skill, and ordinary tools share the main loop. The event processor wakes the lead on cron, team, and background events. |
| s16 Workflow Runtime | `workflow_runtime.py` | Saved `review-changes` workflow with `agent`, `parallel`, `pipeline`, phases, structured outputs, progress events, journal, and resume by run ID. |
| s17 Goal Loop | `goal_runtime.py` | `/goal` criterion, independent evaluator, automatic continuation, background defer, limits, status, clear, and restoration of an active criterion. |

Run from the repository root with the `pythonProject` environment and the existing
API settings:

```sh
python -m AgentHarness.main
```

Useful prompts and commands:

```text
Connect the docs MCP server, search for hooks, and report its version.
Connect the deploy server and check its status.
/mcp approve deploy trigger
Propose a two person team for these independent tasks. Wait for my confirmation before spawning.
Run the saved review-changes Workflow for this diff: ...
/goal run the project tests and finish only when the exit code is 0
/goal
/goal clear
```

MCP servers in this lesson are in-process mocks, matching the reference chapter's
transport scope. `deploy/trigger` requires the host command above; model supplied
server metadata cannot approve it. `remove_worktree()` is a host-only function and
is never a model tool. Worktrees separate working copies; they are not sandboxes.

Offline verification:

```sh
api_key=test model=test python -B -m unittest discover -s tests -v
```

The tests use fake model and workflow runners. A live run requires the project's
configured API endpoint and credentials.
