import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

export const naturalMaterial=(color,options={})=>new THREE.MeshStandardMaterial({color,roughness:.78,...options});
export function randomSequence(seed=42){return ()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/4294967296);}
export function canvasTexture(size,paint){const canvas=document.createElement('canvas');canvas.width=canvas.height=size;paint(canvas.getContext('2d'),size);const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;return texture;}
export function surfaceTexture(kind){
 const random=randomSequence(82);
 return canvasTexture(kind==='eye'?512:256,(ctx,size)=>{
  if(kind==='eye'){
   ctx.fillStyle='#762c26';ctx.fillRect(0,0,size,size);const r=7,h=Math.sqrt(3)*r;
   for(let row=-1;row<44;row++)for(let col=-1;col<40;col++){const x=col*r*1.5,y=row*h+(col%2)*h*.5;ctx.beginPath();for(let i=0;i<6;i++){const a=i*Math.PI/3;ctx.lineTo(x+Math.cos(a)*r*.93,y+Math.sin(a)*r*.93);}ctx.closePath();ctx.fillStyle=`hsl(${8+random()*6} 61% ${29+random()*13}%)`;ctx.fill();ctx.strokeStyle='#552a2630';ctx.lineWidth=.7;ctx.stroke();ctx.fillStyle='#ffe1b820';ctx.fillRect(x-2,y-3,2,2);}
  }else if(kind==='bark'){
   ctx.fillStyle='#a9957d';ctx.fillRect(0,0,size,size);for(let i=0;i<1200;i++){const x=random()*size,y=random()*size;ctx.strokeStyle=i%3?'#54443850':'#ddc3a040';ctx.lineWidth=.5+random()*2;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.sin(i)*3,y+random()*45);ctx.stroke();}
  }else{
   ctx.fillStyle=kind==='ground'?'#758667':kind==='path'?'#c0baa4':'#b99e77';ctx.fillRect(0,0,size,size);
   for(let i=0;i<16000;i++){const x=random()*size,y=random()*size,r=random()*2+.4;ctx.fillStyle=i%3===0?'#eee6b51c':i%3===1?'#263c2818':'#c4c28725';ctx.beginPath();ctx.ellipse(x,y,r,r*.55,random()*Math.PI,0,Math.PI*2);ctx.fill();}
   if(kind==='ground')for(let i=0;i<140;i++){ctx.fillStyle='#b3b48a20';ctx.beginPath();ctx.ellipse(random()*size,random()*size,3+random()*12,2+random()*7,random()*6,0,Math.PI*2);ctx.fill();}
  }
 });
}
export function leafGeometry(){const shape=new THREE.Shape();shape.moveTo(0,0);shape.bezierCurveTo(4,3,5,10,0,17);shape.bezierCurveTo(-5,10,-4,3,0,0);const geom=new THREE.ShapeGeometry(shape,5);geom.rotateX(-Math.PI/2);const p=geom.attributes.position;for(let i=0;i<p.count;i++){const x=p.getX(i),z=p.getZ(i);p.setY(i,Math.sin(-z/17*Math.PI)*2-Math.abs(x)*.18);}geom.computeVertexNormals();return geom;}
export function petalGeometry(){const shape=new THREE.Shape();shape.moveTo(0,0);shape.bezierCurveTo(7,3,8,12,0,15);shape.bezierCurveTo(-8,12,-7,3,0,0);const geom=new THREE.ShapeGeometry(shape,6);geom.rotateX(-Math.PI/2);const p=geom.attributes.position;for(let i=0;i<p.count;i++)p.setY(i,Math.pow(-p.getZ(i)/15,2)*5);geom.computeVertexNormals();return geom;}
export function wingGeometry(){const shape=new THREE.Shape();shape.moveTo(7,0);shape.bezierCurveTo(-7,-1,-34,-7,-49,-2);shape.bezierCurveTo(-64,3,-59,14,-46,19);shape.bezierCurveTo(-26,24,-5,16,7,0);const geom=new THREE.ShapeGeometry(shape,18);geom.rotateX(-Math.PI/2);return geom;}
export function mushroomGeometry(radius=24,height=13){const profile=[];for(let i=0;i<=12;i++){const a=i/12*Math.PI/2;profile.push(new THREE.Vector2(Math.sin(a)*radius,Math.cos(a)*height));}profile.push(new THREE.Vector2(radius*.92,-2),new THREE.Vector2(radius*.2,-5),new THREE.Vector2(0,-5));return new THREE.LatheGeometry(profile,24);}
// One GPU draw per shared geometry/material, rather than a draw for every seed or leaf.
export function instances(parent,geometry,material,entries,{shadow=false,receive=false}={}){
 const mesh=new THREE.InstancedMesh(geometry,material,entries.length),dummy=new THREE.Object3D();
 entries.forEach((entry,i)=>{dummy.position.set(...entry.position);dummy.scale.set(...(entry.scale||[1,1,1]));dummy.rotation.set(...(entry.rotation||[0,0,0]));dummy.updateMatrix();mesh.setMatrixAt(i,dummy.matrix);if(entry.color)mesh.setColorAt(i,new THREE.Color(entry.color));});mesh.castShadow=shadow;mesh.receiveShadow=receive;parent.add(mesh);return mesh;
}
export function skyEnvironment(renderer){const canvas=document.createElement('canvas');canvas.width=512;canvas.height=256;const ctx=canvas.getContext('2d'),gradient=ctx.createLinearGradient(0,0,0,256);gradient.addColorStop(0,'#8ba6b4');gradient.addColorStop(.45,'#dae1d4');gradient.addColorStop(.53,'#f6dfba');gradient.addColorStop(.7,'#7d8866');gradient.addColorStop(1,'#344d3a');ctx.fillStyle=gradient;ctx.fillRect(0,0,512,256);const glow=ctx.createRadialGradient(355,99,0,355,99,55);glow.addColorStop(0,'#fff1c8');glow.addColorStop(1,'#fff1c800');ctx.fillStyle=glow;ctx.fillRect(280,24,150,150);const texture=new THREE.CanvasTexture(canvas);texture.mapping=THREE.EquirectangularReflectionMapping;texture.colorSpace=THREE.SRGBColorSpace;const pmrem=new THREE.PMREMGenerator(renderer),result=pmrem.fromEquirectangular(texture);texture.dispose();pmrem.dispose();return result;}

export function batchStaticMeshes(group,excluded=[]){
 const skip=new Set(excluded),batches=new Map();
 for(const child of [...group.children]){if(!child.isMesh||child.isInstancedMesh||skip.has(child)||Array.isArray(child.material)||child.material.transparent)continue;const key=`${child.material.uuid}:${child.castShadow}:${child.receiveShadow}`;if(!batches.has(key))batches.set(key,[]);batches.get(key).push(child);}
 for(const meshes of batches.values()){if(meshes.length<2)continue;const geometries=meshes.map(mesh=>{mesh.updateMatrix();return mesh.geometry.clone().applyMatrix4(mesh.matrix);}),merged=mergeGeometries(geometries,false);geometries.forEach(geometry=>geometry.dispose());if(!merged)continue;const mesh=new THREE.Mesh(merged,meshes[0].material);mesh.castShadow=meshes[0].castShadow;mesh.receiveShadow=meshes[0].receiveShadow;meshes.forEach(child=>group.remove(child));group.add(mesh);}
}
