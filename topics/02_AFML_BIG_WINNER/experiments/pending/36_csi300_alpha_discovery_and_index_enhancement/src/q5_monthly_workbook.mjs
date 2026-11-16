import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const ep='/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/36_csi300_alpha_discovery_and_index_enhancement';
const out=ep+'/outputs/sensitivity/q5_rebalance_20261116/monthly_records';
const rows=JSON.parse(await fs.readFile(out+'/workbook_data.json','utf8'));
const wb=Workbook.create();
const summary=wb.worksheets.add('逐月净收益');
const detail=wb.worksheets.add('逐月明细');
const labels={'1w':'每周','2w':'双周','1m':'每月'};
const statuses={FULL:'完整月',PARTIAL:'部分月',BLOCKED:'中止后缺失'};
const date=x=>x?new Date(x+'T00:00:00Z'):null;
const hdr=['月份','模型','调仓周期','收益基准日','首收益日','收益终点','交易日数','月份状态','扣费收益','基准收益','超额(pp)','相对收益','期初净值','期末净值','期初指数','期末指数','备注'];
detail.getRange('A2').values=[['Q5 等权逐月明细']];
detail.getRange('A3').values=[['买入10bps／卖出20bps；已确认停牌估值代理。净收益按期末／期初净值计算。']];
detail.getRange('A4').values=[['基准：沪深300全收益 H00300；超额为收益差（百分点）。部分月份以所列起止日期为准。']];
detail.getRange('A5').values=[['来源：q5_rebalance_20261116 封存日净值与 H00300 历史缓存。中止后缺失不填零。']];
detail.getRange('A8:Q8').values=[hdr];
const matrix=rows.map(r=>[date(r.month+'-01'),r.model,labels[r.frequency],date(r.base_date),date(r.start),date(r.end),r.sessions,statuses[r.status],null,null,null,null,r.nav_start,r.nav_end,r.benchmark_start,r.benchmark_end,r.note]);
detail.getRange(`A9:Q${rows.length+8}`).values=matrix;
const formula=rows.map((r,i)=>{const n=i+9;return r.status==='BLOCKED'?['="n.a."','="n.a."','="n.a."','="n.a."']:[`=N${n}/M${n}-1`,`=P${n}/O${n}-1`,`=(I${n}-J${n})*100`,`=(1+I${n})/(1+J${n})-1`];});
detail.getRange(`I9:L${rows.length+8}`).formulas=formula;
detail.tables.add(`A8:Q${rows.length+8}`,true,'MonthlyDetail');
detail.getRange(`A9:A${rows.length+8}`).setNumberFormat('yyyy-mm');
detail.getRange(`D9:F${rows.length+8}`).setNumberFormat('yyyy-mm-dd');
detail.getRange(`I9:J${rows.length+8}`).setNumberFormat('0.00%;[Red]-0.00%');
detail.getRange(`K9:K${rows.length+8}`).setNumberFormat('0.00;[Red]-0.00');
detail.getRange(`L9:L${rows.length+8}`).setNumberFormat('0.00%;[Red]-0.00%');
detail.getRange(`M9:P${rows.length+8}`).setNumberFormat('0.000000');
const models=['E1','E2','E3'],freqs=['1w','2w','1m'];
const keys=models.flatMap(m=>freqs.map(f=>[m,f]));
const months=[...new Set(rows.map(r=>r.month))];
summary.getRange('A2').values=[['E1、E2、E3 逐月扣费收益']];
summary.getRange('A3').values=[['2021-01 至 2026-10；Q5 等权，买入10bps／卖出20bps，停牌估值代理。']];
summary.getRange('A4').values=[['部分月：2021-01；E1周／双周2025-03仅到3日；2026-10各账户到16日或21日。']];
summary.getRange('A5').values=[['n.a.表示账户中止后缺失，不是0。明细表可筛选并查看每条记录的基准、日期与超额。']];
summary.getRange('A8:J8').values=[['月份',...keys.map(([m,f])=>m+' '+labels[f])]];
summary.getRange(`A9:A${months.length+8}`).values=months.map(m=>[date(m+'-01')]);
summary.getRange(`B9:J${months.length+8}`).formulas=months.map(m=>keys.map(([model,f])=>{
 const i=rows.findIndex(r=>r.month===m&&r.model===model&&r.frequency===f);return `='逐月明细'!I${i+9}`;
}));
summary.getRange(`A9:A${months.length+8}`).setNumberFormat('yyyy-mm');
summary.getRange(`B9:J${months.length+8}`).setNumberFormat('0.00%;[Red]-0.00%');
summary.tables.add(`A8:J${months.length+8}`,true,'MonthlySummary');
for(const s of [summary,detail]){
 const used=s.getUsedRange(); used.format.font={name:'Arial',size:11};used.format.rowHeight=23;used.format.columnWidth=14;
 s.showGridLines=false;s.freezePanes.freezeRows(8);
 s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#173B59'};
 s.getRange(s===summary?'A8:J8':'A8:Q8').format={fill:'#24435B',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:28};
}
detail.getRange('D:F').format.columnWidth=15;
detail.getRange('H:H').format.columnWidth=17;
detail.getRange('Q:Q').format.columnWidth=27;
detail.getRange('M:P').format.columnWidth=16;
wb.recalculate();
const actual=detail.getRange(`I9:L${rows.length+8}`).values;
rows.forEach((r,i)=>{if(r.status==='BLOCKED'){if(actual[i][0]!=='n.a.')throw Error('missing');}else{
 const expected=[r.net_return,r.benchmark_return,r.excess_difference*100,r.relative_return];
 expected.forEach((x,j)=>{if(Math.abs(x-actual[i][j])>1e-8)throw Error(`reconciliation ${i} ${j}`);});
}});
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
for(const [s,range,name] of [[summary,'A1:J18','summary'],[detail,'A8:L18','detail']]){
 const img=await wb.render({sheetName:s.name,range,scale:1,format:'png'});
 await fs.writeFile(out+'/'+name+'_preview.png',new Uint8Array(await img.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(out+'/E1_E2_E3_monthly_returns.xlsx');
await fs.writeFile(out+'/workbook_validation.json',JSON.stringify({status:'PASS',rows:rows.length,formula_reconciliation:'PASS',sheets:2},null,2));
console.log('PASS workbook exported; 630 rows reconciled');
