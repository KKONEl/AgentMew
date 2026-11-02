import unittest
from pathlib import Path
import importlib.util
import tempfile
import json

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).with_name('build.py')
        if path.exists():
            spec=importlib.util.spec_from_file_location('course_build',path)
            cls.b=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.b)
        else: cls.b=None
    def test_markdown_link_becomes_relative_local_page(self):
        self.assertIsNotNone(self.b,'静态生成器尚未实现')
        out=self.b.render_markdown('[下一课](RAG核心知识与面试题.md)', '通用知识/Agentic RAG与GraphRAG深度解析.md', 'library/example.html')
        self.assertNotIn('.md"',out)
        self.assertIn('.html',out)
    def test_code_is_text_and_remote_image_does_not_load(self):
        self.assertIsNotNone(self.b,'静态生成器尚未实现')
        out=self.b.render_markdown('```html\n<script>alert(1)</script>\n```\n\n![badge](https://example.com/a.svg)\n<script>alert(2)</script>', 'README.md','index.html')
        self.assertIn('&lt;script&gt;',out)
        self.assertNotIn('<script>',out)
        self.assertNotIn('src="https:',out)
    def test_diagram_includes_accessible_step_controls(self):
        self.assertIsNotNone(self.b,'静态生成器尚未实现')
        out=self.b.diagram_html({'nodes':['问题','证据','回答'],'caption':'测试流程'})
        self.assertIn('<svg',out)
        self.assertIn('data-step',out)
        self.assertIn('data-play',out)
        self.assertIn('aria-label',out)
    def test_missing_evidence_url_is_not_a_local_link(self):
        self.assertIsNotNone(self.b)
        out=self.b.evidence_link(None)
        self.assertNotIn('href=',out)
        self.assertIn('未提供来源',out)
        self.assertIn('href="https://example.com/a"',self.b.evidence_link('https://example.com/a'))
    def test_playback_has_visible_concrete_data_not_only_svg_highlights(self):
        lesson=json.loads((Path(__file__).parent/'lessons/07-rag-basics.json').read_text())
        out=self.b.diagram_html(lesson['diagram'])
        self.assertIn('data-flow-frame',out)
        self.assertIn('data-flow-input',out)
        self.assertIn('500',out)
        self.assertIn('data-flow-case',out)
        self.assertIn('data-prev',out)
    def test_every_lesson_has_normal_and_failure_walkthroughs(self):
        for p in (Path(__file__).parent/'lessons').glob('*.json'):
            lesson=json.loads(p.read_text())
            self.assertIn('walkthrough',lesson['diagram'],p.name)
            cases=lesson['diagram']['walkthrough']['cases']
            self.assertEqual(len(cases),2,p.name)
            self.assertGreaterEqual(len(cases[0]['steps']),5,p.name)
            self.assertIsInstance(cases[1]['steps'][-1]['failure'],bool,p.name)
            for case in cases:
                for step in case['steps']:
                    for key in ('input','action','output','state'):
                        self.assertTrue(step[key],(p.name,key))
    def test_each_step_links_to_an_existing_explanation_and_real_code(self):
        import re
        for p in (Path(__file__).parent/'lessons').glob('*.json'):
            l=json.loads(p.read_text());headings=re.findall(r'^## (.+)$',l['body'],re.M)
            self.assertIn('alignment',l,p.name)
            self.assertIn(l['alignment']['insert_after'],headings,p.name)
            self.assertEqual(len(l['alignment']['question_sections']),len(l['questions']),p.name)
            for title in l['alignment']['question_sections']:self.assertIn(title,headings,p.name)
            code=l['lab']['code'].splitlines()
            for case in l['diagram']['walkthrough']['cases']:
                self.assertTrue(case['basis'],p.name)
                for step in case['steps']:
                    self.assertIn(step['section'],headings,p.name)
                    self.assertTrue(step['why'],p.name)
                    start,end=step['code_lines']
                    self.assertTrue(1<=start<=end<=len(code),(p.name,start,end))
                for number in case.get('code_overrides',{}):self.assertTrue(1<=int(number)<=len(code),p.name)
    def test_case_follows_explanation_and_code_precedes_exercises(self):
        l=json.loads((Path(__file__).parent/'lessons/07-rag-basics.json').read_text())
        captured={};old=self.b.write
        try:
            self.b.write=lambda path,body:captured.update({path:body})
            self.b.lesson_page(l,[l])
        finally:self.b.write=old
        result=captured['lessons/'+l['slug']+'.html']
        self.assertIn('id="case-study"',result)
        self.assertLess(result.index('id="已解例同一个数字为什么有三个条件"'),result.index('id="case-study"'))
        self.assertLess(result.index('id="case-study"'),result.index('id="lab"'))
        self.assertLess(result.index('id="lab"'),result.index('id="exercises"'))
        self.assertIn('data-linked-code',result)
        self.assertIn('id="lab-line-7"',result)

if __name__=='__main__': unittest.main()
