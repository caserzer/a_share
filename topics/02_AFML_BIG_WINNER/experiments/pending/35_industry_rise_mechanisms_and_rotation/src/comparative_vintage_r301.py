from common import *
import pandas as pd
from decimal import Decimal
# Manually read prior-year comparative values, ordered profit/operating cash/capital payment.
VALUES={
'002406.SZ':['54,696,522.24','-17,990,769.99','8,603,816.48'],
'002832.SZ':['414,228,282.65','336,002,677.08','294,905,676.60'],
'002948.SZ':['3,064,683','(56,616)','(96,006)'],
'003021.SZ':['113,271,162.92','46,762,981.56','93,148,661.74'],
'300411.SZ':['13,934,333.52','33,824,071.29','15,610,700.36'],
'300693.SZ':['158,062,743.75','121,376,829.69','52,312,379.03'],
'600236.SH':['1,187,733,386.44','2,907,217,929.40','1,735,965,943.31'],
'600955.SH':['-167,538,817.24','604,372,968.48','467,501,049.68'],
'605123.SH':['175,388,424.03','69,049,002.82','281,095,001.41'],
'920407.BJ':['11,542,337.84','866,342.56','1,410,696.76']}
FIELDS={'net_profit':('income_vip','n_income_attr_p'),'net_cash_operate':('cashflow_vip','n_cashflow_act'),'capex':('cashflow_vip','c_pay_acq_const_fiolta')}
def run():
 out=ROOT/'outputs/r301';base=ROOT/'data/cnequity_fundamental_review_20261114';review=ROOT/'outputs/cnequity_fundamental_review_20261114';cells={(x['symbol'],x['item_code']):x for x in json.loads((review/'reviewed_financial_cells.json').read_text())};docs={x['symbol']:x for x in json.loads((review/'original_receipts.json').read_text())};archive=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');rows=[];lineage=[];inputs={}
 for symbol,values in VALUES.items():
  pdf=base/symbol/'2026H1.pdf';assert sha(pdf)==docs[symbol]['pdf_sha256'];pagespath=base/symbol/'pages.json';pages=json.loads(pagespath.read_text());inputs[str(pdf.relative_to(ROOT))]=sha(pdf);inputs[str(pagespath.relative_to(ROOT))]=sha(pagespath)
  for item,number in zip(FIELDS,values):
   c=cells[(symbol,item)];page=pages[c['pdf_page']-1]['text'];assert number in page and c['reported_number'] in page
   unit=1000 if symbol=='002948.SZ' else 1;raw=Decimal(number.replace(',','').replace('(','-').replace(')',''));val=abs(raw)*unit if item=='capex' else raw*unit;api,field=FIELDS[item];g=archive[archive.ts_code.eq(symbol)&archive.api.eq(api)&archive.end_date.eq(pd.Timestamp('2025-06-30'))];observed=sorted({Decimal(str(v)) for v in g[field].dropna()});delta=[v-val for v in observed];tolerance=Decimal('500') if unit==1000 else Decimal('.005');status='missing' if not observed else 'compatible_at_report_precision' if all(abs(v)<=tolerance for v in delta) else 'difference_or_archive_conflict'
   start=max(0,page.index(number)-170);end=min(len(page),page.index(number)+150)
   rows.append(dict(symbol=symbol,item_code=item,pdf_page=c['pdf_page'],reported_number=number,unit_multiplier=unit,raw_signed_value=str(raw),normalized_value=str(val),sign_rule='absolute cash outflow amount' if item=='capex' else 'reported signed amount',comparative_period='2025H1',document_period='2026H1',announce_date=c['announce_date'],observed_at=docs[symbol]['fetched_at'],pdf_sha256=sha(pdf),page_context=page[start:end],full_page=page,archive_field=field,archive_values=[str(v) for v in observed],archive_differences=[str(v) for v in delta],archive_rows=len(g),status=status,strict_pit=False))
   for _,record in g.iterrows():lineage.append(dict(symbol=symbol,item_code=item,archive_record={k:str(record[k]) for k in ['end_date','ann_date','api',field,'source_page_sha256','archived_available_at'] if k in record}))
 js(out/'comparative_cells.json',rows);js(out/'archive_lineage.json',lineage)
 summary=dict(status='PASS',issuers=len(VALUES),cells=len(rows),statuses=pd.Series([x['status'] for x in rows]).value_counts().to_dict(),archive_records=len(lineage),changed_model_values=0,strict_pit=False,adoption=False);js(out/'summary.json',summary)
 for p in ['data/financial_archive_all_market.parquet','outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json','outputs/cnequity_fundamental_review_20261114/original_receipts.json','src/comparative_vintage_r301.py','protocols/r301.json']:inputs[p]=sha(ROOT/p)
 js(out/'receipt.json',dict(inputs=inputs,outputs={p:sha(out/p) for p in ['comparative_cells.json','archive_lineage.json','summary.json']}));print(summary)
if __name__=='__main__':run()
