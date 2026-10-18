# 错题本

只记录会影响未来判断、设计或实现的错误心智模型。拼写、手误和无长期价值的小错误不记；同一根因更新原条目。

## 使用说明

新增条目使用稳定的 kebab-case ID，并保留以下字段。`minimal_example` 可在字段后附一个短代码块。

<!--
## example-mistake-id

- **topic**: 主题
- **question**: 当时的问题
- **incorrect_model**: 错误理解
- **correct_model**: 正确理解
- **minimal_example**: 最小案例摘要
- **cause**: 为什么会错
- **repeat_count**: 1
- **first_seen**: YYYY-MM-DD
- **last_seen**: YYYY-MM-DD
- **last_review**: -
- **next_review**: YYYY-MM-DD
- **priority**: normal
- **status**: open
- **related_concept**: concept-id
- **related_project**: 文件、符号或场景
-->

## compact-pipeline-trigger-confusion

- **topic**: 上下文压缩管线的触发条件与顺序
- **question**: `tool_result_budget`、`snip_compact` 和基于上下文大小的压缩依次何时触发？
- **incorrect_model**: 将自动压缩视为任务完成时触发，并混淆消息条数、工具结果预算、整体字符硬阈值和 `micro_compact` 目标值。
- **correct_model**: 每轮先对最新工具结果批次运行 `tool_result_budget`；消息超过 50 条才运行 `snip_compact`；整体字符估算超过 50,000 时运行 `micro_compact`，目标降至 40,000，必要时 `fit_tool_results`；处理后仍超过 50,000 才由 LLM 执行 `compact_history`。
- **minimal_example**: 新结果批次过预算时先转存大块并保留预览；历史条数超限才归档中段消息；上下文仍超限时按已读/未读情况继续缩减，最终仍超限才摘要。
- **cause**: 将压缩目标值与 LLM 摘要硬触发线混为一谈，且未稳定追踪各阶段检查的对象。
- **repeat_count**: 3
- **first_seen**: 2026-09-28
- **last_seen**: 2026-09-28
- **last_review**: -
- **next_review**: 2026-09-29
- **priority**: high
- **status**: monitoring
- **related_concept**: context-compaction-priority
- **related_project**: AgentHarness/agent_loop.py

## tool-call-result-compaction-boundary

- **topic**: 压缩时工具调用与结果的配对边界
- **question**: 为什么裁剪消息时要让 assistant 工具调用与对应 tool result 一起保留？
- **incorrect_model**: 保留单个工具调用与其结果的配对，就能在同一批多个调用的中间裁剪；配对主要是为了阻止工具被再次调用。
- **correct_model**: 工具调用与结果需要在 API 历史中成对闭合；孤立的调用或结果可能让消息历史无效。保留已执行结果也能告诉模型副作用已经发生，从而降低重复执行风险。
- **minimal_example**: assistant 的 `tool_calls=[call_a, call_b]` 应与带 `tool_call_id=call_a`、`tool_call_id=call_b` 的结果消息共同处于有效历史边界。
- **cause**: 将单个 call/result 配对误当成完整批次边界，忽略 assistant 消息可能同时声明多个 tool_calls。
- **repeat_count**: 2
- **first_seen**: 2026-09-28
- **last_seen**: 2026-09-28
- **last_review**: 2026-10-02
- **next_review**: 2026-10-09
- **priority**: high
- **status**: resolved
- **related_concept**: context-compaction-priority
- **related_project**: AgentHarness/agent_loop.py

## compact-output-archive

- **topic**: 大工具结果转存与删除的区别
- **question**: 大结果预算压缩后，完整工具输出是否会被丢弃？
- **incorrect_model**: 完整文件内容被丢弃，只留下前 2,000 字符和路径。
- **correct_model**: 完整工具输出写入 `.task_outputs/tool-results/`；当前消息中替换为文件路径和预览，按需可重新读取。
- **minimal_example**: 结果超过单项阈值时，完整内容保存到以 tool_use_id 命名的文件；消息里只保留路径与预览。
- **cause**: 把上下文中的裁剪误当成完整数据删除。
- **repeat_count**: 1
- **first_seen**: 2026-09-28
- **last_seen**: 2026-09-28
- **last_review**: -
- **next_review**: 2026-09-29
- **priority**: normal
- **status**: open
- **related_concept**: context-compaction-priority
- **related_project**: AgentHarness/agent_loop.py

## compact-vs-reactive-tail

