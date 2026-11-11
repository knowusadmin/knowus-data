
import Browserbase from "@browserbasehq/sdk"; import fs from "node:fs";
import { createRequire } from 'node:module'; const require=createRequire('/home/user/x.js'); const { chromium } = require('playwright-core');
const V = JSON.parse(fs.readFileSync("/home/user/tab/.vendor-capability.json", "utf8"));
const bb = new Browserbase({ apiKey: V.token, baseURL: `${V.base_url}/browserbase` });

const OUT=process.argv[2], warm=process.argv[3], items=process.argv.slice(4);
const s = await bb.sessions.create({ projectId: "f2ae15a0-a894-4419-977f-d52f52483f0c", userMetadata:{site:'fl-soe-dl',task:process.env.TAB_TASK_ID||''}, browserSettings:{ solveCaptchas:true } , proxies:true});
const br = await chromium.connectOverCDP(s.connectUrl); const ctx=br.contexts()[0]; const page=ctx.pages()[0]||await ctx.newPage();
await page.goto(warm,{waitUntil:'load',timeout:60000}); await page.waitForTimeout(4000); console.log('warm',await page.title());
for (const it of items){ const [name,u]=it.split('=>');
  try{
    const info=await page.evaluate(async(u)=>{const r=await fetch(u,{credentials:'include'}); const b=await r.arrayBuffer(); window.__B=new Uint8Array(b); return [r.status,r.headers.get('content-type'),b.byteLength];},u);
    console.log(name,info);
    if(info[0]!==200){ continue; }
    const fd=fs.openSync(`${OUT}/${name}`,'w'); const CH=4*1024*1024;
    for(let off=0;off<info[2];off+=CH){ const b64=await page.evaluate(([o,n])=>{const a=window.__B.subarray(o,o+n);let s='';for(let i=0;i<a.length;i+=8192)s+=String.fromCharCode.apply(null,a.subarray(i,i+8192));return btoa(s);},[off,CH]); fs.writeSync(fd,Buffer.from(b64,'base64')); }
    fs.closeSync(fd); console.log('saved',name,fs.statSync(`${OUT}/${name}`).size);
    await page.evaluate(()=>{window.__B=null;});
  }catch(e){console.log('err',name,String(e).slice(0,300));}
}
await br.close(); await bb.sessions.update(s.id,{projectId:"f2ae15a0-a894-4419-977f-d52f52483f0c",status:'REQUEST_RELEASE'}).catch(()=>{});
console.log('DONE');
