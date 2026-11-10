
const pw=require('/home/user/node_modules/playwright-core');const fs=require('fs');
(async()=>{const b=await pw.chromium.launch({executablePath:'/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args:['--no-sandbox']});
const c=await b.newContext();const p=await c.newPage();let HD=null;p.on('request',r=>{if(/api\/ballotStyle\//.test(r.url())&&!HD)HD=r.headers();});
await p.goto(process.argv[2],{waitUntil:'networkidle',timeout:60000}).catch(()=>{});await p.waitForTimeout(3000);
console.error('hdr',JSON.stringify(Object.keys(HD||{})));const pairs=JSON.parse(fs.readFileSync(process.argv[3]));const out={};
for(const [sid,pid,name,pl] of pairs){
  const t=await p.evaluate(async([sid,pid,HD])=>{const h={};for(const k in HD){if(!/^(sec-|user-agent|referer|accept-encoding|host|connection|content-length)/i.test(k))h[k]=HD[k];}const r=await fetch('/ebd/voter/api/ballotStyle/'+sid+'?jurisdictionId=f618f39e-2c4d-4aef-bc04-95cb530a29f9&precinctId='+pid+'&ballotType=sample',{headers:h});return r.status+'|'+(await r.text());},[sid,pid,HD]);
  out[name]={pl,status:t.split('|')[0],body:t.slice(t.indexOf('|')+1)};}
fs.writeFileSync(process.argv[4],JSON.stringify(out));console.log(Object.keys(out).length);await b.close();})();
