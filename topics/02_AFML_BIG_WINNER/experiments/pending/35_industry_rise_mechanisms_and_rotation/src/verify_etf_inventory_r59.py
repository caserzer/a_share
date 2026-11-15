import re
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r59';rec=json.loads((out/'receipt.json').read_text())
 for s in rec['sources']:assert sha(s['path'])==s['sha256']
 for p,h in rec['outputs'].items():assert sha(out/p)==h
 assert sha(rec['code_source']['path'])==rec['code_source']['sha256']
 d=pd.read_parquet(out/'report_references.parquet');checked=0;states={}
 for x in d.to_dict('records'):
  if x['report'] not in states:
   text=Path(x['report']).read_text();start=text.index('LONG_OPPORTUNITY_STATE_BEGIN')+len('LONG_OPPORTUNITY_STATE_BEGIN');end=text.index('LONG_OPPORTUNITY_STATE_END',start);chunk=text[start:end];payload=chunk[chunk.index('{'):chunk.rindex('}')+1];states[x['report']]=json.loads(payload)
  obj=states[x['report']]
  for field,index in re.findall(r'\.([^\.\[\]]+)|\[(\d+)\]',x['json_path'][1:]):obj=obj[field] if field else obj[int(index)]
  assert obj['instrument_code']==x['instrument_code'] and obj['fund_share_as_of']==x['fund_share_as_of'] and obj['fund_share_units']==x['fund_share_units'];checked+=1
 obs=json.loads((out/'observations.json').read_text());assert len(obs)==len(d.groupby(['instrument_code','fund_share_as_of']))
 for x in obs:
  g=d[d.instrument_code.eq(x['instrument_code'])&d.fund_share_as_of.eq(x['share_date'])];assert x['references']==len(g) and x['values']==sorted(g.fund_share_units.unique())
 assert sum(x['references'] for x in obs)==len(d)
 js(out/'verification.json',dict(status='PASS',source_files=len(rec['sources']),direct_JSON_paths=checked,unique_observations=len(obs),deduplication_checked=True,scope='report transcription and deduplication, not raw API authenticity, first-publication time or full-universe coverage'))
 print('R59 VERIFIED',checked,'references',len(obs),'observations')
if __name__=='__main__':run()
