import * as THREE from 'three';
import {instances,canvasTexture} from './art.js';
export class LanHouseScene{
 constructor(garden,canvas){this.garden=garden;this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#171c2b');this.scene.environment=garden.scene.environment;this.scene.environmentIntensity=.3;this.camera=new THREE.PerspectiveCamera(42,innerWidth/innerHeight,1,2000);this.camera.position.set(310,240,355);this.camera.lookAt(-35,100,-15);this.scene.add(new THREE.HemisphereLight('#b0c5ef','#292232',2));const lamp=new THREE.DirectionalLight('#ffe2b5',3);lamp.position.set(70,360,240);this.scene.add(lamp);const purple=new THREE.PointLight('#ad78ff',9000,500,2);purple.position.set(-170,120,-80);this.scene.add(purple);
 const mat=color=>new THREE.MeshStandardMaterial({color,roughness:.65}),wood=mat('#a38267'),dark=mat('#242a3a'),black=mat('#131926');
 const box=(size,pos,material)=>{const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),material);mesh.position.set(...pos);this.scene.add(mesh);return mesh;};
 box([760,5,620],[0,-4,0],mat('#303348'));box([760,290,9],[0,140,-210],mat('#30334b'));box([9,290,620],[-380,140,0],mat('#242b40'));
 for(let x=-340;x<=340;x+=85)box([3,280,5],[x,140,-202],mat('#3a3e56'));
 box([320,9,170],[0,67,15],wood);for(const x of [-140,140])for(const z of [-50,80])box([9,63,9],[x,31,z],dark);
 box([230,140,12],[0,145,-65],black);box([12,29,12],[0,91,-65],dark);box([65,4,35],[0,74,-60],dark);
 this.texture=new THREE.CanvasTexture(canvas);this.texture.colorSpace=THREE.SRGBColorSpace;const screen=new THREE.Mesh(new THREE.PlaneGeometry(211,119),new THREE.MeshBasicMaterial({map:this.texture,toneMapped:false}));screen.position.set(0,145,-58.7);this.scene.add(screen);
 box([124,4,48],[0,74,50],black);const keys=[];for(let row=0;row<4;row++)for(let col=0;col<12;col++)keys.push({position:[-55+col*10,77,33+row*10],scale:[8,2.2,7],color:row===3?'#637c90':'#424d64'});instances(this.scene,new THREE.BoxGeometry(1,1,1),mat('#ffffff'),keys);box([24,8,36],[103,77,45],mat('#697a8c'));box([3,1,9],[103,82,42],dark);
 // A spare seat gives scale without obscuring the insect at the keyboard.
 box([69,9,65],[-178,38,96],mat('#6a617f'));box([68,66,9],[-178,72,129],mat('#6a617f'));for(const x of [-200,-156])box([6,38,6],[x,18,105],dark);
 for(const x of [-310,310])box([5,210,5],[x,130,-196],new THREE.MeshBasicMaterial({color:'#9477d2'}));
 const sign=canvasTexture(512,(ctx,n)=>{ctx.fillStyle='#232b41';ctx.fillRect(0,0,n,n);ctx.fillStyle='#e8dba5';ctx.font='bold 44px Segoe UI';ctx.textAlign='center';ctx.fillText('LAN DA MOSCA',n/2,240);ctx.fillStyle='#b6b7ca';ctx.font='20px Segoe UI';ctx.fillText('UM NOVO JEITO DE APRENDER',n/2,283);});const poster=new THREE.Mesh(new THREE.PlaneGeometry(150,150),new THREE.MeshBasicMaterial({map:sign}));poster.position.set(-215,170,-203);this.scene.add(poster);this.resize();
 }
 enter(){this.scene.add(this.garden.fly,this.garden.contactShadow);this.garden.controls.enabled=false;}
 leave(){this.garden.scene.add(this.garden.fly,this.garden.contactShadow);this.garden.controls.enabled=true;}
 render(time,action){const g=this.garden;g.animateFly({x:0,z:40,angle:-Math.PI/2,speed:0},time,action!==0);g.fly.position.y=79;g.fly.scale.setScalar(.72);g.contactShadow.position.y=79.6;g.contactShadow.scale.setScalar(.72);this.texture.needsUpdate=true;g.renderer.render(this.scene,this.camera);}
 resize(){const mobile=innerWidth<760;this.camera.position.set(mobile?380:310,mobile?300:240,mobile?550:355);this.camera.lookAt(-35,mobile?30:100,-15);this.camera.aspect=innerWidth/innerHeight;this.camera.updateProjectionMatrix();}
}
