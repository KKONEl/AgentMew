# AgentMew / agentDemo

Python 学习项目，包含 Agent Harness 和 RAG 知识库实验。

## 目录

- `AgentHarness/`：Agent 循环、工具、任务、记忆、上下文压缩、团队、MCP、工作流和目标循环。
- `rag/`：文档解析、分块、向量存储、检索及 Streamlit 文件上传界面。
- `tests/`：Agent Harness 离线测试。
- [s13–s17 功能说明](AgentHarness/README_s13_s17.md)。

## 配置

在项目根目录创建 `.env`，配置所用服务的环境变量：

```dotenv
api_key=""
base_url="https://openrouter.ai/api/v1"
model="openrouter/free"
chatting_model="openrouter/free"
embedding_model="nvidia/nemotron-3-embed-1b:free"
```

使用时在本地填入 `api_key`。`model` 供 Agent Harness 使用，`chatting_model` 和 `embedding_model` 供 RAG 使用。

以下 RAG 参数在 `rag/config.py` 中配置；当前代码不会从 `.env` 读取这些参数：

```python
# RAG 文件去重记录
md5_path = "./md5.text"

# Chroma
collection_name = "rag"
persist_directory = "./chroma_db"

# 文档分块
chunk_size = 1000
new_after_n_chars = chunk_size * 0.85
chunk_overlap = 100
combine_text_under_n_chars = 200
separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
max_spliter_char_number = 1000

# 检索阈值
similarity_threshold = 2
```

`.env`、本地数据源、Chroma 数据库、去重记录、运行状态和 IDE 配置不纳入版本控制。
依赖需安装到 Python 环境；当前仓库尚未提供锁定版本的依赖清单。

## 运行

在已安装依赖的环境中，从项目根目录启动 Agent Harness：

```sh
python -m AgentHarness.main
```

RAG 模块使用同目录导入和相对数据路径，从 `rag/` 目录启动上传界面：

```sh
cd rag
streamlit run app_file_uploader.py
```

## 离线测试

从项目根目录运行：

```sh
api_key=test model=test python -B -m unittest discover -s tests -v
```

测试使用模拟模型，不调用真实模型 API；真实服务与 RAG 文档解析需要另行配置依赖及凭据。
