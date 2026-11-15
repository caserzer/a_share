"""Independent scalar reconstruction of all missing dates and classifications."""
import pandas as pd
from collections import Counter
from common import *

def run():
 out=ROOT/'outputs/r79';rec=json.loads((out/'receipt.json').read_text())
 for p,h in {**rec['reads'],**rec['price_partitions']}.items():assert sha(p)==h,p
 paths={Path(p).stem:Path(p) for p in rec['price_partitions']}
 meta=pd.read_parquet(next(p for p in rec['reads'] if p.endswith('/securities.parquet'))).set_index('security_id')
 calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
 previous=pd.DataFrame(json.loads((ROOT/'outputs/r78/gap_rows.json').read_text()));previous=previous[previous.absent_dates.gt(0)].drop_duplicates(['origin','security_id'])
 actual=json.loads((out/'missing_dates.json').read_text());bykey={(x['security_id'],x['origin'],pd.Timestamp(x['date'])):x for x in actual};assert len(bykey)==len(actual)
 iv=json.loads((out/'intervals.json').read_text());ivmap={(x['security_id'],x['origin']):x for x in iv};assert len(ivmap)==len(previous)
 seen=set();unique={};n=0
 for sid,g in previous.groupby('security_id'):
  f=pd.read_parquet(paths[sid]);dates=set(f.date);first=min(dates);last=max(dates);m=meta.loc[sid] if sid in meta.index else None
  for row in g.to_dict('records'):
   counts=Counter();pre=post=total=0
   for date in calendar:
    if date<pd.Timestamp(row['entry']) or date>pd.Timestamp(row['exit']) or date in dates:continue
    key=(sid,row['origin'],date);assert key in bykey;seen.add(key);x=bykey[key]
    position='internal'
    if date<first:position='before_first_observation'
    if date>last:position='after_last_observation'
    b=bool(m is not None and pd.notna(m.listing_date) and date<pd.Timestamp(m.listing_date))
    a=bool(m is not None and pd.notna(m.delist_date) and date>pd.Timestamp(m.delist_date))
    assert (x['position'],x['before_listing_proxy'],x['after_delist_proxy'])==(position,b,a)
    counts[position]+=1;pre+=b;post+=a;total+=1
    value=(position,b,a)
    if (sid,date) in unique:assert unique[sid,date]==value
    unique[sid,date]=value
   y=ivmap[sid,row['origin']];assert total==row['absent_dates']==y['missing_dates']
   assert pre==y['before_listing_proxy'] and post==y['after_delist_proxy']
   assert all(y['positions'][k]==counts[k] for k in y['positions']);n+=total
 assert seen==set(bykey)
 s=json.loads((out/'summary.json').read_text());assert s['stock_origins']==len(previous) and s['securities']==previous.security_id.nunique()
 assert s['interval_missing_dates']==n and s['unique_stock_dates']==len(unique)
 assert s['unique_stock_dates_by_position']==dict(Counter(v[0] for v in unique.values()))
 assert s['unique_dates_before_listing_proxy']==sum(v[1] for v in unique.values())
 assert s['unique_dates_after_delist_proxy']==sum(v[2] for v in unique.values())
 assert s['stock_origins_by_position']=={k:sum(x['positions'][k]>0 for x in iv) for k in ['before_first_observation','internal','after_last_observation']}
 upstream=json.loads((out/'upstream_receipt.json').read_text());expected_matches=set();covered=set()
 for p,h in {**upstream['reads'],**upstream['source_partitions']}.items():assert sha(p)==h,p
 for p in upstream['source_partitions']:
  sid=Path(p).stem;covered.add(sid);label='baseline_input' if '/baseline/' in p else 'immediate_input'
  f=pd.read_parquet(p)
  for date in f.date:
   if (sid,date) in unique:expected_matches.add((label,sid,str(date)))
 assert covered==set(previous.security_id)
 for x in upstream['missing_partitions']:assert not Path(x['path']).exists()
 matches=json.loads((out/'upstream_matches.json').read_text())
 assert expected_matches=={(x['layer'],x['security_id'],x['date']) for x in matches}
 assert upstream['unique_stock_dates']==len(unique)
 assert upstream['matches_by_layer']=={k:sum(v[0]==k for v in expected_matches) for k in ['immediate_input','baseline_input']}
 js(out/'verification.json',dict(status='PASS',stock_origins=len(previous),missing_date_records=n,unique_stock_dates=len(unique),scope='all missing dates independently reconstructed from frozen source; no repair',inputs_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R79 VERIFIED',len(previous),n,len(unique))
if __name__=='__main__':run()
