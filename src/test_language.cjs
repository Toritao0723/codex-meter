const fs=require('fs'),vm=require('vm'),assert=require('assert');
const dir=require('path').join(__dirname, 'ui/');
const elements=new Map(), sent=[];
function el(id){ if(!elements.has(id)) elements.set(id,{textContent:'',innerHTML:'',style:{},dataset:{},offsetWidth:352,offsetHeight:300,attrs:{},events:{},classList:{toggle(){},add(){},remove(){},contains(){return false}},setAttribute(k,v){this.attrs[k]=v},addEventListener(k,v){this.events[k]=v}});return elements.get(id);}
const context={window:{webkit:{messageHandlers:{meter:{postMessage:m=>sent.push(m)}}},CrabPet:{draw:()=> 'typing',titles:{typing:'小螃蟹在打电脑'},busy:['typing']}}, document:{getElementById:el,documentElement:el('root'),querySelector:el,querySelectorAll:()=>[]},matchMedia:()=>({matches:false,addEventListener(){}}),setInterval(){},requestAnimationFrame:f=>f(),Date,URLSearchParams};
vm.createContext(context); vm.runInContext(fs.readFileSync(dir+'task-nav.js','utf8'),context);context.window.TaskNavigation=context.TaskNavigation;vm.runInContext(fs.readFileSync(dir+'meter.js','utf8'),context);
const data={language:'zh',windows:[{known:true,label:'每周额度',percentUsed:69,resetsAt:Date.now()+86400000}],live:false,liveAt:Date.now()-600000,activity:{state:'working'},taskNav:{items:[{id:'demo',title:'保持原文',state:'working'}]}};
context.window.meter.update(data);assert.equal(el('remainingLabel').textContent,'剩余');
el('languageBtn').events.click();assert(sent.some(m=>m.type==='language'&&m.value==='en'));
context.window.meter.update({...data,language:'en'});assert.equal(el('remainingLabel').textContent,'left');assert.equal(el('plan').textContent,'Weekly quota');assert.equal(el('petTitle').textContent,'Typing away');assert.equal(el('taskState').textContent,'Working');assert.equal(el('taskTitle').textContent,'保持原文');assert(el('miniLive').innerHTML.includes('Not live'));
for(const mode of [{mini:true},{mini:true,minimized:true},{}]){context.window.meter.update({...data,...mode,language:'en'});assert.equal(el('resetLabel').textContent,'Resets in');}
el('languageBtn').events.click();assert(sent.some(m=>m.type==='language'&&m.value==='zh'));
context.window.meter.update(data);assert.equal(el('petTitle').textContent,'小螃蟹在打电脑');console.log('PASS: Chinese/English toggle, native preference messages, all modes, labels and original task titles');
