'use strict';
(() => {
 const $ = (q,r=document)=>r.querySelector(q), $$=(q,r=document)=>Array.from(r.querySelectorAll(q));
 const KEY='agent-field-guide-v1';
 const fresh=()=>({version:1,grades:{},notes:{}});
 let state=fresh(), storageOK=true, toastTimer;
 const toast=t=>{const el=$('#toast');el.textContent=t;el.style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.style.display='none',3000);};
 try { const raw=localStorage.getItem(KEY);if(raw) state=validate(JSON.parse(raw));localStorage.setItem(KEY,JSON.stringify(state)); }catch(e){storageOK=false;}
 function validate(s){
   if(!s||s.version!==1||!s.grades||typeof s.grades!=='object'||Array.isArray(s.grades)||!s.notes||typeof s.notes!=='object'||Array.isArray(s.notes))throw Error('不是本学习站的记录文件');
   const out=fresh(), ids=new Set((window.COURSE_LESSONS||[]).map(l=>l.id));
   for(const [k,v] of Object.entries(s.grades)){
     if(!ids.has(k)||!v||!['help','guided','independent'].includes(v.grade)||!/^\d{4}-\d{2}-\d{2}$/.test(v.date)||!/^\d{4}-\d{2}-\d{2}$/.test(v.next)||!Number.isInteger(v.level)||v.level<0||v.level>4)throw Error('自评条目无效');
     out.grades[k]={grade:v.grade,date:v.date,next:v.next,level:v.level};
   }
   for(const[k,v]of Object.entries(s.notes)){if(typeof v!=='string'||v.length>100000||k.length>120||!/^[\w-]+$/.test(k))throw Error('笔记内容无效');out.notes[k]=v;}
   return out;
 }
 function save(){try{localStorage.setItem(KEY,JSON.stringify(state));storageOK=true;}catch(e){storageOK=false;updateStorage();}}
 function updateStorage(){const el=$('#storage-status');if(el&&!storageOK)el.textContent='当前浏览器无法持久保存记录。你仍可使用页面并导出JSON；关闭前请导出。';}
 updateStorage();
 // Use the learner's local date, matching their own review calendar.
 function dateKey(d=new Date()){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
 const plusDays=(d,n)=>{const t=new Date(d+'T12:00:00');t.setDate(t.getDate()+n);return dateKey(t);};
 const label={help:'仍需帮助',guided:'看答案后完成',independent:'独立完成'};
 const intervals=[1,3,7,14,30];
 function grade(id,g){
   const old=state.grades[id],today=dateKey();let level=0;
   if(g==='independent'&&old?.grade==='independent') level=old.level+((old.date<today&&old.next<=today)?1:0);
   level=Math.min(level,4);
   const keepSchedule=old&&g==='independent'&&old.grade==='independent'&&(old.date===today||old.next>today);
   const next=keepSchedule?old.next:plusDays(today,g==='independent'?intervals[level]:1);
   state.grades[id]={grade:g,date:today,next,level};save();updateGrades();renderReviews();toast('已记录：'+label[g]+'；下次 '+next+(storageOK?'':'（请导出保存）'));
 }
 $$('[data-grade]').forEach(b=>b.addEventListener('click',()=>grade(b.dataset.id,b.dataset.grade)));
 function updateGrades(){
   $$('[data-grade-status]').forEach(el=>{const g=state.grades[el.dataset.gradeStatus];el.textContent=g?`${label[g.grade]} · ${g.date} · 下次回测 ${g.next}`:'尚未记录';});
   $$('[data-card-state]').forEach(el=>{const g=state.grades[el.dataset.cardState];el.textContent=g?label[g.grade]:'';});
 }
 updateGrades();
 $$('[data-note]').forEach(el=>{el.value=state.notes[el.dataset.note]||'';el.addEventListener('input',()=>{state.notes[el.dataset.note]=el.value;save();});});
 function renderReviews(){
   const root=$('#review-list');if(!root)return;root.replaceChildren();
   const rows=(window.COURSE_LESSONS||[]).slice().sort((a,b)=>{const ga=state.grades[a.id],gb=state.grades[b.id];return (ga?.next||'9999').localeCompare(gb?.next||'9999')||a.id.localeCompare(b.id);});
   rows.forEach(l=>{
     const g=state.grades[l.id],row=document.createElement('div');row.className='review-row';const a=document.createElement('a');a.href='lessons/'+l.slug+'.html';a.textContent=l.id+' · '+l.title;row.append(a);
     const status=document.createElement('span');status.textContent=g?label[g.grade]:'尚未学习';row.append(status);
     if(g){const time=document.createElement('time');time.dateTime=g.next;time.textContent=(g.next<=dateKey()?'应复测 ':'下次 ')+g.next;if(g.next<=dateKey())time.className='due';row.append(time);}
     const p=document.createElement('p');p.textContent='验收：'+l.checkpoint;row.append(p);root.append(row);
   });
 }
 renderReviews();
 $('#export-state')?.addEventListener('click',()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='agent-study-'+dateKey()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 $('#import-state')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>5000000)throw Error('文件超过5MB');const imported=validate(JSON.parse(await file.text()));if(!confirm('导入将替换当前浏览器中本学习站的自评和答案。建议先导出备份。继续吗？'))return;state=imported;save();updateGrades();renderReviews();toast('导入完成');}catch(err){toast('导入失败：'+err.message);}finally{e.target.value='';}});
 $('#clear-state')?.addEventListener('click',()=>{if(!confirm('清空本学习站的自评和作答？此操作不影响其他网站。请先导出需要的记录。'))return;state=fresh();save();renderReviews();updateGrades();toast('本学习站记录已清空');});
 function syncMenu(){const sidebar=$('.sidebar'),hidden=window.innerWidth<761&&!sidebar.classList.contains('is-open');sidebar.inert=hidden;sidebar.setAttribute('aria-hidden',String(hidden));$('#menu-toggle')?.setAttribute('aria-expanded',String(sidebar.classList.contains('is-open')));}
 $('#menu-toggle')?.addEventListener('click',()=>{$('.sidebar').classList.toggle('is-open');syncMenu();});
 $('#menu-close')?.addEventListener('click',()=>{$('.sidebar').classList.remove('is-open');syncMenu();$('#menu-toggle')?.focus();});
 document.addEventListener('click',e=>{if(window.innerWidth<761&&!e.target.closest('.sidebar')&&!e.target.closest('#menu-toggle')){$('.sidebar')?.classList.remove('is-open');syncMenu();}});
 window.addEventListener('resize',syncMenu);syncMenu();
 // Local search: catalog is a plain script, so file:// needs no fetch or server.
 const dialog=$('#search-dialog'),search=$('#search-input');
 const rootPath=(()=>{const p=document.body.dataset.page;return '../'.repeat((p.match(/\//g)||[]).length);})();
 function searchRender(){
   const q=search.value.trim().toLocaleLowerCase(),tokens=q.split(/\s+/).filter(Boolean),out=$('#search-results');out.replaceChildren();
   if(!q){$('#search-count').textContent='支持课程与109份原文的全文搜索；多个词以空格分隔。';return;}
   const found=(window.COURSE_CATALOG||[]).map(x=>{const title=x.title.toLowerCase(),text=x.text.toLowerCase();return {...x,score:tokens.reduce((n,t)=>n+(title.includes(t)?10:0)+(text.includes(t)?1:0),0),match:tokens.every(t=>title.includes(t)||text.includes(t))};}).filter(x=>x.match).sort((a,b)=>b.score-a.score);
   $('#search-count').textContent=`找到 ${found.length} 项；展示前 ${Math.min(found.length,45)} 项`;
   found.slice(0,45).forEach(x=>{const a=document.createElement('a');a.className='search-result';a.href=rootPath+x.path;const s=document.createElement('small');s.textContent=x.kind;const t=document.createElement('strong');t.textContent=x.title;const p=document.createElement('p');const pos=Math.max(0,x.text.toLowerCase().indexOf(tokens[0])-35);p.textContent=x.text.slice(pos,pos+150).replace(/[#*`]/g,'')+'…';a.append(s,t,p);out.append(a);});
 }
 $('#search-open')?.addEventListener('click',()=>{dialog.showModal();search.focus();searchRender();});
 $('#search-close')?.addEventListener('click',()=>dialog.close());
 search?.addEventListener('input',searchRender);
 document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();dialog.showModal();search.focus();searchRender();}});
 dialog?.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
 // Case playback uses visible HTML frames as its source of truth; SVG is optional.
 $$('[data-flow]').forEach(flow=>{
   const groups=$$('[data-flow-case-panel]',flow);if(!groups.length)return;
   const nodes=$$('[data-node]',flow),status=$('[data-flow-status]',flow),play=$('[data-play]',flow),nextButton=$('[data-step]',flow),prevButton=$('[data-prev]',flow),caseSelect=$('[data-flow-case]',flow),speed=$('[data-flow-speed]',flow),progress=$('[data-flow-progress]',flow);
   let frames=[],step=0,timer=null;
   const stop=()=>{clearInterval(timer);timer=null;flow.classList.remove('is-playing');play.textContent=step===frames.length-1?'重新播放':'播放演示';play.setAttribute('aria-pressed','false');};
   function paint(animate=false){
     const frame=frames[step],nodeIndex=Number(frame.dataset.nodeIndex),visited=new Set(frames.slice(0,step).map(f=>Number(f.dataset.nodeIndex)));
     frames.forEach((f,i)=>{f.hidden=i!==step;});
     nodes.forEach(n=>{const i=Number(n.dataset.node);n.classList.toggle('is-active',i===nodeIndex);n.classList.toggle('is-done',i!==nodeIndex&&visited.has(i));n.classList.toggle('is-failed',i===nodeIndex&&frame.dataset.failure==='true');});
     const title=$('h3',frame).textContent;
     status.textContent=`第 ${step+1}/${frames.length} 步：${title}`+(step===frames.length-1?(frame.dataset.failure==='true'?' · 本分支停止':' · 演示完成'):'');
     progress.max=frames.length;progress.value=step+1;prevButton.disabled=step===0;nextButton.disabled=step===frames.length-1;
     if(animate){const packet=$('.flow-packet',frame);if(packet){packet.style.animation='none';void packet.offsetWidth;packet.style.animation='packet-move 1.8s ease-in-out';}}
   }
   function selectCase(){stop();groups.forEach(g=>g.hidden=g.dataset.flowCasePanel!==caseSelect.value);const selected=groups.find(g=>g.dataset.flowCasePanel===caseSelect.value)||groups[0];frames=$$('[data-flow-frame]',selected);step=0;paint();stop();}
   function advance(){if(step<frames.length-1){step++;paint(true);}if(step===frames.length-1)stop();}
   function start(){if(step===frames.length-1)step=0;paint(true);timer=setInterval(advance,Number(speed.value)||7000);flow.classList.add('is-playing');play.textContent='暂停';play.setAttribute('aria-pressed','true');}
   nextButton.addEventListener('click',()=>{stop();advance();});
   prevButton.addEventListener('click',()=>{stop();step=Math.max(0,step-1);paint(true);});
   play.addEventListener('click',()=>{if(timer)stop();else start();});
   $('[data-reset]',flow).addEventListener('click',()=>{stop();step=0;paint();stop();});
   caseSelect.addEventListener('change',selectCase);speed.addEventListener('change',()=>{if(timer){stop();start();}});
   document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
   selectCase();
 });
 // Copy stays optional on browsers that deny clipboard for file URLs.
 $$('pre').forEach(pre=>{const button=document.createElement('button');button.type='button';button.className='copy-button';button.textContent='复制';button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(pre.querySelector('code')?.textContent||pre.textContent.replace(/^复制/,''));toast('已复制');}catch(e){toast('浏览器未允许复制，请选中代码手动复制。');}});pre.prepend(button);});
 const bank=$('#bank-filter');
 if(bank){const rows=$$('.bank-question');const run=()=>{const q=bank.value.trim().toLowerCase();let count=0;rows.forEach(r=>{r.hidden=!r.dataset.bankText.toLowerCase().includes(q);if(!r.hidden)count++;});$('#bank-count').textContent=`当前显示 ${count} / ${rows.length} 题`;};bank.addEventListener('input',run);run();}
 // RAG simulator: all data synthetic and visible.
 if($('#rag-sim')){
   const docs=[{id:'old',year:2025,role:'员工',score:.95,text:'2025版：上海住宿上限400元/晚。',supports:true},{id:'new',year:2026,role:'员工',score:.89,text:'2026版：上海住宿上限500元/晚。',supports:true},{id:'hotel',year:2026,role:'员工',score:.85,text:'出差应优先选择协议酒店。',supports:false},{id:'manager',year:2026,role:'经理',score:.83,text:'2026版：经理住宿上限700元/晚。',supports:true}];
   function render(){const filter=$('#rag-filter').checked,k=Number($('#rag-k').value);$('#rag-k-label').textContent=k;const allowed=docs.filter(d=>!filter||(d.year===2026&&d.role==='员工'));const chosen=allowed.slice(0,k);const root=$('#rag-docs');root.replaceChildren();docs.forEach(d=>{const el=document.createElement('div');el.className='retrieval-doc'+(chosen.includes(d)?' chosen':'')+(!allowed.includes(d)?' filtered':'');el.textContent=`${d.id} · 相似度 ${d.score} · ${d.text} ${chosen.includes(d)?'← 进入上下文':''}`;root.append(el);});const status=$('#rag-result');status.textContent=!filter?'当前上下文可能含过期或不适用的标准。排名高不是适用性保证；先检查版本与角色。':chosen.some(d=>d.id==='new')?'当前证据支持：普通员工上海住宿上限500元/晚 [new]。hotel只相关，不能单独支持金额。':'当前证据不足，不能编造金额。';}
   $('#rag-filter').addEventListener('change',render);$('#rag-k').addEventListener('input',render);render();
 }
 if($('#graph-sim')){
   let hop=0;const names=['张老师','小李','项目X','研究所Y'];const paths=['指导','参与','资助方'];
   function paint(){ $$('#graph-sim [data-g-node]').forEach(n=>n.classList.toggle('visited',Number(n.dataset.gNode)<=hop));$$('#graph-sim [data-g-edge]').forEach(e=>e.classList.toggle('walked',Number(e.dataset.gEdge)<hop));$('#graph-status').textContent=hop===0?'起点：张老师。下一步需要找到其学生，不能直接按语义相似猜项目。':`第${hop}跳：${names.slice(0,hop+1).join(' → ')}；新增关系：${paths[hop-1]}；来源 doc${hop}。${hop===3?'路径已连通；仍需检查实体身份、时间与原文。':''}`;}
   $('#graph-next').addEventListener('click',()=>{hop=Math.min(3,hop+1);paint();});$('#graph-reset').addEventListener('click',()=>{hop=0;paint();});paint();
 }
 if($('#recovery-sim')){
   let step=-1;const labels=['收到任务','提交业务事务','进程崩溃','恢复读取任务','同幂等键查询','复用已提交结果'];
   function paint(){const root=$('#recovery-steps');root.replaceChildren();labels.forEach((s,i)=>{const el=document.createElement('span');el.className='sim-step'+(i<step?' done':'')+(i===step?(i===2?' failed':' current'):'');el.textContent=(i+1)+' '+s;root.append(el);});const use=$('#recovery-key').checked;$('#recovery-status').textContent=step<0?'从已提交但尚未确认的故障窗口开始推演。':step<2?'记录任务与操作标识，业务效果由数据库确认。':step===2?'业务已提交，客户端未收到确认。超时/崩溃不证明业务未执行。':step<4?'恢复后先检查持久化状态，避免只看内存。':use?'使用相同幂等键查询：发现已提交结果，返回已有结果；业务效果总计1次。':'没有业务侧幂等/状态查询：盲目重试可能产生第二次效果；仅靠调用方记录无法跨系统保证原子性。';}
   $('#recovery-next').addEventListener('click',()=>{step=Math.min(5,step+1);paint();});$('#recovery-reset').addEventListener('click',()=>{step=-1;paint();});$('#recovery-key').addEventListener('change',paint);paint();
 }
})();
// Print all reference answers, restoring the reader's disclosure state afterwards.
(() => {
 let opened=[];
 window.addEventListener('beforeprint',()=>{opened=Array.from(document.querySelectorAll('details:not([open])'));opened.forEach(el=>el.open=true);});
 window.addEventListener('afterprint',()=>{opened.forEach(el=>el.open=false);opened=[];});
})();
