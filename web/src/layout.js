import {blocked} from './simulation.js';
export const LAYOUT_VERSION=2;
export function distanceSegment(x,z,a,b){const dx=b[0]-a[0],dz=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz||1)));return Math.hypot(x-a[0]-t*dx,z-a[1]-t*dz);}
export function pathDistance(world,x,z){return Math.min(...world.paths.flatMap(path=>path.points.slice(1).map((p,i)=>distanceSegment(x,z,path.points[i],p))));}
export function createLayout(){
 let seed=517;const random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/4294967296);
 const sites=[['nectar',2000,1100,'Campo de flores'],['dew',4200,950,'Margem do orvalho'],['shelter',4800,2450,'Bosque dos cogumelos'],['pollen',3450,3100,'Jardim de pólen'],['wind',1450,3100,'Clareira da brisa'],['fireflies',1050,1700,'Recanto dos vaga-lumes']].map(([id,x,z,region])=>({id,x,z,region}));
 const world={layoutVersion:2,width:6000,height:4000,spawn:{x:3000,z:2000},portal:{x:3230,z:2000},sites,regions:sites.map(s=>({...s,radius:430})),paths:sites.map(s=>({points:[[3000,2000],[s.x,s.z]],width:70})),ponds:[[4650,900,230,170],[700,1200,180,130]],obstacles:[],foods:[]};world.paths.push({points:[[3000,2000],[3230,2000]],width:85});
 const forests=[[5100,1150],[4950,3200],[850,2700],[2250,550],[3900,3450]];
 for(let i=0;i<130;i++){const c=forests[i%forests.length],a=random()*Math.PI*2,r=Math.sqrt(random())*600,x=c[0]+Math.cos(a)*r,z=c[1]+Math.sin(a)*r;if(blocked(world,x,z,100)||pathDistance(world,x,z)<145||sites.some(s=>Math.hypot(x-s.x,z-s.z)<250)||Math.hypot(x-3000,z-2000)<360)continue;world.obstacles.push({x:x-25,y:z-25,width:50,height:50,kind:i%5?'tree':'rock'});}
 for(const site of sites)for(let i=0;i<9;i++){const a=i*2.4,r=130+random()*140,x=site.x+Math.cos(a)*r,z=site.z+Math.sin(a)*r;if(!blocked(world,x,z,28))world.foods.push([x,z]);}
 return world;
}
export function migrateGardenMemory(memory,version=2){if(!memory)return null;if(memory.layoutVersion===version)return memory;return {...memory,layoutVersion:version,foods:{},visits:{}};}
