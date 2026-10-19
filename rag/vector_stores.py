from langchain_chroma import Chroma
from langchain_core.documents import Document
import config


class VectorStoreService(object):
    def __init__(self, embedding):
        """

        :param embedding: 嵌入模型
        """
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

    def get_retriever(self):
        """ 返回向量检索器"""
        return self.vector_store.as_retriever(search_kwargs={"k": config.similarity_threshold})


    def search(self, query: str, k: int = 5) -> list[Document]:
        """返回与问题最相关的 k 个片段，保留文本及元数据。"""
        return self.vector_store.similarity_search(query, k=k)