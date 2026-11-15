from common import ROOT,sha,js
import gzip,re,json,hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas as pd

def run():
 out=ROOT/'outputs/r274';out.mkdir(exist_ok=True)
 protocol=json.loads((ROOT/'protocols/r274.json').read_text());sources=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());old=json.loads((ROOT/'outputs/r273/candidates.json').read_text());rows=[];docs=[];excluded=[]
 for x in sources:
  path=ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html";raw=path.read_bytes();assert sha(path)==x['raw_sha256']
  soup=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');selector=protocol['selectors'].get(urlparse(x['url']).netloc);nodes=soup.select(selector) if selector else [];body=nodes[0].get_text(' ',strip=True) if len(nodes)==1 else '';normalized=re.sub(r'\s+','',body)
  (out/'bodies').mkdir(exist_ok=True);bp=out/'bodies'/f"{x['month']}.txt";bp.write_text(body)
  found=[]
  for i,sentence in enumerate(re.split(r'[。！？；\n]',body)):
   s=re.sub(r'\s+','',sentence)
   if not re.search('产量|出口|销量',s) or not re.search('GWh',s,re.I):continue
   scopes=[]
   if re.search(r'动力(?:和|及|与|、)(?:储能|其他)电池',s):scopes.append('power_plus_storage_or_other')
   if '动力电池' in s:scopes.append('power_explicit')
   if '储能电池' in s:scopes.append('storage_explicit')
   row={k:x[k] for k in ['month','raw_sha256','url','page_date','available_at']};row.update(sentence_index=i,sentence=sentence,normalized=s,quantity_types=[name for name,term in [('production','产量'),('export','出口'),('sales','销量')] if term in s],scope_markers=scopes or ['unspecified'],cumulative_marker=bool(re.search(r'累计|全年|1[-—–至到~～]\d{1,2}月|1月份?至',s)),gwh_tokens=re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*GWh',sentence,re.I),status='body_candidate_requires_semantic_review');rows.append(row);found.append(row)
  oldmonth=[r for r in old if r['month']==x['month']]
  for r in oldmonth:
   if r['normalized'] not in normalized:excluded.append(dict(month=x['month'],sentence_index=r['sentence_index'],sentence=r['sentence'],reason='whole_page_sentence_not_contained_in_body; may include boundary concatenation or unrelated content'))
  docs.append(dict(month=x['month'],raw_sha256=x['raw_sha256'],selector=selector,selector_matches=len(nodes),body_path=str(bp.relative_to(ROOT)),body_sha256=sha(bp),body_chars=len(body),whole_page_candidates=len(oldmonth),body_candidates=len(found),production_sentences=sum('production' in r['quantity_types'] for r in found),export_sentences=sum('export' in r['quantity_types'] for r in found),sales_sentences=sum('sales' in r['quantity_types'] for r in found)))
 js(out/'candidates.json',rows);js(out/'excluded_whole_page_sentences.json',excluded);pd.DataFrame(docs).to_csv(out/'document_coverage.csv',index=False)
 summary=dict(status='PASS' if all(d['selector_matches']==1 for d in docs) else 'PARTIAL',documents=len(docs),unique_bodies=sum(d['selector_matches']==1 for d in docs),body_candidate_sentences=len(rows),whole_page_sentences_not_contained=len(excluded),documents_with_production_text=sum(d['production_sentences']>0 for d in docs),documents_with_export_text=sum(d['export_sentences']>0 for d in docs),documents_with_sales_text=sum(d['sales_sentences']>0 for d in docs),model_ready_values=0,strict_pit=False,note='Text discovery only; no amount is assigned to a current-month national economic series; R273 unchanged')
 js(out/'summary.json',summary);js(out/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in ['outputs/r60/frozen_monthly_series.json','outputs/r273/candidates.json','protocols/r274.json','src/battery_body_inventory_r274.py']},sources={str((ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html").relative_to(ROOT)):x['raw_sha256'] for x in sources},outputs={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='receipt.json'},adoption=False));print(summary)
if __name__=='__main__':run()
