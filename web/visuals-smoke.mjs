import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
try{
const page=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:.75});const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
await page.goto(process.env.FLYWORLD_URL||'http://127.0.0.1:5173');await page.waitForFunction(()=>window.flyworld?.snapshot().visuals,null,{timeout:60000});
await page.locator('#pause').evaluate(button=>button.click());await page.waitForTimeout(300);await page.screenshot({path:'test-results/natural-garden.png'});
const snapshot=await page.evaluate(()=>window.flyworld.snapshot());console.log('Renderização',JSON.stringify(snapshot.visuals));assert.equal(snapshot.visuals.legs,6);assert.equal(snapshot.visuals.wings,2);assert.ok(snapshot.visuals.drawCalls<500);assert.equal(snapshot.experiences.sites.length,6);assert.deepEqual(errors,[]);console.log(JSON.stringify({snapshot,errors}));
await page.locator('[data-action="feed"]').click();await page.locator('#help').click();await page.locator('#close-help').click();await page.locator('#replay-mode').click();await page.waitForFunction(()=>window.flyworld.snapshot().recordedSpikes>0);await page.locator('#free-mode').click();
await page.setViewportSize({width:390,height:844});await page.waitForTimeout(300);await page.screenshot({path:'test-results/natural-mobile.png'});assert.deepEqual(errors,[]);
}finally{await browser.close();}
