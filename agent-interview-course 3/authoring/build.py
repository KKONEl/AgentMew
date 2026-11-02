#!/usr/bin/env python3
"""Build offline, dependency-free-at-reading-time study HTML from retained content."""
import hashlib,html,json,os,posixpath,re,shutil
from pathlib import Path
from urllib.parse import quote,unquote,urlsplit
from html.parser import HTMLParser
import markdown
from markdown.extensions.toc import slugify_unicode

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source'; SITE=ROOT/'site'; CONTENT=ROOT/'authoring'/'lessons'
SHA='e5b92617455e5ecc105162a22a42796c3041162d'
REPO='https://github.com/Zchary1106/agent-interview-hub'
MD_FILES=sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*.md'))
DOC_MAP={p:f'library/doc-{i:03}.html' for i,p in enumerate(MD_FILES,1)}
E=lambda s:html.escape(str(s),quote=True)

def relative(target,current):
    return quote(posixpath.relpath(target,posixpath.dirname(current) or '.'),safe='/.-_')

def local_url(url,src,current):
    parts=urlsplit(html.unescape(url)); path=unquote(parts.path)
    if parts.scheme in ('http','https'):
        prefix=f'/Zchary1106/agent-interview-hub/blob/{SHA}/'
        prefixes=[prefix,'/Zchary1106/agent-interview-hub/blob/main/','/Zchary1106/agent-interview-hub/tree/main/']
        if parts.netloc=='github.com' and any(path.startswith(p) for p in prefixes):
            prefix=next(p for p in prefixes if path.startswith(p)); target=path[len(prefix):]
        elif parts.netloc=='raw.githubusercontent.com' and path.startswith('/Zchary1106/agent-interview-hub/'):
            target='/'.join(path.split('/')[4:])
        else: return url
    elif parts.scheme: return url if parts.scheme in ('mailto',) else '#'
    elif not path: return '#'+quote(unquote(parts.fragment),safe='-_.') if parts.fragment else '#'
    else: target=posixpath.normpath(posixpath.join(posixpath.dirname(src),path))
    if target in DOC_MAP:
        result=relative(DOC_MAP[target],current)
    elif (SOURCE/target).is_file() and not target.startswith('../'):
        result=relative('../source/'+target,current)
    elif (SOURCE/target).is_dir() and not target.startswith('../'):
        readme=posixpath.join(target,'README.md').lstrip('./')
        result=relative(DOC_MAP.get(readme,'coverage.html'),current)
    else: return REPO+'/blob/'+SHA+'/'+quote(target,safe='/')+('#'+parts.fragment if parts.fragment else '')
    if parts.fragment: result+='#'+quote(unquote(parts.fragment),safe='-_.')
    return result

class SafeHTML(HTMLParser):
    allowed={'p','br','hr','h1','h2','h3','h4','h5','h6','a','img','strong','em','b','i','del','s','code','pre','blockquote','ul','ol','li','table','thead','tbody','tr','th','td','details','summary','div','span','dl','dt','dd','sup','sub','kbd'}
    void={'br','hr','img'}
    def __init__(self,src,current):
        super().__init__(convert_charrefs=False); self.src=src;self.current=current;self.out=[];self.block=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','iframe','object'}: self.block+=1;return
        if self.block or tag not in self.allowed:return
        a=dict(attrs)
        if tag=='img' and urlsplit(a.get('src','')).scheme:
            self.out.append('<span class="remote-asset">[在线图片：'+E(a.get('alt',''))+']</span>');return
        safe=[]
        for k,v in attrs:
            if k in {'id','class','title','alt','colspan','rowspan','start','open','align'}:
                safe.append((k,v or ''))
            elif k in {'href','src'}:
                safe.append((k,local_url(v or '',self.src,self.current)))
        if tag=='img':safe.extend([('loading','lazy'),('decoding','async')])
        if tag=='a' and urlsplit(dict(safe).get('href','')).scheme in {'http','https'}:safe.append(('rel','noreferrer'))
        self.out.append('<'+tag+''.join(' '+k+'="'+E(v)+'"' for k,v in safe)+'>')
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag in {'script','style','iframe','object'}:
            self.block=max(0,self.block-1);return
        if not self.block and tag in self.allowed and tag not in self.void:self.out.append('</'+tag+'>')
    def handle_data(self,data):
        if not self.block:self.out.append(html.escape(data,quote=False))
    def handle_entityref(self,name):
        if not self.block:self.out.append('&'+name+';')
    def handle_charref(self,name):
        if not self.block:self.out.append('&#'+name+';')

def render_markdown(text,src='README.md',current='index.html'):
    rendered=markdown.markdown(text,extensions=['fenced_code','tables','toc','sane_lists'],extension_configs={'toc':{'slugify':slugify_unicode,'permalink':False}})
    parser=SafeHTML(src,current);parser.feed(rendered);return ''.join(parser.out)

