import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
try {
const page=await browser.newPage({viewport:{width:1000,height:800},deviceScaleFactor:.5});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(process.env.FLYWORLD_URL||'http://127.0.0.1:5173/');await page.waitForFunction(()=>window.flyworld,{timeout:60000});
assert.equal(await page.locator('[data-experience]').count(),6);
await page.locator('#speed').selectOption('4');
for(const id of ['pollen','nectar','dew','shelter','wind','fireflies']){
 const previous=await page.evaluate(id=>window.flyworld.snapshot().experiences.discoveries[id]||0,id);
 await page.locator(`[data-experience="${id}"]`).click();
 await page.waitForFunction(({id,previous})=>window.flyworld&&((window.flyworld.snapshot().experiences.discoveries[id]||0)>=(id==='pollen'?previous+1:1))&&(id!=='nectar'||window.flyworld.snapshot().experiences.deliveries>0),{id,previous},{timeout:90000}).catch(async error=>{console.log('Estado antes da falha',JSON.stringify(await page.evaluate(()=>window.flyworld?.snapshot())));await page.screenshot({path:fileURLToPath(new URL('./test-results/failed-adventure.png',import.meta.url))});throw error;});
 console.log('Visitou',id,JSON.stringify(await page.evaluate(()=>window.flyworld.snapshot().experiences)));
}
const before=await page.evaluate(()=>window.flyworld.snapshot());assert.ok(before.experiences.deliveries>=1);assert.equal(Object.keys(before.experiences.discoveries).length,6);
await page.locator('#pause').click();await page.screenshot({path:fileURLToPath(new URL('./test-results/adventures.png',import.meta.url))});
await page.reload();await page.waitForFunction(()=>window.flyworld);const restored=await page.evaluate(()=>window.flyworld.snapshot());assert.equal(Object.keys(restored.experiences.discoveries).length,6);assert.ok(restored.experiences.deliveries>=1);
await page.locator('#replay-mode').click();await page.waitForFunction(()=>window.flyworld.snapshot().recordedSpikes>0);assert.ok(await page.locator('[data-experience="pollen"]').isDisabled());const journal=await page.evaluate(()=>window.flyworld.snapshot().experiences.journal);await page.waitForTimeout(500);assert.equal((await page.evaluate(()=>window.flyworld.snapshot())).experiences.journal,journal);
await page.setViewportSize({width:390,height:844});await page.locator('#panel-toggle').click();await page.locator('#adventures').scrollIntoViewIfNeeded();await page.screenshot({path:fileURLToPath(new URL('./test-results/adventures-mobile.png',import.meta.url))});
assert.deepEqual(errors,[]);console.log('Experiências, entrega, persistência, replay e mobile: OK');} finally {await browser.close();}
