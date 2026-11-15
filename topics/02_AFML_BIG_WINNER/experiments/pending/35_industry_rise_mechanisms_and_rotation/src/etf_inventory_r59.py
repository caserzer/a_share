import re
import pandas as pd
from common import *
BASE=Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports/long_opportunities/2026')
CODE=Path('/home/xiaolv/code/golden_loop/a_share_market_radar/production/long_opportunity_report_v2.py')
def walk(value,path='$'):
 if isinstance(value,dict):
  if 'fund_share_units' in value and value.get('instrument_type')=='ETF':yield path,value
  for k,v in value.items():yield from walk(v,path+'.'+k)
 elif isinstance(value,list):
  for i,v in enumerate(value):yield from walk(v,f'{path}[{i}]')
def extract(p):
 text=p.read_text();m=re.search(r'<!-- LONG_OPPORTUNITY_STATE_BEGIN\s*(.*?)\s*LONG_OPPORTUNITY_STATE_END -->',text,re.S)
 if not m:return None,[]
 payload=m[1].strip()
 if payload.startswith('-->') and payload.endswith('<!--'):payload=payload[3:-4].strip()
 state=json.loads(payload);rows=[]
 for path,x in walk(state):
  row={k:x.get(k) for k in ['instrument_code','instrument_name','instrument_type','fund_share_units','fund_share_as_of','industry_code','industry_name','index_code','index_name','last_close','fund_size_yuan','fund_size_as_of']}
  row.update(report=str(p),report_sha256=sha(p),json_path=path,target_date=state.get('target_date'),publication_time=None,raw_api_receipt_available=False);rows.append(row)
 return state,rows

def run():
 out=ROOT/'outputs/r59';out.mkdir(exist_ok=True);refs=[];sources=[]
 for p in sorted(BASE.glob('*.md')):
  if not re.fullmatch(r'\d{8}\.md',p.name):continue
  state,rows=extract(p);sources.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,has_state=state is not None,rows=len(rows)));refs+=rows
 d=pd.DataFrame(refs);d.to_parquet(out/'report_references.parquet',index=False)
 known=d[d.fund_share_units.notna()&d.fund_share_as_of.notna()&d.instrument_code.notna()].copy();obs=[]
 for (code,date),g in known.groupby(['instrument_code','fund_share_as_of']):
  values=sorted(g.fund_share_units.unique());obs.append(dict(instrument_code=code,share_date=date,share_units=values[0] if len(values)==1 else None,values=values,conflict=len(values)>1,references=len(g),reports=g.report.nunique(),report_targets=sorted(g.target_date.dropna().unique()),industry_codes=sorted(g.industry_code.dropna().unique()),index_codes=sorted(g.index_code.dropna().unique()),raw_api_receipt_available=False,publication_time=None))
 js(out/'observations.json',obs);by=[]
 for code,g in pd.DataFrame(obs).groupby('instrument_code'):
  by.append(dict(instrument_code=code,dates=len(g),first=g.share_date.min(),last=g.share_date.max(),months=len({str(x)[:6] for x in g.share_date}),conflicts=int(g.conflict.sum())))
 js(out/'coverage.json',by)
 summary=dict(report_files=len(sources),reports_with_state=sum(x['has_state'] for x in sources),references=len(d),known_references=len(known),unique_observations=len(obs),conflicts=sum(x['conflict'] for x in obs),instruments=len(by),share_after_report_rows=int((known.fund_share_as_of.astype(str)>known.target_date.astype(str)).sum()),strict_pit=False,full_ETF_universe=False,shenwan_mapping_certified=False,runtime_directory_present=Path('/home/xiaolv/.openclaw/a-share-market-radar-runtime').exists())
 js(out/'summary.json',summary);js(out/'receipt.json',dict(sources=sources,code_source=dict(path=str(CODE),sha256=sha(CODE)),protocol_sha256=sha(ROOT/'protocols/r59.json'),code_sha256=sha(__file__),outputs={x:sha(out/x) for x in ['report_references.parquet','observations.json','coverage.json','summary.json']}));print(json.dumps(summary,ensure_ascii=False));print(by)
if __name__=='__main__':run()
