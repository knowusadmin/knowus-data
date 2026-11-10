
const pw=require('/home/user/node_modules/playwright-core');const fs=require('fs');
const [,,inF,outF]=process.argv;const items=JSON.parse(fs.readFileSync(inF));
const done=new Set();if(fs.existsSync(outF))fs.readFileSync(outF,'utf8').split('\n').filter(Boolean).forEach(l=>{try{done.add(JSON.parse(l).key)}catch(e){}});
(async()=>{const b=await pw.chromium.launch({executablePath:'/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args:['--no-sandbox']});
const ctx=await b.newContext({userAgent:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'});
await ctx.route('**/*',r=>{const t=r.request().resourceType();if(['image','media','font','stylesheet'].includes(t))return r.abort();return r.continue();});
let p=await ctx.newPage();
const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const W8=(ms)=>new Promise((_,rej)=>setTimeout(()=>rej(new Error('watchdog')),ms));
for(const it of items){if(done.has(it.key))continue;let out={key:it.key,n:it.n,tried:[]};try{await Promise.race([W8(75000),(async()=>{
 for(const sl of it.slugs){try{const u='https://ballotpedia.org/'+sl;await p.goto(u,{timeout:30000,waitUntil:'domcontentloaded'});
   for(let k=0;k<12;k++){const t=await p.title();if(/Ballotpedia/.test(t))break;await p.waitForTimeout(500);}
   const r=await p.evaluate(()=>{const ib=document.querySelector('.infobox');const i=document.querySelector('.infobox img, .widget-img img, img.widget-img');return {t:document.title,u:location.href,img:i&&(i.getAttribute('src')||''),ib:ib?ib.innerText.slice(0,600):'',links:ib?[...ib.querySelectorAll('a')].map(a=>[a.innerText.trim().slice(0,40),a.href]).filter(x=>!/ballotpedia\.org/.test(x[1])&&/^https?:/.test(x[1])):[],dis:/may refer to|disambiguation/i.test(document.body.innerText.slice(0,3000))}});
   out.tried.push(sl);
   const ib=norm(r.ib),ok=r.img&&!r.dis&&(it.must||[]).every(w=>ib.includes(norm(w)))&&(!(it.any||[]).length||it.any.some(w=>ib.includes(norm(w))))&&norm(r.t).includes(norm(it.last));
   if(ok){Object.assign(out,{url:r.u,img:r.img,ib:r.ib.slice(0,240),links:r.links});break;}
   if(r.ib&&!out.ib0)out.ib0=r.ib.slice(0,160);
 }catch(e){out.err=String(e.message).slice(0,80);try{await p.close();}catch(_){};p=await ctx.newPage();}}
 })()]);}catch(e){out.err='watchdog';try{await p.close();}catch(_){};p=await ctx.newPage();}
 fs.appendFileSync(outF,JSON.stringify(out)+'\n');}
await b.close();})();
