"""Exercise the tool against a real temporary Chroma collection, without API calls."""
import json
import tempfile
import unittest
from unittest.mock import patch

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from AgentHarness.knowledge_tool import search_knowledge
from rag import config
from rag.vector_stores import VectorStoreService


class OfflineEmbedding(Embeddings):
    def embed_documents(self, texts):
        return [[1.0, 0.0] if 'RAG' in text else [0.0, 1.0] for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class KnowledgeStoreTests(unittest.TestCase):
    def test_tool_retrieves_from_shared_store_with_sources(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(config, 'persist_directory', directory), \
                patch.object(config, 'collection_name', 'test_knowledge'):
            uploaded = VectorStoreService(embedding=OfflineEmbedding())
            uploaded.vector_store.add_documents([
                Document(page_content='RAG 检索增强生成', metadata={'source': 'guide.pdf', 'page_number': 7}),
                Document(page_content='其他主题', metadata={'source': 'other.txt'}),
            ])
            retrieved = VectorStoreService(embedding=OfflineEmbedding())
            with patch('AgentHarness.knowledge_tool._get_vector_service', return_value=retrieved):
                result = json.loads(search_knowledge('RAG', k=1))
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(len(result['results']), 1)
            self.assertEqual(result['results'][0]['content'], 'RAG 检索增强生成')
            self.assertEqual(result['results'][0]['source'], 'guide.pdf')
            self.assertEqual(result['results'][0]['page_number'], 7)
