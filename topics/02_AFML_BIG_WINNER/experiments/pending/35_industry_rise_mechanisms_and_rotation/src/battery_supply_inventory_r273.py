from common import *
import pandas as pd
import gzip,re
from bs4 import BeautifulSoup

def run():
 out=ROOT/'outputs/r273';out.mkdir(exist_ok=True);source=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());rows=[];docs=[]
 for x in source:
  path=ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html";raw=path.read_bytes();assert sha(path)==x['raw_sha256'];decoded=gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw;soup=BeautifulSoup(decoded,'html.parser');text=soup.get_text(' ',strip=True);sentences=re.split(r'[。！？；\n]',text);found=[]
  for i,sentence in enumerate(sentences):
   s=re.sub(r'\s+','',sentence)
   if not re.search('产量|出口|销量',s) or not re.search('GWh',s,re.I):continue
   types=[name for name,term in [('production','产量'),('export','出口'),('sales','销量')] if term in s];scopes=[]
   if re.search(r'动力(?:和|及|与|、)(?:储能|其他)电池',s):scopes.append('power_plus_storage_or_other')
   if re.search(r'动力电池',s):scopes.append('power_explicit')
   if '储能电池' in s:scopes.append('storage_explicit')
   if not scopes:scopes=['unspecified']
   cumulative=bool(re.search(r'累计|全年|1[-—–至到~～]\d{1,2}月|1月份?至',s));months=re.findall(r'(?<!\d)(\d{1,2})月',s);amounts=re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*GWh',sentence,re.I)
   row=dict(month=x['month'],raw_sha256=x['raw_sha256'],path=str(path.relative_to(ROOT)),url=x['url'],page_date=x['page_date'],available_at=x['available_at'],sentence_index=i,sentence=sentence,normalized=s,quantity_types=types,scope_markers=scopes,cumulative_marker=cumulative,month_tokens=months,gwh_tokens=amounts,status='candidate_requires_semantic_review');rows.append(row);found.append(row)
  docs.append(dict(month=x['month'],raw_sha256=x['raw_sha256'],path=str(path.relative_to(ROOT)),candidates=len(found),production_sentences=sum('production' in a['quantity_types'] for a in found),export_sentences=sum('export' in a['quantity_types'] for a in found),sales_sentences=sum('sales' in a['quantity_types'] for a in found),noncumulative_production_candidates=sum('production' in a['quantity_types'] and not a['cumulative_marker'] for a in found)))
 js(out/'candidates.json',rows);pd.DataFrame(docs).to_csv(out/'document_coverage.csv',index=False);summary=dict(status='PASS',documents=len(docs),candidate_sentences=len(rows),months_with_production=sum(x['production_sentences']>0 for x in docs),months_with_export=sum(x['export_sentences']>0 for x in docs),months_with_sales=sum(x['sales_sentences']>0 for x in docs),model_ready_values=0,strict_pit=False,inventory_series_constructed=False);js(out/'summary.json',summary);js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in ['outputs/r60/frozen_monthly_series.json','protocols/r273.json','src/battery_supply_inventory_r273.py']},source_hashes={x['path']:x['raw_sha256'] for x in docs},adoption=False));print(summary)
if __name__=='__main__':run()
