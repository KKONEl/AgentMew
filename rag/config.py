
from dotenv import load_dotenv
import os

load_dotenv()

md5_path = "./md5.text"
api_key=os.getenv("api_key")
base_url=os.getenv("base_url")
embedding_model= os.getenv("embedding_model")
chatting_model = os.getenv("chatting_model")

# Chroma
collection_name = "rag"
persist_directory = "./chroma_db"

# Spliter
chunk_size = 1000
chunk_overlap = 100
separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
max_spliter_char_number = 1000

#
similarity_threshold = 2
