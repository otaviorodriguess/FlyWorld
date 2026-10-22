import {blocked,clamp} from './simulation.js';
export const EXPERIENCES=[
 {id:'nectar',name:'Banquete de néctar',icon:'✿',color:'#d889a8',description:'Encontrar flores e provar uma pequena reserva de néctar.',duration:2,reward:7,message:'Encontrou néctar entre as flores. A reserva volta a crescer depois de um minuto.'},
 {id:'dew',name:'Gotas de orvalho',icon:'◈',color:'#78c5da',description:'Parar junto às gotas e observar os reflexos da água.',duration:2,reward:5,message:'Explorou as gotas de orvalho, bem longe da água profunda.'},
 {id:'shelter',name:'Abrigo dos cogumelos',icon:'☂',color:'#d8a070',description:'Fazer uma pausa protegida sob um cogumelo gigante.',duration:4,reward:4,message:'Descansou no abrigo dos cogumelos e limpou as antenas.'},
 {id:'pollen',name:'Jardim de pólen',icon:'❋',color:'#e8bf53',description:'Coletar pólen dourado e levá-lo até as flores de néctar.',duration:2,reward:6,message:'Coletou pólen! Uma visita às flores de néctar completa a entrega.'},
 {id:'wind',name:'Clareira da brisa',icon:'≋',color:'#9bc4a5',description:'Sentir uma brisa que muda suavemente o caminho.',duration:3,reward:5,message:'Atravessou a clareira e experimentou a força da brisa.'},
 {id:'fireflies',name:'Dança dos vaga-lumes',icon:'✧',color:'#b5a5d6',description:'Acompanhar pontos de luz que dançam ao redor das flores.',duration:3,reward:6,message:'Observou a dança dos vaga-lumes. Cada luz segue seu próprio ritmo.'},
];
export function createSites(world){
 if(world.sites)return world.sites.map(site=>({...EXPERIENCES.find(e=>e.id===site.id),...site,radius:78}));
 const sites=[];
 EXPERIENCES.forEach((definition,i)=>{let point=null;const base=-Math.PI/2+i*Math.PI/3;
  for(let radius=165;radius<=1000&&!point;radius+=55)for(let offset=0;offset<12&&!point;offset++){
   const angle=base+offset*.09,x=clamp(3000+Math.cos(angle)*radius,110,world.width-110),z=clamp(2000+Math.sin(angle)*radius,110,world.height-110);
   if(!blocked(world,x,z,90)&&sites.every(s=>Math.hypot(s.x-x,s.z-z)>195))point=[x,z];
  }
  if(point)sites.push({...definition,x:point[0],z:point[1],radius:78});
 });return sites;
}
export class GardenExperiences{
 constructor(world,memory={}){memory=memory&&typeof memory==='object'?memory:{};this.sites=createSites(world);this.discoveries={};for(const s of this.sites){const count=memory.discoveries?.[s.id];if(Number.isInteger(count)&&count>0)this.discoveries[s.id]=Math.min(count,1000000);}this.journal=Array.isArray(memory.journal)?memory.journal.filter(e=>e&&typeof e.text==='string'&&Number.isFinite(e.time)).slice(-20):[];this.pollen=memory.pollen===true;this.deliveries=Number.isInteger(memory.deliveries)&&memory.deliveries>=0?memory.deliveries:0;this.cooldowns={};this.active=null;this.elapsed=0;this.now=0;this.lastEvent=null;}
 interest(body){return this.sites.filter(s=>((this.cooldowns[s.id]||0)<=this.now||(s.id==='nectar'&&this.pollen))&&Math.hypot(s.x-body.x,s.z-body.z)<650).sort((a,b)=>(a.id==='nectar'&&this.pollen?-1:this.discoveries[a.id]||0)-(b.id==='nectar'&&this.pollen?-1:this.discoveries[b.id]||0)||Math.hypot(a.x-body.x,a.z-body.z)-Math.hypot(b.x-body.x,b.z-body.z))[0]||null;}
 current(body){return this.sites.find(s=>Math.hypot(s.x-body.x,s.z-body.z)<s.radius&&((this.cooldowns[s.id]||0)<=this.now||(s.id==='nectar'&&this.pollen)))||null;}
 update(body,dt,time){this.now=time;const site=this.current(body);if(!site){this.active=null;this.elapsed=0;return null;}if(this.active?.id!==site.id){this.active=site;this.elapsed=0;return {type:'arrival',site,reward:site.reward};}this.elapsed+=dt;if(this.elapsed<site.duration)return null;
  let text=site.message;const effects={};if(site.id==='pollen')this.pollen=true;if(site.id==='nectar'){effects.food=true;if(this.pollen){this.pollen=false;this.deliveries++;text='Entrega concluída! O pólen chegou às flores de néctar.';}}if(site.id==='shelter')effects.groom=true;
  this.discoveries[site.id]=(this.discoveries[site.id]||0)+1;this.cooldowns[site.id]=time+60;const entry={time,text};this.journal.push(entry);this.journal=this.journal.slice(-20);this.lastEvent=entry;this.active=null;this.elapsed=0;return {type:'complete',site,text,effects};
 }
 progress(){return this.active?Math.min(1,this.elapsed/this.active.duration):0;}
 snapshot(){return {discoveries:this.discoveries,journal:this.journal,pollen:this.pollen,deliveries:this.deliveries};}
}
// Coarse obstacle-aware routes, with swept checks along every edge.
export function planRoute(world,start,end){
 const size=60,key=(x,z)=>`${x},${z}`,cell=p=>[Math.round(p[0]/size),Math.round(p[1]/size)];
 const from=cell(start),to=cell(end),goal=key(...to),open=[from],came=new Map(),cost=new Map([[key(...from),0]]),closed=new Set();
 const clear=(a,b)=>{const distance=Math.hypot(b[0]-a[0],b[1]-a[1]);for(let t=0;t<=distance;t+=6){const f=distance?t/distance:0;if(blocked(world,a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f))return false;}return !blocked(world,...b);};
 if(clear(start,end))return [end];
 for(let count=0;open.length&&count<10000;count++){
  open.sort((a,b)=>(cost.get(key(...a))+Math.hypot(a[0]-to[0],a[1]-to[1]))-(cost.get(key(...b))+Math.hypot(b[0]-to[0],b[1]-to[1])));const current=open.shift(),id=key(...current);if(closed.has(id))continue;closed.add(id);
  if(id===goal){const path=[end];let node=current;while(key(...node)!==key(...from)){path.unshift([node[0]*size,node[1]*size]);node=came.get(key(...node));}if(path.length&&!clear(start,path[0]))return [];return path;}
  for(const [dx,dz]of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]]){const next=[current[0]+dx,current[1]+dz],nid=key(...next);if(closed.has(nid)||!clear([current[0]*size,current[1]*size],[next[0]*size,next[1]*size]))continue;const value=cost.get(id)+Math.hypot(dx,dz);if(value<(cost.get(nid)??Infinity)){cost.set(nid,value);came.set(nid,current);open.push(next);}}
 }return [];
}
export function applyBreeze(world,body,dt,time){const angle=.35+Math.sin(time*.6)*.2,x=body.x+Math.cos(angle)*13*dt,z=body.z+Math.sin(angle)*13*dt;if(!blocked(world,x,z)){body.x=x;body.z=z;}else body.collision=true;}
