from common import *
from decimal import Decimal as D
import fitz,re
PAGES={'002406.SZ':(108,109),'002832.SZ':(119,120),'002948.SZ':(167,167),'003021.SZ':(142,143),'300411.SZ':(103,104),'300693.SZ':(166,167),'600236.SH':(167,167),'600955.SH':(113,114),'605123.SH':(124,125),'920407.BJ':(108,108)}
# Full-table manual readings: consolidated profit, inventory, operating receivables, operating payables; current then comparative.
TARGETS={
'002406.SZ':[['105,019,921.21','56,940,647.71'],['-5,964,409.32','-16,449,316.43'],['-98,941,234.29','-97,574,197.83'],['51,810,746.37','-19,136,945.52']],
'002832.SZ':[['490,472,140.67','414,176,376.37'],['-160,411,057.27','-93,905,879.15'],['-8,278,899.19','4,578,547.01'],['-156,164,798.68','-226,791,780.68']],
'002948.SZ':[['3,707,579','3,152,102'],None,['(30,023,512)','(47,217,392)'],['45,734,950','45,010,910']],
'003021.SZ':[['74,645,686.46','113,271,162.92'],['-38,570,331.50','-30,848,190.60'],['16,842,675.73','-36,042,978.68'],['20,527,107.82','-21,025,622.34']],
'300411.SZ':[['2,827,230.33','12,673,716.76'],['12,562,777.71','-3,829,471.24'],['64,943,154.30','48,986,851.68'],['-71,200,557.18','-29,708,593.47']],
'300693.SZ':[['227,445,626.18','154,926,333.19'],['-119,890,132.66','-140,074,029.48'],['-21,487,176.48','-5,144,278.77'],['4,023,128.18','54,619,261.43']],
'600236.SH':[['2,028,008,721.53','1,364,564,327.96'],['44,085,793.57','203,469,227.65'],['-337,967,519.88','-284,618,279.10'],['605,956,090.87','284,888,119.04']],
'600955.SH':[['-22,400,266.41','-167,538,817.24'],['-94,997,045.25','130,092,904.63'],['84,780,587.75','122,184,349.36'],['366,699,376.61','26,956,332.79']],
'605123.SH':[['198,890,984.51','175,388,424.03'],['-146,929,873.34','-116,240,258.01'],['-397,023,953.37','-299,389,278.69'],['267,799,449.73','225,231,344.22']],
'920407.BJ':[['11,632,657.24','11,432,593.42'],['-13,961,767.93','-14,604,650.10'],['-9,568,039.61','-16,878,977.19'],['8,750,494.53','16,240,912.17']]}
def num(s):return D(s.replace(',','').replace('(','-').replace(')',''))
def spans(page):return [(s['text'].strip(),list(s['bbox'])) for b in page.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
def run():
 out=ROOT/'outputs/r302';base=ROOT/'data/cnequity_fundamental_review_20261114';rev=ROOT/'outputs/cnequity_fundamental_review_20261114'
 facts={(x['symbol'],x['item_code']):x for x in json.loads((rev/'reviewed_financial_cells.json').read_text())};old={(x['symbol'],x['item_code']):x for x in json.loads((ROOT/'outputs/r301/comparative_cells.json').read_text())};docs={x['symbol']:x for x in json.loads((rev/'original_receipts.json').read_text())}
 rows=[];bridges=[];sources={};page_evidence=[]
 for symbol,(first,last) in PAGES.items():
  pdf=base/symbol/'2026H1.pdf';assert sha(pdf)==docs[symbol]['pdf_sha256'];sources[str(pdf.relative_to(ROOT))]=sha(pdf);doc=fitz.open(pdf);raws=[(p,t,b) for p in range(first,last+1) for t,b in spans(doc[p-1])];target=TARGETS[symbol];unit=1000 if symbol=='002948.SZ' else 1
  anchors=[next((p,t,b) for p,t,b in raws if t==v) for v in target[0]];edges=[a[2][2] for a in anchors];start=(anchors[0][0],anchors[0][2][1]-1)
  totals=[facts[symbol,'net_cash_operate']['reported_number'],old[symbol,'net_cash_operate']['reported_number']]
  endanchors=[next((p,t,b) for p,t,b in raws if t==v and abs(b[2]-edges[i])<10) for i,v in enumerate(totals)];end=(endanchors[0][0],endanchors[0][2][1]-2)
  amounts=[[],[]]
  for p,t,b in raws:
   if not(start<=(p,b[1])<=end):continue
   if not re.fullmatch(r'\(?-?\d[\d,]*(?:\.\d+)?\)?',t):continue
   if unit==1 and '.' not in t:continue
   col=min(range(2),key=lambda c:abs(b[2]-edges[c]))
   if abs(b[2]-edges[col])>10:continue
   # Excludes page numbers and headers by numeric column alignment and table bounds.
   value=num(t)*unit;kind='other_disclosed_adjustment'
   for name,pair in zip(['consolidated_profit','inventory','operating_receivables','operating_payables'],target):
    if pair and t==pair[col]:kind=name
   rec=dict(symbol=symbol,period=['2026H1','2025H1'][col],page=p,bbox=b,raw=t,value=str(value),kind=kind,unit_multiplier=unit)
   rows.append(rec);amounts[col].append(rec)
  vals=[]
  for i,aa in enumerate(amounts):
   for j,pair in enumerate(target):
    if pair:assert sum(x['raw']==pair[i] for x in aa)==1,(symbol,pair,i)
   profit=next(D(x['value']) for x in aa if x['kind']=='consolidated_profit');wc=sum((D(x['value']) for x in aa if x['kind'] in ['inventory','operating_receivables','operating_payables']),D(0));other=sum((D(x['value']) for x in aa if x['kind']=='other_disclosed_adjustment'),D(0));total=num(totals[i])*unit;res=total-profit-wc-other
   vals.append(dict(period=['2026H1','2025H1'][i],profit=str(profit),operating_balances=str(wc),other_disclosed_adjustments=str(other),cashflow=str(total),unexplained_residual=str(res),printed_cells=len(aa)))
  delta={k:str(D(vals[0][k])-D(vals[1][k])) for k in ['profit','operating_balances','other_disclosed_adjustments','cashflow','unexplained_residual']}
  bridges.append(dict(symbol=symbol,name=docs[symbol]['name'],financial=symbol=='002948.SZ',unit_multiplier=unit,values=vals,delta=delta,source_pages=[first,last],pdf_sha256=sha(pdf),announce_date=facts[symbol,'net_cash_operate']['announce_date'],observed_at=docs[symbol]['fetched_at'],blank_policy='Unprinted cells retained in full page evidence; sum of disclosed numbers only; no individual blank imputed',strict_pit=False))
  for p in range(first,last+1):page_evidence.append(dict(symbol=symbol,page=p,text=doc[p-1].get_text(),spans=spans(doc[p-1])))
 js(out/'disclosed_cells.json',rows);js(out/'bridges.json',bridges);js(out/'page_evidence.json',page_evidence)
 for p in ['protocols/r302.json','src/cashflow_bridge_r302.py','outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json','outputs/cnequity_fundamental_review_20261114/original_receipts.json','outputs/r301/comparative_cells.json']:sources[p]=sha(ROOT/p)
 js(out/'receipt.json',dict(inputs=sources,outputs={n:sha(out/n) for n in ['disclosed_cells.json','bridges.json','page_evidence.json']}))
 print(json.dumps([{'symbol':b['symbol'],'residuals':[v['unexplained_residual'] for v in b['values']],'delta':b['delta']} for b in bridges],ensure_ascii=False,indent=2))
if __name__=='__main__':run()
