// KUS-SPECIALS-v88 block as inserted into site ballot.js (before '/* ---------- state ---------- */'); prepFull renamed prepFull0 and wrapped; assemble adds spBallots; townHTML in summaryHTML/ballotHTML; Town line in makePDF.
/* ---------- KUS-SPECIALS-v88: local run-off / special elections (Miami-Dade municipal run-offs): one official sample ballot per municipality,
   shown ONLY for addresses inside the official municipal boundary (county GIS), as its own ballot with its own date, never mixed into Nov 3 ---------- */
var SPC=[{id:'fl-miami-dade-2026-11-17',st:'FL',re:/dade/i,day:'2026-11-17',f:'sp-fl-miami-dade-2026-11-17.json',d:null,pick:{}},
  {id:'fl-miami-dade-2026-12-01',st:'FL',re:/dade/i,day:'2026-12-01',f:'sp-fl-miami-dade-2026-12-01.json',d:null,pick:{}}],SPV='?v=88';
function spShowUntil(day){return addDays(day,7);}
function spList(vr){var t=todayISO();return SPC.filter(function(E){return vr&&vr.state===E.st&&E.re.test(countyOf(vr))&&t<=spShowUntil(E.day);});}
function prepSpecial(vr){var L=spList(vr);if(!L.length)return Promise.resolve(false);var a=addrKey(vr.matched||vr.q);
  return Promise.all(L.map(function(E){return (E.d?Promise.resolve():getJSON('data/ballots/'+E.f+SPV).then(function(j){E.d=j;})).then(function(){if(!(a in E.pick))E.pick[a]=geoFind(E.d.geo,vr.x,vr.y);return !!E.pick[a];},function(){return false;});}))
    .then(function(r){return r.some(Boolean);});}
function spContest(E,k,c){return {type:'candidate',key:hashKey('sp|'+E.id+'|'+k+'|'+c.t),office:c.t,district:'',voteFor:/^\d+$/.test(c.vf)?c.vf:'1',
    candidates:c.c.map(function(x){return {name:x[0],party:x[1]||''};}),writein:false,notes:c.n||[],info:[],noParty:c.c.length>0&&c.c.every(function(x){return !x[1];})};}
function spBallots(vr){var a=addrKey(vr&&(vr.matched||vr.q)),addr=vr&&(vr.matched||vr.q)||'',out=[];
  spList(vr).forEach(function(E){var D=E.d,k=D&&E.pick[a],B=k&&D.b[k];if(!B)return;
    var cty=D.county.replace(/, Florida$/,''),pdf={label:'Official sample ballot (PDF)',url:B.pdf,sub:D.office+' \u2014 '+B.name.replace(/^./,function(s){return s.toUpperCase();})};
    var base={id:'kus-sp-'+E.id+'-'+k.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name:B.name.replace(/^./,function(s){return s.toUpperCase();}),day:E.day,address:addr,asOf:D.read+'T12:00:00',showUntil:spShowUntil(E.day),
      county:D.county,town:B.muni,townNote:'Matched from your address on '+cty+'\u2019s official municipal boundary map. Only voters inside '+B.muni+' get this ballot.',special:true,
      source:D.source,sourceUrl:D.sourceUrl,links:[{label:'Official sample ballots by election',url:D.sourceUrl,sub:D.office}]};
    if(B.ok)out.push(Object.assign(base,{kind:'official',full:true,label:'Your full ballot \u00b7 '+fmtDay(E.day)+' '+B.name,
      orderNote:'Every contest on the official sample ballot for '+B.muni+', in the order printed on it. This is a separate election from the Nov 3 general.',coverage:'',
      contests:B.c.map(function(c){return spContest(E,k,c);}),fullLink:pdf}));
    else{var look={label:'See your complete official sample ballot',url:B.pdf||D.lookup,sub:D.office,official:true};
      out.push(Object.assign(base,{kind:'ctpart',full:false,label:'Ballot as of '+fmtDay(E.day)+' '+B.name,orderNote:'From the county\u2019s official sample ballot.',
        coverage:'This ballot couldn\u2019t be checked as complete, so only the races confirmed for your address are shown. Your official sample ballot has every race.',
        contests:B.c.map(function(c){return spContest(E,k,c);}),blx:look,fullLink:look}));}});
  return out;}
function townHTML(b){return b.town?'<p class="bprec"><b>Your town:</b> '+esc(b.town)+(b.county?' \u00b7 '+esc(b.county):'')+'<br><span class="small">'+esc(b.townNote||'')+'</span></p>':'';}
