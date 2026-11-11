
import Browserbase from "@browserbasehq/sdk"; import fs from "node:fs";
import { createRequire } from 'node:module'; const require=createRequire('/home/user/x.js'); const { chromium } = require('playwright-core');
const V = JSON.parse(fs.readFileSync("/home/user/tab/.vendor-capability.json", "utf8"));
const bb = new Browserbase({ apiKey: V.token, baseURL: `${V.base_url}/browserbase` });
const OUT=process.argv[2], counties=process.argv[3].split(',');
const s = await bb.sessions.create({ projectId: "f2ae15a0-a894-4419-977f-d52f52483f0c", userMetadata:{site:'ohio-boe-lookup',task:process.env.TAB_TASK_ID||''}, browserSettings:{ solveCaptchas:true }, proxies:true, timeout:3000});
console.log('session',s.id);
const br = await chromium.connectOverCDP(s.connectUrl); const ctx=br.contexts()[0]; const page=ctx.pages()[0]||await ctx.newPage();
async function cf(){ for(let k=0;k<30;k++){ const t=await page.title(); if(!/Just a moment/i.test(t)) return t; await page.waitForTimeout(2000);} return 'CF'; }
for (const c of counties){
  const html=fs.readFileSync(`${OUT}/${c}-list.html`,'utf8'); const links=[...new Set([...html.matchAll(/getballot\.aspx\?elect=20261103G&amp;prsid=([^&"]+)&amp;bpty=X/g)].map(m=>m[1]))];
  fs.mkdirSync(`${OUT}/${c}`,{recursive:true});
  await page.goto(`https://lookup.boe.ohio.gov/vtrapp/${c}/ballotlist.aspx`,{waitUntil:'load',timeout:60000}); console.log(c, await cf(), links.length);
  let ok=0,bad=0; const todo=links.filter(p=>!fs.existsSync(`${OUT}/${c}/${p}.pdf`));
  for (let i=0;i<todo.length;i+=2){
    const batch=todo.slice(i,i+2); await page.waitForTimeout(1200);
    const res=await page.evaluate(async ([c,batch])=>Promise.all(batch.map(async p=>{ try{ const r=await fetch(`/vtrapp/${c}/getballot.aspx?elect=20261103G&prsid=${encodeURIComponent(p)}&bpty=X`); const b=new Uint8Array(await r.arrayBuffer()); let s=''; for(let i=0;i<b.length;i+=8192) s+=String.fromCharCode.apply(null,b.subarray(i,i+8192)); return [p,r.status,r.headers.get('content-type'),btoa(s)]; }catch(e){return [p,0,String(e),'']} })),[c,batch]);
    for (const [p,st,ct,b64] of res){ const buf=Buffer.from(b64,'base64'); if(st===200 && buf.slice(0,4).toString()==='%PDF'){ fs.writeFileSync(`${OUT}/${c}/${p}.pdf`,buf); ok++; } else { bad++; console.log('bad',c,p,st,ct,buf.slice(0,80).toString()); if(/Just a moment/.test(buf.toString())){ await page.reload(); await cf(); } if(st===429){ await page.waitForTimeout(20000); } } }
    if(i%40===0) console.log(c,i,ok,bad);
  }
  console.log('county done',c,ok,bad);
}
await br.close(); await bb.sessions.update(s.id,{projectId:"f2ae15a0-a894-4419-977f-d52f52483f0c",status:'REQUEST_RELEASE'}).catch(e=>console.log('rel',String(e).slice(0,200)));
console.log('DONE');