def diagram_html(diagram,lesson=None):
    nodes=diagram['nodes']; n=len(nodes); width=960; gap=12; cell=(width-24-gap*(n-1))/n
    svg=['<svg viewBox="0 0 960 '+('152' if diagram.get('loop') else '112')+'" role="img" aria-label="'+E(diagram['caption'])+'"><title>'+E(diagram['caption'])+'</title><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#7a8d99"/></marker></defs>']
    for i,label in enumerate(nodes):
        x=12+i*(cell+gap)
        if i<n-1:svg.append(f'<path d="M{x+cell},55 H{x+cell+gap-2}" stroke="#7a8d99" marker-end="url(#arr)"/>')
        svg.append(f'<g class="flow-node" data-node="{i}"><rect x="{x}" y="17" width="{cell}" height="75" rx="10"/><text x="{x+cell/2}" y="40" class="flow-number">{i+1:02}</text><text x="{x+cell/2}" y="67">{E(label)}</text></g>')
    if diagram.get('loop'):
        loop=diagram['loop'];x1=12+loop['from']*(cell+gap)+cell/2;x2=12+loop['to']*(cell+gap)+cell/2
        svg.append(f'<path d="M{x1},94 V126 H{x2} V96" fill="none" stroke="#b18043" stroke-dasharray="5 4" marker-end="url(#arr)"/><text x="{(x1+x2)/2}" y="146" style="fill:#936b33;font-size:12px">{E(loop["label"])}</text>')
    svg.append('</svg>')
    walkthrough=diagram.get('walkthrough')
    if not walkthrough:
        return '<figure class="flow" data-flow><div class="flow-scroll">'+''.join(svg)+'</div><figcaption>'+E(diagram['caption'])+'</figcaption><div class="controls"><button type="button" data-step>下一步</button><button type="button" data-play>播放</button><button type="button" data-reset>重置</button><span data-flow-status aria-live="polite">尚未开始</span></div></figure>'
    controls='<div class="flow-settings"><label>演示场景 <select data-flow-case aria-label="选择演示场景">'+''.join('<option value="'+E(c['id'])+'">'+E(c['label'])+'</option>' for c in walkthrough['cases'])+'</select></label><label>播放速度 <select data-flow-speed aria-label="选择播放速度"><option value="7000">慢速 · 每步7秒</option><option value="4000">中速 · 每步4秒</option><option value="2000">快速 · 每步2秒</option></select></label></div><div class="controls"><button type="button" data-prev disabled>上一步</button><button type="button" data-step>下一步</button><button type="button" data-play aria-pressed="false">播放演示</button><button type="button" data-reset>从头开始</button></div>'
    panels=[];transcript=[]
    for ci,case in enumerate(walkthrough['cases']):
        panels.append('<div data-flow-case-panel="'+E(case['id'])+'"'+(' hidden' if ci else '')+'><p class="flow-case-basis">'+E(case.get('basis',''))+'</p>')
        transcript.append('<h4>'+E(case['label'])+'</h4><ol>')
        for i,s in enumerate(case['steps']):
            panels.append('<section class="flow-frame '+('flow-failure' if s.get('failure') else '')+'" data-flow-frame="'+str(i)+'" data-node-index="'+str(s['node'])+'" data-failure="'+str(bool(s.get('failure'))).lower()+'"'+(' hidden' if i else '')+'><div class="flow-frame-head"><span>步骤 '+str(i+1)+' / '+str(len(case['steps']))+'</span><h3>'+E(s['title'])+'</h3></div><div class="flow-lane" aria-hidden="true"><span>输入</span><i class="flow-packet">数据</i><span>处理</span><span>输出</span></div><div class="flow-cards"><div data-flow-input><h4>① 输入什么</h4><p>'+E(s['input'])+'</p></div><div><h4>② 这一刻做什么</h4><p>'+E(s['action'])+'</p></div><div class="flow-output"><h4>③ 得到什么</h4><p>'+E(s['output'])+'</p></div></div><div class="flow-state"><strong>状态快照</strong><code>'+E(s['state'])+'</code></div></section>')
            if lesson is not None:
                refs=lesson['_section_ids'];section=s['section'];a,b=s['code_lines'];lines=lesson['lab']['code'].splitlines()
                edits=case.get('code_overrides',{})
                for number,line in edits.items():lines[int(number)-1]=line
                excerpt='\n'.join(lines[a-1:b])
                related='<div class="flow-concept"><p><strong>为什么这样做：</strong>'+E(s['why'])+'</p><a href="#'+quote(refs[section])+'">回看这一段原理：'+E(section)+'</a></div>'
                label='对应变式代码' if edits else '对应下方参考程序'
                related+='<div class="flow-linked-code" data-linked-code><h4>'+label+' · 第'+str(a)+'—'+str(b)+'行</h4><pre class="numbered-code"><code>'+code_html(excerpt,start=a)+'</code></pre>'
                if edits:related+='<p class="variant-notice">本分支改动：'+E('；'.join('第'+str(n)+'行 → '+line for n,line in edits.items()))+'。下方完整代码仍为正常版本。</p>'
                related+='<a href="#lab-line-'+str(a)+'">在完整程序中找到第'+str(a)+'行 →</a></div>'
                panels[-1]=panels[-1].removesuffix('</section>')+related+'</section>'
            transcript.append('<li><strong>'+E(s['title'])+'</strong><p>输入：'+E(s['input'])+'<br>处理：'+E(s['action'])+'<br>输出：'+E(s['output'])+'</p><code>'+E(s['state'])+'</code></li>')
        panels.append('</div>');transcript.append('</ol>')
    initial=walkthrough['cases'][0]['steps']
    return '<figure class="flow flow-walkthrough" data-flow><div class="eyebrow">STEP-BY-STEP / 可视化步骤演示</div><p class="flow-scenario">'+E(walkthrough['scenario'])+'</p><p class="flow-disclaimer">先看输入和输出，再看“为什么”与对应代码行。按下一步或播放观察变化；这是代码机制回放，不是视频。</p><div class="flow-scroll">'+''.join(svg)+'</div><figcaption>'+E(diagram['caption'])+'</figcaption>'+controls+'<div class="flow-meter"><progress data-flow-progress max="'+str(len(initial))+'" value="1" aria-label="步骤进度"></progress><span data-flow-status role="status">第 1/'+str(len(initial))+' 步：'+E(initial[0]['title'])+'</span></div>'+''.join(panels)+'<details class="flow-transcript"><summary>展开全部步骤文字（不播放也能阅读）</summary>'+''.join(transcript)+'</details><noscript><p class="callout">当前环境未运行JavaScript。首步与“全部步骤文字”仍可阅读；如需播放，请用普通浏览器打开本HTML。</p></noscript></figure>'

