import './style.css';
import {Garden} from './garden.js';
import {GardenExperiences,planRoute,applyBreeze} from './experiences.js';
import {Learner,blocked,sense,move,wrap,clamp,validateMemory} from './simulation.js';
const $=id=>document.getElementById(id);
const STORAGE='flyworld-learning-v1';
const state={mode:'free',paused:false,time:0,foods:0,speed:1,action:'explore',target:null,until:0,replayTime:0,record:null,selected:'food',manual:false,visit:null,route:[],groomUntil:0};
let garden,world,agent,body,experiences,records=[],phase=0,accumulator=0,last=performance.now(),lastUI=0,lastSave=0,toastUntil=0;
const keys=new Set();
function notify(text){$('toast').textContent=text;$('toast').style.opacity=1;toastUntil=performance.now()+6000;}
function save(){try{localStorage.setItem(STORAGE,JSON.stringify({...agent.snapshot(),experiences:experiences.snapshot()}));}catch{notify('Não foi possível salvar neste navegador. Use Exportar memória em Informações.');}}
function choose(action,point=null){
 if(state.mode!=='free'){notify('O replay é uma gravação. Volte ao modo Livre para interações guiadas.');return;}
 agent.suspend();state.visit=null;state.route=[];state.action=action;state.selected=['call','play','pet'].includes(action)?action:'food';state.until=state.time+({feed:12,call:20,pet:4,play:16,explore:0}[action]);state.target=null;
 if(['feed','call','play'].includes(action)){const target=point||[body.x+Math.cos(body.angle)*100,body.z+Math.sin(body.angle)*100];target[0]=clamp(target[0],30,world.width-30);target[1]=clamp(target[1],30,world.height-30);if(blocked(world,...target,25)){state.action='explore';notify('Escolha um ponto livre, longe da água e dos obstáculos.');return;}state.target=target;if(action==='feed'){world.foods.push(target);garden.refreshFood();}}
 notify({feed:'Uma fruta para sua exploradora. Ela vai tentar encontrá-la.',call:'Um convite no jardim. Clique no chão para mudar o destino.',pet:'Limpando as antenas · animação lúdica, não uma resposta neural.',play:'Uma pequena luz para seguir · brincadeira artificial.',explore:'Livre para explorar, aprender e fazer novas descobertas.'}[action]);
 document.querySelectorAll('[data-action]').forEach(button=>button.classList.toggle('selected',button.dataset.action===action));
}
function visitExperience(id){
 if(state.mode!=='free'){notify('Volte ao modo Livre para visitar as experiências.');return;}
 const site=experiences.sites.find(s=>s.id===id);if(!site)return;
 const route=planRoute(world,[body.x,body.z],[site.x,site.z]);if(!route.length){notify('Não há um caminho livre até esse local. Aproxime-se pelo mapa e tente novamente.');return;}
 choose('call',[site.x,site.z]);state.visit=id;state.route=route;state.until=state.time+300;state.paused=false;notify(`Convite: ${site.name}. ${site.description}`);
}
function guided(){
 if(state.action==='explore'||state.time>=state.until){state.action='explore';state.target=null;return null;}
 if(state.action==='pet')return [0,0];
 if(!state.target)return null;
 if(state.visit){while(state.route.length>1&&Math.hypot(state.route[0][0]-body.x,state.route[0][1]-body.z)<12)state.route.shift();const waypoint=state.route[0]||state.target,distance=Math.hypot(waypoint[0]-body.x,waypoint[1]-body.z),turn=wrap(Math.atan2(waypoint[1]-body.z,waypoint[0]-body.x)-body.angle);return distance<10?[0,0]:[Math.abs(turn)<.25?.65:0,clamp(turn,-1,1)];}

 const [x,z]=state.target,tx=x+(state.action==='play'?Math.cos(state.time*1.4)*45:0),tz=z+(state.action==='play'?Math.sin(state.time*1.4)*45:0);
 const distance=Math.hypot(tx-body.x,tz-body.z),turn=wrap(Math.atan2(tz-body.z,tx-body.x)-body.angle);return distance<24?[0,0]:[Math.abs(turn)<.8?.7:.22,clamp(turn,-1,1)];
}
async function loadRecording(id){const entry=records.find(record=>record.id===id);if(!entry)return;const response=await fetch(entry.file);if(!response.ok)throw Error('Não foi possível abrir a gravação.');state.record=await response.json();state.replayTime=0;$('spikes').textContent=state.record.spikes.toLocaleString('pt-BR');$('active-neurons').textContent=state.record.active;$('brain-state').textContent='Spikes reais gravados · reprodução, sem simulação live.';$('source-info').textContent=`Fonte: ${state.record.source}. SHA-256 do Parquet original: ${state.record.sha256}. Sugar GRNs: ${state.record.sugar_spikes} spikes; P9: ${state.record.p9_spikes}. O raster mostra uma amostra dos 16 neurônios mais ativos; os IDs completos constam nos dados públicos da gravação.`;drawRaster();}
async function mode(mode){state.mode=mode;state.visit=null;state.route=[];experiences.active=null;experiences.elapsed=0;state.action='explore';state.target=null;state.paused=false;agent.suspend();$('free-mode').classList.toggle('active',mode==='free');$('replay-mode').classList.toggle('active',mode==='replay');$('neural-details').hidden=mode!=='replay';$('learning').disabled=mode==='replay';$('mode-description').textContent=mode==='free'?'Autonomia com aprendizagem artificial.':'Gravação neural · movimento não inferido de spikes arbitrários.';
 if(mode==='replay'){state.speed=.1;$('speed').value='.1';await loadRecording($('recording').value);notify('Replay real de açúcar. P9 não dispara nesta amostra: use as setas para movimento manual.');}else{state.speed=1;$('speed').value='1';$('brain-state').textContent='Cérebro completo: disponível no aplicativo local.';notify('De volta à exploração autônoma. Sua memória foi preservada.');}}
