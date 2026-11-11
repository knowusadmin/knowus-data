
const pw=require(process.env.PW_CORE); const fs=require('fs');
(async()=>{const b=await pw.chromium.launch({executablePath:process.env.PW_CHROME,args:['--no-sandbox']});
const ctx=await b.newContext({userAgent:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}); const p=await ctx.newPage();
const base='https://assets01.aws.connect.clarityelections.com/Assets/Connect/RootPublish/dallas-tx.connect.clarityelections.com/SampleBallots/2026/261103GeneralJoint/';
const out=process.argv[2]; fs.mkdirSync(out,{recursive:true});
await p.goto(base+'1.pdf',{timeout:45000}).catch(()=>{}); await p.waitForTimeout(6000);
for(let n=1;n<=216;n++){ const f=out+'/'+n+'.pdf'; if(fs.existsSync(f)&&fs.statSync(f).size>100000) continue;
  for(let t=0;t<3;t++){ try{const r=await ctx.request.get(base+n+'.pdf',{timeout:60000}); const bd=await r.body();
    if(r.status()===200 && bd.slice(0,4).toString()==='%PDF'){fs.writeFileSync(f,bd); console.log(n,'ok',bd.length); break;}
    console.log(n,'status',r.status(),bd.length); await p.goto(base+n+'.pdf',{timeout:45000}).catch(()=>{}); await p.waitForTimeout(6000);
  }catch(e){console.log(n,'err',String(e).slice(0,80));} } }
console.log('DONE'); await b.close();})();
