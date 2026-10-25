# RAG 路径与启动方式

路径统一在 `config.py` 配置，以该文件的位置确定项目根目录，不依赖当前工作目录。

| 用途 | 项目内位置 |
| --- | --- |
| 环境配置 | `.env` |
| 示例数据源 | `data_source/` |
| Chroma 数据库 | `chroma_db/` |
| 文件去重记录 | `md5.text` |

上传和检索共用数据库路径、集合名称和文件去重记录。上传文件当前直接解析，不额外保存原始文件。系统环境变量默认优先于 `.env`。

## 启动

当前代码使用同目录模块导入，建议按以下方式运行；替换成实际项目路径：

```bash
conda activate pythonProject
cd /你的项目路径/agentDemo/rag
python -m streamlit run app_file_uploader.py
```

另一个终端在相同环境中运行：

```bash
cd /你的项目路径/agentDemo/rag
python test_search.py
```

解析本地示例文件：

```bash
python load_data.py
```

也可使用脚本的绝对路径启动。不要直接用 `python rag.py` 测试问答：它目前只定义服务，没有调用入口。当前目录尚未整理成支持 `python -m rag.xxx` 的包结构。

## 数据维护

更换数据库时，需同步考虑对应的 MD5 记录；仅删除数据库却保留去重记录，可能让重新上传的文件被跳过。更改 embedding 模型或维度后，应重新建立对应索引。


## Agent 知识库工具

从项目根目录运行 `python -m AgentHarness.main`，可向 Agent 提问：

> 请使用知识库检索 RAG-Fusion 的优势，并引用文档来源和页码。

主 Agent 已注册 `search_knowledge(query, k=5)`，`k` 范围为 1–10。工具返回 JSON，
包含 `status`、`query` 和 `results`；每个结果包含 `content`、`source`、`page_number`
及 `truncated`。片段最多返回 2000 字符。没有片段时为 `no_results`；检索异常由 Agent
循环作为工具错误回传，与空结果区分。向量近邻结果不保证语义相关，Agent 仍需判断资料是否足以回答。

检索复用 `rag/model.py` 的 embedding 配置以及项目根目录的 Chroma 数据库，首次调用时
才初始化，不额外调用 RAG 问答模型。请先上传文件，并保持上传与检索的 embedding 配置一致。
检索内容作为参考资料处理，由主 Agent 根据证据生成回答和引用。

`rag.model` 与 `rag.vector_stores` 支持从项目根目录导入；原有在 `rag/` 下启动上传和
检索脚本的方式仍可使用。当前只向主 Agent 提供该工具，子 Agent 的工具集合保持原有配置。

离线验证（临时 Chroma 数据库及测试 embedding，不调用真实模型 API）：

```bash
api_key=test model=test python -B -m unittest discover -s tests -v
```
