const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(__dirname+'/app.js','utf8');
function element(extra={}){return {textContent:'',style:{},dataset:{},listeners:{},hidden:false,disabled:false,offsetWidth:0,classList:{values:new Set(),contains(k){return this.values.has(k)},toggle(k,on){if(on===undefined)on=!this.values.has(k);on?this.values.add(k):this.values.delete(k);return on},remove(k){this.values.delete(k)},add(k){this.values.add(k)}},addEventListener(t,fn){this.listeners[t]=fn},setAttribute(k,v){this[k]=v},querySelector(){return null},querySelectorAll(){return []},...extra};}
function setup(lesson,withSvg){
 const cases=lesson.diagram.walkthrough.cases,buttons={},intervals=new Map();let timerId=0;
 const nodes=withSvg?lesson.diagram.nodes.map((_,i)=>element({dataset:{node:String(i)}})):[];
 const groups=cases.map(c=>{const frames=c.steps.map((s,i)=>{const title=element({textContent:s.title}),packet=element();return element({dataset:{nodeIndex:String(s.node),failure:String(s.failure)},hidden:i!==0,querySelector:q=>q==='h3'?title:q==='.flow-packet'?packet:null,example:s});});return element({dataset:{flowCasePanel:c.id},querySelectorAll:q=>q==='[data-flow-frame]'?frames:[],frames});});
 for(const q of ['[data-play]','[data-step]','[data-prev]','[data-reset]','[data-flow-case]','[data-flow-speed]','[data-flow-progress]','[data-flow-status]'])buttons[q]=element();
 buttons['[data-flow-case]'].value='normal';buttons['[data-flow-speed]'].value='2000';
 const flow=element({querySelector:q=>buttons[q]||null,querySelectorAll:q=>q==='[data-flow-case-panel]'?groups:q==='[data-node]'?nodes:[]});
 const sidebar=element(),toast=element(),docEvents={};
 const document={body:{dataset:{page:'lessons/test.html'}},hidden:false,activeElement:{tagName:'BODY'},querySelector:q=>q==='.sidebar'?sidebar:q==='#toast'?toast:null,querySelectorAll:q=>q==='[data-flow]'?[flow]:[],addEventListener(t,fn){(docEvents[t]??=[]).push(fn)}};
 const local=new Map();
 vm.runInNewContext(source,{document,window:{COURSE_LESSONS:[{id:lesson.id}],innerWidth:1200,addEventListener(){}},localStorage:{getItem:k=>local.get(k)||null,setItem:(k,v)=>local.set(k,v)},setTimeout:()=>1,clearTimeout(){},setInterval(fn){const id=++timerId;intervals.set(id,fn);return id},clearInterval(id){intervals.delete(id)},console,Date});
 const click=q=>buttons[q].listeners.click();
 return {groups,nodes,buttons,intervals,document,click,select(id){buttons['[data-flow-case]'].value=id;buttons['[data-flow-case]'].listeners.change()},tick(){for(const fn of Array.from(intervals.values()))fn()},status:()=>buttons['[data-flow-status]'].textContent,visible:()=>groups.filter(g=>!g.hidden).flatMap(g=>g.frames.filter(f=>!f.hidden))};
}
const files=fs.readdirSync(__dirname+'/lessons').filter(n=>n.endsWith('.json'));
for(const file of files){
 const lesson=JSON.parse(fs.readFileSync(path.join(__dirname,'lessons',file)));
 for(const withSvg of [true,false]){
  const h=setup(lesson,withSvg),normal=lesson.diagram.walkthrough.cases[0];
  assert.equal(h.visible().length,1);assert.equal(h.visible()[0].example.input,normal.steps[0].input);
  assert(h.buttons['[data-prev]'].disabled);
  h.click('[data-play]');assert.equal(h.intervals.size,1);assert.equal(h.buttons['[data-play]'].textContent,'暂停');
  h.tick();assert.equal(h.visible()[0].example.output,normal.steps[1].output);assert(h.status().startsWith('第 2/'));
  h.click('[data-play]');assert.equal(h.intervals.size,0,'pause cancels automatic advancement');
  h.tick();assert.equal(h.visible()[0].example.output,normal.steps[1].output);
  h.click('[data-prev]');assert.equal(h.visible()[0].example.input,normal.steps[0].input);
  h.click('[data-play]');for(let i=0;i<normal.steps.length;i++)h.tick();
  assert.equal(h.intervals.size,0);assert(h.buttons['[data-step]'].disabled);assert(h.status().includes('演示完成'));
  h.select('failure');assert.equal(h.visible().length,1);assert(h.status().startsWith('第 1/'));
  h.click('[data-play]');for(let i=0;i<10;i++)h.tick();
  assert.equal(h.intervals.size,0);const last=lesson.diagram.walkthrough.cases[1].steps.at(-1);assert(h.status().includes(last.failure?'本分支停止':'演示完成'));assert.equal(h.visible()[0].example.failure,last.failure);
  h.click('[data-reset]');assert(h.status().startsWith('第 1/'));assert.equal(h.intervals.size,0);
 }
}
console.log('PASS: 26 lessons × SVG present/absent; visible frames, play, timer advance, pause, previous, completion, failure selection/stop, reset');
