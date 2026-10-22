import test from 'node:test';
import assert from 'node:assert/strict';
import {Learner,blocked,move,sense,validateMemory} from './simulation.js';
const world=()=>({width:1000,height:1000,obstacles:[],ponds:[],foods:[]});
test('Q update and JSON checkpoint preserve learned policy',()=>{const l=new Learner();l.learn('a',0,15,'b',true);assert.equal(l.q.a[0],.02+.18*(15-.02));const checkpoint=JSON.parse(JSON.stringify(l.snapshot()));assert.ok(validateMemory(checkpoint));const restored=new Learner({},checkpoint);assert.deepEqual(restored.q,l.q);assert.equal(restored.steps,1);assert.ok(!validateMemory({schema:1,q:{a:[null]}}));});
test('swept movement cannot cross obstacle or water',()=>{const w=world();w.obstacles=[{x:150,y:0,width:20,height:400}];const body={x:100,z:200,angle:0};move(w,body,[1,0],2);assert.ok(body.x<138);assert.equal(body.collision,true);w.ponds=[[500,500,100,100]];assert.ok(blocked(w,500,500));});
test('learner remembers only food within sensing range',()=>{const w=world();w.foods=[[900,900]];const b={x:100,z:100,angle:0};const l=new Learner();l.command(w,b,sense(w,b));assert.equal(Object.keys(l.foods).length,0);w.foods.push([150,100]);l.command(w,b,sense(w,b));assert.equal(Object.keys(l.foods).length,1);});
test('food collection removes consumed food exactly once',()=>{const w=world();w.foods=[[100,100]];const b={x:100,z:100,angle:0};assert.equal(move(w,b,[0,0],.1),1);assert.equal(move(w,b,[0,0],.1),0);});