- **topic**: 主动/阈值历史摘要与 API 错误补救的区别
- **question**: `compact_history` 和 `reactive_compact` 如何处理最近消息？
- **incorrect_model**: LLM 压缩都是随机丢失精度，并总结旧消息后拼接最近消息。
- **correct_model**: 摘要是有损的，但提示要求提炼目标、文件、决定、剩余工作和用户约束。普通 `compact_history` 用含当前请求、摘要和 transcript 路径的新消息替换历史；`reactive_compact` 额外保留最近 5 条消息并修正工具消息边界。
- **minimal_example**: 主动 `compact_history` 返回单条 `[Compacted]` 摘要消息；API 报错时 Reactive Compact 返回摘要消息加近期尾部。
- **cause**: 将摘要模型可能遗漏信息泛化为随机丢失，并把两种摘要流程的尾部策略合并。
- **repeat_count**: 1
- **first_seen**: 2026-09-28
- **last_seen**: 2026-09-28
- **last_review**: -
- **next_review**: 2026-09-29
- **priority**: normal
- **status**: open
- **related_concept**: context-compaction-priority
- **related_project**: AgentHarness/agent_loop.py

## agent-loop-vs-cli-loop

- **topic**: Agent Loop 的终止条件与 CLI 输入循环
- **question**: 模型没有 `tool_calls` 时为何应 `return`？
- **incorrect_model**: 曾认为 `agent_loop` 只负责执行工具，外层 `main.py` 的循环才是对话。
- **correct_model**: `agent_loop` 负责一次用户任务内的模型-工具往返；无 `tool_calls` 代表模型已给出最终回答，应结束本次任务。`main.py` 的循环只负责接收下一条用户输入。
- **minimal_example**: 若不 return，会用相同 history 反复请求模型，得到重复或无意义的后续回复。
- **cause**: 将交互入口循环与单任务 agent loop 的层级职责混淆。
- **repeat_count**: 1
- **first_seen**: 2026-09-19
- **last_seen**: 2026-09-19
- **last_review**: 2026-09-29
- **next_review**: 2026-10-02
- **priority**: normal
- **status**: monitoring
- **related_concept**: openai-compatible-tool-loop
- **related_project**: AgentHarness/main.py；AgentHarness/agent_loop.py

## permission-api-shape-mismatch

- **topic**: 权限管线的工具调用接口适配
- **question**: 如何把 `check_permission()` 接入 OpenAI Chat Completions 的工具循环？
- **incorrect_model**: 可以直接把文档中使用 `block.name` 和 `block.input` 的权限函数传入 OpenAI 工具名字符串。
- **correct_model**: 权限函数与循环必须约定同一输入契约；当前循环应将解析后的 `tool.function.name` 与 `args` 一并传给权限函数，或显式适配为其所需对象。
- **minimal_example**: `check_permission("bash")` 访问 `.name` 会抛出 `AttributeError`；`check_permission("bash", {"command": "ls"})` 才能按名称和参数判定。
- **cause**: 混用了不同 SDK/文档示例的工具调用对象结构，未在边界处做接口适配。
- **repeat_count**: 6
- **first_seen**: 2026-09-21
- **last_seen**: 2026-09-22
- **last_review**: 2026-09-22
- **next_review**: 2026-09-24
- **priority**: high
- **status**: monitoring
- **related_concept**: permission-pipeline
- **related_project**: AgentHarness/permission.py；AgentHarness/agent_loop.py

## post-hook-before-output

- **topic**: Hook 时机与数据可用性
- **question**: `PostToolUse` 应在工具 handler 的哪一侧触发？
- **incorrect_model**: 只要事件名是 PostToolUse，就可在 handler 前触发，之后再取得 output。
- **correct_model**: PostToolUse 依赖真实 output，必须在 handler 返回并完成 `output` 赋值后触发；否则调用表达式会先读取未定义变量并失败。
- **minimal_example**: `trigger_hooks("PostToolUse", tool_name, args, output)` 必须位于 `output = handler(**args)` 之后。
- **cause**: 已能口头区分 Pre 与 Post，但把数据生产顺序遗漏在实现中。
- **repeat_count**: 2
- **first_seen**: 2026-09-22
- **last_seen**: 2026-09-22
- **last_review**: 2026-09-22
- **next_review**: 2026-09-24
- **priority**: normal
- **status**: monitoring
- **related_concept**: hook-dispatch
- **related_project**: AgentHarness/agent_loop.py

## tool-result-message-schema

