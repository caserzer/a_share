"""Independent exact-date gap reasons and bounded-source negative-match checks."""
import pandas as pd
from common import *
from stock_raw_daily_r80 import BASE

def run():
 out=ROOT/'outputs/r176';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 old=json.loads((ROOT/'outputs/r174/receipt.json').read_text());paths={Path(p).stem:Path(p) for p in old['price_partitions']};release=next(iter(paths.values())).parents[2];meta=pd.read_parquet(release/'inputs/normalized/securities.parquet').set_index('security_id');cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);e=pd.read_parquet(out/'stock_date_gaps.parquet');windows=pd.read_parquet(out/'failed_windows.parquet');flags=['absent_date','raw_close_missing','raw_close_nonpositive','close_conflict_true','close_conflict_unknown','adjusted_close_missing','adjusted_close_nonpositive','chain_missing','chain_value_changed'];expected_events={};expected_windows=set()
 detail=pd.read_parquet(ROOT/'outputs/r174/stock_interval_audit.parquet');iv=pd.read_csv(ROOT/'outputs/r174/intervals.csv',parse_dates=['origin','entry','exit']);keys=['variant','era','level','method','origin'];d=detail.merge(iv[keys+['entry','exit']],on=keys,validate='many_to_one');bad=d[~(d.price_valid&d.chain_stable)].drop_duplicates(['security_id','entry','exit']);wl=windows.set_index(['security_id','entry','exit'])
 for sid,g in bad.groupby('security_id'):
  f=pd.read_parquet(paths[sid]).set_index('date');lookup=f.to_dict('index');listing=pd.to_datetime(meta.loc[sid,'listing_date']);delist=pd.to_datetime(meta.loc[sid,'delist_date'])
  for row in g.itertuples():
   dates=cal[(cal>=row.entry)&(cal<=row.exit)];chains=[lookup[x]['factor_chain_id'] for x in dates if x in lookup and pd.notna(lookup[x]['factor_chain_id'])];first=chains[0] if chains else None;counts={k:0 for k in flags};badcount=0
   for date in dates:
    present=date in lookup;x=lookup.get(date,{});raw=x.get('close',np.nan);adj=x.get('qfq_close',np.nan);flag=x.get('close_conflict',None);chain=x.get('factor_chain_id',None)
    vals=dict(absent_date=not present,raw_close_missing=present and pd.isna(raw),raw_close_nonpositive=present and pd.notna(raw) and raw<=0,close_conflict_true=present and pd.notna(flag) and bool(flag),close_conflict_unknown=present and pd.isna(flag),adjusted_close_missing=present and pd.isna(adj),adjusted_close_nonpositive=present and pd.notna(adj) and adj<=0,chain_missing=pd.isna(chain),chain_value_changed=pd.notna(chain) and chain!=first)
    for k,v in vals.items():counts[k]+=int(v)
    relevant=any(vals[k] for k in flags if k not in ['raw_close_missing','raw_close_nonpositive'])
    if relevant:
     badcount+=1;key=(sid,date);prior=expected_events.setdefault(key,{k:False for k in flags})
     for k,v in vals.items():prior[k]=prior[k] or bool(v)
     prior.update(position='before_first_observation' if date<f.index.min() else 'after_last_observation' if date>f.index.max() else 'internal',before_listing_proxy=bool(pd.notna(listing) and date<listing),after_delist_proxy=bool(pd.notna(delist) and date>delist))
   key=(sid,row.entry,row.exit);expected_windows.add(key);a=wl.loc[key];assert a.expected_days==len(dates) and a.bad_dates==badcount and a.observed_chain_count==len(set(chains))
   for k,v in counts.items():assert a[k]==v
 assert expected_windows==set(wl.index);el=e.set_index(['security_id','date']);assert set(el.index)==set(expected_events)
 for key,vals in expected_events.items():
  for k,v in vals.items():assert el.loc[key,k]==v
 wanted=set()
 for row in d[d.buy_state.eq(0)].itertuples():wanted.add((row.security_id,row.entry,'can_buy'))
 for row in d[d.sell_state.eq(0)].itertuples():wanted.add((row.security_id,row.exit,'can_sell'))
 requests=pd.read_parquet(out/'unknown_permission_requests.parquet');assert wanted==set(requests.itertuples(index=False,name=None))
 up=pd.read_parquet(out/'upstream_dates.parquet');absent=e[e.absent_date];assert len(up)==2*len(absent)
 for (layer,sid),g in up.groupby(['layer','security_id']):
  base=release/('inputs/normalized/prices' if layer=='immediate_input' else 'inputs/inputs/baseline/normalized/prices');p=base/f'{sid}.parquet';dates=set(pd.read_parquet(p,columns=['date']).date) if p.is_file() else set();assert g.partition_present.eq(p.is_file()).all();assert g.date_present.to_numpy().tolist()==[x in dates for x in g.date]
 aliases=json.loads((out/'observed_aliases.json').read_text());raw=json.loads((out/'raw_daily_matches.json').read_text());byday={}
 for row in raw:byday.setdefault(row['date'],[]).append(row)
 assert {(x['security_id'],pd.Timestamp(x['date'])) for x in raw}==set(absent[['security_id','date']].itertuples(index=False,name=None))
 for day,rows in byday.items():
  p=BASE/f'backfill_v2/acquired/daily/{day}.parquet';f=pd.read_parquet(p) if p.exists() else None
  for row in rows:
   aliases_code={a[:2].lower()+'.'+a[2:] for a in aliases[row['security_id']]};matches=[] if f is None else f[f.code.isin(aliases_code)].to_dict('records');expected='no_local_daily_archive' if f is None else 'matching_raw_record' if matches else 'no_record_for_observed_aliases';assert row['status']==expected and len(row['matches'])==len(matches)
 summary=json.loads((out/'summary.json').read_text());assert summary['unique_gap_stock_dates']==len(e) and summary['unique_failed_windows']==len(windows) and summary['permission_requests']==len(requests) and summary['prices_repaired']==0
 for k in flags:assert summary['reason_date_counts'][k]==int(e[k].sum())
 js(out/'verification.json',dict(status='PASS',failed_windows=len(windows),gap_stock_dates=len(e),permission_requests=len(requests),upstream_rows=len(up),raw_lookup_rows=len(raw),prices_repaired=0,adoption=False));print('PASS R176',len(windows),len(e),len(requests))
if __name__=='__main__':run()
