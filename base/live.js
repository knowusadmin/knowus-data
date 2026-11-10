/* KnowUS: live data layer (v39: official / open-government sources only).
   Baked data (data.js) paints instantly and is the offline fallback.
   On open, this checks the current U.S. Congress roster (the public-domain congress-legislators dataset,
   built from official House/Senate/Bioguide records) and merges it over the baked copy, then caches it.
   State officers, the Cabinet, the President and chief justices are NOT live-updated in the browser any more
   (owner's rule, Nov 9 2026: no Wikipedia/Wikidata); they come from the baked copy, which is rebuilt from
   official government sites. */
(function(){
'use strict';
var D=window.GOV_DATA; if(!D) return;
var KEY='wio-live-v2:'+D.asOf, FRESH_MS=20*60*1000, TIMEOUT=20000, RETRY_MS=2000;
var PRIMARY=['congress'];
var SRC={
  congress:'https://unitedstates.github.io/congress-legislators/legislators-current.json'
};
/* nothing from these hosts is ever applied over the baked data (old caches / old overlays included) */
var BANNED_HOST=/(^|\.)(wikipedia\.org|wikimedia\.org|wikidata\.org|apnews\.com|reuters\.com)$/i;
function bannedUrl(u){if(!u||typeof u!=='string')return false;var m=/^(?:https?:)?\/\/([^\/?#]+)/i.exec(u);return !!(m&&BANNED_HOST.test(m[1].replace(/^www\./,'')));}
function clean(x){if(!x)return x;if(x.w)delete x.w;if(x.d&&x.live)delete x.d;['img','u','src','bioSrc'].forEach(function(k){if(bannedUrl(x[k]))delete x[k];});return x;}
function bioguideImg(bg){return 'https://bioguide.congress.gov/bioguide/photo/'+bg[0]+'/'+bg+'.jpg';}
var BP=JSON.parse(JSON.stringify(D.people));
var BS={}; Object.keys(D.states).forEach(function(ab){var s=D.states[ab];BS[ab]={exec:s.exec.slice(),sen:s.sen.slice(),rep:s.rep.slice(),vacant:s.vacant.slice(),chief:s.court&&s.court.chief};});
var BF={president:D.fed.president,vp:D.fed.vp,cabinet:D.fed.cabinet.slice(),presidents:D.fed.presidents.slice()};
var NAMES={}; Object.keys(D.states).forEach(function(ab){NAMES[ab]=D.states[ab].name;});
var BYNAME=Object.keys(NAMES).sort(function(a,b){return NAMES[b].length-NAMES[a].length;});
var MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
var L=window.GOV_LIVE={state:'baked',checkedAt:null,savedAt:null,parts:{},changes:[],refresh:refresh};

function today(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);}
function iso2txt(s){if(!s)return '';var m=/^(\d{4})-(\d\d)-(\d\d)/.exec(s);return m?MONTHS[+m[2]-1]+' '+(+m[3])+', '+m[1]:'';}
function txt2iso(s){var m=new RegExp('('+MONTHS.join('|')+')\\s+(\\d{1,2}),?\\s+(\\d{4})').exec(s||'');if(!m)return null;return m[3]+'-'+('0'+(MONTHS.indexOf(m[1])+1)).slice(-2)+'-'+('0'+m[2]).slice(-2);}
function norm(n){return String(n||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(jr|sr|ii|iii|iv)\b\.?/g,'').replace(/\([^)]*\)/g,'').replace(/[^a-z ]/g,' ').replace(/\s+/g,' ').trim();}
function sameName(a,b){a=norm(a);b=norm(b);if(!a||!b)return false;if(a===b)return true;var A=a.split(' '),B=b.split(' ');return A[A.length-1]===B[B.length-1]&&(A[0]===B[0]||A[0][0]===B[0][0]);}
function okName(n){return typeof n==='string'&&n.length>3&&n.length<70&&/^[^\d]*$/.test(n)&&/\S+\s+\S+/.test(n)&&!/^Q\d+$/.test(n)&&!/vacant/i.test(n);}
function clone(o){return JSON.parse(JSON.stringify(o));}
function timed(url,opt,ms){var c=('AbortController' in window)?new AbortController():null;var t=setTimeout(function(){c&&c.abort();},ms||TIMEOUT);opt=opt||{};if(c)opt.signal=c.signal;opt.cache='no-store';opt.credentials='omit';
  return fetch(url,opt).then(function(r){clearTimeout(t);if(!r.ok)throw new Error('HTTP '+r.status);return r.json();},function(e){clearTimeout(t);throw e;});}

/* ---------- cache ---------- */
function load(){try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){return null;}}
function save(ov){try{localStorage.setItem(KEY,JSON.stringify(ov));}catch(e){}
  try{for(var i=localStorage.length-1;i>=0;i--){var k=localStorage.key(i);if(k&&k.indexOf('wio-live-')===0&&k!==KEY)localStorage.removeItem(k);}}catch(e){}}

/* ---------- apply an overlay onto the live data object ---------- */
function apply(ov){
  if(!ov||!(ov.v>=2))return;
  Object.keys(ov.people||{}).forEach(function(id){D.people[id]=clean(clone(ov.people[id]));});
  Object.keys(ov.states||{}).forEach(function(ab){var s=D.states[ab],o=ov.states[ab];if(!s)return;
    ['exec','sen','rep','vacant'].forEach(function(k){if(o[k])s[k]=o[k].slice();});
    if(o.chief&&s.court)s.court.chief=o.chief;});
  var f=ov.fed||{};['president','vp'].forEach(function(k){if(f[k])D.fed[k]=f[k];});
  ['cabinet','presidents'].forEach(function(k){if(f[k])D.fed[k]=f[k].slice();});
}

/* ---------- Congress ---------- */
function ord(n){var s=['th','st','nd','rd'],v=n%100;return n+(s[(v-20)%10]||s[v]||s[0]);}
function party(p){return p==='Democrat'?'Democratic':p;}
function runStart(ts){var i=ts.length-1,t=ts[i];while(i>0){var p=ts[i-1];if(p.type!==t.type||p.state!==t.state)break;if(Date.parse(ts[i].start)-Date.parse(p.end)>8*864e5)break;i--;}return ts[i].start;}
function buildCongress(list,ov,changes){
  var st={},nSen=0,nRep=0;Object.keys(BS).forEach(function(ab){st[ab]={sen:[],rep:[]};});
  list.forEach(function(l){var ts=l.terms||[],t=ts[ts.length-1],bg=l.id&&l.id.bioguide;if(!t||!bg||!st[t.state])return;
    var x=BP[bg]?clone(BP[bg]):null,isNew=!x,sn=NAMES[t.state];
    var role=t.type==='sen'?((t.state_rank==='senior'?'Senior':'Junior')+' U.S. Senator from '+sn):('U.S. Representative, '+(t.district===0?sn+' at-large':sn+"'s "+ord(t.district)+' district'));
    if(isNew){var nm=l.name||{};x={id:bg,n:nm.official_full||((nm.first||'')+' '+(nm.last||'')).trim(),r:role,p:party(t.party),s:iso2txt(runStart(ts)),
      u:t.url||'',born:iso2txt(l.bio&&l.bio.birthday),te:iso2txt(t.end),phone:t.phone||'',office:t.office||'',bg:bg,img:bioguideImg(bg),live:1};
      changes.push({k:'new',who:x.n,role:role});}
    else{var changed=false;
      if(x.r!==role){x.r=role;changed=true;}
      if(party(t.party)&&party(t.party).slice(0,5)!==String(x.p).slice(0,5)){x.p=party(t.party);changed=true;}
      if(t.type==='rep'&&x.dist!==t.district){x.dist=t.district;changed=true;}
      var te=t.end>=today()?iso2txt(t.end):'';if(te&&x.te!==te){x.te=te;changed=true;}
      if(!changed)x=null;}
    if(t.type==='rep'&&isNew)x.dist=t.district;
    if(x)ov.people[bg]=x;
    if(t.type==='sen'){st[t.state].sen.push([t.state_rank==='senior'?0:1,bg]);nSen++;}else{st[t.state].rep.push(bg);nRep++;}
  });
  if(nSen<90||nRep<400)throw new Error('congress roster looks incomplete ('+nSen+' senators, '+nRep+' reps)');
  Object.keys(st).forEach(function(ab){var s=st[ab],b=BS[ab],seats=b.rep.length+b.vacant.length;
    if(!s.sen.length||!s.rep.length&&seats)return;
    s.sen.sort(function(a,c){return a[0]-c[0];});
    var dist=function(id){return ov.people[id]?ov.people[id].dist:BP[id].dist;};
    var filled={};s.rep.forEach(function(id){filled[dist(id)]=1;});
    var vac=[];if(seats===1){if(!s.rep.length)vac.push(0);}else for(var d=1;d<=seats;d++)if(!filled[d])vac.push(d);
    if(s.rep.length+vac.length!==seats)return;
    var o=ov.states[ab]=ov.states[ab]||{};o.sen=s.sen.map(function(e){return e[1];});o.rep=s.rep;o.vacant=vac;
    b.sen.forEach(function(id){if(o.sen.indexOf(id)<0)changes.push({k:'left',who:BP[id].n,role:BP[id].r});});
    b.rep.forEach(function(id){if(o.rep.indexOf(id)<0)changes.push({k:'left',who:BP[id].n,role:BP[id].r});});
  });
}

/* ---------- refresh ---------- */
var running=null;
function refresh(force){
  if(running)return running;
  if(!force&&L.checkedAt&&Date.now()-L.checkedAt<FRESH_MS)return Promise.resolve(L);
  if(!('fetch' in window))return Promise.resolve(L);
  L.loading=true;emit();
  var ov={v:2,asOf:D.asOf,people:{},states:{},fed:{},parts:{},changes:[]};
  function later(ms){return new Promise(function(res){setTimeout(res,ms);});}
  // every source gets one automatic retry ~2 s after a failure or timeout
  function part(name,fn){var p=fn(false).catch(function(){return later(RETRY_MS).then(function(){return fn(true);});});
    return p.then(function(v){ov.parts[name]='live';return v;},function(e){ov.parts[name]='failed';L.errors=L.errors||{};L.errors[name]=String(e&&e.message||e);return null;});}
  var pc=part('congress',function(){return timed(SRC.congress).then(function(list){buildCongress(list,ov,ov.changes);});});
  running=Promise.all([pc]).then(function(){
    var ok=Object.keys(ov.parts).filter(function(k){return ov.parts[k]==='live';}).length;
    if(!ok)throw new Error('all sources failed');
    return ov;
  }).then(function(ov){
    ov.checkedAt=Date.now();
    // start from baked, then lay the fresh overlay on top (a person dropped since last time goes back to baked)
    reset();apply(ov);save(ov);
    L.state='live';L.via='phone';L.checkedAt=ov.checkedAt;L.parts=ov.parts;L.changes=ov.changes;L.loading=false;running=null;emit(true);return L;
  },function(e){L.loading=false;running=null;if(L.state!=='live'||!L.checkedAt||Date.now()-L.checkedAt>FRESH_MS)L.state='saved';L.error=String(e&&e.message||e);emit();return L;});
  return running;
}
function reset(){Object.keys(BS).forEach(function(ab){var s=D.states[ab],b=BS[ab];s.exec=b.exec.slice();s.sen=b.sen.slice();s.rep=b.rep.slice();s.vacant=b.vacant.slice();if(s.court)s.court.chief=b.chief;});
  D.fed.president=BF.president;D.fed.vp=BF.vp;D.fed.cabinet=BF.cabinet.slice();D.fed.presidents=BF.presidents.slice();
  Object.keys(D.people).forEach(function(id){if(BP[id])D.people[id]=clone(BP[id]);else if(/^L/.test(id)||(D.people[id]&&D.people[id].live))delete D.people[id];});}
function emit(changed){try{window.dispatchEvent(new CustomEvent('govdata:status',{detail:{changed:!!changed}}));}catch(e){}}

/* ---------- v25: the hourly GitHub refresh (knowusadmin/knowus-data) ----------
   The workflow runs this same merge on GitHub every hour and commits the overlay.
   Phones read that file first (one small request); only when it is missing, stale,
   or built for a different baked copy do they fall back to their own live refresh,
   and the baked data.js stays the offline fallback under everything. */
var GH='https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/', GH_TIMEOUT=6000, GH_FRESH_MS=3*60*60*1000;
window.KUS_GH_BASE=GH;
function ghGet(f){return timed(GH+f+'?t='+Math.floor(Date.now()/60000),{},GH_TIMEOUT);}
/* would this overlay change anything on screen? (checked without touching the data, so nothing is redrawn for nothing) */
function sameAsNow(ov){var k4=function(x){return x?[x.n,x.r,x.p,x.s].join('|'):'';},srt=function(a){return (a||[]).slice().sort().join(',');},ok=true;
  Object.keys(ov.people||{}).forEach(function(id){if(k4(D.people[id])!==k4(ov.people[id]))ok=false;});
  Object.keys(D.people).forEach(function(id){var x=D.people[id];if((/^L/.test(id)||x.live)&&!BP[id]&&!(ov.people||{})[id])ok=false;});
  Object.keys(ov.states||{}).forEach(function(ab){var s=D.states[ab],o=ov.states[ab];if(!s)return;['exec','sen','rep','vacant'].forEach(function(k){if(o[k]&&srt(o[k])!==srt(s[k]))ok=false;});if(o.chief&&s.court&&o.chief!==s.court.chief)ok=false;});
  var f=ov.fed||{};['president','vp'].forEach(function(k){if(f[k]&&f[k]!==D.fed[k])ok=false;});['cabinet','presidents'].forEach(function(k){if(f[k]&&f[k].join(',')!==(D.fed[k]||[]).join(','))ok=false;});
  return ok;}
function ghPull(){
  if(!('fetch' in window))return Promise.resolve(false);
  return Promise.all([ghGet('officials-overlay.json'),ghGet('officials-meta.json').catch(function(){return null;}),ghGet('last-check.json').catch(function(){return null;})]).then(function(r){
    var ov=r[0],meta=r[1],lc=r[2];
    if(meta&&meta.checkedAt){var mt=Date.parse(meta.checkedAt);if(mt){L.ghCheckedAt=mt;L.ghMeta=meta;}}
    /* v30: the hourly job stamps last-check.json on every run (even when nothing changed), so a quiet day doesn't look stale */
    if(lc&&lc.checkedAt&&lc.officials==='success'){var lt=Date.parse(lc.checkedAt);if(lt&&(!L.ghCheckedAt||lt>L.ghCheckedAt))L.ghCheckedAt=lt;}
    if(!ov||!(ov.v>=2)||ov.asOf!==D.asOf||!ov.people||!ov.checkedAt){L.ghState='mismatch';emit();return false;}
    L.ghState='ok';if(!L.ghCheckedAt)L.ghCheckedAt=ov.checkedAt;
    var mine=load();
    var changed=false;
    if(!mine||!(mine.v>=2)||mine.asOf!==D.asOf||!mine.checkedAt||ov.checkedAt>=mine.checkedAt){changed=!sameAsNow(ov);if(changed){reset();apply(ov);}save(ov);L.parts=ov.parts||{};L.changes=ov.changes||[];L.savedAt=ov.checkedAt;}
    if(Date.now()-ov.checkedAt<GH_FRESH_MS){L.state='live';L.checkedAt=ov.checkedAt;L.via='github';}
    emit(changed);return L.via==='github';
  },function(e){L.ghState='failed';L.ghError=String(e&&e.message||e);return false;});
}
L.ghPull=ghPull;

/* ---------- start: lay the last fetched copy over the baked data before first paint ---------- */
var cached=load();
if(cached&&cached.v>=2&&cached.asOf===D.asOf){apply(cached);L.parts=cached.parts||{};L.changes=cached.changes||[];L.savedAt=cached.checkedAt;
  if(Date.now()-cached.checkedAt<FRESH_MS){L.state='live';L.checkedAt=cached.checkedAt;}else L.state='saved';}
else L.state='saved';
L.statusText=function(){
  var t=function(ms){var d=new Date(ms),now=new Date(),same=d.toDateString()===now.toDateString();
    return (same?'':d.toLocaleDateString(undefined,{month:'short',day:'numeric'})+', ')+d.toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'});};
  if(L.loading&&L.state!=='live')return {cls:'chk',txt:'Checking for updates…'};
  if(L.state==='live'&&L.via==='github'){return {cls:'live',txt:'Updated '+t(L.ghCheckedAt||L.checkedAt)+' · hourly check of official sources'};}
  if(L.state==='live'){var miss=PRIMARY.filter(function(k){return L.parts&&L.parts[k]==='failed';}).length;return {cls:'live',txt:'Live data · checked '+t(L.checkedAt)+(miss?' · a few details from saved copy':'')};}
  if(L.ghCheckedAt&&L.ghState==='ok')return {cls:'saved',txt:'Updated '+t(L.ghCheckedAt)+' · saved copy'};
  return {cls:'saved',txt:'Saved copy from '+(L.savedAt?new Date(L.savedAt).toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'}):D.asOf)};
};
var ghTried=0;
function kick(){if(Date.now()-ghTried>10*60*1000){ghTried=Date.now();ghPull().then(function(fresh){if(!fresh)refresh(false);});}else if(!(L.via==='github'&&L.checkedAt&&Date.now()-L.checkedAt<GH_FRESH_MS))refresh(false);}
if(document.readyState==='complete')setTimeout(kick,50);else window.addEventListener('load',function(){setTimeout(kick,50);});
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')kick();});
window.addEventListener('online',kick);
})();