def page(title,body,current,lessons,active='',description='循序渐进的 Agent 工程与面试学习手册'):
    nav=''.join(f'<a class="lesson-nav {"active" if active==l["id"] else ""}" href="{relative("lessons/"+l["slug"]+".html",current)}"><span>{l["id"]}</span>{E(l["title"])}</a>' for l in lessons)
    root=lambda p:relative(p,current)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{E(description)}"><title>{E(title)} · Agent 工程学习手册</title><link rel="stylesheet" href="{root('assets/style.css')+'?v=linked-3'}"><script defer src="{root('assets/catalog.js')}"></script><script defer src="{root('assets/app.js')+'?v=linked-3'}"></script></head><body data-page="{E(current)}" data-lesson="{active}"><a class="skip" href="#main">跳到正文</a><aside class="sidebar"><a class="brand" href="{root('index.html')}"><span class="brand-mark">A</span><span>Agent 工程<span class="brand-sub">学习 · 实验 · 面试</span></span></a><button type="button" id="menu-close" aria-label="关闭课程导航">关闭</button><nav class="top-nav" aria-label="主要导航"><a href="{root('index.html')}">学习路线</a><a href="{root('library.html')}">全库资料</a><a href="{root('questions.html')}">156 题练习</a><a href="{root('visuals.html')}">图解实验室</a><a href="{root('review.html')}">复习与自评</a><a href="{root('corrections.html')}">勘误与来源</a><a href="{root('coverage.html')}">文件覆盖清单</a></nav><div class="nav-label">顺序课程 / 26 LESSONS</div><nav class="course-nav" aria-label="课程">{nav}</nav><p class="sidebar-foot">本地离线 · 相对路径<br>同例教学 v3 · 源快照 2026-11-01 · {SHA[:7]}</p></aside><div class="shell"><header class="toolbar"><button type="button" id="menu-toggle" aria-label="展开课程导航" aria-expanded="false">☰</button><span>FIELD GUIDE / AGENT ENGINEERING</span><button type="button" id="search-open">搜索课程与资料 <kbd>/</kbd></button><button type="button" onclick="window.print()" class="print-button">打印</button></header><main id="main" tabindex="-1">{body}</main><footer>源资料 © 2026 Zchary1106 · <a href="{root('../source/LICENSE')}">MIT 许可</a> · 教学编排与实验为本次补充 · <a href="{root('coverage.html')}">来源和覆盖清单</a></footer></div><dialog id="search-dialog"><div class="search-heading"><label for="search-input">检索全部本地资料</label><button type="button" id="search-close" aria-label="关闭搜索">关闭</button></div><input id="search-input" type="search" placeholder="输入主题、术语、公司或文件名…"><p id="search-count" aria-live="polite"></p><div id="search-results"></div></dialog><div id="toast" role="status"></div></body></html>'''

def evidence_link(url):
    if isinstance(url,str) and urlsplit(url).scheme in ('http','https') and urlsplit(url).netloc:
        return '<a href="'+E(url)+'">访问原始来源（在线）</a>'
    return '<span>原始数据未提供来源</span>'

def write(path,body):
    p=SITE/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)

