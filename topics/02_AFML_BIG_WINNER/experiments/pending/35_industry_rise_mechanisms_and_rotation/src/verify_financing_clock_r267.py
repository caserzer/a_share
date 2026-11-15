from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r267';q=pd.read_parquet(out/'endpoints.parquet');manifest=json.loads((out/'source_manifest.json').read_text());price=Path(manifest['price_release']);share=Path(manifest['shares_release']);aliases=json.loads((CACHE/'extension_v2/products/aliases.json').read_text());old=pd.read_parquet(share/'normalized/securities.parquet');inv=pd.read_parquet(price/'inputs/normalized/securities.parquet').set_index('security_id');oldids={};checked=0
 for row in old.itertuples():
  sid=aliases.get(row.instrument)
  if sid:oldids.setdefault(sid,[]).append(row.security_id)
 for prefix,key in [(price,'prices'),(share,'shares')]:
  for name,digest in manifest[key].items():assert sha(prefix/name)==digest
 for sid,g in q[q.security_id.notna()].groupby('security_id'):
  part=price/f'normalized/prices_qfq/{sid}.parquet';bars=pd.read_parquet(part,columns=['date','close','close_conflict']).set_index('date') if part.exists() else None;pieces=[pd.read_parquet(share/f'normalized/shares/{s}.parquet') for s in oldids.get(sid,[]) if (share/f'normalized/shares/{s}.parquet').exists()];events=[]
  if pieces:
   raw=pd.concat(pieces,ignore_index=True)
   for date,z in raw.groupby('effective_date'):
    vals=z.total_shares.dropna().unique();valid=len(vals)==1 and vals[0]>0 and not (z.total_shares_conflict.any() if 'total_shares_conflict' in z else False);events.append((pd.Timestamp(date),float(vals[0]) if valid else np.nan))
  events.sort();edates=pd.DatetimeIndex([x[0] for x in events]);meta=inv.loc[sid];start=meta.bse_listing_proxy if meta.exchange=='BJ' else meta.listing_date
  for row in g.itertuples():
   val=np.nan
   if bars is not None and row.snapshot_date in bars.index:
    b=bars.loc[row.snapshot_date]
    if b.close_conflict==False and b.close>0 and np.isfinite(b.close):val=float(b.close)
   ix=edates.searchsorted(row.snapshot_date,side='right')-1;s=events[ix][1] if ix>=0 else np.nan;effective=events[ix][0] if ix>=0 else pd.NaT;listed=row.snapshot_date>=start and (pd.isna(meta.delist_date) or row.snapshot_date<meta.delist_date) and not bool(meta.identity_date_conflict)
   assert np.isclose(val,row.snapshot_raw_close,equal_nan=True) and np.isclose(s,row.snapshot_shares,equal_nan=True);assert bool(row.snapshot_listed)==listed;assert (pd.isna(effective) and pd.isna(row.snapshot_share_effective_date)) or effective==row.snapshot_share_effective_date
   valid=row.identity_count==1 and listed and ix>=0 and np.isfinite(val) and val>0 and np.isfinite(s) and s>0 and row.financing>0 and np.isfinite(row.financing);assert row.snapshot_valid==valid;checked+=1
 v=q[q.common_valid];other=np.log(v.raw_close/v.snapshot_raw_close)+np.log(v.total_shares/v.snapshot_shares);assert np.allclose(other,v.clock_dlog_intensity,atol=1e-12);assert q.common_valid.eq(q.valid&q.snapshot_valid).all();cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index;assert np.all(cal.get_indexer(q.date)-cal.get_indexer(q.snapshot_date)==2)
 js(out/'independent_verification.json',dict(status='PASS',mapped_endpoint_checks=checked,clock_identity_checks=len(v),source_hashes=len(manifest['prices'])+len(manifest['shares']),scope='Exact-date raw closes, independent latest effective share event lookup, listing, validity, two-session clocks and log-ratio identity; first publication still unverified',adoption=False));print('VERIFIED',checked,len(v))
if __name__=='__main__':run()
