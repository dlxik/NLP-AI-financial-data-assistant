// Second arithmetic implementation: exact BigInt fractions, no build.mjs/TV2 imports.
// Constants were reread visually from the PDF page images on 2026-11-23.
// Rerunning this script checks against that transcription; it does NOT reread images.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const read=n=>JSON.parse(fs.readFileSync(path.join(root,n),'utf8'));
const hash=n=>createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex');
const observed={
 HPG_q24:'34490282626689',HPG_q23:'34383804927755',HPG_fy24:'138855112131887',HPG_fy23:'118953027893654',HPG_pat:'12020020984285',HPG_eq0:'102836419239379',HPG_eq1:'114647455346716',
 FPT_q24:'17607817805892',FPT_q23:'14690412703323',FPT_fy24:'62848794351368',FPT_fy23:'52617900827385',FPT_pat:'9420078521864',FPT_eq0:'29933011216233',FPT_eq1:'35796626418970',
 VNM_q24:'15477073125441',VNM_q23:'15618710944490',VNM_fy24:'61782609528445',VNM_fy23:'60368951511505',VNM_pat:'9452892989948',VNM_eq0:'35025743765470',VNM_eq1:'36174402829663',
 VCB_pat:'33853117',VCB_eq0:'165080490',VCB_eq1:'196209168',CTG_pat:'25475009',CTG_eq0:'125871820',CTG_eq1:'149944138'
};
const pages={HPG_q24:6,HPG_q23:6,HPG_fy24:6,HPG_fy23:6,HPG_pat:6,HPG_eq0:5,HPG_eq1:5,FPT_q24:8,FPT_q23:8,FPT_fy24:8,FPT_fy23:8,FPT_pat:8,FPT_eq0:7,FPT_eq1:7,VNM_q24:8,VNM_q23:8,VNM_fy24:8,VNM_fy23:8,VNM_pat:9,VNM_eq0:7,VNM_eq1:7,VCB_pat:67,VCB_eq0:66,VCB_eq1:66,CTG_pat:7,CTG_eq0:4,CTG_eq1:4};
const cells=read('source_cells.json'),gold=read('pilot_gold.json'),qs=read('pilot_questions.json'),manifest=read('sources/manifest.json');
assert.equal(cells.length,Object.keys(observed).length);
const cellChecks=cells.map(c=>{assert.equal(c.value,observed[c.id],c.id);assert.equal(c.pdf_page,pages[c.id]);const ticker=c.id.split('_')[0];assert.equal(c.unit,['VCB','CTG'].includes(ticker)?'million_VND':'VND');assert.equal(c.report_id,ticker==='VCB'?'VCB_FY':ticker+'_Q4');return {cell_id:c.id,value:c.value,pdf_page:c.pdf_page,result:'pass'};});
for(const m of manifest)assert.equal(hash(m.file),m.sha256);
function decimal(n,d=1n,places=8){assert(d>0n);const neg=n<0n;n=neg?-n:n;const scale=10n**BigInt(places);const rounded=(n*scale*2n+d)/(2n*d);const s=rounded.toString().padStart(places+1,'0');return (neg?'-':'')+s.slice(0,-places)+'.'+s.slice(-places);}
const val=id=>BigInt(observed[id]);
const direct=(t,k,period)=>({ticker:t,period,metric:'net_revenue',unit:'VND',ids:[t+'_'+k],n:val(t+'_'+k),d:1n});
const growth=(t,fy=false)=>{const a=t+(fy?'_fy24':'_q24'),b=t+(fy?'_fy23':'_q23');return {ticker:t,period:fy?'FY2024':'2024Q4',metric:'net_revenue_yoy',unit:'pct',ids:[a,b],n:100n*(val(a)-val(b)),d:val(b)};};
const roe=t=>({ticker:t,period:'TTM@2024-12-31',metric:'roe_total',unit:'pct',ids:[t+'_pat',t+'_eq0',t+'_eq1'],n:200n*val(t+'_pat'),d:val(t+'_eq0')+val(t+'_eq1')});
const expected=[];
for(const t of ['HPG','FPT','VNM'])expected.push([direct(t,'q24','2024Q4')]);
for(const t of ['HPG','FPT','VNM'])expected.push([growth(t)]);
for(const t of ['HPG','FPT','VNM'])expected.push([direct(t,'fy24','FY2024')]);
for(const t of ['HPG','FPT','VNM'])expected.push([growth(t,true)]);
for(const t of ['HPG','FPT','VNM','VCB','CTG'])expected.push([roe(t)]);
expected.push([],[],[],[],[]);
expected.push([{ticker:'HPG',period:'2024Q4',metric:'net_revenue_delta',unit:'VND',ids:['HPG_q24','HPG_q23'],n:val('HPG_q24')-val('HPG_q23'),d:1n}]);
expected.push(['HPG','FPT','VNM'].map(t=>direct(t,'q24','2024Q4')));
expected.push([direct('HPG','q24','2024Q4')],[growth('FPT')],[],[],['VCB','CTG'].map(roe));
expected.push([{ticker:'HPG',period:'9M2024',metric:'net_revenue',unit:'VND',ids:['HPG_fy24','HPG_q24'],n:val('HPG_fy24')-val('HPG_q24'),d:1n}]);
assert.equal(expected.length,30);
const gm=new Map(gold.map(g=>[g.question_id,g]));
const results=expected.map((rows,i)=>{
 const id='P'+String(i+1).padStart(2,'0'),g=gm.get(id);assert(g);
 const action=i>=17&&i<=21?'clarify':i===26?'empty':i===27?'missing_data':'answer';assert.equal(g.expected_action,action,id);assert.equal(g.rows.length,rows.length,id);
 const checked=rows.map(e=>{const r=g.rows.find(r=>r.ticker===e.ticker);assert(r,id);for(const k of ['period','metric','unit'])assert.equal(r[k],e[k],id+':'+k);assert.deepEqual(r.source_cell_ids,e.ids,id+':inputs');const exact=decimal(e.n,e.d);assert.equal(Number(r.value).toFixed(8),exact,id+':value');assert.equal(r.display_value,e.unit==='pct'?decimal(e.n,e.d,4):e.n.toString(),id+':display');return {ticker:e.ticker,period:e.period,recomputed:exact,unit:e.unit,result:'pass'};});
 return {question_id:id,expected_action:action,rows:checked,result:'pass_under_documented_policy'};
});
assert(val('HPG_q24')>val('FPT_q24')&&val('HPG_q24')>val('VNM_q24'));
const f=growth('FPT');for(const t of ['HPG','VNM']){const x=growth(t);assert(f.n*x.d>x.n*f.d);}
for(const t of ['HPG','FPT','VNM']){const x=growth(t);assert(x.n<100n*x.d);}
assert.equal(gm.get('P20').interpretations[0].value.toString(),observed.HPG_q24);
assert.equal(gm.get('P20').interpretations[1].value.toString(),observed.HPG_fy24);
assert.equal(gm.get('P21').interpretations[0].value.toString(),(val('FPT_q24')-val('FPT_q23')).toString());
assert.equal(gm.get('P21').interpretations[1].value.toFixed(8),decimal(f.n,f.d));
const fixtures=read('input_fixtures.json');assert(!fixtures.find(f=>f.id==='withhold_vnm_opening_equity').allowed_cell_ids.includes('VNM_eq0'));
assert.equal(qs.find(q=>q.id==='P28').fixture_id,'withhold_vnm_opening_equity');
const artifacts=['source_cells.json','pilot_questions.json','pilot_gold.json','contrast_pairs.json','input_fixtures.json','sources/manifest.json'];
const output={visual_review_date:'2026-11-23',reviewer:'Codex assistant (same conversation; not independent human TV5)',calculation:'BigInt exact rational; half-up to 8 decimals, display to 4',artifact_sha256:Object.fromEntries(artifacts.map(n=>[n,hash(n)])),pdf_sha256:Object.fromEntries(manifest.map(m=>[m.id,hash(m.file)])),cell_checks:cellChecks,question_checks:results,numeric_corrections:0,full_phase_gate_approved:false};
fs.writeFileSync(path.join(root,'assistant_audit.json'),JSON.stringify(output,null,2)+'\n');
console.log(`PASS: ${cellChecks.length} reread source values; ${results.length} question/action checks; ${results.reduce((n,r)=>n+r.rows.length,0)} exact numeric results; 5 PDF hashes. No numeric corrections.`);