def toc_html(body):
    class Headings(HTMLParser):
        def __init__(self):super().__init__();self.rows=[];self.collect=False;self.title='';self.ident=''
        def handle_starttag(self,t,a):
            if t in ('h2','h3'):self.collect=True;self.title='';self.ident=dict(a).get('id','')
        def handle_data(self,d):
            if self.collect:self.title+=d
        def handle_endtag(self,t):
            if t in ('h2','h3') and self.collect:self.rows.append((self.ident,self.title));self.collect=False
    p=Headings();p.feed(body)
    return '<details class="toc" open><summary>本页目录</summary><nav>'+''.join(f'<a href="#{quote(i)}">{E(t)}</a>' for i,t in p.rows if i)+'</nav></details>'

def code_html(code,start=1,anchors=False):
    rows=[]
    for i,line in enumerate(code.splitlines(),start):
        ident=f' id="lab-line-{i}"' if anchors else ''
        rows.append(f'<span class="code-line" data-line="{i}"{ident}>{E(line)}</span>')
    return '\n'.join(rows)+'\n'

def render_lab(l,current):
    lab=l['lab'];src=l['sources'][0]
    body='<section class="lab-section linked-lab" id="lab"><div class="eyebrow">SAME CASE / 用同一份代码动手验证</div><h2>动手跑：'+E(lab['title'])+'</h2><p>'+E(lab['task'])+'</p>'
    body+='<p class="case-handoff">刚才演示里的数据与变量来自这份程序。先对照行号读，再运行；参考程序对应“正常”场景，边界场景的改动已在演示中单独标出。</p>'
    body+='<p class="lab-runtime">运行环境：Python 3.10+，只用标准库，无需 API Key。</p><details class="lab-boundary"><summary>这份小实验能验证什么、还没实现什么</summary><p>'+E(l['alignment']['coverage'])+'</p></details>'
    body+='<h3>先把代码与概念对上</h3>'+render_markdown(lab['explanation'],src,current)
    body+='<p>在终端先进入本学习文件夹，再执行：</p><pre><code>cd site/labs\npython3 '+E(l['slug'])+'.py</code></pre><p><a class="button" href="../labs/'+E(l['slug'])+'.py" download>下载同一份参考程序</a></p>'
    body+='<details class="answer full-reference" open><summary>完整参考实现 · 带行号供演示对照</summary><pre class="numbered-code"><code class="language-python">'+code_html(lab['code'],anchors=True)+'</code></pre></details><h3>运行后应看到</h3><pre><code>'+E(lab['expected'])+'</code></pre>'
    for i,ext in enumerate(lab['extensions']):
        body+='<details class="answer"><summary>在同一案例上改一个条件 '+str(i+1)+'：'+E(ext)+'</summary>'+render_markdown(lab['extension_answers'][i],src,current)+'</details>'
    return body+'</section>'

def render_case(l,current):
    a=l['alignment'];refs=l['_section_ids'];source=refs[a['insert_after']]
    return '<section class="linked-case" id="case-study"><div class="eyebrow">WORKED EXAMPLE / 从刚才的原理到这份代码</div><h2>'+E(a['case_title'])+'</h2><div class="case-bridge prose">'+render_markdown(a['bridge'],l['sources'][0],current)+'</div><p class="case-location">对应刚才的讲解：<a href="#'+quote(source)+'">'+E(a['insert_after'])+'</a>。本案例的运行范围：'+E(a['coverage_summary'])+'</p>'+diagram_html(l['diagram'],l)+render_lab(l,current)+'</section>'

def render_connected_body(l,current,content):
    pieces=re.split(r'(?=<h2\b)',content)
    refs={};sections=[]
    for piece in pieces:
        if not piece.strip():continue
        m=re.match(r'<h2 id="([^"]+)">(.*?)</h2>',piece,re.S)
        title=html.unescape(re.sub('<[^>]+>','',m.group(2))) if m else ''
        if m:refs[title]=m.group(1)
        sections.append((title,piece))
    local=dict(l,_section_ids=refs);anchor=l['alignment']['insert_after']
    if anchor not in refs:raise ValueError('Missing insertion section: '+l['id']+' '+anchor)
    result=[]
    for title,piece in sections:
        result.append('<section class="reading-section" data-reading-section="'+E(title)+'"><article class="prose">'+piece+'</article>')
        if title==anchor:result.append(render_case(local,current))
        result.append('</section>')
    return ''.join(result),refs

def render_exercises(l,current,refs):
    body='<section class="exercise-section" id="exercises"><div class="eyebrow">TRANSFER / 在学过的概念上换条件</div><h2>课后练习与详解</h2><p>先完成刚才的例子，再回答这些问题。每题都标出了对应讲解；不会时回到那一段，而不是重新猜一整章。</p>'
    for i,q in enumerate(l['questions'],1):
        section=l['alignment']['question_sections'][i-1]
        body+='<div class="question"><h3>'+f'{i:02} · '+E(q['q'])+'</h3><p class="question-context">对应概念：<a href="#'+quote(refs[section])+'">'+E(section)+'</a></p>'
        body+=f'<textarea data-note="{l["id"]}-q{i}" aria-label="第{i}题你的答案" placeholder="先说明原因，再用本课案例或变式验证。"></textarea><details class="answer"><summary>展开参考答案与评分要点</summary>{render_markdown(q["a"],l["sources"][0],current)}<p class="rubric"><strong>检查：</strong>{E(q["rubric"])}</p></details></div>'
    return body+'</section>'

