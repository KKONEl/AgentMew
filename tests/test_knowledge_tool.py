import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from AgentHarness import tools


class KnowledgeToolTests(unittest.TestCase):
    def setUp(self):
        self.assertIn('search_knowledge', tools.TOOL_HANDLERS)
        self.search = tools.TOOL_HANDLERS['search_knowledge']

    def search_with(self, docs, query='RAG 是什么', k=5):
        service = SimpleNamespace(search=lambda query, k: docs)
        with patch('AgentHarness.knowledge_tool._get_vector_service', return_value=service):
            return json.loads(self.search(query=query, k=k))

    def test_search_returns_citable_evidence(self):
        result = self.search_with([
            SimpleNamespace(page_content='检索增强生成', metadata={'source': '指南.pdf', 'page_number': 3}),
            SimpleNamespace(page_content='第二段', metadata={}),
        ])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['results'][0], {
            'content': '检索增强生成', 'source': '指南.pdf', 'page_number': 3, 'truncated': False,
        })
        self.assertIsNone(result['results'][1]['page_number'])
        self.assertEqual(result['results'][1]['source'], '未知')

    def test_empty_results_are_explicit(self):
        result = self.search_with([])
        self.assertEqual(result['status'], 'no_results')
        self.assertEqual(result['results'], [])

    def test_invalid_arguments_do_not_initialize_rag(self):
        with patch('AgentHarness.knowledge_tool._get_vector_service', side_effect=AssertionError('must not initialize')):
            for query, k in [('', 5), ('  ', 5), (None, 5), ('q', 0), ('q', 11), ('q', True), ('q', 1.5)]:
                with self.subTest(query=query, k=k), self.assertRaises(ValueError):
                    self.search(query=query, k=k)

    def test_long_content_is_bounded_and_marked(self):
        result = self.search_with([SimpleNamespace(page_content='中' * 3000, metadata={})])
        self.assertEqual(len(result['results'][0]['content']), 2000)
        self.assertTrue(result['results'][0]['truncated'])

    def test_query_and_limit_reach_retrieval(self):
        def retrieve(query, k):
            return [SimpleNamespace(page_content=f'{query}:{k}', metadata={})]
        with patch('AgentHarness.knowledge_tool._get_vector_service', return_value=SimpleNamespace(search=retrieve)):
            result = json.loads(self.search('  索引  ', 2))
        self.assertEqual(result['results'][0]['content'], '索引:2')

    def test_agent_receives_evidence_in_matching_tool_message(self):
        from AgentHarness import agent_loop
        from test_s13_s17 import FakeClient, FakeMessage, fake_call
        client = FakeClient([
            FakeMessage('', [fake_call('search_knowledge', {'query': 'RAG'}, 'search-1')]),
            FakeMessage('根据指南.pdf 第 3 页回答'),
        ])
        messages = [{'role': 'user', 'content': '从知识库查 RAG'}]
        service = SimpleNamespace(search=lambda query, k: [
            SimpleNamespace(page_content='检索增强生成', metadata={'source': '指南.pdf', 'page_number': 3})])
        with patch('AgentHarness.knowledge_tool._get_vector_service', return_value=service), \
                patch.object(agent_loop, 'client', client), \
                patch.object(agent_loop.COMPACTOR, 'prepare', side_effect=lambda m, _: m), \
                patch.object(agent_loop, 'trigger_hooks', return_value=None), \
                patch.object(agent_loop, 'extract_memories', return_value=False), \
                patch.object(agent_loop.GOAL, 'after_turn', return_value=('allow', '')):
            agent_loop.agent_loop(messages)
        self.assertIn('search_knowledge', client.tool_names[0])
        result = next(m for m in messages if m['role'] == 'tool')
        self.assertEqual(result['tool_call_id'], 'search-1')
        self.assertEqual(json.loads(result['content'])['results'][0]['source'], '指南.pdf')
        self.assertEqual(messages[-1]['content'], '根据指南.pdf 第 3 页回答')

    def test_retrieval_failure_is_tool_error_not_empty_results(self):
        with patch('AgentHarness.knowledge_tool._get_vector_service', side_effect=RuntimeError('database unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'database unavailable'):
                self.search('RAG')
