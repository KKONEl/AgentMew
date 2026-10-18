"""
知识库
"""
import os
from datetime import datetime

from langchain_core.documents import Document
from unstructured.chunking.title import chunk_by_title

import config
import hashlib
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.auto import partition

from model import embedding


def check_md5(md5_str :str):
    if not os.path.isfile(config.md5_path):
        open(config.md5_path, 'w',encoding='utf-8').close()
        return False
    else :
        for line in open(config.md5_path,'r',encoding='utf-8').readlines():
            line = line.strip()
            if line == md5_str:
                return True
        return False

def save_md5(md5_str : str):
    with open(config.md5_path,'a',encoding='utf-8') as f:
         f.write(md5_str + "\n")

def get_md5(input_str : str,encoding='utf-8'):
    str_bytes =  input_str.encode(encoding=encoding)
    return hashlib.md5(str_bytes).hexdigest()

class KnowledgeBaseService(object):
    def __init__(self):
        os.makedirs(config.persist_directory,exist_ok=True)
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function = embedding,
            persist_directory=config.persist_directory
        ) # Chroma向量数据库对象
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        ) # 文本分割器

    def upload_by_str(self,data:str,filename):
        md5_hex = get_md5(data)
        if check_md5(md5_hex):
            return f"跳过{filename}已经存在在数据库中"
        if len(data) > config.max_spliter_char_number:
            knowledge_chunks : list[str] = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        meta_data = {
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator":"test"
        }

        self.chroma.add_texts(
            knowledge_chunks,
            metadatas=[meta_data for _ in knowledge_chunks]
        )

        save_md5(md5_hex)
        return f"{filename} success into 向量数据库"

    def upload_file(self,file,filename,filetype):
        elements = partition(
            file=file,
            metadata_filename=filename,
            content_type=filetype
        )

        chunks = chunk_by_title(
            elements,
            max_characters=config.chunk_size,
            new_after_n_chars=config.new_after_n_chars,
            combine_text_under_n_chars=config.combine_text_under_n_chars
        )
        #  转换为 Document
        documents = []
        for chunk in chunks:
            metadata = {
                "source": filename,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operator": "test"
            }
            if chunk.metadata.page_number is not None:
                metadata["page_number"] = chunk.metadata.page_number
            documents.append(
                Document(
                    page_content=chunk.text,
                    metadata=metadata
                )
            )
        # 4. 存入 Chroma
        if documents:
            self.chroma.add_documents(documents)
        return f"{filename} success into 向量数据库"