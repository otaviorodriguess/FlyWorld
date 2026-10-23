import test from 'node:test';
import assert from 'node:assert/strict';
import {NeuralClient} from './neural-client.js';

function mock(responses,calls){return async(url,options)=>{calls.push([url,JSON.parse(options.body)]);const value=responses.shift();if(value instanceof Error)throw value;return {ok:true,json:async()=>value};};}
const ready={state:'ready',population:138639};
const block={experiment:'sugar',sequence:1,start_ms:0,end_ms:20,command:[.5,0]};
test('only a returned neural block can become a motor command',async()=>{
 const calls=[],client=new NeuralClient(mock([ready,ready,{state:'pending'},{...ready,frame:block}],calls));
 assert.equal(client.take(),null);
 await client.connect();await client.pump({food:.4},2,1000);
 assert.equal(client.take(),null);
 assert.deepEqual(calls[2],[ '/api/neural/step',{food:.4,world_s:2,calibration:0}]);
 await client.pump({food:1},2,1500);
 assert.deepEqual(client.take(),block);assert.equal(client.take(),null);
});
test('network failure and malformed commands never yield fallback motion',async()=>{
 for(const response of [new Error('offline'),{...ready,frame:{...block,experiment:'p9'}},{...ready,frame:{...block,command:[1,1]}}]){
  const client=new NeuralClient(mock([ready,response],[]));await client.connect();await client.pump({food:1},0,1000);
  assert.equal(client.state,'error');assert.equal(client.take(),null);
 }
});
test('one request at a time and calibration is explicit',async()=>{
 const calls=[],client=new NeuralClient(mock([ready,ready,{state:'pending'}],calls));
 await client.connect('p9');await Promise.all([client.pump({food:0},0,1000),client.pump({food:1},0,1000)]);
 assert.equal(calls.length,3);assert.equal(calls[2][1].calibration,1);
});
test('late responses after leaving neural mode cannot move the body',async()=>{
 let release;
 const client=new NeuralClient(async()=>({ok:true,json:()=>new Promise(resolve=>release=resolve)}));
 const connecting=client.connect();await new Promise(resolve=>setImmediate(resolve));
 client.disconnect();release(ready);await connecting;
 assert.equal(client.state,'offline');assert.equal(client.population,0);assert.equal(client.take(),null);
});
