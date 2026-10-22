import * as THREE from 'three';
import {blocked} from './simulation.js';
import {naturalMaterial as material,surfaceTexture,randomSequence,leafGeometry,petalGeometry,mushroomGeometry,instances} from './art.js';
const ball=new THREE.SphereGeometry(1,12,8);
const cylinder=new THREE.CylinderGeometry(.75,1,1,7);
function segment(a,b,r){const av=new THREE.Vector3(...a),bv=new THREE.Vector3(...b),direction=bv.clone().sub(av),quaternion=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),direction.clone().normalize()),rotation=new THREE.Euler().setFromQuaternion(quaternion);return {position:av.add(bv).multiplyScalar(.5).toArray(),scale:[r,direction.length(),r],rotation:[rotation.x,rotation.y,rotation.z]};}
export function buildNaturalGround(g){
 const groundTexture=surfaceTexture('ground');groundTexture.wrapS=groundTexture.wrapT=THREE.RepeatWrapping;groundTexture.repeat.set(26,18);groundTexture.anisotropy=Math.min(4,g.renderer.capabilities.getMaxAnisotropy());
 const ground=g.mesh(new THREE.PlaneGeometry(g.world.width,g.world.height),material('#c4d4b4',{map:groundTexture,bumpMap:groundTexture,bumpScale:.5}));ground.rotation.x=-Math.PI/2;ground.position.set(g.world.width/2,-.4,g.world.height/2);ground.receiveShadow=true;
 const vertices=[],uv=[],indices=[];for(let x=0,i=0;x<=g.world.width;x+=40,i++){const z=2000+Math.sin(x*.0018)*260,width=24+Math.sin(x*.011)*3;vertices.push(x,.35,z-width,x,.35,z+width);uv.push(x/100,0,x/100,1);if(i){const n=i*2;indices.push(n-2,n-1,n,n-1,n+1,n);}}const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geometry.setIndex(indices);geometry.computeVertexNormals();const pathTexture=surfaceTexture('path');pathTexture.wrapS=pathTexture.wrapT=THREE.RepeatWrapping;const path=g.mesh(geometry,material('#d3d0bc',{map:pathTexture,side:THREE.DoubleSide,roughness:1}));path.receiveShadow=true;
 g.water=[];g.ripples=[];const stones=[],reeds=[],leaves=[];
 for(const [x,z,rx,rz] of g.world.ponds){const shore=g.mesh(new THREE.CircleGeometry(1,64),material('#aaad80'));shore.rotation.x=-Math.PI/2;shore.scale.set(rx*1.07,rz*1.07,1);shore.position.set(x,.45,z);const water=g.mesh(new THREE.CircleGeometry(1,72),new THREE.MeshPhysicalMaterial({color:'#568f85',roughness:.2,metalness:.2,clearcoat:.8,envMapIntensity:.8,side:THREE.DoubleSide}));water.rotation.x=-Math.PI/2;water.scale.set(rx,rz,1);water.position.set(x,.8,z);g.water.push(water);
  for(let i=0;i<3;i++){const ripple=g.mesh(new THREE.RingGeometry(1,1.025,48),new THREE.MeshBasicMaterial({color:'#c3d9bb',side:THREE.DoubleSide,transparent:true,opacity:.14,depthWrite:false}));ripple.rotation.x=-Math.PI/2;ripple.position.set(x+rx*.27,.95,z-rz*.1);g.ripples.push({mesh:ripple,rx:rx*.28,rz:rz*.28,phase:i/3});}
  for(let i=0;i<18;i++){const a=i*2.4;stones.push({position:[x+Math.cos(a)*rx*1.06,2,z+Math.sin(a)*rz*1.06],scale:[6+i%4,4,5+i%3],rotation:[0,a,0]});}
  for(let i=0;i<10;i++){const a=i*2.4,lx=x+Math.cos(a)*rx*.7,lz=z+Math.sin(a)*rz*.7;const shape=new THREE.Shape();shape.absarc(0,0,9,.2,Math.PI*2-.2,false);shape.lineTo(0,0);const lily=g.mesh(new THREE.ShapeGeometry(shape,14),material('#648b54',{side:THREE.DoubleSide}));lily.rotation.x=-Math.PI/2;lily.rotation.z=a;lily.position.set(lx,1.1,lz);if(i%4===0){for(let j=0;j<6;j++){const petal=g.mesh(petalGeometry(),material('#d7b0ad',{side:THREE.DoubleSide}));petal.position.set(lx,2,lz);petal.scale.setScalar(.45);petal.rotation.y=j*Math.PI/3;}}
   const ex=x+Math.cos(a)*rx*1.13,ez=z+Math.sin(a)*rz*1.13;for(let j=0;j<3;j++){reeds.push(segment([ex+j*2,0,ez],[ex+j*2+3,25+j*7,ez+3],.55));leaves.push({position:[ex,3,ez],scale:[.5,1,2],rotation:[0,a+j,0]});}
  }
 }
 instances(g.scene,ball,material('#92947e'),stones,{receive:true});instances(g.scene,cylinder,material('#718249'),reeds);instances(g.scene,leafGeometry(),material('#6c8251',{side:THREE.DoubleSide}),leaves);
}
export function buildNaturalPlants(g){
 const random=randomSequence(74),grass=[],stems=[],petals=[],centers=[],leaves=[];
 const spot=()=>{for(let i=0;i<15;i++){const x=random()*g.world.width,z=random()*g.world.height;if(!blocked(g.world,x,z,4)&&Math.abs(z-2000-Math.sin(x*.0018)*260)>30)return [x,z];}return null;};
 for(let i=0;i<6500;i++){const p=spot();if(!p)continue;grass.push({position:[p[0],0,p[1]],scale:[.6+random(),.4+random()*.85,.6+random()],rotation:[0,random()*Math.PI*2,0],color:['#71804d','#8c965c','#a2a36a','#5b7550'][i%4]});}
 const blade=new THREE.BufferGeometry();blade.setAttribute('position',new THREE.Float32BufferAttribute([-1.4,0,0,1.4,0,0,-.7,8,-.7,1,8,-.7,2.8,17,-2.5],3));blade.setIndex([0,1,2,1,3,2,2,3,4]);blade.computeVertexNormals();instances(g.scene,blade,material('#ffffff',{side:THREE.DoubleSide}),grass);
 const palette=['#e6d0a1','#d2a4ad','#b7acc4','#d8bd6c','#eee4ca'];
 for(let i=0;i<620;i++){const p=spot();if(!p)continue;const [x,z]=p,height=14+random()*15,a=random()*6.28,scale=.35+random()*.35;stems.push(segment([x,0,z],[x+2,height,z],.4));centers.push({position:[x+2,height+1,z],scale:[2.1,1.3,2.1],color:i%2?'#b5914d':'#bfa15a'});for(let j=0;j<6;j++)petals.push({position:[x+2,height,z],scale:[scale,scale,scale],rotation:[0,j*Math.PI/3+a,0],color:palette[i%palette.length]});for(let j=0;j<2;j++)leaves.push({position:[x,height*.35+j*4,z],scale:[.45,.45,.65],rotation:[-.2,a+j*Math.PI,.2]});}
 instances(g.scene,cylinder,material('#687f49'),stems);instances(g.scene,petalGeometry(),material('#ffffff',{side:THREE.DoubleSide}),petals);instances(g.scene,ball,material('#ffffff'),centers);instances(g.scene,leafGeometry(),material('#7e9259',{side:THREE.DoubleSide}),leaves);
}
export function buildNaturalObstacles(g){
 const random=randomSequence(104),trunks=[],crowns=[],foliage=[],rocks=[],caps=[],mushroomStems=[],spots=[],moss=[];const rockGeometry=new THREE.IcosahedronGeometry(1,2),positions=rockGeometry.attributes.position;for(let i=0;i<positions.count;i++){const x=positions.getX(i),y=positions.getY(i),z=positions.getZ(i),f=1+Math.sin(x*6+z*4)*.1;positions.setXYZ(i,x*f,y*f,z*f);}rockGeometry.computeVertexNormals();
 for(const o of g.world.obstacles){const x=o.x+o.width/2,z=o.y+o.height/2;
  if(o.kind==='tree'){const height=145+random()*30;trunks.push(segment([x,0,z],[x-5,height*.55,z+3],10),segment([x-5,height*.55,z+3],[x+2,height,z],6));for(let j=0;j<5;j++){const a=j*2.4,r=27+random()*19,cx=x+Math.cos(a)*r,cz=z+Math.sin(a)*r,cy=height+15+random()*35;trunks.push(segment([x-3,height*.65,z],[cx,cy-12,cz],3.5));crowns.push({position:[cx,cy,cz],scale:[33+random()*15,29+random()*16,30+random()*16],rotation:[random(),a,random()],color:['#718756','#7c905b','#899867','#607c50','#98a16b'][j]});
    for(let k=0;k<14;k++){const b=random()*Math.PI*2,t=random()*Math.PI;foliage.push({position:[cx+Math.cos(b)*Math.sin(t)*37,cy+Math.cos(t)*31,cz+Math.sin(b)*Math.sin(t)*37],scale:[1.2,1.3,1.7],rotation:[random()*2,b,random()],color:k%2?'#8c9c66':'#758b55'});}
   }
  }else{rocks.push({position:[x,10,z],scale:[o.width*.56,17,o.height*.56],rotation:[.1,random()*6,.1]});moss.push({position:[x-3,21,z+2],scale:[o.width*.39,4,o.height*.35]});const radius=18+random()*10;caps.push({position:[x,53,z],scale:[radius,radius,radius],rotation:[.05,random()*6,.08],color:random()>.5?'#bb8a6f':'#aa7964'});mushroomStems.push(segment([x,20,z],[x+1,54,z],3.5));for(let j=0;j<5;j++){const a=j*2.4,r=radius*.6;spots.push({position:[x+Math.cos(a)*r,53+radius*.4,z+Math.sin(a)*r],scale:[2.6,.65,2.4]});}}
 }
 const bark=surfaceTexture('bark');bark.wrapS=bark.wrapT=THREE.RepeatWrapping;bark.repeat.set(2,2);
 instances(g.scene,cylinder,material('#a9957c',{map:bark,bumpMap:bark,bumpScale:.4}),trunks,{shadow:true});instances(g.scene,new THREE.IcosahedronGeometry(1,2),material('#ffffff',{roughness:.95}),crowns,{shadow:true});instances(g.scene,leafGeometry(),material('#ffffff',{side:THREE.DoubleSide}),foliage);
 instances(g.scene,rockGeometry,material('#9a9d8d',{roughness:1}),rocks,{shadow:true,receive:true});instances(g.scene,ball,material('#788659'),moss);instances(g.scene,mushroomGeometry(1,.55),material('#ffffff'),caps,{shadow:true});instances(g.scene,cylinder,material('#c9bb99'),mushroomStems,{shadow:true});instances(g.scene,ball,material('#ddcba4'),spots);
}
export function refreshNaturalFood(g){
 for(const child of [...g.foodGroup.children]){g.foodGroup.remove(child);child.dispose?.();}
 const geometry=g.foodGeometry||(g.foodGeometry=new THREE.SphereGeometry(1,16,10));const mats=g.foodMaterials||(g.foodMaterials=[material('#ffffff'),material('#dfa2a0'),material('#e6c78e')]);const skins=[],flesh=[],seeds=[];
 g.world.foods.forEach(([x,z],i)=>{const a=i*2.4;skins.push({position:[x,5,z],scale:[18,5.5,17],color:['#745d72','#a16c60','#b39161'][i%3]});flesh.push({position:[x,8,z],scale:[15.5,2.7,14.5],rotation:[0,a,0]});for(let j=0;j<9;j++){const b=j*2.4;seeds.push({position:[x+Math.cos(b)*9,10.3,z+Math.sin(b)*9],scale:[.8,.3,1.15],rotation:[0,b,0]});}});
 instances(g.foodGroup,geometry,mats[0],skins);instances(g.foodGroup,geometry,mats[1],flesh);instances(g.foodGroup,ball,mats[2],seeds);
}
