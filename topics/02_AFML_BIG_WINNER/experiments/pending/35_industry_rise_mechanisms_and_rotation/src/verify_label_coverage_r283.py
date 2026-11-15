from common import *
import pandas as pd
from build_panel import delayed_labels,price_features

def run():
 o=ROOT/'outputs/r283';records=pd.read_parquet(o/'unique_labels.parquet');daily=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;checks=0
 for ident,g in daily[daily.industry_code.isin(['801737.SI','857371.SI'])&daily.era.eq('SW2021')].groupby(KEY):
  expected=[]
  for _,block in g.groupby('block'):
   block=block.sort_values('date');expected.append(delayed_labels(price_features(block),market))
  labels=pd.concat(expected).set_index('date');q=records.copy()
  for k,v in zip(KEY,ident):q=q[q[k]==v]
  for _,r in q.iterrows():
   h=int(r.horizon);ref=labels.loc[r.date];available=list(market.index[market.index>r.date]);assert r.entry==available[0];assert r.additional_sessions_needed==max(0,h+1-len(available));assert r.observed_path_sessions==min(h+1,len(available));assert r.missing_nav_on_observed_calendar==0 and r.observed_blocks==1
   value=ref[f'excess{h}'];assert pd.isna(value)==pd.isna(r.reconstructed_target)
   if pd.notna(value):assert abs(value-r.reconstructed_target)<1e-12 and ref[f'maturity{h}']==r.exit
   checks+=1
 pred=pd.read_parquet(ROOT/'outputs/r281/predictions.parquet');keys=KEY+['date','horizon'];paired=pred.merge(records[keys+['reconstructed_target']],on=keys,validate='many_to_one');assert len(paired)==1080;assert paired.target.isna().equals(paired.reconstructed_target.isna());assert np.allclose(paired.target,paired.reconstructed_target,equal_nan=True,atol=1e-12)
 receipt=json.loads((o/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(f)==h
 for f,h in receipt['outputs'].items():assert sha(o/f)==h
 js(o/'independent_verification.json',dict(status='PASS',unique_labels=checks,prediction_rows=1080,missing_rows=240,scope='Original delayed-label implementation over repaired continuous blocks; separate calendar enumeration, full1080 prediction target identity and source hashes; no search outside bounded known sources'))
 print('PASS',checks,len(paired))
if __name__=='__main__':run()
