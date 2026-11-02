// Behaviour checks without a browser: use the real shipped script and a minimal DOM adapter.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
let today='2026-11-01';
class Clock extends Date{constructor(...args){super(...(args.length?args:[today+'T12:00:00']));}}
const element=(extra={})=>({textContent:'',style:{},dataset:{},listeners:{},classList:{contains:()=>false,toggle:()=>false,remove:()=>{}},addEventListener(type,fn){this.listeners[type]=fn},setAttribute(){},...extra});
function harness(seed){
 const data=new Map(seed?[['agent-field-guide-v1',JSON.stringify(seed)]]:[]);
 const status=element({dataset:{gradeStatus:'01'}}),toast=element(),sidebar=element(),storage=element(),input=element(),button=element({dataset:{id:'01',grade:'independent'}});
 const single={'.sidebar':sidebar,'#toast':toast,'#storage-status':storage,'#import-state':input};
 const doc={body:{dataset:{page:'lessons/test.html'}},activeElement:{tagName:'BODY'},querySelector:q=>single[q]||null,querySelectorAll:q=>q==='[data-grade]'?[button]:q==='[data-grade-status]'?[status]:[],addEventListener(){}};
 const win={COURSE_LESSONS:[{id:'01',title:'test',slug:'test',checkpoint:'test'}],innerWidth:1200,addEventListener(){}};
 const ctx={document:doc,window:win,localStorage:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)},Date:Clock,setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},console,confirm:()=>true};
 vm.runInNewContext(fs.readFileSync(__dirname+'/app.js','utf8'),ctx);
 return {data,status,input,button,read:()=>JSON.parse(data.get('agent-field-guide-v1'))};
}
const h=harness();h.button.listeners.click();assert.equal(h.read().grades['01'].next,'2026-11-02');assert.equal(h.read().grades['01'].level,0);
h.button.listeners.click();assert.equal(h.read().grades['01'].level,0,'same day must not inflate streak');
today='2026-11-02';h.button.listeners.click();assert.equal(h.read().grades['01'].next,'2026-11-05');assert.equal(h.read().grades['01'].level,1);
today='2026-11-03';h.button.listeners.click();assert.equal(h.read().grades['01'].level,1,'early recall must not advance interval');assert.equal(h.read().grades['01'].next,'2026-11-05','early recall must preserve scheduled review');
h.button.dataset.grade='help';h.button.listeners.click();assert.equal(h.read().grades['01'].next,'2026-11-04');assert.equal(h.read().grades['01'].level,0);
(async()=>{
 const before=h.read();const bad={version:1,grades:{'01':{grade:'mastered',date:'2026-11-03',next:'2026-11-04',level:0}},notes:{}};
 await h.input.listeners.change({target:{files:[{size:100,text:async()=>JSON.stringify(bad)}],value:'test'}});
 assert.deepEqual(h.read(),before,'invalid import must preserve current record');
 const valid={version:1,grades:{},notes:{'01-q1':'<script>not executable</script>'}};
 await h.input.listeners.change({target:{files:[{size:100,text:async()=>JSON.stringify(valid)}],value:'test'}});
 assert.equal(h.read().notes['01-q1'],'<script>not executable</script>');
 console.log('PASS: same-day, due-day, early review, failed review, invalid import, text-only notes');
})().catch(e=>{console.error(e);process.exitCode=1;});
