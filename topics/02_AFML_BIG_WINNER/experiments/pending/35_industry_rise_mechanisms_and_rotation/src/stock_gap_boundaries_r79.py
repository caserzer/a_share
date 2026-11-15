"""Classify missing observations without repairing price or eligibility."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r79';out.mkdir(exist_ok=True)
 gap=ROOT/'outputs/r78/gap_rows.json';prior=ROOT/'outputs/r78/receipt.json'
 d=pd.DataFrame(json.loads(gap.read_text()));d=d[d.absent_dates.gt(0)].drop_duplicates(['origin','security_id'])
 receipt=json.loads(prior.read_text());paths={Path(p).stem:Path(p) for p in receipt['price_partitions']}
 release=next(iter(paths.values())).parents[2];mp=release/'inputs/normalized/securities.parquet'
 meta=pd.read_parquet(mp);assert not meta.security_id.duplicated().any();meta=meta.set_index('security_id')
 cp=CACHE/'forecast_v5/CSI_ALL.parquet';cal=pd.DatetimeIndex(pd.read_parquet(cp).index)
 rows=[];days=[];reads={}
 for sid,g in d.groupby('security_id'):
  p=paths[sid];assert sha(p)==receipt['price_partitions'][str(p)];reads[str(p)]=sha(p)
  f=pd.read_parquet(p);idx=pd.DatetimeIndex(f.date);assert idx.is_unique
  m=meta.loc[sid] if sid in meta.index else None
  listing=pd.to_datetime(m.listing_date) if m is not None else pd.NaT
  delist=pd.to_datetime(m.delist_date) if m is not None else pd.NaT
  for x in g.to_dict('records'):
   expected=cal[(cal>=pd.Timestamp(x['entry']))&(cal<=pd.Timestamp(x['exit']))];missing=expected.difference(idx);assert len(missing)==x['absent_dates']
   local=[]
   for date in missing:
    z=dict(security_id=sid,origin=x['origin'],date=date,position='before_first_observation' if date<idx.min() else 'after_last_observation' if date>idx.max() else 'internal',before_listing_proxy=bool(pd.notna(listing) and date<listing),after_delist_proxy=bool(pd.notna(delist) and date>delist))
    days.append(z);local.append(z)
   rows.append(dict(security_id=sid,origin=x['origin'],entry=x['entry'],exit=x['exit'],instruments=x['instruments'],missing_dates=len(local),positions={k:sum(z['position']==k for z in local) for k in ['before_first_observation','internal','after_last_observation']},before_listing_proxy=sum(z['before_listing_proxy'] for z in local),after_delist_proxy=sum(z['after_delist_proxy'] for z in local),first_observation=idx.min(),last_observation=idx.max(),listing_date=None if pd.isna(listing) else listing,delist_date=None if pd.isna(delist) else delist,metadata_present=m is not None,identity_date_conflict=None if m is None else m.identity_date_conflict,quality_tier=None if m is None else m.quality_tier))
 js(out/'intervals.json',rows);js(out/'missing_dates.json',days)
 u=pd.DataFrame(days).drop_duplicates(['security_id','date'])
 summary=dict(stock_origins=len(rows),securities=d.security_id.nunique(),interval_missing_dates=len(days),unique_stock_dates=len(u),unique_stock_dates_by_position=u.position.value_counts().to_dict(),stock_origins_by_position={k:sum(x['positions'][k]>0 for x in rows) for k in ['before_first_observation','internal','after_last_observation']},unique_dates_before_listing_proxy=int(u.before_listing_proxy.sum()),unique_dates_after_delist_proxy=int(u.after_delist_proxy.sum()),missing_metadata_intervals=sum(not x['metadata_present'] for x in rows),metadata_conflict_intervals=sum(x['identity_date_conflict']==True for x in rows),strict_PIT=False,prices_repaired=0)
 js(out/'summary.json',summary)
 inputs=[gap,prior,mp,cp,ROOT/'protocols/r79.json',Path(__file__)]
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},price_partitions=reads))
 print(json.dumps(clean(summary),ensure_ascii=False))
if __name__=='__main__':run()
