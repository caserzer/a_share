import pandas as pd
from common import *
from margin_inventory_r44 import SOURCE

def run():
 out=ROOT/'outputs/r45';receipt=json.loads((out/'receipt.json').read_text())
 for path,h in receipt['inputs'].items():assert sha(Path(path))==h
 q=pd.read_parquet(ROOT/'data/r45_financing_intensity.parquet');assert sha(ROOT/'data/r45_financing_intensity.parquet')==receipt['feature_sha256']
 assert not q.duplicated(KEY+['date']).any();assert q.ratio_known.le(q.margin_known).all() and q.ratio_known.le(q.cap_known).all();assert (q.ready==q.financing_intensity.notna()).all()
 d=pd.read_parquet(SOURCE/'normalized_detail.parquet');cols=['month']+KEY+['security_id','instrument'];m=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)])
 s=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=['date','security_id','raw_close','total_shares','share_effective_date','listed']).set_index(['date','security_id'])
 samples=pd.concat([g.iloc[np.linspace(0,len(g)-1,20,dtype=int)] for _,g in q.groupby(['era','level'])]);checks=[]
 for x in samples.to_dict('records'):
  members=m[m.month.eq(x['date'].to_period('M')-1)]
  for k in KEY:members=members[members[k].eq(x[k])]
  records=d[d.date.eq(x['date'])].set_index('instrument');values=[]
  for member in members.itertuples():
   if member.instrument not in records.index or (x['date'],member.security_id) not in s.index:continue
   stock=s.loc[(x['date'],member.security_id)]
   if not stock.listed or not(stock.raw_close>0 and stock.total_shares>0 and stock.share_effective_date<=x['date']):continue
   value=records.loc[member.instrument,'financing']/(stock.raw_close*stock.total_shares)
   if np.isfinite(value):values.append(value)
  assert len(values)==x['ratio_known'] and len(members)==x['members']
  median=float(np.median(values)) if values else np.nan
  assert np.isclose(median,x['raw_median'],equal_nan=True,rtol=1e-12,atol=1e-15)
  ready=len(values)>=5 and len(values)/len(members)>=.8;assert ready==x['ready']
  if ready:assert np.isclose(x['financing_intensity'],median,rtol=1e-12,atol=1e-15)
  checks.append(dict(date=str(x['date']),era=x['era'],level=x['level'],industry_code=x['industry_code'],members=len(members),known=len(values),ready=ready))
 js(out/'verification.json',dict(status='PASS',direct_checks=len(checks),checks=checks,scope='source hashes, denominator arithmetic, missing and coverage; not predictive validity'))
 print('R45 VERIFIED',len(checks),'direct company-ratio medians')

if __name__=='__main__':run()
