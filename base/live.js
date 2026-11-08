/* KnowUS: live data layer.
   Baked data (data.js) paints instantly and is the offline fallback.
   On open, this fetches current officeholders from public CORS-enabled sources,
   merges them over the baked copy, and caches the result for the next open. */
(function(){
'use strict';
var D=window.GOV_DATA; if(!D) return;
var KEY='wio-live-v1:'+D.asOf, FRESH_MS=20*60*1000, TIMEOUT=20000, WD_TIMEOUT=12000, RETRY_MS=2000;
/* parts that drive the status line; 'wikidata' is a backup source whose slots are covered by the saved copy */
var PRIMARY=['congress','gov','lg','ag','sos','cabinet','exec','fed'];
var SRC={
  congress:'https://unitedstates.github.io/congress-legislators/legislators-current.json',
  wp:function(page){return 'https://en.wikipedia.org/w/api.php?action=parse&prop=text&formatversion=2&format=json&origin=*&redirects=1&page='+encodeURIComponent(page);},
  wd:'https://query.wikidata.org/sparql?format=json&query=',
  sum:function(t){return 'https://en.wikipedia.org/api/rest_v1/page/summary/'+encodeURIComponent(t);}
};
var PAGES={gov:'List_of_current_United_States_governors',lg:'List_of_current_United_States_lieutenant_governors',ag:'State_attorney_general',sos:'Secretary_of_state_(U.S._state_government)',cab:'Cabinet_of_the_United_States'};
var POS={"Q179261":"CO.lg","Q288316":"IN.lg","Q845950":"AL.lg","Q846307":"GA.lg","Q880198":"GA.gov","Q887010":"CA.gov","Q887090":"CT.gov","Q912560":"HI.lg","Q913797":"FL.lg","Q929060":"ID.lg","Q1540336":"AR.gov","Q1853515":"AR.lg","Q1853520":"IA.lg","Q3112719":"IL.gov","Q3238284":"CA.lg","Q3238288":"IL.lg","Q3406489":"CA.ag","Q4112147":"AR.ag","Q4818624":"AL.ag","Q4818633":"GA.ag","Q4818635":"HI.ag","Q5253226":"DE.ag","Q5589655":"HI.gov","Q7024182":"CA.sos","Q7444359":"AL.sos","Q7444360":"AZ.sos","Q7444364":"CO.sos","Q7444365":"DE.sos","Q7444366":"FL.sos","Q7444367":"GA.sos","Q7444368":"ID.sos","Q7444369":"IN.sos","Q16147601":"IN.gov","Q17031696":"DE.lg","Q17089716":"AR.sos","Q20198851":"FL.gov","Q20801644":"AK.gov","Q20801656":"DE.gov","Q20948752":"CT.lg","Q29514575":"AL.gov","Q29514606":"AZ.gov","Q29514674":"ID.gov","Q29514964":"CO.gov","Q60095901":"AK.lg","Q83981607":"IA.ag","Q115549231":"AZ.lg","Q383699":"MD.lg","Q693032":"MD.gov","Q20766109":"LA.gov","Q878632":"MS.gov","Q887117":"MA.gov","Q1274366":"MA.lg","Q1420322":"LA.lg","Q1532983":"KY.lg","Q1586403":"MI.lg","Q1853527":"KS.lg","Q1853534":"MT.lg","Q3112728":"NJ.gov","Q3506352":"ME.gov","Q4151335":"KY.gov","Q4818639":"KY.ag","Q4818647":"MD.ag","Q5589668":"KS.gov","Q5589680":"MI.gov","Q5589682":"MN.gov","Q5589687":"NH.gov","Q5589688":"NE.gov","Q6544423":"MS.lg","Q6544426":"NJ.lg","Q7444371":"KS.sos","Q7444374":"LA.sos","Q7444375":"ME.sos","Q7444376":"MD.sos","Q7444377":"MS.sos","Q7444379":"NE.sos","Q7444380":"NJ.sos","Q7444381":"NV.sos","Q16191529":"NV.lg","Q16197533":"MT.sos","Q17091482":"KY.sos","Q20801646":"MT.gov","Q20801651":"NV.gov","Q20801667":"MO.gov","Q27841906":"LA.ag","Q61612454":"MN.lg","Q96482513":"MO.lg","Q100255527":"MO.sos","Q126719900":"NE.lg","Q238994":"NM.lg","Q639115":"TX.lg","Q887220":"UT.gov","Q1402980":"PA.lg","Q1538949":"NC.lg","Q1660669":"OH.lg","Q1853541":"OK.lg","Q1853549":"SD.lg","Q1853553":"UT.lg","Q2347975":"NY.gov","Q2550683":"OK.gov","Q2626318":"SD.gov","Q3773741":"ND.gov","Q3773745":"VT.gov","Q3773752":"SC.gov","Q4818643":"NM.ag","Q4818646":"OK.ag","Q4818654":"RI.ag","Q5589724":"TN.gov","Q5589725":"TX.gov","Q6544428":"NY.lg","Q6544436":"TN.lg","Q7013056":"NY.ag","Q7444382":"NM.sos","Q7444385":"RI.sos","Q7444386":"SD.sos","Q7444387":"SC.sos","Q7444388":"TX.sos","Q7444389":"VT.sos","Q15110606":"UT.ag","Q16148056":"NY.sos","Q16149111":"OR.gov","Q16202700":"NC.gov","Q17059070":"ND.lg","Q17089908":"NM.gov","Q17989863":"OH.gov","Q20765611":"RI.gov","Q20801659":"PA.gov","Q28020371":"SC.lg","Q28132187":"VT.lg","Q100255535":"UT.sos","Q115677246":"RI.lg","Q878942":"VA.gov","Q931202":"VA.lg","Q1853559":"WA.lg","Q3112727":"WI.gov","Q4818656":"VA.ag","Q6544440":"WI.lg","Q7444392":"WA.sos","Q7444393":"WV.sos","Q7444394":"WI.sos","Q7444395":"WY.sos","Q7444414":"PA.sos","Q7444415":"VA.sos","Q8563951":"FL.ag","Q19647220":"WA.gov","Q20801647":"WY.gov","Q20801652":"WV.gov","Q27841920":"WI.ag","Q83981561":"WA.ag","Q6064575":"IA.sos","Q7444426":"CT.sos","Q20801664":"IA.gov","Q3406491":"IL.ag","Q3477292":"IL.sos","Q4708496":"AK.ag","Q4791244":"AZ.ag","Q5148732":"CO.ag","Q5161480":"CT.ag","Q6023060":"IN.ag","Q6364574":"KS.ag","Q16147713":"ID.ag","Q3406492":"MA.ag","Q6736314":"ME.ag","Q6837452":"MI.ag","Q6868157":"MN.ag","Q6868428":"MN.sos","Q6879059":"MS.ag","Q6879488":"MO.ag","Q6984676":"NE.ag","Q7008094":"NH.ag","Q7008307":"NH.sos","Q15110599":"NV.ag","Q83981544":"MT.ag","Q12061506":"MA.sos","Q16147324":"MI.sos","Q15110603":"NJ.ag","Q7054426":"NC.ag","Q7054588":"NC.sos","Q7054992":"ND.ag","Q7055042":"ND.sos","Q7080745":"OH.ag","Q7080891":"OH.sos","Q7082315":"OK.sos","Q7101039":"OR.ag","Q7101331":"OR.sos","Q7163643":"PA.ag","Q7566950":"SD.ag","Q19845419":"SC.ag","Q7700018":"TN.ag","Q7700163":"TN.sos","Q7707525":"TX.ag","Q7921680":"VT.ag","Q8040304":"WY.ag","Q19845411":"WV.ag","Q127686476":"CT.cj","Q139972518":"FL.cj","Q127689693":"AL.cj","Q127692059":"MT.cj","Q81589384":"ND.cj","Q125251563":"CO.cj","Q5096818":"OH.cj","Q114354452":"PA.cj","Q106781470":"NJ.cj","Q58494023":"RI.cj","Q104203603":"DE.cj","Q99336934":"NC.cj","Q116946829":"SC.cj","Q117406642":"TN.cj","Q64210783":"IA.cj","Q111010414":"AR.cj","Q11696":"US.pres","Q11699":"US.vp"};
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
function wpUrl(href){if(!href)return null;var m=/^\/wiki\/([^#?]+)/.exec(href);return m?'https://en.wikipedia.org/wiki/'+m[1]:null;}
function wpTitle(u){var m=/\/wiki\/([^#?]+)/.exec(u||'');return m?decodeURIComponent(m[1]):null;}
function timed(url,opt,ms){var c=('AbortController' in window)?new AbortController():null;var t=setTimeout(function(){c&&c.abort();},ms||TIMEOUT);opt=opt||{};if(c)opt.signal=c.signal;opt.cache='no-store';opt.credentials='omit';
  return fetch(url,opt).then(function(r){clearTimeout(t);if(!r.ok)throw new Error('HTTP '+r.status);return r.json();},function(e){clearTimeout(t);throw e;});}

/* ---------- cache ---------- */
function load(){try{return JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){return null;}}
function save(ov){try{localStorage.setItem(KEY,JSON.stringify(ov));}catch(e){}
  try{for(var i=localStorage.length-1;i>=0;i--){var k=localStorage.key(i);if(k&&k.indexOf('wio-live-')===0&&k!==KEY)localStorage.removeItem(k);}}catch(e){}}

/* ---------- apply an overlay onto the live data object ---------- */
function apply(ov){
  if(!ov)return;
  Object.keys(ov.people||{}).forEach(function(id){D.people[id]=clone(ov.people[id]);});
  Object.keys(ov.states||{}).forEach(function(ab){var s=D.states[ab],o=ov.states[ab];if(!s)return;
    ['exec','sen','rep','vacant'].forEach(function(k){if(o[k])s[k]=o[k].slice();});
    if(o.chief&&s.court)s.court.chief=o.chief;});
  var f=ov.fed||{};['president','vp'].forEach(function(k){if(f[k])D.fed[k]=f[k];});
  ['cabinet','presidents'].forEach(function(k){if(f[k])D.fed[k]=f[k].slice();});
}

/* ---------- Wikipedia table reading ---------- */
function grid(tbl){var out=[],rows=tbl.querySelectorAll('tr'),pend={};
  for(var r=0;r<rows.length;r++){var row=[],cells=rows[r].children,c=0;
    for(var i=0;i<cells.length;i++){var cell=cells[i];if(!/^T[DH]$/.test(cell.tagName))continue;
      while(pend[c]&&pend[c].n>0){row[c]=pend[c].cell;pend[c].n--;c++;}
      var cs=Math.min(+cell.getAttribute('colspan')||1,20),rs=Math.min(+cell.getAttribute('rowspan')||1,60);
      for(var k=0;k<cs;k++){row[c]=cell;if(rs>1)pend[c]={cell:cell,n:rs-1};c++;}}
    while(pend[c]&&pend[c].n>0){row[c]=pend[c].cell;pend[c].n--;c++;}
    out.push({el:rows[r],cells:row});}
  return out;}
function ctext(cell){if(!cell)return '';var x=cell.cloneNode(true);Array.prototype.forEach.call(x.querySelectorAll('sup,style,.sortkey,[style*="display:none"]'),function(n){n.remove();});return x.textContent.replace(/\s+/g,' ').trim();}
function personLink(cell){if(!cell)return null;var as=cell.querySelectorAll('a[href^="/wiki/"]');for(var i=0;i<as.length;i++){var h=as[i].getAttribute('href');if(h.indexOf(':')<0&&as[i].textContent.trim().length>3)return {name:as[i].textContent.replace(/\s+/g,' ').trim(),url:wpUrl(h)};}return null;}
function cellImg(cell){var im=cell&&cell.querySelector('img');if(!im)return null;var s=im.getAttribute('src')||'';if(s.indexOf('//')===0)s='https:'+s;if(!/upload\.wikimedia\.org/.test(s)||/Flag_of|Seal_of/i.test(s)||(+im.getAttribute('width')||99)<30)return null;return s;}
function stateOf(t){t=(t||'').replace(/\(.*?\)/g,'').trim();for(var i=0;i<BYNAME.length;i++){var ab=BYNAME[i];if(t.indexOf(NAMES[ab])===0)return ab;}return null;}
function readTables(html,spec){
  var doc=new DOMParser().parseFromString(html,'text/html'),res=[];
  Array.prototype.forEach.call(doc.querySelectorAll('table.wikitable'),function(tbl){
    var g=grid(tbl);if(g.length<2)return;
    var hi=-1;for(var i=0;i<Math.min(g.length,3);i++){if(g[i].cells.length&&g[i].cells.every(function(c){return c&&c.tagName==='TH';})){hi=i;}}
    if(hi<0)return;
    var cols={};g[hi].cells.forEach(function(c,ix){var t=ctext(c).replace(/\[.*?\]/g,'').trim();Object.keys(spec).forEach(function(k){if(spec[k].test(t)){(cols[k]=cols[k]||[]);if(cols[k].indexOf(ix)<0)cols[k].push(ix);}});});
    if(!cols.name)return;
    for(var r=hi+1;r<g.length;r++){var cells=g[r].cells,o={};
      function val(k){return (cols[k]||[]).map(function(ix){return ctext(cells[ix]);}).filter(Boolean).join(' ').replace(/\[.*?\]/g,'').trim();}
      var nc=cells[cols.name[0]];var pl=personLink(nc);if(!pl)continue;
      o.name=pl.name;o.url=pl.url;o.acting=/\bacting\b/i.test(ctext(nc));
      o.party=val('party');o.start=txt2iso(val('start'));o.te=val('end');o.office=val('office');o.state=cols.state?stateOf(val('state')):null;
      o.img=cols.img?cellImg(cells[cols.img[0]]):cellImg(nc);
      res.push(o);}
  });
  return res;}
var SPEC={name:/^(Governor|Name|Officeholder|Lieutenant governor)$/i,state:/^State$/i,party:/^Party$/i,start:/^(Term start|Assumed office|Took office|Start)$/i,end:/^(Term end|Term expires)$/i,img:/^(Image|Portrait|Photo)$/i};
var CABSPEC={office:/^Office/i,name:/^Name$/i,start:/^Start$/i,party:/^Party$/i};
function wpPage(slot){return timed(SRC.wp(PAGES[slot])).then(function(j){var h=j&&j.parse&&j.parse.text;if(!h)throw new Error('no page');return h;});}

/* ---------- Wikidata (President, VP, chief justices, second opinion on state officers) ---------- */
function wdQuery(retry){var q='SELECT ?pos ?h ?hLabel ?start ?ord ?img ?art ?partyLabel WHERE { VALUES ?pos { '+Object.keys(POS).map(function(k){return 'wd:'+k;}).join(' ')+' } '+
  '?h p:P39 ?st . ?st ps:P39 ?pos ; wikibase:rank ?rk . FILTER(?rk != wikibase:DeprecatedRank) ?st pq:P580 ?start . OPTIONAL { ?st pq:P582 ?end } OPTIONAL { ?st pq:P1545 ?ord } FILTER(!BOUND(?end) || ?end > NOW()) FILTER(?start <= NOW()) '+
  'OPTIONAL { ?h wdt:P18 ?img } OPTIONAL { ?art schema:about ?h ; schema:isPartOf <https://en.wikipedia.org/> } '+
  'OPTIONAL { ?h rdfs:label ?hLabel . FILTER(LANG(?hLabel)="en") } '+
  'OPTIONAL { ?h p:P102 ?ps . ?ps ps:P102 ?party . FILTER NOT EXISTS { ?ps pq:P582 ?pe } ?party rdfs:label ?partyLabel . FILTER(LANG(?partyLabel)="en") } }';
  var req=retry
    // first try: GET (cacheable at Wikidata's edge); retry: POST form body (no URL-length limits, different path through their servers)
    ?timed(SRC.wd.split('?')[0],{method:'POST',headers:{Accept:'application/sparql-results+json','Content-Type':'application/x-www-form-urlencoded'},body:'format=json&query='+encodeURIComponent(q)},TIMEOUT)
    :timed(SRC.wd+encodeURIComponent(q),{headers:{Accept:'application/sparql-results+json'}},WD_TIMEOUT);
  return req.then(function(j){
    var best={};(j.results.bindings||[]).forEach(function(b){var pos=b.pos.value.split('/').pop(),st=b.start&&b.start.value.slice(0,10);if(!st||!b.art||!b.hLabel)return;
      var cur=best[pos];if(cur&&cur.start>st)return;
      var img=b.img&&b.img.value.replace(/^http:/,'https:');if(img)img+='?width=250';
      if(cur&&cur.h===b.h.value){if(!cur.img&&img)cur.img=img;if(!cur.party&&b.partyLabel)cur.party=b.partyLabel.value;return;}
      best[pos]={h:b.h.value,ord:b.ord?b.ord.value:null,name:b.hLabel.value,start:st,img:img||null,url:b.art?b.art.value:null,party:b.partyLabel?b.partyLabel.value.replace(/ Party$/,'').replace(/^Democratic$/,'Democratic'):''};});
    var out={};Object.keys(best).forEach(function(pos){var k=POS[pos];out[k]=best[pos];});return out;});}

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
      w:l.id.wikipedia?'https://en.wikipedia.org/wiki/'+l.id.wikipedia.replace(/ /g,'_'):'',d:'',u:t.url||'',born:iso2txt(l.bio&&l.bio.birthday),te:iso2txt(t.end),phone:t.phone||'',office:t.office||'',bg:bg,img:'c',live:1};
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

/* ---------- state executives, cabinet, president, chief justices ---------- */
function slotOf(r){r=r||'';if(/Lieutenant Governor/i.test(r))return 'lg';if(/Governor/i.test(r))return 'gov';if(/Attorney General/i.test(r))return 'ag';if(/Secretary of/i.test(r))return 'sos';return null;}
// A live answer replaces the baked holder only when it names someone else who took office AFTER the baked holder did.
function newer(c,b){if(!c||!okName(c.name)||!c.start||c.start>today())return false;if(sameName(c.name,b.n))return false;var bs=txt2iso(b.s);return !bs||c.start>bs;}
function makePerson(id,b,c,src){var r=String(b.r||'').replace(/^Acting /,'');if(c.acting)r='Acting '+r;
  var x={id:id,n:c.name,r:r,p:c.party||'',s:iso2txt(c.start),w:c.url||'',d:'',img:c.img||null,live:1,src:src};
  if(c.te)x.te=c.te;['note','also','grp','short'].forEach(function(k){if(b[k])x[k]=b[k];});return x;}
function partyFill(ov,wd){Object.keys(ov.people).forEach(function(id){var x=ov.people[id];if(!x.live||x.p||/^Lcab|cj$/.test(id))return;Object.keys(wd).forEach(function(k){if(!x.p&&wd[k].party&&sameName(wd[k].name,x.n))x.p=wd[k].party;});});}
function mergeSlots(found,wd,ov,changes){
  var used={};
  Object.keys(BS).forEach(function(ab){var ex=BS[ab].exec.slice(),touched=false;
    ex.forEach(function(id,i){var b=BP[id],slot=slotOf(b.r);if(!slot)return;
      var w=found[slot]&&found[slot][ab],d=wd[ab+'.'+slot],c=null,src='';
      if(w&&newer(w,b)){c=w;src='Wikipedia';if(d&&sameName(d.name,w.name)){c.img=c.img||d.img;c.url=c.url||d.url;}}
      else if(!w&&d&&newer(d,b)){c=d;src='Wikidata';}
      if(!c)return;
      var nid='L'+ab+slot;ov.people[nid]=makePerson(nid,b,c,src);ex[i]=nid;touched=true;
      changes.push({k:'replaced',who:c.name,was:b.n,role:b.r,src:src});});
    if(touched){(ov.states[ab]=ov.states[ab]||{}).exec=ex;}
    var cj=BS[ab].chief,d2=wd[ab+'.cj'];
    if(cj&&d2&&newer(d2,BP[cj])){var nid='L'+ab+'cj';ov.people[nid]=makePerson(nid,BP[cj],d2,'Wikidata');ov.people[nid].p='';(ov.states[ab]=ov.states[ab]||{}).chief=nid;changes.push({k:'replaced',who:d2.name,was:BP[cj].n,role:BP[cj].r,src:'Wikidata'});}
  });}
function mergeCabinet(rows,wd,ov,changes){
  var cab=BF.cabinet.slice(),touched=false,vp=null;
  rows.forEach(function(r){var off=(r.office||'').replace(/\(.*$/,'').trim();if(/^Vice President/i.test(off))vp=r;});
  if(rows.length>=10){cab.forEach(function(id,i){var b=BP[id],m=null;
    rows.forEach(function(r){var off=(r.office||'').replace(/\(.*$/,'').replace(/\s+/g,' ').trim();if(!m&&off&&(off===b.r||off.replace(/^United States /,'')===b.r))m=r;});
    if(m&&newer(m,b)){var nid='Lcab'+i;ov.people[nid]=makePerson(nid,b,m,'Wikipedia');cab[i]=nid;touched=true;changes.push({k:'replaced',who:m.name,was:b.n,role:b.r,src:'Wikipedia'});}});}
  var f=ov.fed;if(touched)f.cabinet=cab;
  var bv=BP[BF.vp],cv=(vp&&newer(vp,bv))?vp:(!vp&&wd['US.vp']&&newer(wd['US.vp'],bv)?wd['US.vp']:null);
  if(cv){ov.people.Lvp=makePerson('Lvp',bv,cv,vp?'Wikipedia':'Wikidata');f.vp='Lvp';changes.push({k:'replaced',who:cv.name,was:bv.n,role:bv.r});}
  var bp=BP[BF.president],cp=wd['US.pres'];
  // a new president is taken only when Wikidata numbers the term as the next presidency
  if(cp&&String(cp.ord)===String((bp.no||47)+1)&&newer(cp,bp)){var no=(bp.no||47)+1,id='pr'+no,yr=cp.start.slice(0,4);
    var x=makePerson(id,bp,cp,'Wikidata');x.r=ord(no)+' President of the United States';x.no=no;x.yrs=yr+'–present';x.term=iso2txt(cp.start)+' – present';x.current=true;
    var old=clone(bp);old.current=false;old.yrs=String(old.yrs||'').replace('present',yr);old.term=String(old.term||'').replace('present',iso2txt(cp.start));
    ov.people[id]=x;ov.people[bp.id]=old;f.president=id;f.presidents=[id].concat(BF.presidents);changes.push({k:'replaced',who:cp.name,was:bp.n,role:'President'});}
}

/* ---------- fill in photo + bio for anyone new ---------- */
function enrich(ov){var ids=Object.keys(ov.people).filter(function(id){var x=ov.people[id];return x.live&&x.w&&!x.bio;}).slice(0,80);
  var i=0;function next(){if(i>=ids.length)return Promise.resolve();var x=ov.people[ids[i++]],t=wpTitle(x.w);if(!t)return next();
    return timed(SRC.sum(t)).then(function(j){if(j.description)x.d=j.description;if(j.extract)x.bio=j.extract;if(!x.img&&j.thumbnail&&j.thumbnail.source)x.img=j.thumbnail.source;},function(){}).then(next);}
  return Promise.all([next(),next(),next(),next(),next(),next()]);}

/* ---------- refresh ---------- */
var running=null;
function refresh(force){
  if(running)return running;
  if(!force&&L.checkedAt&&Date.now()-L.checkedAt<FRESH_MS)return Promise.resolve(L);
  if(!('fetch' in window)||!('DOMParser' in window))return Promise.resolve(L);
  L.loading=true;emit();
  var ov={v:1,asOf:D.asOf,people:{},states:{},fed:{},parts:{},changes:[]};
  function later(ms){return new Promise(function(res){setTimeout(res,ms);});}
  // every source gets one automatic retry ~2 s after a failure or timeout
  function part(name,fn){var p=fn(false).catch(function(){return later(RETRY_MS).then(function(){return fn(true);});});
    return p.then(function(v){ov.parts[name]='live';return v;},function(e){ov.parts[name]='failed';L.errors=L.errors||{};L.errors[name]=String(e&&e.message||e);return null;});}
  var pc=part('congress',function(){return timed(SRC.congress).then(function(list){buildCongress(list,ov,ov.changes);});});
  var pw={};['gov','lg','ag','sos'].forEach(function(s){pw[s]=part(s,function(){return wpPage(s).then(function(h){var rows=readTables(h,SPEC),by={},n=0;rows.forEach(function(r){if(r.state&&!by[r.state]){by[r.state]=r;n++;}});if(n<35)throw new Error('table unreadable ('+n+' states)');return by;});});});
  var pcab=part('cabinet',function(){return wpPage('cab').then(function(h){var rows=readTables(h,CABSPEC);if(rows.length<10)throw new Error('table unreadable');return rows;});});
  var pwd=part('wikidata',wdQuery);
  running=Promise.all([pc,pw.gov,pw.lg,pw.ag,pw.sos,pcab,pwd]).then(function(r){
    var found={gov:r[1],lg:r[2],ag:r[3],sos:r[4]},wd=r[6]||{};L._found=found;L._wd=wd;L._cab=r[5];
    try{mergeSlots(found,wd,ov,ov.changes);}catch(e){ov.parts.exec='failed';}
    try{mergeCabinet(r[5]||[],wd,ov,ov.changes);}catch(e){ov.parts.fed='failed';}
    try{partyFill(ov,wd);}catch(e){}
    var ok=Object.keys(ov.parts).filter(function(k){return ov.parts[k]==='live';}).length;
    if(!ok)throw new Error('all sources failed');
    return enrich(ov).then(function(){return ov;});
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
/* what the screen shows: lists, federal posts and every live-added person (a reorder within a list counts only if the set changed) */
function sigD(){var s={};Object.keys(D.states).forEach(function(ab){var x=D.states[ab];s[ab]=['exec','sen','rep','vacant'].map(function(k){return (x[k]||[]).slice().sort().join(',');}).join('|')+'|'+(x.court&&x.court.chief||'');});
  var l={};Object.keys(D.people).forEach(function(id){if(/^L/.test(id)||D.people[id].live)l[id]=D.people[id];});
  return JSON.stringify([s,D.fed.president,D.fed.vp,D.fed.cabinet,l]);}
function ghPull(){
  if(!('fetch' in window))return Promise.resolve(false);
  return Promise.all([ghGet('officials-overlay.json'),ghGet('officials-meta.json').catch(function(){return null;})]).then(function(r){
    var ov=r[0],meta=r[1];
    if(meta&&meta.checkedAt){var mt=Date.parse(meta.checkedAt);if(mt){L.ghCheckedAt=mt;L.ghMeta=meta;}}
    if(!ov||ov.asOf!==D.asOf||!ov.people||!ov.checkedAt){L.ghState='mismatch';emit();return false;}
    L.ghState='ok';if(!L.ghCheckedAt)L.ghCheckedAt=ov.checkedAt;
    var mine=load();
    var changed=false;
    if(!mine||mine.asOf!==D.asOf||!mine.checkedAt||ov.checkedAt>=mine.checkedAt){var before=sigD();reset();apply(ov);changed=sigD()!==before;save(ov);L.parts=ov.parts||{};L.changes=ov.changes||[];L.savedAt=ov.checkedAt;}
    if(Date.now()-ov.checkedAt<GH_FRESH_MS){L.state='live';L.checkedAt=ov.checkedAt;L.via='github';}
    emit(changed);return L.via==='github';
  },function(e){L.ghState='failed';L.ghError=String(e&&e.message||e);return false;});
}
L.ghPull=ghPull;

/* ---------- start: lay the last fetched copy over the baked data before first paint ---------- */
var cached=load();
if(cached&&cached.asOf===D.asOf){apply(cached);L.parts=cached.parts||{};L.changes=cached.changes||[];L.savedAt=cached.checkedAt;
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
