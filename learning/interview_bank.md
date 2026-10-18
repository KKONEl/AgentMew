# 面试题来源与阶段抽题规则

## 主来源

- 小林面试笔记：《2026 最全 AI 大模型面试题 | Agent 面试题 | AI 应用开发面试题》
- 入口：[xiaolincoding.com/project/xiaolinnote.html](https://www.xiaolincoding.com/project/xiaolinnote.html)
- 页面列出的专题：Agent、RAG、LLM 工具调用、大模型工程。页面当前列有 Agent 16 题、RAG 20 题、工具调用 16 题、大模型工程 22 题；目录可能更新，抽题时以网页最新目录为准。
- 定位：作为阶段性面试训练题库和延伸阅读入口，不替代当前项目代码、课程材料或已观察到的薄弱点。

## 阶段练习方式

1. 每完成一个学习阶段/主题模块，抽取 2–4 道相关题；若模块很小，至少 1 道。优先覆盖核心概念、项目实现和一个设计权衡。
2. 从与已学内容直接匹配的题目开始，结合当前项目追问“为什么这样设计”“失败或规模变化时会怎样”。题目所需知识尚未学习时，注明“拓展题”，不作为本阶段掌握判据。
3. 一次只呈现适量题目，先让用户独立回答，再逐点分析：正确依据、遗漏/含糊处、可迁移到项目的判断。不要先展示标准答案或要求背诵长文。
4. 将有价值的错误按 learning-coach 状态规则归并到错题；只有回答证据支持时才更新概念掌握状态。
5. 阶段题可以从网站目录抽取，也可改写为项目化追问；保留原题链接/专题以便回查，不复制整篇答案。

## 与当前学习路线的初步映射

按项目实际阶段灵活调整，不要求每个阶段覆盖整个专题。

| 项目学习主题 | 优先题库 | 可抽取的题目方向 |
|---|---|---|
| Agent Loop、Harness、规划与上下文管理 | Agent | Agent 核心组件；ReAct 实现；Workflow/Agent/Tools 区别；任务拆分；规划；记忆与压缩；手写 Agent 的取舍 |
| Function Calling、工具 schema/执行、安全与 MCP | LLM 工具调用 | Function Calling 原理；Schema 与执行链；MCP 组成及与 Function Calling/Skill 的边界；失败处理；网关 |
| Hooks、权限、工具治理、可观测性 | LLM 工具调用 + Agent | 工具调用的安全/治理追问；结合项目分析执行前后钩子、失败兜底与审计 |
| Subagent / Multi-Agent | Agent | Single-Agent 与 Multi-Agent 设计；任务拆分、协作与动态切换；上下文隔离、共享状态和失败恢复 |
| Skill Loading / Tooling 扩展 | LLM 工具调用 | Skill 是什么；Skill、MCP、Function Calling 的区别；结合当前注册表、按需加载和权限边界追问 |
| Context Compact / 长上下文阶段 | Agent + 大模型工程（应用相关） | Agent 记忆压缩；长短期记忆；KV Cache / Prompt Caching（拓展，按本阶段教学范围取舍） |
| RAG 阶段（进入后） | RAG | 完整流程、Chunking、Embedding、混合检索、Query Rewrite、评估、更新与幻觉治理 |
| 模型与推理工程（进入后） | 大模型工程 | 优先 Prompt、解码参数、幻觉、KV Cache、部署选型；训练/对齐等偏算法内容按目标岗位选作拓展 |

## 当前安排

- 当前项目已完成 s07 Skill Loading，接下来从 s08 Context Compact 学习。
- s08 完成时安排 Agent 记忆/压缩相关面试题，并结合 `agent_loop.py` 与上下文构造流程做分析；KV Cache 可作为区分模型推理缓存与应用层对话压缩的拓展追问。
- 之后每个阶段结束都执行上述抽题回路；若用户在阶段中明确要求面试模拟，也可提前抽题。
