from collections import Counter, defaultdict
from decimal import Decimal
import statistics
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r90';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 pairs=pd.read_parquet(ROOT/'outputs/r89/paired_events.parquet');expected={(x.stock_code,x.broker,str(x.publication_date),h):x for x in pairs.itertuples() for h in ['current','next']}
 roster=pd.read_parquet(ROOT/'outputs/r85/report_roster.parquet');groups={k:set(g.infoCode) for k,g in roster.groupby(['stock_code','broker','publication_proxy_date'])}
 v=pd.read_parquet(ROOT/'data/r24_source_exclusion_overlay.parquet');values={(x.infoCode,x.fiscal_year):x.value for x in v.itertuples() if x.basis=='profit_cny'}
 actual={(x['stock_code'],x['fiscal_year']):x for x in json.loads((ROOT/'outputs/r89/annual_actuals.json').read_text())};rows=json.loads((out/'event_accuracy.json').read_text());seen=set();cg=defaultdict(list);joint=defaultdict(dict)
 for r in rows:
  key=(r['stock_code'],r['broker'],str(pd.Timestamp(r['publication_date'])),r['horizon']);assert key not in seen;seen.add(key);p=expected[key];h=r['horizon'];fy=getattr(p,'fiscal_year_'+h);assert r['fiscal_year']==fy and r['publication_year']==p.publication_date.year
  for label,date,field in [('previous',getattr(p,'previous_date_'+h),'before'),('current',p.publication_date,'after')]:
   ids=groups[p.stock_code,p.broker,date];assert set(r[label+'_report_ids'])==ids;vs=[values.get((i,fy)) for i in ids];assert all(z is not None and np.isfinite(z) for z in vs) and len(set(vs))==1 and r[field]==vs[0]
  a=actual[p.stock_code,fy];assert r['actual']==a['profit_cny'] and r['actual_status']==a['status'];common=p.actual_status_current==p.actual_status_next=='candidate';assert r['common_actual']==common
  if a['profit_cny'] is None:
   assert r['result']=='unknown' and all(r[k] is None for k in ['scale','error_before_cny','error_after_cny','change_cny','fixed_before','fixed_after','fixed_change'])
  else:
   b,c,t=map(lambda z:Decimal(str(z)),[r['before'],r['after'],r['actual']]);e0=abs(b-t);e1=abs(c-t);delta=e1-e0;s=abs(b)+abs(t)
   for k,val in [('scale',s),('error_before_cny',e0),('error_after_cny',e1),('change_cny',delta),('fixed_before',e0/s),('fixed_after',e1/s),('fixed_change',delta/s)]:assert np.isclose(r[k],float(val),rtol=1e-10,atol=1e-10 if k.startswith('fixed_') else .001),(key,k)
   assert r['result']==('improved' if delta<Decimal('-.01') else 'worsened' if delta>Decimal('.01') else 'unchanged')
  if common:cg[p.stock_code,p.publication_date.year,h].append(r);joint[key[:3]][h]=r['result']
 assert seen==set(expected)
 companies=json.loads((out/'company_years.json').read_text());assert len(companies)==len(cg);sg=defaultdict(list)
 for c in companies:
  g=cg[c['stock_code'],c['publication_year'],c['horizon']];assert c['events']==len(g)
  for k in ['fixed_before','fixed_after','fixed_change']:assert np.isclose(c[k],statistics.mean(r[k] for r in g))
  for k,label in [('improved_share','improved'),('worsened_share','worsened')]:assert np.isclose(c[k],sum(r['result']==label for r in g)/len(g))
  sg[c['publication_year'],c['horizon']].append(c)
 summary=json.loads((out/'summary.json').read_text());assert len(summary)==len(sg)
 for s in summary:
  g=sg[s['publication_year'],s['horizon']];assert s['companies']==len(g) and s['events']==sum(c['events'] for c in g)
  for k in ['fixed_before','fixed_after','fixed_change','improved_share','worsened_share']:assert np.isclose(s['mean_'+k],statistics.mean(c[k] for c in g))
 assert {(x['current'],x['next']):x['events'] for x in json.loads((out/'joint_matrix.json').read_text())}==dict(Counter((v['current'],v['next']) for v in joint.values()))
 assert json.loads((out/'coverage.json').read_text())==dict(paired_events=len(pairs),long_rows=len(rows),common_events=len(joint),unmatched_actual_pairs=len(pairs)-len(joint),common_company_years=len(cg)//2,zero_or_missing_scale_common=sum(r['fixed_change'] is None for r in rows if r['common_actual']))
 js(out/'verification.json',dict(status='PASS',events=len(rows),company_year_horizons=len(companies),scope='source forecast reconstruction, actual and maturity mapping, Decimal monetary errors, equal-company aggregation and joint matrix',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R90 VERIFIED',len(rows),len(companies))
if __name__=='__main__':run()
