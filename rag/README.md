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
