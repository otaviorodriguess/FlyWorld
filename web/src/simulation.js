export const ACTIONS=[[.85,0],[.55,-.65],[.55,.65],[0,-1],[0,1],[.3,0],[0,0]];
export const wrap=a=>Math.atan2(Math.sin(a),Math.cos(a));
export const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function blocked(world,x,z,r=12){
 if(x<r||z<r||x>world.width-r||z>world.height-r)return true;
 for(const o of world.obstacles){const dx=Math.max(o.x-x,0,x-o.x-o.width),dz=Math.max(o.y-z,0,z-o.y-o.height);if(dx*dx+dz*dz<r*r)return true;}
 return world.ponds.some(([px,pz,rx,rz])=>((x-px)/(rx+r))**2+((z-pz)/(rz+r))**2<1);
}
export function sense(world,body){
 let food=null,distance=Infinity;
 for(const p of world.foods){const d=Math.hypot(p[0]-body.x,p[1]-body.z);if(d<distance){distance=d;food=p;}}
 const sensors={food:Math.max(0,1-distance/220),distance,bearing:food?wrap(Math.atan2(food[1]-body.z,food[0]-body.x)-body.angle):0};
 for(const [name,offset] of [['front',0],['left',-.6],['right',.6]]){let hit=220;for(let d=12;d<=220;d+=8){if(blocked(world,body.x+Math.cos(body.angle+offset)*d,body.z+Math.sin(body.angle+offset)*d)){hit=d;break;}}sensors[name]=1-hit/220;}
 return sensors;
}
export function move(world,body,command,dt){
 const [drive,turn]=command;body.angle=wrap(body.angle+turn*2.8*dt);body.speed=clamp(drive,0,1)*110;body.collision=false;
 const steps=Math.max(1,Math.ceil(body.speed*dt/6));
 for(let i=0;i<steps;i++){const x=body.x+Math.cos(body.angle)*body.speed*dt/steps,z=body.z+Math.sin(body.angle)*body.speed*dt/steps;if(blocked(world,x,z)){body.speed=0;body.collision=true;break;}body.x=x;body.z=z;}
 let collected=0;world.foods=world.foods.filter(p=>{if(Math.hypot(p[0]-body.x,p[1]-body.z)<25){collected++;return false;}return true;});return collected;
}
export class Learner{
 constructor(seed={},memory=null){const source=memory?.schema===1?memory:seed;this.q=structuredClone(source.q||{});this.steps=source.steps||0;this.visits=memory?.visits||{};this.foods=memory?.foods||{};this.enabled=true;this.state=null;this.action=0;this.elapsed=0;this.reward=0;this.lastReward=0;this.goal=null;this.exploreGoal=null;this.previousDistance=null;this.cell=null;this.collisionPending=false;}
 epsilon(){return this.enabled?Math.max(.05,.28*Math.exp(-this.steps/6000)):0;}
 values(state){return this.q[state]??(this.q[state]=[.02,0,0,0,0,0,-.02]);}
 learn(state,action,reward,next,terminal=false){const values=this.values(state);values[action]+=.18*(reward+(terminal?0:.92*Math.max(...this.values(next)))-values[action]);this.steps++;this.lastReward=reward;}
 command(world,body,sensors){
 let observed=null;if(sensors.food>0){const a=body.angle+sensors.bearing;observed=[body.x+Math.cos(a)*sensors.distance,body.z+Math.sin(a)*sensors.distance];this.foods[`${Math.round(observed[0]/20)},${Math.round(observed[1]/20)}`]=observed;}
 for(const [key,p] of Object.entries(this.foods)){if(Math.hypot(p[0]-body.x,p[1]-body.z)<45&&(!observed||Math.hypot(p[0]-observed[0],p[1]-observed[1])>25))delete this.foods[key];}
 const remembered=Object.values(this.foods).sort((a,b)=>Math.hypot(a[0]-body.x,a[1]-body.z)-Math.hypot(b[0]-body.x,b[1]-body.z));
 if(remembered.length)this.goal=remembered[0];else{if(!this.exploreGoal||Math.hypot(this.exploreGoal[0]-body.x,this.exploreGoal[1]-body.z)<55){let best=Infinity;for(let i=0;i<8;i++){const a=i*Math.PI/4,x=clamp(body.x+Math.cos(a)*260,35,world.width-35),z=clamp(body.z+Math.sin(a)*260,35,world.height-35);const score=(this.visits[`${Math.floor(x/160)},${Math.floor(z/160)}`]||0)+Math.random()*.5;if(score<best){best=score;this.exploreGoal=[x,z];}}}this.goal=this.exploreGoal;}
 const distance=Math.hypot(this.goal[0]-body.x,this.goal[1]-body.z),bearing=wrap(Math.atan2(this.goal[1]-body.z,this.goal[0]-body.x)-body.angle);
 const state=[Math.min(7,Math.floor((bearing+Math.PI)/(Math.PI*2)*8)),Math.min(2,Math.floor(distance/80)),Math.min(2,Math.floor(sensors.front*3)),+(sensors.left>.55),+(sensors.right>.55),+(remembered.length>0)].join(':');
 if(this.state===null||this.elapsed>=.35){if(this.state!==null&&this.enabled)this.learn(this.state,this.action,this.reward-.02,state);this.state=state;this.action=Math.random()<this.epsilon()?Math.floor(Math.random()*7):this.values(state).indexOf(Math.max(...this.values(state)));this.elapsed=0;this.reward=0;this.previousDistance=distance;this.collisionPending=false;}
 let command=[...ACTIONS[this.action]];if(sensors.front>.7)command=[Math.min(command[0],.12),sensors.left<sensors.right?-1:1];return command;
 }
 observe(body,dt,collected){this.elapsed+=dt;const cell=`${Math.floor(body.x/160)},${Math.floor(body.z/160)}`;if(cell!==this.cell){this.reward+=(this.visits[cell]||0)?-.035:1.2;this.visits[cell]=(this.visits[cell]||0)+1;this.cell=cell;}if(this.goal){const distance=Math.hypot(this.goal[0]-body.x,this.goal[1]-body.z);if(this.previousDistance!==null)this.reward+=clamp((this.previousDistance-distance)*.018,-.2,.2);this.previousDistance=distance;}if(collected){this.reward+=15*collected;for(const [key,p] of Object.entries(this.foods))if(Math.hypot(p[0]-body.x,p[1]-body.z)<45)delete this.foods[key];this.exploreGoal=null;this.previousDistance=null;}if(body.collision&&!this.collisionPending){this.reward-=2;this.collisionPending=true;this.exploreGoal=null;}}
 suspend(){this.state=null;this.elapsed=0;this.reward=0;this.previousDistance=null;}
 snapshot(){return {schema:1,kind:'artificial Q-learning, not connectome plasticity',q:this.q,steps:this.steps,visits:this.visits,foods:this.foods};}
}
export function validateMemory(value){return value?.schema===1&&value.q&&Object.keys(value.q).length<10000&&Object.values(value.q).every(a=>Array.isArray(a)&&a.length===7&&a.every(Number.isFinite));}
