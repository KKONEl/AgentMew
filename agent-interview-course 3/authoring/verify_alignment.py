"""Check teaching alignment against published code; exercise only authored standard-library labs."""
from pathlib import Path
from html.parser import HTMLParser
import json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
class CodeReader(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.link_at=None;self.pre=None;self.in_code=False;self.text=[];self.snippets=[];self.full=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t not in {'br','hr','img','input','meta','link'}:self.depth+=1
  if 'data-linked-code' in a:self.link_at=self.depth
  if t=='pre' and 'numbered-code' in a.get('class',''):
   self.pre='snippet' if self.link_at is not None else 'full';self.text=[]
  if t=='code' and self.pre:self.in_code=True
 def handle_endtag(self,t):
  if t=='code':self.in_code=False
  if t=='pre' and self.pre:
   (self.snippets if self.pre=='snippet' else self.full).append(''.join(self.text));self.pre=None
  if self.link_at==self.depth:self.link_at=None
  self.depth-=1
 def handle_data(self,d):
  if self.in_code:self.text.append(d)
report={'lessons':0,'linked_frames':0,'boundary_programs_executed':0,'errors':[],'variants':[]}
for f in sorted((ROOT/'authoring/lessons').glob('*.json')):
 l=json.loads(f.read_text());code=l['lab']['code'];page=ROOT/'site/lessons'/(l['slug']+'.html')
 parser=CodeReader();parser.feed(page.read_text())
 expected=[];heads=re.findall(r'^## (.+)$',l['body'],re.M)
 for case in l['diagram']['walkthrough']['cases']:
  lines=code.splitlines()
  for n,s in case.get('code_overrides',{}).items():lines[int(n)-1]=s
  for frame in case['steps']:
   a,b=frame['code_lines'];expected.append('\n'.join(lines[a-1:b])+'\n')
   assert frame['section'] in heads
  if case.get('code_overrides'):
   run=subprocess.run([sys.executable,'-c','\n'.join(lines)+'\n'],capture_output=True,text=True,timeout=15,cwd=ROOT)
   report['boundary_programs_executed']+=1
   report['variants'].append(dict(lesson=l['id'],returncode=run.returncode,stdout=run.stdout,exception=run.stderr.strip().splitlines()[-1] if run.stderr.strip() else None))
 if parser.snippets!=expected:report['errors'].append('snippet mismatch '+l['id'])
 if parser.full!=[code.rstrip('\n')+'\n']:report['errors'].append('full code mismatch '+l['id'])
 if (ROOT/'site/labs'/(l['slug']+'.py')).read_text()!=code:report['errors'].append('download mismatch '+l['id'])
 if page.read_text().find('id="case-study"')>page.read_text().find('id="lab"'):report['errors'].append('case/code ordering '+l['id'])
 if page.read_text().find('id="lab"')>page.read_text().find('id="exercises"'):report['errors'].append('code/exercise ordering '+l['id'])
 report['lessons']+=1;report['linked_frames']+=len(expected)
report['status']='PASS' if not report['errors'] else 'FAIL'
(ROOT/'authoring/alignment-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='variants'},ensure_ascii=False,indent=2));sys.exit(bool(report['errors']))
