import { Stagehand, browserbase } from "@browserbasehq/stagehand"; import fs from "node:fs";
const V = JSON.parse(fs.readFileSync("/home/user/tab/.vendor-capability.json", "utf8"));
const url = process.argv[2], out = process.argv[3];
const browser = await browserbase.launch({ apiKey: V.token, baseUrl: `${V.base_url}/browserbase`, projectId: "f2ae15a0-a894-4419-977f-d52f52483f0c", keepAlive: false, timeout: 600, userMetadata: { site: "mvic", task: process.env.TAB_TASK_ID, purpose: "knowus-local-officials" } });
const sh = await Stagehand.create({ browser, model: { generate: async () => ({ role: "assistant", outputFormat: "text", content: "" }) }, logging: { level: "error" } });
try {
  const page = await browser.context.activePage();
  await page.goto(url, { waitUntil: "load", timeout: 60000 });
  let title = await page.title();
  for (let i=0;i<20 && /moment|security|attention/i.test(title);i++){ await page.waitForTimeout(2000); title = await page.title(); }
  await page.waitForTimeout(3000);
  const counties = JSON.parse(fs.readFileSync(process.argv[4],"utf8")); let res={};
  if (fs.existsSync(out)) res = JSON.parse(fs.readFileSync(out,"utf8"));
  for (const [id,name] of counties) {
    if (res["c"+id]) continue;
    const r = await page.evaluate(async ([id,name]) => {
      const H={"X-Requested-With":"XMLHttpRequest","Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"};
      const out={county:"",locals:{}};
      try {
        const b=new URLSearchParams({CountyName:name,CountyID:id,Address:"",Latitude:"0",Longitude:"0"});
        const r = await fetch("/Voter/SearchByCounty",{method:"POST",headers:H,body:b.toString()}); const t=await r.text(); out.county=t;
        const doc=new DOMParser().parseFromString(t,"text/html");
        for (const a of doc.querySelectorAll("a.local-clerk-link")) {
          const u=new URL(a.getAttribute("href"),location.href); const p=u.searchParams;
          const b2=new URLSearchParams({jurisdictionCode:p.get("jurisdictionCode"),countyID:p.get("countyID"),jurisdictionName:p.get("jurisdictionName")});
          for (let k=0;k<3;k++){ try { const r2=await fetch("/Voter/LocalClerk",{method:"POST",headers:H,body:b2.toString()}); if (r2.ok){ out.locals[p.get("jurisdictionCode")+"|"+p.get("jurisdictionName")]=await r2.text(); break;} } catch(e){}
            await new Promise(s=>setTimeout(s,1500)); }
          await new Promise(s=>setTimeout(s,250));
        }
      } catch(e) { out.err=""+e; }
      return out; }, [id,name]);
    res["c"+id]=r; fs.writeFileSync(out, JSON.stringify(res)); console.log(id, name, Object.keys(r.locals).length);
  }
  console.log(JSON.stringify({title, url: page.url()}));
} finally { await browser.close().catch(()=>{}); }
