"""Extract explicitly monthly installations, retain conflict and missing states."""
import gzip,re
import pandas as pd
from bs4 import BeautifulSoup
from common import *
def run():
 out=ROOT/'outputs/r38';ledger=json.loads((out/'download_ledger.json').read_text());rows=[]
 for x in ledger:
  if x['status']!='saved':continue
  raw=Path(x['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==x['sha256'];decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw;soup=BeautifulSoup(decoded,'html.parser');text=soup.get_text(' ',strip=True);title=soup.title.get_text() if soup.title else '';m=re.search(r'(202\d)年\s*(\d{1,2})月',title);pub=re.search(r'更新于:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',text)
  if m is None:m=re.search(r'(202\d)年\s*(\d{1,2})月[，,]?\s*(?:我国|国内|中国)动力电池',text)
  if m is None:m=re.search(r'发布(202\d)年\s*(\d{1,2})月新能源汽车电池产销量及装车量数据',text)
  if m is None:m=re.search(r'发布(?:了)?(?:我国)?\s*(202\d)\s*年\s*(\d{1,2})\s*月(?:的)?动力(?:和储能)?电池月度数据',text)
  candidates=re.findall(r'(?<![\d—–至到~～-])(\d{1,2})\s*月[，,]?\s*(?:我国|国内|中国)动力电池\s*装车量(?:共计|为)?\s*([\d.]+)\s*GWh',text,re.I)
  candidates+=re.findall(r'(?:我国|国内|中国)(\d{1,2})\s*月动力电池\s*装车量(?:共计|为)?\s*([\d.]+)\s*GWh',text,re.I)
  candidates+=re.findall(r'(?<![\d—–-])(\d{1,2})\s*月[，,]\s*(?:我国|国内|中国)动力电池装车量再次呈现较大幅度下降，共计装车([\d.]+)\s*GWh',text,re.I)
  if pub is None:pub=re.search(r'时间[：:]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})',text)
  month=f'{m[1]}-{int(m[2]):02d}' if m else None;values=sorted({float(v) for mo,v in candidates if m and int(mo)==int(m[2])});status='extracted_unverified' if len(values)==1 else 'conflict' if len(values)>1 else 'missing_or_image_only'
  rows.append(dict(url=x['url'],title=title,economic_month=month,page_updated=pub[1] if pub else None,page_timezone='Asia/Shanghai assumed from host display',retrieved_at=x['retrieved_at'],raw_sha256=x['sha256'],decoded_sha256=hashlib.sha256(decoded).hexdigest(),response_gzip=raw[:2]==b'\x1f\x8b',values=values,value_gwh=values[0] if len(values)==1 else None,status=status,quality='attributed republication; no first-release/revision certification'))
 js(out/'extractions.json',rows);grid=[]
 for month in pd.period_range('2020-01','2026-09',freq='M').astype(str):
  q=[r for r in rows if r['economic_month']==month];v={r['value_gwh'] for r in q if r['value_gwh'] is not None};grid.append(dict(month=month,documents=len(q),values=sorted(v),status='missing_document' if not q else 'conflict' if len(v)>1 else 'extracted_pending_review' if len(v)==1 else 'unparsed'))
 js(out/'month_coverage.json',grid)
 js(out/'progress.json',dict(status='active_collection_authorized',saved_documents=len(rows),bytes_read=sum(x['bytes_read'] for x in ledger),attempts=len(ledger),months_with_document=sum(x['documents']>0 for x in grid),months_extracted=sum(x['status']=='extracted_pending_review' for x in grid),authorization_ref='outputs/r37/external_data_request.json',next='continue missing-month and primary-source discovery, then crosscheck extraction and temporal availability',limitation='not yet a frozen or model-ready series'))
 print(json.dumps(json.loads((out/'progress.json').read_text()),ensure_ascii=False))
if __name__=='__main__':run()