def lesson_page(l,lessons):
    current='lessons/'+l['slug']+'.html'
    body=f'<div class="eyebrow">{E(l["stage"])} / LESSON {l["id"]}</div><h1>{E(l["title"])}</h1><p class="lead">先理解原理，再沿同一个例子看演示、读代码、运行和做变式。</p><div class="meta">建议学习 {l["minutes"]} 分钟起 · 先修：{E("、".join(l["prerequisites"]))} · 原理 → 同例演示 → 同份代码 → 练习</div>'
    body+='<section class="objectives"><h2>这一课要做到</h2><ul>'+''.join('<li>'+E(x)+'</li>' for x in l['goals'])+'</ul></section>'
    content=render_markdown(l['body'],l['sources'][0],current)
    connected,refs=render_connected_body(l,current,content)
    body+=toc_html(content)+'<nav class="lesson-reading-path" aria-label="本课阅读路径"><a href="#'+quote(next(iter(refs.values())))+'">① 原理讲解</a><span>→</span><a href="#case-study">② 同例演示</a><span>→</span><a href="#lab">③ 同份代码</a><span>→</span><a href="#exercises">④ 变式练习</a></nav>'+connected+render_exercises(l,current,refs)
    body+='<section class="pitfalls"><h2>容易踩的坑</h2><ul>'+''.join('<li>'+E(x)+'</li>' for x in l['pitfalls'])+'</ul></section>'
    body+='<section class="checkpoint"><h2>这一课的验收</h2><p>'+E(l['checkpoint'])+'</p><p>自评只记录学习过程，不等同于客观掌握；看答案后完成请如实选择。</p><div class="controls">'+''.join(f'<button type="button" data-grade="{g}" data-id="{l["id"]}">{label}</button>' for g,label in [('help','仍需帮助'),('guided','看答案后完成'),('independent','独立完成')])+'</div><p data-grade-status="'+l['id']+'" aria-live="polite">尚未记录</p></section>'
    body+='<section id="sources"><h2>对应原文与继续深挖</h2><p>上面为教练补充讲解；下列本地页完整保留仓库原文，包含更广的题库和例子。</p><ul>'+''.join('<li><a href="'+relative(DOC_MAP[s],current)+'">'+E(s)+'</a></li>' for s in l['sources'])+'</ul></section>'
    i=lessons.index(l);body+='<nav class="lesson-pager" aria-label="上下课">'
    if i:body+='<a href="'+relative('lessons/'+lessons[i-1]['slug']+'.html',current)+'">← '+E(lessons[i-1]['title'])+'</a>'
    if i<len(lessons)-1:body+='<a href="'+relative('lessons/'+lessons[i+1]['slug']+'.html',current)+'">下一课：'+E(lessons[i+1]['title'])+' →</a>'
    body+='</nav>'
    write(current,page(l['title'],body,current,lessons,l['id']))
    write('labs/'+l['slug']+'.py',l['lab']['code'])

