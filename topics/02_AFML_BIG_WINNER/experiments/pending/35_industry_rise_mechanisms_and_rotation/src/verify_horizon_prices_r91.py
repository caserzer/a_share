from collections import defaultdict
import statistics
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r91';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 prior=json.loads((ROOT/'outputs/r26/receipt.json').read_text())
 for p,h in prior['sources'].items():
  if p.endswith(('assignments.parquet','daily_industries.parquet','CSI_ALL.parquet')):assert sha(p)==h,p
 pairs=pd.read_parquet(ROOT/'outputs/r89/paired_events.parquet');mapped=pd.read_parquet(out/'mapped_pairs.parquet');keys=['stock_code','broker','publication_date'];lookup={tuple(x[k] for k in keys):x for x in pairs.to_dict('records')};assert set(map(tuple,mapped[keys].to_numpy()))==set(lookup)
 market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;calendar=pd.DatetimeIndex(market.index).sort_values();members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet');members['stock_code']=members.instrument.str[2:];membership={k:g for k,g in members.groupby(['stock_code','month'])};cg=defaultdict(list)
 for key,g in mapped.groupby(keys):
  p=lookup[key];signal=calendar[calendar.searchsorted(key[2],side='right')];month=signal.to_period('M')-1;assert g.signal_date.eq(signal).all() and g.month.eq(month).all();original=membership.get((key[0],month));ok=g[g._merge.eq('both')]
  expected=set() if original is None else set(map(tuple,original[KEY+['security_id','instrument']].to_numpy()));assert set(map(tuple,ok[KEY+['security_id','instrument']].to_numpy()))==expected
  if not expected:assert len(g)==1 and g._merge.iloc[0]=='left_only'
  for x in ok.to_dict('records'):
   assert x['revision_current']==p['revision_current'] and x['revision_next']==p['revision_next'];cg[tuple(x[k] for k in KEY)+(signal,key[2].year,x['security_id'])].append(x)
 company=pd.read_parquet(out/'company_events.parquet');assert len(company)==len(cg);eg=defaultdict(list)
 for x in company.to_dict('records'):
  key=tuple(x[k] for k in KEY)+ (x['signal_date'],x['publication_year'],x['security_id']);g=cg[key];assert x['current']==statistics.median(r['revision_current'] for r in g) and x['next']==statistics.median(r['revision_next'] for r in g) and x['brokers']==len(set(r['broker'] for r in g));eg[key[:-1]].append(x)
 daily=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet');paths={k:g.sort_values('date').reset_index(drop=True) for k,g in daily.groupby(KEY+['block'])};index={k:{d:i for i,d in enumerate(g.date)} for k,g in paths.items()};events=pd.read_parquet(out/'industry_events.parquet');assert len(events)==len(eg);dg=defaultdict(list)
 def equal(a,b):return (pd.isna(a) and pd.isna(b)) or np.isclose(a,b,rtol=1e-10,atol=1e-12)
 for x in events.to_dict('records'):
  key=tuple(x[k] for k in KEY)+(x['signal_date'],x['publication_year']);g=eg[key];assert x['companies']==len(g) and x['broker_company_pairs']==sum(r['brokers'] for r in g);assert x['current']==statistics.median(r['current'] for r in g) and x['next']==statistics.median(r['next'] for r in g)
  assert x['current_sign']==np.sign(x['current']) and x['next_sign']==np.sign(x['next']);pk=key[:3]+(x['block'],);path=paths.get(pk);i=index.get(pk,{}).get(x['signal_date'])
  for metric,a,b in [('pre20',-21,-1),('pre60',-61,-1),('reaction',-1,0),('post20',1,21),('post60',1,61)]:
   val=np.nan
   if i is not None and i+a>=0 and i+b<len(path):
    left=path.iloc[i+a];right=path.iloc[i+b];val=right.nav/left.nav-1-(market.loc[right.date]/market.loc[left.date]-1)
   assert equal(x[metric],val),(key,metric,x[metric],val)
   dg[x['era'],x['level'],x['signal_date'],metric].append(x)
 dates=json.loads((out/'date_scores.json').read_text());assert len(dates)==len(dg)
 for d in dates:
  g=dg[d['era'],d['level'],pd.Timestamp(d['signal_date']),d['metric']];q=[x for x in g if pd.notna(x[d['metric']])];assert d['rows']==len(g) and d['known']==len(q)
  for label in ['current','next','contrast']:
   vals=[(x['current_sign']-x['next_sign'] if label=='contrast' else x[label+'_sign'])*x[d['metric']] for x in q];v=statistics.mean(vals) if vals else np.nan;k=label if label=='contrast' else label+'_score';assert equal(np.nan if d[k] is None else d[k],v)
 for s in json.loads((out/'summary.json').read_text()):
  g=[d for d in dates if all(d[k]==s[k] for k in ['era','level','metric']) and (s['scope']=='pooled' or d['year']==s['year'])];assert s['dates']==len(g) and s['known_dates']==sum(d['contrast'] is not None for d in g) and s['rows']==sum(d['rows'] for d in g) and s['known']==sum(d['known'] for d in g)
  for k in ['current_score','next_score','contrast']:
   vals=[d[k] for d in g if d[k] is not None];assert equal(np.nan if s[k] is None else s[k],statistics.mean(vals) if vals else np.nan)
 c=json.loads((out/'coverage.json').read_text());assert c==dict(pairs=len(pairs),mapped_rows=len(mapped),unmapped_rows=int(mapped._merge.ne('both').sum()),company_events=len(company),industry_events=len(events),industry_opposite=int((events.current_sign*events.next_sign<0).sum()),industry_same=int(events.current_sign.eq(events.next_sign).sum()),industry_one_zero=int(((events.current_sign==0)^(events.next_sign==0)).sum()),known_post20=int(events.post20.notna().sum()),known_post60=int(events.post60.notna().sum()),excluded_on_actual=0)
 js(out/'verification.json',dict(status='PASS',events=len(events),price_windows=len(events)*5,scope='all paired original membership and calendar, company/industry medians, direct raw NAV window arithmetic, all date and annual aggregates',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R91 VERIFIED',len(events),len(events)*5)
if __name__=='__main__':run()
