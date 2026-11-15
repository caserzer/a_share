from common import ROOT,sha,js
import json,gzip,re,csv
from bs4 import BeautifulSoup

def run():
 out=ROOT/'outputs/r274';receipt=json.loads((out/'receipt.json').read_text());checks=0
 for group in ['inputs','sources']:
  for p,h in receipt[group].items():assert sha(ROOT/p)==h;checks+=1
 for p,h in receipt['outputs'].items():assert sha(out/p)==h;checks+=1
 docs=list(csv.DictReader((out/'document_coverage.csv').open()));rows=json.loads((out/'candidates.json').read_text());excluded=json.loads((out/'excluded_whole_page_sentences.json').read_text());count=0
 for d in docs:
  raw=(ROOT/'data/r38_battery_originals'/f"{d['raw_sha256']}.html").read_bytes();s=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');nodes=s.select(d['selector']);assert len(nodes)==1
  body=nodes[0].get_text(' ',strip=True);assert body==(ROOT/d['body_path']).read_text();parts=re.split('[。！？；\n]',body)
  expected=[(i,t) for i,t in enumerate(parts) if any(k in t for k in ['产量','出口','销量']) and 'gwh' in t.lower()];actual=[r for r in rows if r['month']==d['month']];assert [(r['sentence_index'],r['sentence']) for r in actual]==expected
  for r in actual:
   assert r['gwh_tokens']==re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*GWh',r['sentence'],flags=re.I);count+=1
  original=[r for r in json.loads((ROOT/'outputs/r273/candidates.json').read_text()) if r['month']==d['month']]
  removed=[r['sentence_index'] for r in original if r['normalized'] not in re.sub(r'\s+','',body)]
  assert removed==[r['sentence_index'] for r in excluded if r['month']==d['month']]
 # Concrete sidebar exclusion: old NE-time document must not acquire later August production.
 oldbody=(out/'bodies/2023-08.txt').read_text();assert '73.3GWh' in re.sub(r'\s+','',oldbody);assert '237.0GWh' not in re.sub(r'\s+','',oldbody)
 result=dict(status='PASS',hash_checks=checks,independently_reparsed_bodies=len(docs),candidate_sentences=count,exclusion_records=len(excluded),scope='Hash integrity, unique selected DOM, complete sentence/token reconstruction, exact exclusion identity; not economic-series or publisher-truth certification',model_ready_values=0)
 js(out/'independent_verification.json',result);print(result)
if __name__=='__main__':run()
