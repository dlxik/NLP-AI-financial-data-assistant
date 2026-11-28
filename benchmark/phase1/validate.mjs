import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=path.dirname(fileURLToPath(import.meta.url));
const read=n=>JSON.parse(fs.readFileSync(path.join(root,n),'utf8'));
const q=read('pilot_questions.json'),g=read('pilot_gold.json'),c=read('source_cells.json'),p=read('contrast_pairs.json'),m=read('sources/manifest.json'),reviews=read('review_register.json'),fixtures=read('input_fixtures.json');
const cm=new Map(c.map(x=>[x.id,x])),gm=new Map(g.map(x=>[x.question_id,x]));
assert.equal(q.length,30);assert.equal(g.length,30);assert.equal(new Set(q.map(x=>x.id)).size,30);assert.equal(gm.size,30);assert.equal(cm.size,c.length);
assert.deepEqual([...new Set(q.flatMap(x=>x.tickers))].sort(),['CTG','FPT','HPG','VCB','VNM']);
let checkedRows=0;
for(const x of q){
 const gold=gm.get(x.id);assert(gold,`Missing Gold ${x.id}`);assert.equal(x.split,'pilot_public');
 assert(['answer','clarify','missing_data','empty'].includes(gold.expected_action));
 if(gold.expected_action==='answer')assert(gold.rows.length>0);
 else assert.equal(gold.rows.length,0);
 if(gold.expected_action==='clarify')assert(gold.clarification);
 if(x.family_id==='BANK_REVENUE'||gold.expected_action==='missing_data')assert(gold.required_warning?.ticker && gold.required_warning?.period && gold.required_warning?.input);
 const f=fixtures.find(f=>f.id===(x.fixture_id??x.snapshot_id));assert(f);
 for(const r of [...gold.rows,...(gold.comparison_rows??[])]){
  assert(x.tickers.includes(r.ticker));const inputs=r.source_cell_ids.map(id=>{assert(f.allowed_cell_ids.includes(id));assert(cm.has(id));return cm.get(id);});
  assert(inputs.every(i=>i.report_id===inputs[0].report_id&&i.unit===inputs[0].unit),'Mixed version/unit');
  const [a,b,d]=inputs.map(i=>Number(i.value));
  const result={lookup:()=>a,subtract:()=>a-b,yoy_pct:()=>100*(a-b)/b,roe_ttm_pct:()=>200*a/(b+d)}[r.operation]();
  assert(Number.isFinite(result));assert(Math.abs(result-r.value)<=r.absolute_tolerance,`${x.id} arithmetic`);
  assert.equal(r.operands.length,inputs.length);r.operands.forEach((v,i)=>assert.equal(v.value,inputs[i].value));checkedRows++;
 }
}
for(const pair of p){const a=gm.get(pair.left),b=gm.get(pair.right);assert(a&&b);assert.notDeepEqual({action:a.expected_action,rows:a.rows.map(r=>[r.ticker,r.value,r.unit])},{action:b.expected_action,rows:b.rows.map(r=>[r.ticker,r.value,r.unit])},`Non-discriminating pair ${pair.id}`);}
for(const id of ['P25','P26']){const z=gm.get(id);const winner=z.comparison_rows.reduce((a,b)=>a.value>b.value?a:b);assert.equal(z.rows[0].ticker,winner.ticker);}
assert(gm.get('P27').comparison_rows.every(r=>r.value<=100));
assert(!fixtures.find(f=>f.id==='withhold_vnm_opening_equity').allowed_cell_ids.includes('VNM_eq0'));
let localPdfs=0;
for(const r of m){assert(/^[a-f0-9]{64}$/.test(r.sha256),'Missing SHA256');const f=path.join(root,r.file);if(fs.existsSync(f)){assert.equal(createHash('sha256').update(fs.readFileSync(f)).digest('hex'),r.sha256);localPdfs++;}else if(process.argv.includes('--require-pdfs'))throw Error(`Missing ${r.file}`);}
for(const cell of c){assert(m.some(r=>r.id===cell.report_id));assert(cell.pdf_page>0&&cell.row&&cell.column);assert(/^\d+$/.test(cell.value));}
assert.equal(read('related_work_samples.json').length,30);
assert.equal(reviews.length,30);
console.log(`PASS: 30 questions; ${c.length} cells; ${checkedRows} result/comparison rows; ${p.length} discriminating pairs; ${localPdfs}/5 local PDF hashes.`);
console.log('This checks TV4 package consistency only, not TV5 scoring or independent human verification.');
if(process.argv.includes('--gate')){
 const pending=reviews.filter(r=>!r.hien_checked_source||!r.hien_recalculated||!r.reviewer||!r.reviewed_at);
 const audited=reviews.filter(r=>r.tv5_sampled);
 if(pending.length||!audited.length||audited.some(r=>r.tv5_result!=='pass')){console.error(`GATE NOT APPROVED: ${pending.length} pending Hiền reviews; ${audited.length} TV5 sampled records. See HANDOFF.md for other team gate conditions.`);process.exitCode=2;}
 else console.log('TV4 human review fields are complete. Full team gate still requires TV5 scorer attacks and team decisions.');
}
