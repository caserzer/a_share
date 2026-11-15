from common import *
import pandas as pd
import sys
sys.path.insert(0,str(EP32/'src'))
from observe import Release,shares_asof

def run():
 out=ROOT/'outputs/r267';out.mkdir(exist_ok=True);p=pd.read_parquet(ROOT/'outputs/r260/endpoints.parquet');r5=Release('pit_v5');r2=Release('backfill_v2');inv=r5.read('inputs/normalized/securities.parquet').set_index('security_id');old=r2.read('normalized/securities.parquet');aliaspath=CACHE/'extension_v2/products/aliases.json';aliases=json.loads(aliaspath.read_text());oldids={}
 for row in old.itertuples():
  sid=aliases.get(row.instrument)
  if sid:oldids.setdefault(sid,[]).append(row.security_id)
 parts=[]
 for i,(sid,g) in enumerate(p[p.security_id.notna()].groupby('security_id')):
  z=g.copy();part=f'normalized/prices_qfq/{sid}.parquet';z['snapshot_raw_close']=np.nan;z['signal_raw_recheck']=np.nan
  if part in r5.files:
   bars=r5.read(part,columns=['date','close','close_conflict']).set_index('date');assert not bars.index.duplicated().any();v=bars.close.where(bars.close_conflict.eq(False)&bars.close.gt(0)&np.isfinite(bars.close));z['snapshot_raw_close']=z.snapshot_date.map(v);z['signal_raw_recheck']=z.date.map(v)
  pieces=[r2.read(f'normalized/shares/{s}.parquet') for s in oldids.get(sid,[]) if f'normalized/shares/{s}.parquet' in r2.files];shares=pd.concat(pieces,ignore_index=True) if pieces else pd.DataFrame();dates=pd.DatetimeIndex(sorted(set(z.snapshot_date)|set(z.date)));ss=shares_asof(shares,dates).set_index('date');z['snapshot_shares']=z.snapshot_date.map(ss.total_shares);z['signal_shares_recheck']=z.date.map(ss.total_shares);z['snapshot_share_effective_date']=z.snapshot_date.map(ss.effective_date) if 'effective_date' in ss else pd.NaT;z['snapshot_share_known_at']=z.snapshot_date.map(ss.share_known_at)
  meta=inv.loc[sid];listed=meta.bse_listing_proxy if meta.exchange=='BJ' else meta.listing_date;z['snapshot_listed']=z.snapshot_date.ge(listed)&(pd.isna(meta.delist_date)|z.snapshot_date.lt(meta.delist_date))&~bool(meta.identity_date_conflict)
  assert np.allclose(z.loc[z.valid,'signal_raw_recheck'],z.loc[z.valid,'raw_close'],equal_nan=True)
  assert np.allclose(z.loc[z.valid,'signal_shares_recheck'],z.loc[z.valid,'total_shares'],equal_nan=True)
  parts.append(z)
  if (i+1)%500==0:print('CHECKED',i+1,flush=True)
 q=pd.concat(parts,ignore_index=True);missing=p[p.security_id.isna()];q=pd.concat([q,missing],ignore_index=True);q['snapshot_valid']=q.identity_count.eq(1)&q.snapshot_listed.eq(True)&q.snapshot_share_effective_date.le(q.snapshot_date)
 for c in ['financing','snapshot_raw_close','snapshot_shares']:q['snapshot_valid']&=q[c].gt(0)&np.isfinite(q[c])
 q['common_valid']=q.valid&q.snapshot_valid;q['snapshot_intensity']=(q.financing/(q.snapshot_raw_close*q.snapshot_shares)).where(q.snapshot_valid);q['signal_intensity']=(q.financing/(q.raw_close*q.total_shares)).where(q.valid);q['clock_dlog_intensity']=np.log(q.snapshot_intensity.where(q.common_valid)/q.signal_intensity.where(q.common_valid));q.to_parquet(out/'endpoints.parquet',index=False)
 q.groupby('date')[['valid','snapshot_valid','common_valid']].sum().to_csv(out/'date_coverage.csv');v=q[q.common_valid];summary=dict(status='PASS',endpoints=len(q),original_valid=int(q.valid.sum()),snapshot_valid=int(q.snapshot_valid.sum()),common_valid=len(v),share_changed=int(v.snapshot_shares.ne(v.total_shares).sum()),median_abs_clock_log=float(v.clock_dlog_intensity.abs().median()),p95_abs_clock_log=float(v.clock_dlog_intensity.abs().quantile(.95)),snapshot_share_known_at=int(v.snapshot_share_known_at.notna().sum()),strict_pit=False,outcomes_read=False);js(out/'summary.json',summary);js(out/'source_manifest.json',dict(price_release=str(r5.root),shares_release=str(r2.root),prices=r5.reads,shares=r2.reads,aliases_sha256=sha(aliaspath)));js(out/'receipt.json',dict(inputs={str(x):sha(x) for x in [ROOT/'outputs/r260/endpoints.parquet',ROOT/'protocols/r267.json',Path(__file__),aliaspath]},outputs={'endpoints.parquet':sha(out/'endpoints.parquet'),'source_manifest.json':sha(out/'source_manifest.json')},adoption=False));print(summary,flush=True)
if __name__=='__main__':run()
