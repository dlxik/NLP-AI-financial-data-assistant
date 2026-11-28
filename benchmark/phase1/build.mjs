// TV4-only transcription and arithmetic worksheet. No TV2/system imports.
// Run from any directory: node benchmark/phase1/build.mjs
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.dirname(fileURLToPath(import.meta.url));
const write=(name,data)=>fs.writeFileSync(path.join(root,name),typeof data==='string'?data:JSON.stringify(data,null,2)+'\n');
const reports=[
 ['HPG_Q4','HPG','HPG_2024Q4.pdf','https://file.hoaphat.com.vn/hoaphat-com-vn/2025/02/bao-cao-tai-chinh-hop-nhat-quy-4-2024.pdf','quarterly_unaudited','issuer'],
 ['FPT_Q4','FPT','FPT_2024Q4.pdf','https://file.fpts.com.vn/FileStore2/File/2025/01/24/20250124_-_FPT_-_BCTC_hop_nhat_Quy_4_nam_2024.pdf','quarterly_unaudited','issuer_document_on_broker_mirror'],
 ['VNM_Q4','VNM','VNM_2024_VAS.pdf','https://cdn.24hmoney.vn/upload/file/2025-1/2025-02-25/no-name-1740468308.pdf','quarterly_unaudited','issuer_document_on_mirror'],
 ['VCB_FY','VCB','VCB_2024.pdf','https://www.vietcombank.com.vn/-/media/Project/VCB-Sites/VCB/Nha-Dau-tu/Files/BC-dinh-ky/BC-thuong-nien/2024/EN_VCB-Annual-Report-2024_Full_250426_FN_compressed.pdf','annual_audited_2023_restated','issuer'],
 ['CTG_Q4','CTG','CTG_2024Q4.pdf','https://investor.vietinbank.vn/documents/20126/214683/Consolidated%2BFinancial%2BStatements%2B4Q2024.pdf/ad2420ea-a354-17c8-17e5-81c59671ddb3?t=1763311366556','quarterly_unaudited','issuer']
].map(([id,ticker,file,url,version,hosting])=>({id,ticker,file:'sources/'+file,url,version,hosting,scope:'consolidated',basis:'VAS',retrieved_date:'2026-11-22',publication_date:null,publication_note:'Ngày tải không phải ngày công bố. Chưa kiểm chứng ngày công bố lịch sử.',sha256:fs.existsSync(path.join(root,'sources',file))?createHash('sha256').update(fs.readFileSync(path.join(root,'sources',file))).digest('hex'):null}));
write('sources/manifest.json',reports);
const cells=[];
function cell(id,report,page,printed,row,column,period,value,unit='VND') {
 cells.push({id,report_id:report,pdf_page:page,printed_page:printed,row,column,period,value:String(value),unit,scope:'consolidated',basis:'VAS',verification:'assistant_visual_transcription',human_verified_by:null});return id;
}
const nums={
 HPG:['34490282626689','34383804927755','138855112131887','118953027893654','12020020984285','102836419239379','114647455346716'],
 FPT:['17607817805892','14690412703323','62848794351368','52617900827385','9420078521864','29933011216233','35796626418970'],
 VNM:['15477073125441','15618710944490','61782609528445','60368951511505','9452892989948','35025743765470','36174402829663'],
 VCB:[null,null,null,null,'33853117','165080490','196209168'],
 CTG:[null,null,null,null,'25475009','125871820','149944138']
};
for(const t of ['HPG','FPT','VNM','VCB','CTG']) {
 const r=t==='VCB'?'VCB_FY':t+'_Q4';
 const revPage={HPG:[6,'5'],FPT:[8,'6'],VNM:[8,'7']}[t];
 if(revPage) ['q24','q23','fy24','fy23'].forEach((k,i)=>cell(t+'_'+k,r,...revPage,'10 - Doanh thu thuần', ['Quý IV 2024','Quý IV 2023','Lũy kế cả năm 2024','Lũy kế cả năm 2023'][i],['2024Q4','2023Q4','FY2024','FY2023'][i],nums[t][i]));
 const [p,pr,e,er,u]=({HPG:[6,'5',5,'4','VND'],FPT:[8,'6',7,'5','VND'],VNM:[9,'8',7,'6','VND'],VCB:[67,'133',66,'131','million_VND'],CTG:[7,'5',4,'2','million_VND']})[t];
 cell(t+'_pat',r,p,pr,t==='VCB'?'XIII - NET PROFIT AFTER TAX':t==='CTG'?'XIII - Profit after corporate income tax':'60 - Lợi nhuận sau thuế TNDN','Cả năm 2024','FY2024',nums[t][4],u);
 for(const [i,k,date] of [[5,'eq0','2023-12-31'],[6,'eq1','2024-12-31']]) cell(t+'_'+k,r,e,er,t==='VCB'?'TOTAL OWNERS’ EQUITY':t==='CTG'?'VIII - Capital and reserves':'400 - Vốn chủ sở hữu',k==='eq0'&&['HPG','VNM'].includes(t)?'01/01/2024 (số dư đầu năm)':date+(t==='VCB'&&k==='eq0'?' (restated)':''),date,nums[t][i],u);
}
write('source_cells.json',cells);
const byId=Object.fromEntries(cells.map(c=>[c.id,c]));
const value=id=>Number(byId[id].value);
const calc=(operation,ids)=>{
 const v=ids.map(value);
 if(operation==='lookup') return v[0];
 if(operation==='subtract') return v[0]-v[1];
 if(operation==='yoy_pct') return (v[0]/v[1]-1)*100;
 if(operation==='roe_ttm_pct') return v[0]/((v[1]+v[2])/2)*100;
 throw Error(operation);
};
const questions=[],gold=[];
function add(text,family,tickers,periods,action,rows=[],extra={}) {
 const id='P'+String(questions.length+1).padStart(2,'0');
 questions.push({id,question:text,family_id:family,split:'pilot_public',tickers,periods,question_date:'2026-11-22',snapshot_id:'tv4-evidence-v0.1',input_type:'structured_snapshot',scope:'consolidated',...extra});
 gold.push({question_id:id,expected_action:action,rows,required_warning:null,clarification:null,allowed_assumptions:[],provenance_status:'assistant_prepared_pending_human_review',independent_human_reviewer:null});return gold.at(-1);
}
function row(t,period,metric,op,ids,unit){const formula=({lookup:'a',subtract:'a - b',yoy_pct:'(a / b - 1) * 100',roe_ttm_pct:'a / ((b + c) / 2) * 100'})[op];return {ticker:t,period,metric,unit,value:Number(calc(op,ids).toFixed(unit==='pct'?8:0)),display_value:calc(op,ids).toFixed(unit==='pct'?4:0),operation:op,formula,source_cell_ids:ids,operands:ids.map(id=>({id,value:byId[id].value,unit:byId[id].unit})),absolute_tolerance:unit==='pct'?0.0001:1};}
const rev=t=>row(t,'2024Q4','net_revenue','lookup',[t+'_q24'],'VND');
const yoy=t=>row(t,'2024Q4','net_revenue_yoy','yoy_pct',[t+'_q24',t+'_q23'],'pct');
const roe=t=>row(t,'TTM@2024-12-31','roe_total','roe_ttm_pct',[t+'_pat',t+'_eq0',t+'_eq1'],'pct');
for(const t of ['HPG','FPT','VNM']) add(`Doanh thu thuần hợp nhất riêng quý IV/2024 của ${t} là bao nhiêu VND, theo bản BCTC quý IV trong snapshot?`,'REV_Q',[t],['2024Q4'],'answer',[rev(t)]);
for(const t of ['HPG','FPT','VNM']) add(`Doanh thu thuần hợp nhất quý IV/2024 của ${t} tăng trưởng bao nhiêu phần trăm so với quý IV/2023? Dùng cùng bản BCTC quý IV trong snapshot.`,'REV_YOY',[t],['2024Q4','2023Q4'],'answer',[yoy(t)]);
for(const t of ['HPG','FPT','VNM']) add(`Doanh thu thuần hợp nhất lũy kế cả năm 2024 của ${t} là bao nhiêu VND theo bản BCTC quý IV trong snapshot?`,'REV_YTD',[t],['FY2024'],'answer',[row(t,'FY2024','net_revenue','lookup',[t+'_fy24'],'VND')]);
for(const t of ['HPG','FPT','VNM']) add(`Doanh thu thuần hợp nhất cả năm 2024 của ${t} tăng trưởng bao nhiêu phần trăm so với cả năm 2023, theo bản BCTC quý IV trong snapshot?`,'REV_YOY',[t],['FY2024','FY2023'],'answer',[row(t,'FY2024','net_revenue_yoy','yoy_pct',[t+'_fy24',t+'_fy23'],'pct')]);
for(const t of ['HPG','FPT','VNM','VCB','CTG']) add(`Tính ROE TTM hợp nhất của ${t} tại 31/12/2024 (%): lấy tổng LNST năm 2024 chia bình quân tổng vốn chủ sở hữu đầu và cuối năm, đều gồm lợi ích không kiểm soát, theo đúng bản báo cáo trong snapshot.`,'ROE_TTM',[t],['FY2024','2023-12-31','2024-12-31'],'answer',[roe(t)]);
for(const t of ['VCB','CTG']) {
 const g=add(`Doanh thu thuần hợp nhất của ngân hàng ${t} năm 2024 là bao nhiêu?`,'BANK_REVENUE',[t],['FY2024'],'clarify');
 g.required_warning={code:'BANK_REVENUE_UNDEFINED',ticker:t,period:'FY2024',input:'net_revenue',message:`${t} là ngân hàng; chưa có ánh xạ doanh thu thuần được chốt. Không tự thay bằng thu nhập lãi thuần hoặc tổng thu nhập hoạt động.`};g.clarification='Bạn muốn hỏi thu nhập lãi thuần hay tổng thu nhập hoạt động?';
}
let g=add('Doanh thu thuần hợp nhất HPG cuối năm 2024 là bao nhiêu?','AMBIG_PERIOD',['HPG'],['2024'],'clarify',[],{ambiguity_type:'quarter_vs_year'});
g.clarification='Bạn muốn riêng quý IV/2024 hay lũy kế cả năm 2024?';g.interpretations=[{label:'Q4',resolved_question:'P01',value:rev('HPG').value,unit:'VND'},{label:'FY',resolved_question:'P07',value:value('HPG_fy24'),unit:'VND'}];
g=add('Doanh thu thuần hợp nhất FPT quý IV/2024 tăng bao nhiêu so với cùng kỳ?','AMBIG_MEASURE',['FPT'],['2024Q4','2023Q4'],'clarify',[],{ambiguity_type:'absolute_vs_percentage'});
g.clarification='Bạn muốn mức tăng tính bằng VND hay tỷ lệ tăng trưởng phần trăm?';g.interpretations=[{label:'absolute',value:calc('subtract',['FPT_q24','FPT_q23']),unit:'VND',source_cell_ids:['FPT_q24','FPT_q23']},{label:'percentage',resolved_question:'P05',value:yoy('FPT').value,unit:'pct'}];
g=add('ROE của VCB là bao nhiêu?','AMBIG_PERIOD',['VCB'],[],'clarify',[],{ambiguity_type:'missing_period_and_formula'});g.clarification='Bạn muốn ROE tại kỳ nào, tính theo LNST và vốn chủ sở hữu tổng cộng hay phần thuộc cổ đông ngân hàng?';
add('Doanh thu thuần hợp nhất HPG quý IV/2024 tăng bao nhiêu VND so với quý IV/2023, theo cùng bản BCTC quý IV?','REV_ABSOLUTE',['HPG'],['2024Q4','2023Q4'],'answer',[row('HPG','2024Q4','net_revenue_delta','subtract',['HPG_q24','HPG_q23'],'VND')]);
add('Lập bảng doanh thu thuần hợp nhất riêng quý IV/2024 (VND) của HPG, FPT và VNM theo các bản BCTC quý IV trong snapshot.','MULTI_TABLE',['HPG','FPT','VNM'],['2024Q4'],'answer',['HPG','FPT','VNM'].map(rev));
add('Trong HPG, FPT, VNM, mã nào có doanh thu thuần hợp nhất riêng quý IV/2024 lớn nhất? Dùng snapshot đã chỉ định.','RANK_ABSOLUTE',['HPG','FPT','VNM'],['2024Q4'],'answer',[rev('HPG')]);gold.at(-1).comparison_rows=['HPG','FPT','VNM'].map(rev);
add('Trong HPG, FPT, VNM, mã nào có tỷ lệ tăng trưởng YoY doanh thu thuần hợp nhất riêng quý IV/2024 cao nhất? Dùng snapshot đã chỉ định.','RANK_GROWTH',['HPG','FPT','VNM'],['2024Q4','2023Q4'],'answer',[yoy('FPT')]);gold.at(-1).comparison_rows=['HPG','FPT','VNM'].map(yoy);
add('Chỉ trong HPG, FPT, VNM, lọc mã có YoY doanh thu thuần hợp nhất quý IV/2024 lớn hơn 100%, theo snapshot đã chỉ định.','FILTER_EMPTY',['HPG','FPT','VNM'],['2024Q4','2023Q4'],'empty');gold.at(-1).comparison_rows=['HPG','FPT','VNM'].map(yoy);gold.at(-1).reason='Đủ số liệu cả 3 mã; không mã nào thỏa điều kiện > 100%.';
g=add('Tính ROE TTM hợp nhất VNM tại 31/12/2024 bằng tổng LNST năm chia bình quân tổng vốn chủ đầu/cuối năm, chỉ dùng dữ liệu được cấp.','MISSING_EQUITY',['VNM'],['FY2024','2023-12-31','2024-12-31'],'missing_data',[],{fixture_id:'withhold_vnm_opening_equity',data_variant:'real_data_withheld',excluded_cell_ids:['VNM_eq0']});
g.required_warning={code:'MISSING_OPENING_EQUITY',ticker:'VNM',period:'2023-12-31',input:'total_equity',message:'Thiếu vốn chủ sở hữu đầu kỳ VNM tại 31/12/2023 trong đầu vào được cấp; không thay bằng vốn chủ cuối kỳ.'};g.reason='Ca kiểm thử chủ động che ô số thật, không khẳng định doanh nghiệp thiếu báo cáo.';
add('Lập bảng ROE TTM VCB và CTG tại 31/12/2024 (%), dùng tổng LNST cả năm chia bình quân tổng vốn chủ đầu/cuối năm (đều gồm lợi ích không kiểm soát), theo phiên bản từng mã trong snapshot.','MULTI_ROE',['VCB','CTG'],['FY2024','2023-12-31','2024-12-31'],'answer',['VCB','CTG'].map(roe));
add('Tính doanh thu thuần hợp nhất 9 tháng đầu năm 2024 của HPG bằng doanh thu cả năm trừ riêng quý IV, chỉ dùng cùng bản BCTC quý IV trong snapshot.','REV_YTD',['HPG'],['9M2024'],'answer',[row('HPG','9M2024','net_revenue','subtract',['HPG_fy24','HPG_q24'],'VND')]);
write('pilot_questions.json',questions);write('pilot_gold.json',gold);
const pairs=[['CP01','P01','P07','quarter_vs_ytd'],['CP02','P02','P08','quarter_vs_ytd'],['CP03','P03','P09','quarter_vs_ytd'],['CP04','P04','P23','percentage_vs_absolute'],['CP05','P25','P26','rank_absolute_vs_growth'],['CP06','P15','P28','available_vs_withheld_input']].map(([id,left,right,dimension])=>({id,left,right,dimension,split_group:id,evidence_status:'computed_from_transcribed_real_cells',human_verified_by:null}));
write('contrast_pairs.json',pairs);
if(!fs.existsSync(path.join(root,'review_register.json'))) write('review_register.json',questions.map(q=>({question_id:q.id,hien_checked_source:false,hien_recalculated:false,tv5_sampled:false,tv5_recomputed_value:null,tv5_result:null,reviewer:null,reviewed_at:null,notes:''})));
write('input_fixtures.json',[
 {id:'tv4-evidence-v0.1',allowed_cell_ids:cells.map(c=>c.id),note:'Đầu vào pilot; không phải snapshot ETL 5 năm của TV1.'},
 {id:'withhold_vnm_opening_equity',allowed_cell_ids:cells.filter(c=>c.id!=='VNM_eq0').map(c=>c.id),excluded_cell_ids:['VNM_eq0'],note:'TV3 chỉ cấp các ô trong allowlist; không cấp PDF, Gold, Internet hoặc bộ snapshot đầy đủ trong ca P28.'}
]);
const related=Array.from({length:30},(_,i)=>({sample_id:'VF'+String(i+1).padStart(2,'0'),work:'ViFinQA',source_question_id:i+1,source_url:'https://huggingface.co/datasets/HuuDong03uet/ViFinQA',input_type:'question_plus_retrieved_report_corpus',period_count:1,company_count:1,operation:'lookup',unit_normalization:'check_against_source_report',evidence:'public_question_text_only',label_status:'assistant_label_pending_review'}));
write('related_work_samples.json',related);
const lines=['# 30 câu pilot và Gold nháp của TV4','','Sinh từ `build.mjs`; số gốc chép từ ảnh BCTC, không dùng code TV2. Tất cả chờ Hiền tính lại và TV5 kiểm tra.','','Quy ước: snapshot báo cáo cố định; hợp nhất/VAS; ROE tổng LNST / bình quân tổng vốn chủ (bao gồm NCI); TTM kết thúc 31/12/2024 = cả năm 2024. Đơn vị pct là phần trăm, không phải tỷ lệ 0–1.',''];
for(let i=0;i<questions.length;i++){const q=questions[i],g=gold[i];lines.push(`## ${q.id} — ${q.family_id}`, '', q.question,'',`**Hành động:** ${g.expected_action}.`,'');for(const r of g.rows)lines.push(`- ${r.ticker}, ${r.period}: **${r.display_value} ${r.unit}**; công thức \`${r.formula}\`; a/b/c theo thứ tự: ${r.operands.map(o=>`${o.value} (${o.id})`).join('; ')}.`);if(g.required_warning)lines.push('',g.required_warning.message);if(g.clarification)lines.push('',`Hỏi lại: ${g.clarification}`);if(g.reason)lines.push('',g.reason);if(g.interpretations)lines.push('',...g.interpretations.map(x=>`- Cách hiểu ${x.label}: ${x.value} ${x.unit}.`));lines.push('');}
write('PILOT_VA_GOLD.md',lines.join('\n'));
console.log(`Wrote ${questions.length} questions, ${gold.length} gold records, ${cells.length} source cells, ${pairs.length} contrast pairs.`);