def build():
    lessons=[json.loads(p.read_text()) for p in sorted(CONTENT.glob('*.json'))]
    ids=[l['id'] for l in lessons];assert len(ids)==len(set(ids))
    for l in lessons:
        for s in l['sources']:assert s in DOC_MAP,(l['id'],s)
    (SITE/'assets').mkdir(parents=True,exist_ok=True)
    for asset in ['style.css','app.js']:shutil.copy2(ROOT/'authoring'/asset,SITE/'assets'/asset)
    for l in lessons:lesson_page(l,lessons)
    catalog=[];coverage=[]
    for src,output in DOC_MAP.items():
        text=(SOURCE/src).read_text();body=render_markdown(text,src,output)
        title=next((l.lstrip('# ').strip() for l in text.splitlines() if l.startswith('# ')),Path(src).stem)
        warning='<div class="callout">原文快照 / 非本课程新编正文。公司信息、面经、趋势及产品参数可能有时效或二手转述问题；示例代码不保证可直接运行。原文内容保持原样，请结合勘误页和一手来源使用。</div>'
        mapped=[l for l in lessons if src in l['sources']]
        related='<p>关联课程：'+(' · '.join(f'<a href="{relative("lessons/"+l["slug"]+".html",output)}">{l["id"]} {E(l["title"])}</a>' for l in mapped) or '拓展资料；按目录选择性深挖')+'</p>'
        head='<div class="eyebrow">SOURCE LIBRARY / 完整原文</div><p class="source-path">'+E(src)+'</p>'+warning+related+f'<p><a href="{REPO}/blob/{SHA}/{quote(src)}">GitHub 固定版本</a> · <a href="{relative("../source/"+src,output)}" download>下载原始 Markdown</a></p>'
        write(output,page(title,head+toc_html(body)+'<article class="prose source-prose">'+body+'</article>',output,lessons))
        catalog.append(dict(title=title,path=output,kind='原文 · '+src.split('/')[0],text=re.sub(r'\s+',' ',text)))
    for l in lessons:catalog.insert(int(l['id'])-1,dict(title=l['title'],path='lessons/'+l['slug']+'.html',kind='课程 '+l['id'],text=l['body']+' '+' '.join(q['q'] for q in l['questions'])))
    companies=json.loads((SOURCE/'data.json').read_text())
    cb='<div class="eyebrow">COMPANY PRACTICE / EDITORIAL SOURCE</div><h1>公司主题题库 · 222题</h1><p class="lead">完整展开源 data.json 的13组公司主题题与答案。下列内容是作者编排与判断，未逐题独立核验为公司官方真题；公司特点、产品和招聘情况应再查当前一手来源。</p><p><a href="questions.html">按主题练156题</a> · <a href="evidence.html">查看125条来源档案</a></p>'
    for company in companies:
        cb+='<section><h2>'+E(company['company'])+'</h2>'
        for i,q in enumerate(company.get('questions',[]),1):
            ident='company-'+str(len(catalog))
            cb+='<section class="bank-question" id="'+ident+'"><h3>'+str(i)+' · '+E(q['question'])+'</h3><details class="answer"><summary>作者参考答案与思路</summary>'+render_markdown(q.get('answer',''),current='companies.html')+'<p class="rubric">作者思路（非公司官方口径）：'+E(q.get('thinking',''))+'</p></details></section>'
            catalog.append(dict(title=company['company']+' · '+q['question'],path='companies.html#'+ident,kind='公司主题题 · 未独立核验',text=q.get('answer','')+' '+q.get('thinking','')))
        cb+='</section>'
    write('companies.html',page('公司主题题库',cb,'companies.html',lessons))
    archives=json.loads((SOURCE/'data/interviews.json').read_text())['items']
    eb='<div class="eyebrow">EVIDENCE ARCHIVE / SOURCE LABELS</div><h1>125条面经与资料来源档案</h1><p>完整呈现源 data/interviews.json 的记录。标题、评分、可信度和核验日期均来自仓库原数据，不表示本次逐条复核。资料链接需要联网，学习正文可离线。</p>'
    for item in archives:
        eb+='<section class="bank-question"><h2>'+E(item.get('title',''))+'</h2><p>'+E(item.get('summary',''))+'</p><p class="meta">平台 '+E(item.get('platform',''))+' · 类型 '+E(item.get('source_type',''))+' · 源标记可信度 '+E(item.get('confidence',''))+' · 源核验日期 '+E(item.get('verified_at',''))+'</p><p>'+evidence_link(item.get('source_url'))+'</p><p>'+E(' / '.join(item.get('topics',[])))+'</p></section>'
    write('evidence.html',page('面经来源档案',eb,'evidence.html',lessons))
    write('assets/catalog.js','window.COURSE_CATALOG='+json.dumps(catalog,ensure_ascii=False).replace('</','<\\/')+';\nwindow.COURSE_LESSONS='+json.dumps([{k:l[k] for k in ['id','title','slug','stage','checkpoint']} for l in lessons],ensure_ascii=False)+';\n')
    # Home: one manageable route; stages in source order.
    body='<div class="eyebrow">A PERSONAL FIELD GUIDE · 2026 EDITION</div><section class="hero"><div><h1>从理解 Agent，<br>到讲清工程取舍。</h1><p class="lead">把资料库变成一条能走完的学习路线。先读讲解，再看图、跑小实验、做变式，最后用项目证据回答面试追问。</p><a class="button primary" href="lessons/'+lessons[0]['slug']+'.html">从第 01 课开始 →</a> <a class="button" href="#study-guide">怎么学这套课</a></div><div class="hero-graphic" aria-label="理解、实践、复测三阶段"><div>01 <b>理解机制</b><small>解释因果与边界</small></div><div>02 <b>运行实验</b><small>观察数据与状态</small></div><div>03 <b>迁移复测</b><small>换约束仍能独立判断</small></div></div></section>'
    body+=f'<div class="stats"><div><strong>{len(lessons)}</strong><span>顺序教学课</span></div><div><strong>{len(MD_FILES)}</strong><span>完整原文页</span></div><div><strong>{sum(len(l["questions"]) for l in lessons)+156+222}</strong><span>问答与参考解</span></div><div><strong>{len(lessons)}</strong><span>可运行小实验</span></div></div>'
    body+='<section class="start-guide" id="study-guide"><h2>怎样循序渐进地使用</h2><ol><li><strong>每次读一课：</strong>先修不熟就返回对应课；先理解场景和已解例，不需要先接受测验。</li><li><strong>看图并手推：</strong>在对应原理后看同一案例的演示；逐步核对变量、为什么这样做和对应代码行。</li><li><strong>跑实验并改约束：</strong>先预测输出，再运行Python参考程序，完成两项变式；输出一致只证明程序行为。</li><li><strong>先答后看解：</strong>用自己的话解释原因、反例与权衡，再展开答案；自评“独立完成”只在确实未看答案时使用。</li><li><strong>隔日再测：</strong>复习页会按自评安排下次回测。迁移题、跨日回忆和项目证据一起用于判断面试准备程度。</li></ol><p>这是完整学习材料与训练路径，能帮助你准备面试；录用还取决于岗位匹配、项目深度、编码表现和具体面试，无法保证结果。</p></section>'
    body+='<section><h2>学习路线</h2><p>主线按先修顺序安排；第21课训练专题可作为进阶分支，应用岗位可先完成22—26再回来。你最初关注的RAG专题集中在07—14课。</p>'
    stage=''
    for l in lessons:
        if l['stage']!=stage:
            if stage:body+='</div>'
            stage=l['stage'];body+='<h3 class="stage-title">'+E(stage)+'</h3><div class="lesson-grid">'
        body+='<a class="lesson-card" href="lessons/'+l['slug']+'.html"><span class="card-number">'+l['id']+'</span><h4>'+E(l['title'])+'</h4><p>'+E(l['goals'][0])+'</p><span class="card-footer">讲解 · 图解 · 练习 · 实验 <span data-card-state="'+l['id']+'"></span></span></a>'
    body+='</div></section><section class="callout"><h2>全库覆盖，不丢原资料</h2><p>174个源文件已保留，109份Markdown逐篇转换为本地HTML；41张SVG可在图解页与原文页查看。公司面经、项目实战、算法代码、数据JSON和工具说明均在覆盖清单中。新编课负责搭梯子，完整原文负责深挖。</p><a href="coverage.html">查看文件到页面的对应关系 →</a></section>'
    write('index.html',page('学习路线',body,'index.html',lessons))
    # Library by directory, one entry per Markdown; preserve true categories rather than pretending all are lessons.
    groups={}
    for src in MD_FILES:groups.setdefault(src.split('/')[0] if '/' in src else '总览与路线',[]).append(src)
    body='<div class="eyebrow">COMPLETE SOURCE LIBRARY</div><h1>全库资料，逐篇保留。</h1><p class="lead">按目录浏览原文，或按 / 搜索全文。这里保留作者观点和示例；新增教学与勘误另行标识。</p><div class="controls"><a class="button" href="companies.html">222道公司主题题</a><a class="button" href="evidence.html">125条来源档案</a><a class="button" href="coverage.html">全部174文件</a></div>'
    for group,items in groups.items():
        body+='<section><h2>'+E(group)+f' <small>{len(items)} 篇</small></h2><div class="library-list">'+''.join('<a href="'+DOC_MAP[s]+'"><strong>'+E(Path(s).stem)+'</strong><span>'+E(s)+'</span></a>' for s in items)+'</div></section>'
    write('library.html',page('全库资料',body,'library.html',lessons))
    # Question bank preserves source labels and answer provenance.
    qs=json.loads((SOURCE/'data/practice-2026-10/questions.json').read_text())
    body='<div class="eyebrow">PRACTICE / REFERENCE ANSWERS</div><h1>156 题：按主题回测。</h1><p class="lead">这些是仓库编辑整理题，并非已核实的公司官方真题。答案为参考表达，不能替代你的项目证据。</p><p>另见：<a href="companies.html">222道公司主题题</a> · <a href="evidence.html">125条来源档案</a></p><label for="bank-filter">筛选题目与主题</label><input type="search" id="bank-filter" placeholder="例如：MCP、超时、检索、缓存"><p id="bank-count" aria-live="polite"></p>'
    topic=''
    for i,q in enumerate(qs,1):
        body+='<section class="bank-question" data-bank-text="'+E(q['topic']+' '+q['question'])+'"><span class="eyebrow">'+E(q['topic'])+' / '+str(i).zfill(3)+'</span><h2>'+E(q['question'])+'</h2><textarea data-note="bank-'+E(q['id'])+'" aria-label="你的作答" placeholder="先解释机制，再给项目例子与边界。"></textarea><details class="answer"><summary>参考答案、要点与追问</summary>'+render_markdown(q.get('reference_answer',''),current='questions.html')+'<ul>'+''.join('<li>'+E(x)+'</li>' for x in q.get('answer_key_points',[]))+'</ul><p><strong>追问：</strong>'+E(q.get('answer_follow_up',''))+'</p><p class="rubric"><strong>易错：</strong>'+E(q.get('answer_pitfall',''))+'</p></details><details><summary>来源与证据等级</summary><p>'+E(q.get('note',''))+'</p><p>来源等级：'+E(q.get('provenance',''))+'；公司官方题已核实：'+E(q.get('authentic_company_question_verified',False))+'</p><ul>'+''.join('<li><a href="'+E(u)+'">'+E(u)+'</a></li>' for u in q.get('source_urls',[]))+'</ul></details></section>'
    write('questions.html',page('156题练习',body,'questions.html',lessons))
    # Full source manifest and license.
    body=f'<div class="eyebrow">TRACEABILITY / SNAPSHOT</div><h1>全库覆盖清单</h1><p>源仓库：<a href="{REPO}">Zchary1106/agent-interview-hub</a><br>固定提交：<code>{SHA}</code><br>保存日期：2026-11-01（Asia/Shanghai）。共174个源文件，Markdown 109份；原文和教练补充明确分开。</p><p><a href="../source/LICENSE">MIT原始许可</a> · <a href="../README.md">使用说明</a> · <a href="../manifest.json">机器可读清单</a></p><div class="table-wrap"><table><thead><tr><th>原文件（相对仓库）</th><th>HTML或原件</th><th>类型</th></tr></thead><tbody>'
    for p in sorted(x for x in SOURCE.rglob('*') if x.is_file()):
        src=p.relative_to(SOURCE).as_posix(); dest=DOC_MAP.get(src,'../source/'+src)
        mapped=[l['id'] for l in lessons if src in l['sources']]
        coverage.append(dict(source=src,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),html=DOC_MAP.get(src),lessons=mapped))
        body+='<tr><td>'+E(src)+'</td><td><a href="'+quote(dest,safe='/.-_')+'">'+('阅读HTML' if src in DOC_MAP else '本地原件')+'</a></td><td>'+E(p.suffix or '纯文本')+'</td></tr>'
    body+='</tbody></table></div><h2>许可与归属</h2><pre>'+E((SOURCE/'LICENSE').read_text())+'</pre>'
    write('coverage.html',page('覆盖清单',body,'coverage.html',lessons))
    (ROOT/'manifest.json').write_text(json.dumps(dict(repository=REPO,commit=SHA,snapshot_date='2026-11-01',source_files=len(coverage),markdown_pages=len(MD_FILES),lessons=len(lessons),files=coverage),ensure_ascii=False,indent=2))
    # Review dashboard; no external service, no fake grading.
    body='''<div class="eyebrow">RECALL / SELF-REPORTED EVIDENCE</div><h1>复习与自评</h1><p class="lead">看过不是掌握。留下自己的答案，隔日用新条件再解释一次。</p><div class="callout" id="storage-status">记录仅保存在当前浏览器。file://下的存储策略依浏览器而异，请定期导出；改用不同路径或端口也可能是独立存储。</div><div class="controls"><button type="button" id="export-state">导出记录 JSON</button><label class="button" for="import-state">导入记录</label><input type="file" id="import-state" accept="application/json,.json"><button type="button" id="clear-state">清空本学习站记录</button></div><p>“仍需帮助”和“看答案后完成”默认次日再测；独立完成按1→3→7→14天安排。相同日期不会重复推进间隔。这是学习安排的启发式，不是科学掌握诊断。长期掌握还需要跨情境证据。</p><div id="review-list"></div><section><h2>阶段验收：怎样知道可以往下走</h2><ol><li>01—06：能手推工具调用与结果回传，区分模型建议、协议接入和执行保证；能处理预算与隔离。</li><li>07—09：能画完整RAG链路，手算检索指标，定位候选缺失与上下文缺失。</li><li>10—14：能设计有界自主检索，区分控制流和知识图，处理局部、多跳、综述三类任务。</li><li>15—20：能推演崩溃恢复、幂等、协作终止、注入隔离、发布回归及成本取舍。</li><li>21—26：能解释必要模型机制，独立手写关键算法，用真实证据陈述项目并完成压力面试。</li></ol><h2>一次模拟面试怎么做</h2><p>第26课提供综合题与参考标准。另从156题库每个薄弱主题挑一题：2分钟组织，5分钟解释，再追问一个失败边界。不要只背术语，要画数据流、提出验证、讲清你实际做过什么。</p><p>若参考答案与自己的设计不同，先比较约束、正确性和代价，不按关键词机械判错。</p></section>'''
    write('review.html',page('复习与自评',body,'review.html',lessons))
    corrections=ROOT/'authoring'/'corrections.md'
    write('corrections.html',page('勘误与来源',render_markdown(corrections.read_text(),current='corrections.html'),'corrections.html',lessons))
    visuals=(ROOT/'authoring'/'visuals.html').read_text()
    visuals+='<h2>仓库原始图解 · 41 张 SVG</h2><p>本地图像，断网可看；点击打开原图，可放大查看。原图观点沿用教材，版本相关细节结合勘误页使用。</p><div class="diagram-gallery">'
    for p in sorted((SOURCE/'diagrams').glob('*.svg')):
        src='../source/diagrams/'+p.name
        visuals+='<figure><a href="'+src+'"><img loading="lazy" src="'+src+'" alt="'+E(p.stem.replace('-',' '))+'"></a><figcaption>'+E(p.stem.replace('-',' '))+'</figcaption></figure>'
    visuals+='</div>'
    write('visuals.html',page('图解实验室',visuals,'visuals.html',lessons))
    print(json.dumps(dict(lessons=len(lessons),source_pages=len(MD_FILES),source_files=len(coverage),questions=sum(len(l['questions']) for l in lessons)+len(qs)+sum(len(c.get('questions',[])) for c in companies),labs=len(lessons)),ensure_ascii=False))

if __name__=='__main__':build()