function tick(dt){let command=[0,0],learning=false;state.manual=keys.has('ArrowUp')||keys.has('ArrowLeft')||keys.has('ArrowRight')||keys.has('ArrowDown');
 if(state.manual){agent.suspend();command=[keys.has('ArrowUp')&&!keys.has('ArrowDown')?.85:0,(keys.has('ArrowRight')?1:0)-(keys.has('ArrowLeft')?1:0)];}
 else if(state.mode==='free'){
  const nearby=experiences.current(body);
  if(nearby){command=[0,0];}
  else {const interaction=guided();if(interaction){agent.suspend();command=interaction;}else{command=agent.command(world,body,sense(world,body),experiences.interest(body));learning=true;}}
 }
 else if(state.record){state.replayTime=Math.min(state.record.duration_ms,state.replayTime+dt*1000);if(state.replayTime>=state.record.duration_ms){state.paused=true;notify('Fim da gravação. Repetir reproduz os mesmos dados; Livre retoma a exploração.');}}
 let collected=move(world,body,command,dt);
 if(state.mode==='free'){
  if(experiences.active?.id==='wind')applyBreeze(world,body,dt,state.time);
  const event=experiences.update(body,dt,state.time);
  if(event?.type==='arrival'){
   if(!state.manual&&state.action==='explore'&&agent.enabled&&agent.state!==null)agent.learn(agent.state,agent.action,event.reward,agent.state,true);
   agent.suspend();learning=false;notify(`${event.site.name} · ${event.site.description}`);
  }
  if(event?.type==='complete'){
   if(event.effects.food){collected++;}
   if(event.effects.groom)state.groomUntil=state.time+3;
   notify(event.text);save();if(state.visit===event.site.id){state.visit=null;state.route=[];state.action='explore';state.target=null;state.until=0;agent.suspend();}
  }
 }
 if(learning)agent.observe(body,dt,collected);if(collected){state.foods+=collected;garden.refreshFood();notify(`${state.foods===1?'Primeira fruta encontrada!':`Mais uma descoberta: ${state.foods} frutas encontradas.`} A experiência faz parte do jardim.`);if(experiences.lastEvent&&state.time-experiences.lastEvent.time<.1)notify(experiences.lastEvent.text);}state.time+=dt;
}
function drawMap(){const canvas=$('map'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.fillStyle='#b3c896';ctx.fillRect(0,0,w,h);const point=(x,z)=>[x/world.width*w,z/world.height*h];ctx.strokeStyle='#ddd2a7';ctx.lineWidth=4;ctx.beginPath();for(let x=0;x<=world.width;x+=80){const [px,py]=point(x,2000+Math.sin(x*.0018)*260);if(!x)ctx.moveTo(px,py);else ctx.lineTo(px,py);}ctx.stroke();ctx.fillStyle='#7aaea1';for(const [x,z,rx,rz]of world.ponds){ctx.beginPath();ctx.ellipse(x/world.width*w,z/world.height*h,rx/world.width*w,rz/world.height*h,0,0,Math.PI*2);ctx.fill();}ctx.fillStyle='#92ad75';for(const cell of Object.keys(agent.visits)){const [x,z]=cell.split(',').map(Number);ctx.fillRect(x*160/world.width*w,z*160/world.height*h,160/world.width*w,160/world.height*h);}ctx.fillStyle='#698751';for(const o of world.obstacles){ctx.beginPath();ctx.arc(...point(o.x,o.y),2,0,Math.PI*2);ctx.fill();}for(const site of experiences.sites){ctx.fillStyle=site.color;ctx.beginPath();ctx.arc(...point(site.x,site.z),4,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#fffbea';ctx.lineWidth=1;ctx.stroke();}ctx.fillStyle='#f8edba';for(const p of world.foods){ctx.beginPath();ctx.arc(...point(...p),1.3,0,Math.PI*2);ctx.fill();}const [x,z]=point(body.x,body.z);ctx.fillStyle='#304f39';ctx.beginPath();ctx.arc(x,z,4,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#304f39';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,z);ctx.lineTo(x+Math.cos(body.angle)*9,z+Math.sin(body.angle)*9);ctx.stroke();}
function drawRaster(){if(!state.record)return;const canvas=$('raster'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,r=state.record;ctx.clearRect(0,0,w,h);ctx.strokeStyle='#b5c7a0';ctx.lineWidth=.5;for(let i=0;i<16;i++){ctx.beginPath();ctx.moveTo(0,(i+.5)*h/16);ctx.lineTo(w,(i+.5)*h/16);ctx.stroke();}ctx.fillStyle='#507962';for(const [time,row]of r.raster)ctx.fillRect(time/r.duration_ms*w,(row+.5)*h/16,1,3);ctx.fillStyle='#bd8d4b';ctx.fillRect(state.replayTime/r.duration_ms*w,0,2,h);$('neural-time').textContent=`${Math.round(state.replayTime)} / ${r.duration_ms.toLocaleString('pt-BR')} ms`;}
function updateUI(){const seconds=Math.floor(state.time);$('time').textContent=`${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;$('foods').textContent=state.foods;$('experience').textContent=agent.steps.toLocaleString('pt-BR');$('regions').textContent=Object.keys(agent.visits).length;$('reward').textContent=agent.lastReward.toFixed(2).replace('.',',');$('status').textContent=state.paused?'Pausado':state.manual?'Manual':state.mode==='replay'?'Reprodução':'Explorando';$('action').textContent=state.manual?'Controle manual':state.mode==='replay'?'Observar spikes':state.action==='pet'?'Limpar antenas':['Avançar','Curvar à esquerda','Curvar à direita','Girar à esquerda','Girar à direita','Avançar devagar','Parar'][agent.action];updateExperiencesUI();$('pause').textContent=state.paused?'▶ Continuar':'Ⅱ Pausar';drawMap();if(state.mode==='replay')drawRaster();}
function updateExperiencesUI(){
 const found=Object.keys(experiences.discoveries).length;$('discovered').textContent=`${found} / ${experiences.sites.length}`;
 $('pollen').textContent=experiences.pollen?'Pólen coletado':`${experiences.deliveries} entregas`;
 $('adventure-progress').value=experiences.progress();
 const destination=experiences.sites.find(s=>s.id===state.visit);const waiting=destination&&Math.hypot(destination.x-body.x,destination.z-body.z)<destination.radius&&experiences.cooldowns[destination.id]>state.time;
 $('adventure-status').textContent=state.mode==='replay'?'Experiências pausadas durante o replay.':experiences.active?`${experiences.active.name} · ${Math.round(experiences.progress()*100)}%`:waiting?`${destination.name} · renovando em ${Math.ceil(experiences.cooldowns[destination.id]-state.time)} s`:destination?`A caminho: ${destination.name}`:'Livre para descobrir o próximo cantinho.';
 for(const button of $('adventures').children){const id=button.dataset.experience;button.disabled=state.mode!=='free';button.classList.toggle('completed',Boolean(experiences.discoveries[id]));button.setAttribute('aria-pressed',String(state.visit===id));button.querySelector('small').textContent=experiences.discoveries[id]?`Visitado ${experiences.discoveries[id]}×`:'Descobrir';}
 const signature=JSON.stringify(experiences.journal);if($('journal').dataset.signature!==signature){$('journal').dataset.signature=signature;$('journal').replaceChildren();for(const entry of [...experiences.journal].reverse()){const li=document.createElement('li');li.textContent=entry.text;$('journal').append(li);}if(!experiences.journal.length){const li=document.createElement('li');li.textContent='As primeiras descobertas aparecerão aqui.';$('journal').append(li);}}
 if(experiences.active)$('action').textContent=experiences.active.name;
}
function frame(now){const elapsed=Math.min((now-last)/1000,.08);last=now;if(!document.hidden&&!state.paused&&!$('help-dialog').open){accumulator+=elapsed*state.speed;let steps=0;while(accumulator>=1/60&&steps++<24){tick(1/60);accumulator-=1/60;}}
 let target=state.time<state.until?state.target:null;if(target&&state.action==='play')target=[target[0]+Math.cos(state.time*1.4)*45,target[1]+Math.sin(state.time*1.4)*45];garden.setMarker(target,state.action==='play');garden.animateExperiences(state.time,experiences.active?.id,experiences.pollen);garden.animate(body,state.time,(state.action==='pet'&&state.time<state.until)||experiences.active?.id==='shelter'||state.time<state.groomUntil);
 if(now-lastUI>150){updateUI();lastUI=now;}if(now-lastSave>5000){save();lastSave=now;}if(now>toastUntil)$('toast').style.opacity=.25;requestAnimationFrame(frame);}
async function boot(){
 const [worldResponse,seedResponse,indexResponse]=await Promise.all([fetch('/world.json'),fetch('/learning-seed.json'),fetch('/neural/index.json')]);if(!worldResponse.ok||!seedResponse.ok||!indexResponse.ok)throw Error('Os arquivos do mundo não foram carregados. Atualize a página.');world=await worldResponse.json();const seed=await seedResponse.json();records=await indexResponse.json();let memory=null;try{const value=JSON.parse(localStorage.getItem(STORAGE)||'null');if(validateMemory(value))memory=value;}catch{}
 agent=new Learner(seed,memory);body={x:3000,z:2000,angle:-1.3,speed:0,collision:false};garden=new Garden($('scene'),world);experiences=new GardenExperiences(world,memory?.experiences);garden.buildExperienceSites(experiences.sites);
 for(const site of experiences.sites){const button=document.createElement('button');button.dataset.experience=site.id;button.title=site.description;button.setAttribute('aria-label',`Visitar ${site.name}`);const icon=document.createElement('span');icon.textContent=site.icon;const label=document.createTextNode(site.name);const small=document.createElement('small');small.style.display='block';small.textContent='Descobrir';button.append(icon,label,small);button.addEventListener('click',()=>visitExperience(site.id));$('adventures').append(button);}

 for(const entry of records)$('recording').add(new Option(entry.label,entry.id));
 document.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>choose(button.dataset.action)));
 $('free-mode').addEventListener('click',()=>mode('free').catch(showError));$('replay-mode').addEventListener('click',()=>mode('replay').catch(showError));$('library').addEventListener('click',()=>mode('replay').then(()=>$('recording').focus()).catch(showError));$('recording').addEventListener('change',()=>loadRecording($('recording').value).catch(showError));$('restart-replay').addEventListener('click',()=>{state.replayTime=0;state.paused=false;});
 $('pause').addEventListener('click',()=>state.paused=!state.paused);$('speed').addEventListener('change',()=>state.speed=Number($('speed').value));$('learning').addEventListener('change',()=>{agent.enabled=$('learning').checked;agent.suspend();notify(agent.enabled?'Aprendizagem artificial retomada.':'Atualizações Q pausadas. A política aprendida continua disponível.');});
 $('overview').addEventListener('click',()=>{$('overview').textContent=garden.overview(body)?'Visão geral':'Seguir mosca';});$('panel-toggle').addEventListener('click',()=>$('monitor').classList.toggle('open'));
 $('help').addEventListener('click',()=>$('help-dialog').showModal());$('close-help').addEventListener('click',()=>$('help-dialog').close());$('export-memory').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({...agent.snapshot(),experiences:experiences.snapshot()},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='flyworld-memory.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 let down=null;garden.renderer.domElement.addEventListener('pointerdown',event=>down=[event.clientX,event.clientY]);garden.renderer.domElement.addEventListener('pointerup',event=>{if(event.button!==0||!down||Math.hypot(event.clientX-down[0],event.clientY-down[1])>8)return;const point=garden.pick(event);if(!point||blocked(world,...point,25))return;if(state.selected==='call'||state.selected==='play')choose(state.selected,point);else if(state.selected==='pet'){if(Math.hypot(point[0]-body.x,point[1]-body.z)<70)choose('pet');else notify('Clique perto da mosca para interagir.');}else if(state.mode==='free'){world.foods.push(point);garden.refreshFood();notify('Fruta adicionada ao jardim.');}});
 $('map').addEventListener('click',event=>{const rect=$('map').getBoundingClientRect(),point=[(event.clientX-rect.left)/rect.width*world.width,(event.clientY-rect.top)/rect.height*world.height];choose('call',point);});
 window.addEventListener('keydown',event=>{if($('help-dialog').open||['INPUT','SELECT','BUTTON'].includes(document.activeElement.tagName))return;if(event.key.startsWith('Arrow')){event.preventDefault();keys.add(event.key);}if(event.code==='Space'){event.preventDefault();state.paused=!state.paused;}const action={b:'feed',c:'call',k:'pet',j:'play',l:'explore'}[event.key.toLowerCase()];if(action)choose(action);});window.addEventListener('keyup',event=>keys.delete(event.key));window.addEventListener('blur',()=>keys.clear());window.addEventListener('pagehide',save);
 // Read-only diagnostics for automated verification; not a control backdoor.
 window.flyworld={snapshot:()=>({mode:state.mode,time:state.time,foods:state.foods,updates:agent.steps,paused:state.paused,neuralLive:false,recordedSpikes:state.record?.spikes||0,memory:validateMemory(agent.snapshot()),experiences:{sites:experiences.sites.map(s=>({id:s.id,x:s.x,z:s.z})),discoveries:{...experiences.discoveries},active:experiences.active?.id||null,visit:state.visit,pollen:experiences.pollen,deliveries:experiences.deliveries,journal:experiences.journal.length},position:{x:body.x,z:body.z}})};
 updateUI();requestAnimationFrame(frame);
}
function showError(error){console.error(error);$('error').hidden=false;$('error').textContent=`Não foi possível iniciar o FlyWorld: ${error.message}. Este jardim precisa de WebGL 2 habilitado. Tente atualizar o navegador ou ativar a aceleração gráfica.`;}
boot().catch(showError);
