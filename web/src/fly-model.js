import * as THREE from 'three';
import {naturalMaterial as material,surfaceTexture,canvasTexture,wingGeometry,randomSequence,batchStaticMeshes} from './art.js';

export function buildDetailedFly(garden){
 const g=garden;g.fly=new THREE.Group();g.scene.add(g.fly);g.fly.name='Drosophila estilizada';
 const bodyTexture=canvasTexture(256,(ctx,size)=>{ctx.fillStyle='#ceaa70';ctx.fillRect(0,0,size,size);for(let i=0;i<7;i++){const y=i*size/7;const band=ctx.createLinearGradient(0,y,0,y+size/7);band.addColorStop(0,'#473a2b');band.addColorStop(.22,'#725237');band.addColorStop(.28,'#b28b55');band.addColorStop(1,'#d7b676');ctx.fillStyle=band;ctx.fillRect(0,y,size,size/7);}const random=randomSequence(83);ctx.fillStyle='#503d2620';for(let i=0;i<2400;i++)ctx.fillRect(random()*size,random()*size,1,1);});
 const amber=material('#dfb571',{map:bodyTexture,roughness:.56}),thorax=material('#7c6850',{roughness:.66}),head=material('#b39562',{roughness:.56}),dark=material('#453b2d',{roughness:.58});
 const eyeMap=surfaceTexture('eye');const eye=new THREE.MeshPhysicalMaterial({color:'#f1c4ac',map:eyeMap,bumpMap:eyeMap,bumpScale:.18,roughness:.27,clearcoat:.6,clearcoatRoughness:.25});
 const abdomenPoints=[];for(let i=0;i<=24;i++){const t=i/24;abdomenPoints.push(new THREE.Vector2(Math.max(.2,Math.sin(Math.PI*t)**.68*(9.5+2*t)),-25+t*48));}const abdomen=g.mesh(new THREE.LatheGeometry(abdomenPoints,36),amber,g.fly);abdomen.rotation.z=-Math.PI/2;abdomen.position.set(-21,20,0);abdomen.scale.z=.92;abdomen.castShadow=true;
 g.ball([0,25,0],[15,12,11],thorax,g.fly);g.ball([0,33,0],[10,4,8],material('#a38c62'),g.fly);g.ball([19,26,0],[10,8.5,9.3],head,g.fly);
 for(const side of [-1,1]){
  const eyeBall=g.ball([23,28,side*7],[7,8,5.7],eye,g.fly);eyeBall.rotation.x=side*.13;
  g.link([27,28,side*3],[33,30,side*5],.65,dark,g.fly);g.ball([33,30,side*5],[2.8,1.7,1.7],head,g.fly);
  g.link([33,30,side*5],[40,34,side*7],.3,dark,g.fly);
  for(let i=0;i<5;i++)g.link([35+i,31+i*.5,side*(5.5+i*.3)],[34+i,34+i*.6,side*(8+i*.4)],.13,dark,g.fly);
  g.link([-8,24,side*11],[-13,23,side*18],.55,head,g.fly);g.ball([-13,23,side*18],[1.8,1.5,1.8],head,g.fly);
 }
 g.link([26,21,0],[31,19,0],1.4,dark,g.fly);g.ball([31,18.5,0],[2,1.2,2.3],head,g.fly);
 // Fine bristles share a single line buffer.
 const random=randomSequence(91),hair=[];for(let i=0;i<230;i++){const a=random()*Math.PI*2,t=random()*Math.PI*.8,x=Math.cos(t)*13-2,y=25+Math.sin(t)*Math.cos(a)*11,z=Math.sin(t)*Math.sin(a)*10;const direction=new THREE.Vector3(x+2,(y-25)*1.4,z).normalize().multiplyScalar(1.3+random()*2.8);hair.push(x,y,z,x+direction.x,y+direction.y,z+direction.z);}
 for(let i=0;i<60;i++){const x=-42+random()*40,a=random()*Math.PI,y=20+Math.sin(a)*9,z=Math.cos(a)*9;hair.push(x,y,z,x-1,y+Math.sin(a)*2,z+Math.cos(a)*2);}
 const hairs=new THREE.BufferGeometry();hairs.setAttribute('position',new THREE.Float32BufferAttribute(hair,3));g.fly.add(new THREE.LineSegments(hairs,new THREE.LineBasicMaterial({color:'#504330',transparent:true,opacity:.7})));
 g.legs=[];for(const side of [-1,1])for(let i=0;i<3;i++){const rootX=-11+i*11,group=new THREE.Group();g.fly.add(group);g.legs.push({group,side,i,rootX});}
 g.legMat=dark;g.legGeometry=new THREE.CylinderGeometry(.8,1,1,8);for(const leg of g.legs){leg.parts=[1.15,.8,.4].map(radius=>{const mesh=g.mesh(g.legGeometry,dark,leg.group);mesh.userData.radius=radius;mesh.castShadow=true;return mesh;});}
 const wingMat=new THREE.MeshPhysicalMaterial({color:'#e6e2ce',roughness:.3,metalness:.05,transparent:true,opacity:.34,side:THREE.DoubleSide,depthWrite:false,clearcoat:.65,iridescence:.3,iridescenceIOR:1.3,iridescenceThicknessRange:[120,350]});
 const outline=[[-48,1],[-56,5],[-54,12],[-43,18],[-27,19],[-8,12],[5,0]];
 g.wings=[];for(const side of [-1,1]){const wing=new THREE.Group();wing.position.set(-2,35,side*7);wing.rotation.y=-side*.12;wing.scale.z=-side;g.fly.add(wing);const membrane=g.mesh(wingGeometry(),wingMat,wing);membrane.castShadow=false;
  const veins=[];const edge=(a,b)=>veins.push(a[0],.3,-a[1],b[0],.3,-b[1]);for(let i=0;i<outline.length-1;i++)edge(outline[i],outline[i+1]);for(const end of [[-52,4],[-53,10],[-43,17],[-28,18]]){edge([4,0],[-19,7]);edge([-19,7],end);}edge([-39,3],[-36,13]);edge([-25,4],[-26,17]);edge([-15,5],[-10,12]);
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(veins,3));wing.add(new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({color:'#8c876b',transparent:true,opacity:.55})));g.wings.push({wing,side});
 }
 batchStaticMeshes(g.fly);
 // A soft contact shadow anchors the feet without costly post-processing.
 const shadow=canvasTexture(128,(ctx,size)=>{const gradient=ctx.createRadialGradient(size/2,size/2,4,size/2,size/2,size/2);gradient.addColorStop(0,'#25362670');gradient.addColorStop(.45,'#25362630');gradient.addColorStop(1,'#25362600');ctx.fillStyle=gradient;ctx.fillRect(0,0,size,size);});
 g.contactShadow=g.mesh(new THREE.PlaneGeometry(110,80),new THREE.MeshBasicMaterial({map:shadow,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1}));g.contactShadow.rotation.x=-Math.PI/2;g.contactShadow.position.y=.6;
}
