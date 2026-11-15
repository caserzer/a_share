"""Exact L2 failed-date ledger and bounded read-only upstream lookup."""
import pandas as pd
from common import *
from stock_raw_daily_r80 import decode,BASE

def run():
 out=ROOT/'outputs/r176';ap=ROOT/'outputs/r174/stock_interval_audit.parquet';ip=ROOT/'outputs/r174/intervals.csv';rp=ROOT/'outputs/r174/receipt.json';bp=CACHE/'forecast_v5/CSI_ALL.parquet';r=json.loads(rp.read_text());paths={Path(p).stem:Path(p) for p in r['price_partitions']};release=next(iter(paths.values())).parents[2];metap=release/'inputs/normalized/securities.parquet';meta=pd.read_parquet(metap).set_index('security_id');calendar=pd.DatetimeIndex(pd.read_parquet(bp).index);keys=['variant','era','level','method','origin'];d=pd.read_parquet(ap).merge(pd.read_csv(ip,parse_dates=['origin','entry','exit'])[keys+['entry','exit']],on=keys,validate='many_to_one');bad=d[~(d.price_valid&d.chain_stable)].drop_duplicates(['security_id','entry','exit']);events=[];windows=[];aliases={};reads={str(p):sha(p) for p in [ap,ip,rp,bp,metap,ROOT/'protocols/r176.json',ROOT/'src/stock_raw_daily_r80.py',Path(__file__)]}
 flags=['absent_date','raw_close_missing','raw_close_nonpositive','close_conflict_true','close_conflict_unknown','adjusted_close_missing','adjusted_close_nonpositive','chain_missing','chain_value_changed']
 for sid,g in bad.groupby('security_id'):
  path=paths[sid];assert sha(path)==r['price_partitions'][str(path)];reads[str(path)]=sha(path);f=pd.read_parquet(path).set_index('date');aliases[sid]=sorted(f.instrument.dropna().unique());listing=pd.to_datetime(meta.loc[sid,'listing_date']) if sid in meta.index else pd.NaT;delist=pd.to_datetime(meta.loc[sid,'delist_date']) if sid in meta.index else pd.NaT
  for x in g.itertuples():
   dates=calendar[(calendar>=x.entry)&(calendar<=x.exit)];q=f.reindex(dates);present=pd.Series(dates.isin(f.index),index=dates);raw=pd.to_numeric(q.close);adj=pd.to_numeric(q.qfq_close);chain=q.factor_chain_id;known=chain.dropna();first=known.iloc[0] if len(known) else None
   z=pd.DataFrame(dict(absent_date=~present,raw_close_missing=present&raw.isna(),raw_close_nonpositive=present&raw.le(0),close_conflict_true=present&q.close_conflict.eq(True),close_conflict_unknown=present&q.close_conflict.isna(),adjusted_close_missing=present&adj.isna(),adjusted_close_nonpositive=present&adj.le(0),chain_missing=chain.isna(),chain_value_changed=chain.notna()&chain.ne(first)))
   relevant=z[['absent_date','close_conflict_true','close_conflict_unknown','adjusted_close_missing','adjusted_close_nonpositive','chain_missing','chain_value_changed']].any(axis=1);assert relevant.any()
   windows.append(dict(security_id=sid,entry=x.entry,exit=x.exit,expected_days=len(dates),bad_dates=int(relevant.sum()),observed_chain_count=int(chain.nunique()),**{c:int(z[c].sum()) for c in flags}))
   for date,v in z[relevant].iterrows():events.append(dict(security_id=sid,date=date,position='before_first_observation' if date<f.index.min() else 'after_last_observation' if date>f.index.max() else 'internal',before_listing_proxy=bool(pd.notna(listing) and date<listing),after_delist_proxy=bool(pd.notna(delist) and date>delist),**v.to_dict()))
 event=pd.DataFrame(events).groupby(['security_id','date'],as_index=False).agg({**{c:'max' for c in flags},'position':'first','before_listing_proxy':'max','after_delist_proxy':'max'});event.to_parquet(out/'stock_date_gaps.parquet',index=False);pd.DataFrame(windows).to_parquet(out/'failed_windows.parquet',index=False);js(out/'observed_aliases.json',aliases)
 permission=pd.concat([d[d.buy_state.eq(0)][['security_id','entry']].rename(columns={'entry':'date'}).assign(field='can_buy'),d[d.sell_state.eq(0)][['security_id','exit']].rename(columns={'exit':'date'}).assign(field='can_sell')],ignore_index=True).drop_duplicates().sort_values(['security_id','date','field']);permission.to_parquet(out/'unknown_permission_requests.parquet',index=False)
 absent=event[event.absent_date];upstream=[]
 for layer,base in [('immediate_input',release/'inputs/normalized/prices'),('baseline_input',release/'inputs/inputs/baseline/normalized/prices')]:
  for sid,g in absent.groupby('security_id'):
   p=base/f'{sid}.parquet';found=set()
   if p.is_file():reads[str(p)]=sha(p);f=pd.read_parquet(p,columns=['date']);found=set(pd.to_datetime(f.date))
   for date in g.date:upstream.append(dict(layer=layer,security_id=sid,date=date,partition_present=p.is_file(),date_present=date in found))
 pd.DataFrame(upstream).to_parquet(out/'upstream_dates.parquet',index=False);rawrows=[];rawsources=[]
 for date,g in absent.groupby('date'):
  day=str(date.date());p=BASE/f'backfill_v2/acquired/daily/{day}.parquet';raw=None
  if p.is_file():
   receiptp=Path(str(p)+'.receipt.json');rr=json.loads(receiptp.read_text());assert sha(p)==rr['parquet_sha256'];reads[str(p)]=sha(p);reads[str(receiptp)]=sha(receiptp);frames=[]
   for digest in rr['response_sha256']:
    src=BASE/'raw/sha256'/digest[:2]/digest;assert sha(src)==digest;reads[str(src)]=digest;frames.append(decode(src))
   raw=pd.concat(frames,ignore_index=True);pd.testing.assert_frame_equal(raw,pd.read_parquet(p),check_dtype=False);assert raw.date.eq(day).all() and raw.adjustflag.eq('3').all();raw['instrument']=raw.code.str[:2].str.upper()+raw.code.str[3:];rawsources.append(dict(date=day,rows=len(raw),observed_at=rr['observed_at'],response_sha256=rr['response_sha256']))
  for x in g.itertuples():
   matches=[] if raw is None else raw[raw.instrument.isin(aliases[x.security_id])].to_dict('records');rawrows.append(dict(security_id=x.security_id,date=day,status='no_local_daily_archive' if raw is None else 'matching_raw_record' if matches else 'no_record_for_observed_aliases',matches=matches))
 js(out/'raw_daily_matches.json',rawrows);js(out/'raw_daily_sources.json',rawsources);summary=dict(failed_position_rows=int((~(d.price_valid&d.chain_stable)).sum()),unique_failed_windows=len(bad),affected_securities=bad.security_id.nunique(),unique_gap_stock_dates=len(event),reason_date_counts={c:int(event[c].sum()) for c in flags},absent_position_counts=absent.position.value_counts().to_dict(),absent_before_listing=int(absent.before_listing_proxy.sum()),absent_after_delist=int(absent.after_delist_proxy.sum()),permission_requests=len(permission),upstream_matches=pd.DataFrame(upstream).groupby('layer').date_present.sum().to_dict(),raw_status_counts=pd.Series([x['status'] for x in rawrows]).value_counts().to_dict(),raw_archived_dates=len(rawsources),prices_repaired=0,adoption=False)
 js(out/'summary.json',summary);js(out/'receipt.json',dict(status='PASS',reads=reads,scope='bounded local source audit; exact gaps not repaired'));print(json.dumps(clean(summary),ensure_ascii=False),flush=True)
if __name__=='__main__':run()
