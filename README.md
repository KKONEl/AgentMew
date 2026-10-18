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
api_key=your-api-key
base_url=https://your-provider.example/v1
model=your-chat-model
embedding_model=your-embedding-model
chatting_model=your-chat-model
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
