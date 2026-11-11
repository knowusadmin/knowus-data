
import Browserbase from "@browserbasehq/sdk"; import fs from "node:fs";
import { createRequire } from 'node:module'; const require=createRequire('/home/user/x.js'); const { chromium } = require('playwright-core');
const V = JSON.parse(fs.readFileSync("/home/user/tab/.vendor-capability.json", "utf8"));
const bb = new Browserbase({ apiKey: V.token, baseURL: `${V.base_url}/browserbase` });
const OUT=process.argv[2], counties=process.argv[3].split(',');
const s = await bb.sessions.create({ projectId: "f2ae15a0-a894-4419-977f-d52f52483f0c", userMetadata:{site:'ohio-boe-lookup',task:process.env.TAB_TASK_ID||''}, browserSettings:{ solveCaptchas:true } , proxies:true});
console.log('session',s.id);
const br = await chromium.connectOverCDP(s.connectUrl); const ctx=br.contexts()[0]; const page=ctx.pages()[0]||await ctx.newPage();
async function cf(){ for(let k=0;k<30;k++){ const t=await page.title(); if(!/Just a moment/i.test(t)) return t; await page.waitForTimeout(2000);} return 'CF'; }
for (const c of counties){
  try{ await page.goto(`https://lookup.boe.ohio.gov/vtrapp/${c}/ballotlist.aspx`,{waitUntil:'load',timeout:60000}); console.log(c, await cf());
    const has=await page.$('#cmbelectionlist'); if(!has){ console.log(c,'no list'); fs.writeFileSync(`${OUT}/${c}-list.html`, await page.content()); continue; }
    await page.selectOption('#cmbelectionlist','20261103G').catch(e=>console.log('sel',String(e).slice(0,100)));
    await page.waitForTimeout(2500); await cf();
    await Promise.all([page.waitForLoadState('load',{timeout:60000}).catch(()=>{}), page.click('#btnsubmit')]); await page.waitForTimeout(2500); await cf();
    fs.writeFileSync(`${OUT}/${c}-list.html`, await page.content()); console.log(c,'saved', (await page.content()).length);
  }catch(e){console.log('err',c,String(e).slice(0,300));}
}
await br.close(); await bb.sessions.update(s.id,{projectId:"f2ae15a0-a894-4419-977f-d52f52483f0c",status:'REQUEST_RELEASE'}).catch(e=>console.log('rel',String(e).slice(0,200)));
console.log('DONE');