- **topic**: SDK 间的工具结果消息结构适配
- **question**: Stop hook 如何统计当前 OpenAI 工具循环的工具调用次数？
- **incorrect_model**: 可以沿用参考实现，遍历 `content` 列表中类型为 `tool_result` 的块。
- **correct_model**: 当前 OpenAI 循环把每条工具结果追加为独立的 `{ "role": "tool", ... }` 消息，应按该角色计数。
- **minimal_example**: `sum(1 for message in messages if message.get("role") == "tool")`。
- **cause**: 复制 Hook 时未同步适配历史消息的数据结构。
- **repeat_count**: 1
- **first_seen**: 2026-09-22
- **last_seen**: 2026-09-22
- **last_review**: 2026-09-22
- **next_review**: 2026-09-24
- **priority**: normal
- **status**: monitoring
- **related_concept**: openai-compatible-tool-loop
- **related_project**: AgentHarness/agent_loop.py；AgentHarness/hooks.py

## todo-single-in-progress

- **topic**: Todo 计划状态约束
- **question**: Todo 列表能否同时有多个 `in_progress` 项？
- **incorrect_model**: 多个任务可以同时标记为 `in_progress`。
- **correct_model**: 本课 TodoManager 同时只允许一个 `in_progress`，使当前工作焦点明确；其他未开始任务保持 `pending`。
- **minimal_example**: `completed → in_progress → pending` 合法；两个 `in_progress` 会被拒绝。
- **cause**: 理解了计划用于聚焦，但尚未把“单一当前焦点”识别为校验不变量。
- **repeat_count**: 1
- **first_seen**: 2026-09-23
- **last_seen**: 2026-09-23
- **last_review**: -
- **next_review**: 2026-09-24
- **priority**: normal
- **status**: open
- **related_concept**: todo-plan-state
- **related_project**: AgentHarness/tools.py；AgentHarness/agent_loop.py

## todo-responsibility-boundaries

- **topic**: TodoWrite 的模块职责划分
- **question**: TodoManager、工具注册、提醒计数和提示词分别应位于哪里？
- **incorrect_model**: 工具注册应在 main，轮次计数应在 tools，Todo 状态逻辑直接混在 tools。
- **correct_model**: TodoManager 独立管理计划状态；tools 声明 schema、包装 run_todo_write、注册 handler；agent_loop 跟踪每轮调用并注入 reminder；prompts 保留计划指令；main 只负责交互入口与启动装配。
- **minimal_example**: `rounds_since_todo` 必须在每次模型响应的工具调用轮次结束后更新，因此属于 agent_loop。
- **cause**: 尚未按“状态管理 / 工具适配 / 循环编排 / 交互入口”分离职责。
- **repeat_count**: 2
- **first_seen**: 2026-09-26
- **last_seen**: 2026-09-26
- **last_review**: -
- **next_review**: 2026-09-27
- **priority**: normal
- **status**: open
- **related_concept**: todo-integration-boundaries
- **related_project**: AgentHarness/todo_manager.py；AgentHarness/tools.py；AgentHarness/agent_loop.py；AgentHarness/prompts.py

## subagent-context-vs-workspace

- **topic**: Subagent 的消息隔离与共享工作目录
- **question**: 子 Agent 的上下文独立，是否意味着它修改的文件父 Agent 看不到？子 Agent 的工具调用和任务状态会自动并入父 Agent 吗？
- **incorrect_model**: 父子对话隔离意味着子 Agent 修改的工作区文件不会对父 Agent 可见；父 Agent 收到结果后还需要同步子 Agent 的任务状态和工具调用。
- **correct_model**: 隔离的是消息历史。父子共享工作目录时，子 Agent 写入的文件对父 Agent 可见；子 Agent 的中间消息与工具调用不会自动进入父历史，父侧只收到 task handler 返回的最终文本作为工具结果，再由父循环据此继续。工具权限策略可以共享，也可以按 agent_type 缩减；具体看传给子循环的工具集合与执行器。
- **minimal_example**: 子 Agent 写入 `notes.md` 后，父 Agent 可读取该共享文件；父消息列表中只有父侧的 `task` 调用及其工具结果，不包含子 Agent 自己的 `read_file` 或 `write_file` 消息。
- **cause**: 把上下文隔离误推成执行环境隔离，并把父循环收到的工具返回值和子循环的内部状态混为一谈。
- **repeat_count**: 1
- **first_seen**: 2026-09-27
- **last_seen**: 2026-09-27
- **last_review**: -
- **next_review**: 2026-09-28
- **priority**: normal
- **status**: open
- **related_concept**: subagent-context-boundary
- **related_project**: AgentHarness/agent_loop.py；AgentHarness/tools.py
