import os
from pathlib import Path

from dotenv import load_dotenv

# 所有文件路径以代码位置为基准，不依赖启动命令所在的目录。
RAG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RAG_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
DATA_SOURCE_DIR = PROJECT_ROOT / "data_source"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
MD5_PATH = PROJECT_ROOT / "md5.text"

load_dotenv(dotenv_path=ENV_PATH)

# 保留现有配置名，供上传、检索共用。
md5_path = str(MD5_PATH)
api_key=os.getenv("api_key")
base_url=os.getenv("base_url")
embedding_model= os.getenv("embedding_model")
chatting_model = os.getenv("chatting_model")

# Chroma
collection_name = "rag"
persist_directory = str(CHROMA_DIR)

# Spliter
chunk_size = 1000
new_after_n_chars = chunk_size * 0.85
chunk_overlap = 100
combine_text_under_n_chars = 200
separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
max_spliter_char_number = 1000

#
similarity_threshold = 2
