# 学习状态模型

`learning/` 中的 Markdown 是唯一学习状态来源。保持人类可读、Git 友好、短小。未知信息留空，不用推测填充。

## 文件职责

- `profile.md`：稳定背景、目标、已观察到的偏好与教学调整；不存每轮流水账。
- `progress.md`：当前焦点、下一步和精简的学习事件日志。
- `concepts.md`：每个概念一行的结构化掌握状态。
- `mistakes.md`：长期有价值的错误心智模型；每个错误一个条目。
- `review_queue.md`：由脚本根据概念和错题生成的待复习视图。
- `skill_feedback.md`：有明显信号时记录教学机制的效果。
- `archive/`：只存被保守归档的旧记录。

## 概念状态

允许值：

- `new`：已纳入计划，但尚无学习证据。
- `learning`：已接触，尚不能稳定独立使用。
- `weak`：答错、解释含糊、依赖较强提示或重复犯错。
- `understood`：至少两次在不同题型或情境中独立正确。
- `mastered`：跨至少 14 天有三次高质量回忆，并包含迁移或项目应用。

`concepts.md` 固定列：

| 字段 | 规则 |
|---|---|
| `id` | 稳定、小写 kebab-case；同义概念合并 |
| `topic` | 简短的人类可读名称 |
| `status` | 上述五种状态之一 |
| `confidence` | 0–5；表示有证据支持的独立性，不是情绪评分 |
| `first_seen` | 首次进入学习的日期 |
| `last_review` | 最近一次有效回忆或应用日期 |
| `review_count` | 有实际作答/应用的复习次数 |
| `success_streak` | 连续质量分 ≥4 的次数 |
| `interval_days` | 当前计划间隔；允许按证据调整 |
| `next_review` | 下次复习日期；无需复习时留空 |
| `related_project` | 相关文件、符号或项目场景，多个用 `<br>` |
| `common_mistakes` | 相关 mistake ID，多个用逗号 |
| `notes` | 一句话证据或边界，不写长教程 |

## 错题条目

只有会影响未来判断、设计或实现的错误才记录。错题 ID 使用稳定 kebab-case。每条包含：

- `topic`
- `question`
- `incorrect_model`
- `correct_model`
- `minimal_example`
- `cause`
- `repeat_count`
- `first_seen`
- `last_seen`
- `last_review`
- `next_review`
- `priority`：`low` / `normal` / `high` / `critical`
- `status`：`open` / `monitoring` / `resolved`
- `related_concept`
- `related_project`

同一根因再次出现：更新原条目的上下文、`repeat_count`、`last_seen`、`priority` 与 `next_review`。不要按题目表面差异制造重复条目。只有在新错误具有不同根因时才新建。

## 进度与反馈

进度日志只记录有决策价值的事件：学了什么、证据如何、下一步是什么。多次细碎事件可以合并成一条阶段摘要。

`skill_feedback.md` 只在出现明显信号时更新，例如用户明确觉得解释过长、练习难度不合适，或同一种教学方式连续有效/无效。记录证据和下一次调整，不推断性格。

## 体积控制

- 优先更新而不是追加。
- 概念 `notes` 保持一句话；详细知识属于代码、文档或课程回答，不属于状态文件。
- 每 20–30 条进度事件合并旧记录为阶段摘要。
- 只有 `mastered`/`resolved`、无待复习日期且长期未活动的记录才可归档。
- 归档前运行校验；归档动作必须可通过 Git 或 archive 文件恢复。

