const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export const ACTIONS=[-1,0,1],DECISION_DT=.05;
export function rng(seed){let state=seed>>>0;return ()=>((state=Math.imul(state,1664525)+1013904223>>>0)/4294967296);}
export class Pong{
 constructor(seed=1){const random=rng(seed);this.width=640;this.height=360;this.paddle=180;this.halfPaddle=32;this.radius=6;this.time=0;this.hits=0;this.done=false;this.lost=false;this.ball={x:420,y:65+random()*230,vx:-(210+random()*40),vy:(random()>.5?1:-1)*(70+random()*130)};}
 step(action,dt=DECISION_DT){if(this.done)return {reward:0,done:true};let reward=0;dt=clamp(Number.isFinite(dt)?dt:0,0,.1);const steps=Math.max(1,Math.ceil(dt*Math.max(Math.abs(this.ball.vx),Math.abs(this.ball.vy),280)/3)),step=dt/steps;
  for(let i=0;i<steps&&!this.done;i++){this.paddle=clamp(this.paddle+clamp(action,-1,1)*280*step,32,328);const oldX=this.ball.x;this.ball.x+=this.ball.vx*step;this.ball.y+=this.ball.vy*step;
   if(this.ball.y<6){this.ball.y=12-this.ball.y;this.ball.vy=Math.abs(this.ball.vy);}if(this.ball.y>354){this.ball.y=708-this.ball.y;this.ball.vy=-Math.abs(this.ball.vy);}if(this.ball.x>634){this.ball.x=1268-this.ball.x;this.ball.vx=-Math.abs(this.ball.vx);}
   if(this.ball.vx<0&&oldX>=52&&this.ball.x<=52&&Math.abs(this.ball.y-this.paddle)<=38){this.ball.x=104-this.ball.x;this.ball.vx=Math.abs(this.ball.vx);this.ball.vy=clamp(this.ball.vy+(this.ball.y-this.paddle)*2,-220,220);this.hits++;reward++;}
   this.time+=step;if(this.ball.x < -6){this.lost=true;this.done=true;reward--;}else if(this.time>=30){this.time=30;this.done=true;}
  }return {reward,done:this.done};
 }
}
const validTable=t=>t&&typeof t==='object'&&!Array.isArray(t)&&Object.keys(t).length<=20000&&Object.entries(t).every(([key,v])=>key.length<=100&&Array.isArray(v)&&v.length===3&&v.every(n=>Number.isFinite(n)&&Math.abs(n)<1e8));
export function validatePongMemory(m){return Boolean(m&&m.schema===1&&validTable(m.q)&&validTable(m.examples)&&['updates','demonstrations','episodes','totalHits','losses'].every(k=>Number.isSafeInteger(m[k])&&m[k]>=0)&&Array.isArray(m.history)&&m.history.length<=100&&m.history.every(e=>e&&Number.isFinite(e.hits)&&Number.isFinite(e.time)));}
export class PongAgent{
 constructor(memory=null){const m=validatePongMemory(memory)?memory:null;this.q=structuredClone(m?.q||{});this.examples=structuredClone(m?.examples||{});this.updates=m?.updates||0;this.demonstrations=m?.demonstrations||0;this.episodes=m?.episodes||0;this.totalHits=m?.totalHits||0;this.losses=m?.losses||0;this.history=structuredClone(m?.history||[]);}
 state(g){const b=g.ball;return [clamp(Math.floor((b.y-g.paddle)/35),-5,5),Math.min(3,Math.floor(b.x/160)),Math.min(3,Math.floor(b.y/90)),+(b.vx>0),Math.sign(b.vy),Math.min(3,Math.floor(g.paddle/90))].join(':');}
 preference(s){const values=this.q[s]||this.examples[s]||[0,0,0],best=Math.max(...values),choices=values.flatMap((v,i)=>v===best?[i]:[]);return choices;}
 act(g,{explore=true,rng:random=Math.random}={}){const epsilon=explore?Math.max(.03,.45*Math.exp(-this.episodes/3500)):0;if(random()<epsilon)return Math.floor(random()*3)-1;const choices=this.preference(this.state(g));return choices[Math.min(choices.length-1,Math.floor(random()*choices.length))]-1;}
 demonstrate(state,action){const counts=this.examples[state]||(this.examples[state]=[0,0,0]);counts[clamp(action+1,0,2)]++;this.demonstrations++;}
 update(state,action,reward,next,terminal){const values=this.q[state]||(this.q[state]=[0,0,0]);const index=action+1,target=reward+(terminal?0:.99*Math.max(...(this.q[next]||[0,0,0])));values[index]+=.18*(target-values[index]);this.updates++;}
 finish(g){this.episodes++;this.totalHits+=g.hits;this.losses+=+g.lost;this.history.push({hits:g.hits,time:g.time});this.history=this.history.slice(-100);}
 snapshot(){return {schema:1,kind:'artificial Pong Q-learning',q:structuredClone(this.q),examples:structuredClone(this.examples),updates:this.updates,demonstrations:this.demonstrations,episodes:this.episodes,totalHits:this.totalHits,losses:this.losses,history:structuredClone(this.history)};}
}
