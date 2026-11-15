import sys,json,re
sys.path.insert(0,'topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation/src')
from cnequity_fundamental_review import *
def norm(t):return re.sub(r'\s+','',t).replace('（','(').replace('）',')').replace(',','').replace('－','-').replace('—','-').replace('–','-')
r=[]
for x in json.loads((DATA/'RPT_F10_EH_HOLDERS.json').read_text()):
 sym=x['SECUCODE'];pages=json.loads((DATA/sym/'pages.json').read_text());hits=[]
 for pg in pages:
  t=norm(pg['text']);name=norm(x['HOLDER_NAME']);at=t.find(name)
  if at>=0:
   tail=t[at:at+400];num=str(int(x['HOLD_NUM']));hits.append(dict(page=pg['page'],name_and_amount_found=num in tail,context=tail[:240]))
 r.append(dict(**x,hits=hits,status='name_amount_text_match' if any(h['name_and_amount_found'] for h in hits) else 'unresolved'))
dump(OUT/'top_holder_crosscheck.json',r)
from collections import Counter
print(Counter(x['status'] for x in r))
for x in r:
 if x['status']=='unresolved':print(x['SECUCODE'],x['HOLDER_NAME'],x['HOLD_NUM'],x['hits'][:1])
# dates from source metadata, not inferred financial availability
from zoneinfo import ZoneInfo
receipts=json.loads((OUT/'original_receipts.json').read_text());em=json.loads((ROOT/'data/cnequity_probe_20261114/adapters/financials/RPT_LICO_FN_CPD_raw.json').read_text());dates=[]
for r in receipts:
 n=r['notice'];dt=datetime.fromtimestamp(n['announcementTime']/1000,ZoneInfo('Asia/Shanghai'));e=next(x for x in em if x['SECUCODE']==r['symbol']);dates.append(dict(symbol=r['symbol'],cninfo_timestamp=dt.isoformat(),cninfo_date=dt.date().isoformat(),pdf_path_date=n['adjunctUrl'].split('/')[1],eastmoney_date=e['NOTICE_DATE'][:10],same_date=dt.date().isoformat()==e['NOTICE_DATE'][:10]))
dump(OUT/'disclosure_date_crosscheck.json',dates);print(dates)
