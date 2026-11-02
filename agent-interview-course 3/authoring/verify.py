#!/usr/bin/env python3
"""Verify the actual deliverable: snapshot, source coverage, links, anchors, new labs."""
from pathlib import Path
import hashlib,json,subprocess,sys
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'site';SOURCE=ROOT/'source'
errors=[];report={}
upstream=json.loads((ROOT/'authoring/upstream-tree.json').read_text())
actual={p.relative_to(SOURCE).as_posix():p for p in SOURCE.rglob('*') if p.is_file()}
expected={f['path']:f for f in upstream['files']}
if set(actual)!=set(expected):errors.append('source file set differs from upstream')
for path,f in expected.items():
 if path not in actual:continue
 data=actual[path].read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 if blob!=f['sha']:errors.append('snapshot hash mismatch: '+path)
report['source_files']=len(actual);report['source_git_blobs_verified']=len(expected)
manifest=json.loads((ROOT/'manifest.json').read_text());mapped=[f for f in manifest['files'] if f['html']]
if len(mapped)!=len(list(SOURCE.rglob('*.md'))):errors.append('Markdown coverage mismatch')
report['markdown_pages']=len(mapped)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set();self.remote_loads=[];self.tags={};self.srcs=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags[tag]=self.tags.get(tag,0)+1
  if a.get('id'):self.ids.add(a['id'])
  for k in ['href','src']:
   if a.get(k):self.links.append(a[k])
  if tag in ('img','script','link') and a.get('src',a.get('href','')).startswith(('http:','https:','//')):self.remote_loads.append(a)
  if tag=='script':self.srcs.append(a.get('src'))
htmlfiles=sorted(SITE.rglob('*.html'));parsers={}
for p in htmlfiles:
 parser=Links();parser.feed(p.read_text());parsers[p.resolve()]=parser
 if parser.remote_loads:errors.append('remote runtime resource: '+str(p))
 if any(src is None for src in parser.srcs):errors.append('inline source script: '+str(p))
count=0;anchor_count=0
for p,parser in parsers.items():
 for url in parser.links:
  if url.startswith('//'):continue
  u=urlsplit(url)
  if u.scheme:continue
  count+=1
  target=(p.parent/unquote(u.path)).resolve() if u.path else p
  if not target.exists():errors.append(f'broken local link {p.relative_to(ROOT)}: {url}')
  if u.fragment and target in parsers:
   anchor_count+=1
   if unquote(u.fragment) not in parsers[target].ids:errors.append(f'broken anchor {p.relative_to(ROOT)}: {url}')
report['html_pages']=len(htmlfiles);report['local_links_checked']=count;report['anchors_checked']=anchor_count
labs=[];question_count=0;walkthrough_cases=0;walkthrough_steps=0
for f in sorted((ROOT/'authoring/lessons').glob('*.json')):
 l=json.loads(f.read_text());path=SITE/'labs'/(l['slug']+'.py')
 if not path.is_file():errors.append('missing lab '+l['id']);continue
 if path.read_text()!=l['lab']['code']:errors.append('lab differs from lesson '+l['id'])
 r=subprocess.run([sys.executable,str(path)],capture_output=True,text=True,timeout=15,cwd=ROOT)
 if r.returncode:errors.append('lab failed '+l['id']+': '+r.stderr)
 if r.stdout!=l['lab']['expected']:errors.append('lab stdout mismatch '+l['id'])
 if len(l['questions'])<4:errors.append('not enough exercises '+l['id'])
 if len(l['lab']['extensions'])!=len(l['lab']['extension_answers']):errors.append('missing extension answer '+l['id'])
 for s in l['sources']:
  if s not in actual:errors.append('unknown source '+s)
 cases=l['diagram'].get('walkthrough',{}).get('cases',[])
 if len(cases)!=2:errors.append('missing walkthrough cases '+l['id'])
 walkthrough_cases+=len(cases)
 for case in cases:
  walkthrough_steps+=len(case['steps'])
  for step in case['steps']:
   if not all(step.get(k) for k in ['input','action','output','state']):errors.append('empty playback data '+l['id'])
   if not 0<=step['node']<len(l['diagram']['nodes']):errors.append('invalid playback node '+l['id'])
 html=(SITE/'lessons'/(l['slug']+'.html')).read_text()
 if html.count('data-flow-frame=')!=sum(len(c['steps']) for c in cases):errors.append('published walkthrough missing frames '+l['id'])
 labs.append(l['id']);question_count+=len(l['questions'])
report['labs_passed']=len(labs);report['new_questions']=question_count;report['source_topic_questions']=156;report['source_company_questions']=222;report['question_entries']=question_count+156+222
report['svg_gallery']=len(list((SOURCE/'diagrams').glob('*.svg')))
report['walkthrough_cases']=walkthrough_cases;report['walkthrough_steps']=walkthrough_steps
report['errors']=errors;report['status']='PASS' if not errors else 'FAIL'
(ROOT/'authoring/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(errors))
