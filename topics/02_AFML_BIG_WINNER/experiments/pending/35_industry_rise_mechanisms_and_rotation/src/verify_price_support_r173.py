"""Independently reconstruct source eligibility, endpoint coverage and portfolio mass."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r173';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 paths={Path(p).stem:Path(p) for p in receipt['stock_source_hashes']};s=pd.read_parquet(out/'stock_endpoint_eligibility.parquet');assert not s.duplicated(['security_id','date']).any();checked=0
 cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
 anchors={}
 for date in cal:anchors[date.to_period('M')]=date
 for sid,g in s.groupby('security_id'):
  p=paths[sid];assert sha(p)==receipt['stock_source_hashes'][str(p)];f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date');need=set(g.date)|set(g.anchor);lookup=f.reindex(sorted(need)).to_dict('index')
  for row in g.itertuples():
   assert row.anchor==anchors[row.date.to_period('M')-1]
   a=lookup[row.date];b=lookup[row.anchor];good=bool(pd.notna(a['qfq_close']) and pd.notna(b['qfq_close']) and a['qfq_close']>0 and b['qfq_close']>0 and a['close_conflict']==False and b['close_conflict']==False);chain=bool(pd.notna(a['factor_chain_id']) and pd.notna(b['factor_chain_id']) and a['factor_chain_id']==b['factor_chain_id']);eligible=good and chain
   assert row.valid_price==good and row.valid_chain==chain and row.eligible==eligible
   assert np.isclose(row.relative,a['qfq_close']/b['qfq_close']-1 if eligible else np.nan,equal_nan=True);checked+=1
 sl=s.set_index(['security_id','date']);m=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=KEY+['month','security_id','unresolved']);ml={k:g for k,g in m[m.level.eq('L2')].groupby(KEY+['month'])};ep=pd.read_csv(out/'industry_endpoints.csv',parse_dates=['date']);daily=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').set_index(KEY+['date'])
 for row in ep.to_dict('records'):
  key=(row['era'],row['level'],row['industry_code'],row['date']);g=ml.get((*key[:3],row['date'].to_period('M')-1));kind=daily.loc[key,'source_kind'] if key in daily.index else 'missing';assert row['source_kind']==kind
  if g is None:assert row['status']=='no_monthly_members';continue
  q=sl.loc[[(sid,row['date']) for sid in g.security_id]];cnt=int(q.eligible.sum());n=len(g);u=int(g.unresolved.max());den=n+u
  for name,value in dict(known=n,unresolved=u,denominator=den,priced=cnt,invalid_price=(~q.valid_price).sum(),price_valid_chain_invalid=(q.valid_price&~q.valid_chain).sum(),coverage=cnt/den,relative_mean=q.relative.mean()).items():assert np.isclose(row[name],value,equal_nan=True)
  assert row['eligible_rule']==(n>=5 and cnt/den>=.8)
  if kind=='observed':assert np.isclose(daily.loc[key,'coverage'],cnt/den) and daily.loc[key,'members']==n
 links=pd.read_parquet(out/'holding_endpoint_links.parquet');assert len(links)==receipt['holding_endpoints'];seen=set()
 for variant,n in [('top10',169),('top20',137)]:
  root=ROOT/f'outputs/r{n}/evaluation/outputs/r04';h=pd.read_parquet(root/'holdings.parquet');h=h[h.level.eq('L2')];iv=pd.read_csv(root/'intervals.csv',parse_dates=['origin','entry','exit']).set_index(['era','level','method','origin']);ll=links[links.variant.eq(variant)].set_index(['era','level','method','origin','industry_code','phase'])
  for row in h.itertuples():
   base=(row.era,row.level,row.method,row.origin);a=ml.get((row.era,row.level,row.industry_code,row.origin.to_period('M')));aa=set() if a is None else set(a.security_id)
   for phase in ['entry','exit']:
    key=(*base,row.industry_code,phase);seen.add((variant,*key));x=ll.loc[key];assert x.date==iv.loc[base,phase] and np.isclose(x.industry_weight,row.weight);b=ml.get((row.era,row.level,row.industry_code,x.date.to_period('M')-1));bb=set() if b is None else set(b.security_id);assert x.added_price_members==len(bb-aa) and x.removed_nominal_members==len(aa-bb)
 assert len(seen)==len(links)
 for row in pd.read_csv(out/'portfolio_endpoints.csv',parse_dates=['origin']).to_dict('records'):
  g=links[links.variant.eq(row['variant'])&links.era.eq(row['era'])&links.method.eq(row['method'])&links.origin.eq(row['origin'])&links.phase.eq(row['phase'])];ready=g.status.eq('observed');assert row['selected_industries']==len(g) and row['observed_industries']==ready.sum() and row['anchor_industries']==g.source_kind.eq('anchor').sum() and row['missing_industries']==g.source_kind.eq('missing').sum()
  expected=sum(w*(1-c) for w,c in zip(g.industry_weight,g.coverage)) if g.coverage.notna().all() else np.nan
  assert np.isclose(row['unpriced_nominal_mass'],expected,equal_nan=True) and np.isclose(row['observed_industry_weight'],g.loc[ready,'industry_weight'].sum());assert row['added_price_members']==g.added_price_members.sum() and row['removed_nominal_members']==g.removed_nominal_members.sum()
 js(out/'verification.json',dict(status='PASS',stock_rows_checked=checked,industry_endpoints=len(ep),holding_endpoints=len(links),source_hashes_checked=len(paths),whole_stock_path_certified=False,adoption=False))
 print('PASS R173',checked,len(ep),len(links))
if __name__=='__main__':run()
