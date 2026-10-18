# 复习队列

此表由 `update_review_queue.py` 从 `concepts.md` 与 `mistakes.md` 生成。需要改计划时先更新源记录，再重新生成；不要直接把本表当作唯一事实来源。

| due_date | priority | type | item_id | topic | source | reason |
|---|---|---|---|---|---|---|
| 2026-09-21 | high | concept | tool-dispatch | 工具注册与分发 | concepts.md | overdue |
| 2026-09-24 | high | mistake | permission-api-shape-mismatch | 权限管线的工具调用接口适配 | mistakes.md | overdue mistake; repeated |
| 2026-09-24 | normal | mistake | post-hook-before-output | Hook 时机与数据可用性 | mistakes.md | overdue mistake; repeated |
| 2026-09-24 | normal | mistake | todo-single-in-progress | Todo 计划状态约束 | mistakes.md | overdue mistake |
| 2026-09-24 | normal | mistake | tool-result-message-schema | SDK 间的工具结果消息结构适配 | mistakes.md | overdue mistake |
| 2026-09-26 | normal | concept | permission-pipeline | 工具执行前的权限管线 | concepts.md | overdue |
| 2026-09-27 | normal | mistake | todo-responsibility-boundaries | TodoWrite 的模块职责划分 | mistakes.md | overdue mistake; repeated |
| 2026-09-28 | normal | mistake | subagent-context-vs-workspace | Subagent 的消息隔离与共享工作目录 | mistakes.md | overdue mistake |
| 2026-09-29 | high | mistake | compact-pipeline-trigger-confusion | 上下文压缩管线的触发条件与顺序 | mistakes.md | overdue mistake; repeated |
| 2026-09-29 | normal | concept | context-compaction-priority | 上下文压缩的优先级与保真边界 | concepts.md | overdue |
| 2026-09-29 | normal | concept | hook-dispatch | Hook 注册、顺序与短路 | concepts.md | overdue |
| 2026-09-29 | normal | mistake | compact-output-archive | 大工具结果转存与删除的区别 | mistakes.md | overdue mistake |
| 2026-09-29 | normal | mistake | compact-vs-reactive-tail | 主动/阈值历史摘要与 API 错误补救的区别 | mistakes.md | overdue mistake |
| 2026-09-30 | normal | concept | multitenant-skill-governance | 多租户 Skill 的隔离、版本与授权 | concepts.md | overdue |
| 2026-10-01 | normal | concept | todo-integration-boundaries | TodoWrite 模块职责与接入边界 | concepts.md | overdue |
| 2026-10-01 | normal | concept | todo-plan-state | Todo 计划状态与不变量 | concepts.md | overdue |
| 2026-10-01 | normal | concept | todo-reminder-cadence | Todo reminder 计数节奏 | concepts.md | overdue |
| 2026-10-02 | normal | concept | subagent-context-boundary | Subagent 上下文隔离与共享副作用 | concepts.md | due today |
| 2026-10-02 | normal | mistake | agent-loop-vs-cli-loop | Agent Loop 的终止条件与 CLI 输入循环 | mistakes.md | mistake due today |
| 2026-10-03 | normal | concept | skill-catalog-lazy-loading | Skill 目录与按需全文加载 | concepts.md | scheduled review |
| 2026-10-05 | normal | concept | todo-input-validation | Todo 输入安全解析与校验 | concepts.md | scheduled review |
| 2026-10-09 | high | mistake | tool-call-result-compaction-boundary | 压缩时工具调用与结果的配对边界 | mistakes.md | scheduled mistake review; repeated |
| 2026-10-09 | normal | concept | openai-compatible-tool-loop | OpenAI-compatible 工具调用循环 | concepts.md | scheduled review |
